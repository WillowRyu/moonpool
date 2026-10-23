// @vitest-environment happy-dom
/** T07 / SPEC §5, §7, §8.1 — admit host-owned configuration before creating a Portal. */
import { createHost, parseManifest } from '@moonpool/host';
import { type JsonValue, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createLinkedTransports,
  flush,
} from '../../../packages/host/test/helpers/memory-transport';
import exampleText from '../../hello-miniapp/moonpool.json?raw';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));
vi.mock('@moonpool/host', async (importOriginal) => {
  const original = await importOriginal<typeof import('@moonpool/host')>();
  return {
    ...original,
    createHost: vi.fn(original.createHost),
    parseManifest: vi.fn(original.parseManifest),
  };
});

const EXAMPLE = parseManifest(exampleText);
const navigation: unknown = Reflect.get(window, 'happyDOM')?.settings?.navigation;
if (
  typeof navigation !== 'object' ||
  navigation === null ||
  !('disableChildFrameNavigation' in navigation) ||
  typeof navigation.disableChildFrameNavigation !== 'boolean'
) {
  throw new Error('manifest entry-point tests require happy-dom navigation settings');
}
const originalChildNavigation = navigation.disableChildFrameNavigation;
let bridge: ReturnType<typeof createLinkedTransports>;

function useManifest(source: string): void {
  vi.doMock('../../hello-miniapp/moonpool.json?raw', () => ({ default: source }));
}

beforeEach(() => {
  vi.resetModules();
  vi.doUnmock('../../hello-miniapp/moonpool.json?raw');
  vi.mocked(createHost).mockClear();
  vi.mocked(parseManifest).mockClear();
  vi.mocked(createIframeTransport).mockReset();
  document.body.innerHTML = '<div id="app"></div>';
  navigation.disableChildFrameNavigation = true;
  bridge = createLinkedTransports();
  vi.mocked(createIframeTransport).mockReturnValue(bridge.b);
});

afterEach(() => {
  bridge.a.close();
  bridge.b.close();
  vi.restoreAllMocks();
  vi.doUnmock('../../hello-miniapp/moonpool.json?raw');
  document.body.replaceChildren();
  navigation.disableChildFrameNavigation = originalChildNavigation;
});

describe('T07 — actual host-owned moonpool.json', () => {
  it('passes the shipped file text to the real parser before creating the iframe', async () => {
    await import('../src/main');

    expect(parseManifest).toHaveBeenCalledExactlyOnceWith(exampleText);
    expect(createHost).toHaveBeenCalledWith(expect.objectContaining({ manifest: EXAMPLE }));
    expect(document.querySelector('iframe')?.src).toBe('http://localhost:5174/index.html');
  });

  it('uses the file version and declared permissions in the real handshake', async () => {
    useManifest(JSON.stringify({ ...EXAMPLE, version: '2.3.4', permissions: ['storage'] }));
    const replies: JsonValue[] = [];
    bridge.a.onMessage((message) => replies.push(message));

    await import('../src/main');
    bridge.a.send({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: PROTOCOL_VERSION },
    });
    await flush();

    expect(replies).toEqual([
      expect.objectContaining({
        result: expect.objectContaining({
          miniApp: { id: EXAMPLE.id, version: '2.3.4' },
          grantedScopes: [],
        }),
      }),
    ]);
  });

  it.each([
    { entry: 'pages/start.html', url: 'http://localhost:5174/pages/start.html' },
    { entry: './index.html', url: 'http://localhost:5174/index.html' },
    { entry: 'pages/../index.html', url: 'http://localhost:5174/index.html' },
    {
      entry: '시작/hello world.html',
      url: 'http://localhost:5174/%EC%8B%9C%EC%9E%91/hello%20world.html',
    },
  ])('resolves $entry from the pinned package-root origin', async ({ entry, url }) => {
    useManifest(JSON.stringify({ ...EXAMPLE, entry }));

    await import('../src/main');

    const iframe = document.querySelector('iframe');
    expect(iframe?.src).toBe(url);
    expect(iframe?.title).toBe(EXAMPLE.id);
    expect(createIframeTransport).toHaveBeenCalledWith(
      expect.objectContaining({ peerOrigin: 'http://localhost:5174' }),
    );
    expect(vi.mocked(createHost).mock.calls[0]?.[0].manifest.entry).toBe(entry);
  });

  it('stops when a valid app id has no host-pinned origin', async () => {
    useManifest(JSON.stringify({ ...EXAMPLE, id: 'com.example.other' }));

    await expect(import('../src/main')).rejects.toThrow('no development origin pinned');

    expect(document.querySelector('iframe')).toBeNull();
    expect(createIframeTransport).not.toHaveBeenCalled();
    expect(createHost).not.toHaveBeenCalled();
  });

  it.each([
    { source: '{', field: 'json' },
    { source: JSON.stringify({ ...EXAMPLE, manifestVersion: 2 }), field: 'manifestVersion' },
    { source: JSON.stringify({ ...EXAMPLE, id: 'invalid' }), field: 'id' },
    { source: JSON.stringify({ ...EXAMPLE, entry: '../index.html' }), field: 'entry' },
    { source: JSON.stringify({ ...EXAMPLE, entry: 'https://other.example/' }), field: 'entry' },
    { source: JSON.stringify({ ...EXAMPLE, permissions: ['camera'] }), field: 'permissions' },
  ])('rejects invalid $field before creating any Portal connection', async ({ source, field }) => {
    useManifest(source);
    const createElement = vi.spyOn(document, 'createElement');

    await expect(import('../src/main')).rejects.toMatchObject({ name: 'ManifestError', field });

    expect(createElement.mock.calls.some(([tag]) => tag === 'iframe')).toBe(false);
    expect(createIframeTransport).not.toHaveBeenCalled();
    expect(createHost).not.toHaveBeenCalled();
  });

  it('attaches the receiver in the same task as inserting the iframe', async () => {
    const listen = vi.spyOn(bridge.b, 'onMessage');
    const replace = Element.prototype.replaceChildren;
    let attachedBeforeNextMicrotask = false;
    vi.spyOn(Element.prototype, 'replaceChildren').mockImplementation(function (
      this: Element,
      ...nodes: (Node | string)[]
    ) {
      replace.apply(this, nodes);
      if (nodes.some((node) => node instanceof HTMLIFrameElement)) {
        queueMicrotask(() => {
          attachedBeforeNextMicrotask = listen.mock.calls.length > 0;
          bridge.a.send({
            jsonrpc: '2.0',
            id: 1,
            method: 'portal.initialize',
            params: { protocolVersion: PROTOCOL_VERSION },
          });
        });
      }
    });
    const replies: JsonValue[] = [];
    bridge.a.onMessage((message) => replies.push(message));

    await import('../src/main');
    await flush();

    expect(attachedBeforeNextMicrotask).toBe(true);
    expect(replies).toEqual([
      expect.objectContaining({ result: expect.objectContaining({ grantedScopes: ['profile'] }) }),
    ]);
  });
});
