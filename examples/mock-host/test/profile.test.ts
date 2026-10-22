// @vitest-environment happy-dom
/**
 * T02–T03 / SPEC §6.3 — the shipped example must supply its capability providers.
 * Replace iframe delivery and record config with a forwarding host spy.
 * Requests still run through the actual host kernel.
 * Real cross-origin browser wiring is verified separately.
 */
import { createHost } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import type { Window as HappyDomWindow } from 'happy-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createLinkedTransports,
  flush,
} from '../../../packages/host/test/helpers/memory-transport';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));
vi.mock('@moonpool/host', async (importOriginal) => {
  const original = await importOriginal<typeof import('@moonpool/host')>();
  return { ...original, createHost: vi.fn(original.createHost) };
});

let bridge: ReturnType<typeof createLinkedTransports>;
const browserWindow = window as unknown as HappyDomWindow;
const navigation = browserWindow.happyDOM.settings.navigation;
const originalChildNavigation = navigation.disableChildFrameNavigation;

beforeEach(() => {
  vi.resetModules();
  vi.mocked(createHost).mockClear();
  document.body.innerHTML = '<div id="app"></div>';
  // Tests exercise the entry point without making a network request for its iframe.
  navigation.disableChildFrameNavigation = true;
  bridge = createLinkedTransports();
  vi.mocked(createIframeTransport).mockReturnValue(bridge.b);
});

afterEach(() => {
  bridge.a.close();
  bridge.b.close();
  document.body.replaceChildren();
  navigation.disableChildFrameNavigation = originalChildNavigation;
});

describe('mock-host capability providers', () => {
  it('serves the example profile over the bridge while granting only profile', async () => {
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
    bridge.a.send({ jsonrpc: '2.0', id: 2, method: 'profile.get' });
    await flush();

    expect(replies).toEqual([
      expect.objectContaining({
        id: 1,
        result: expect.objectContaining({ grantedScopes: ['profile'] }),
      }),
      { jsonrpc: '2.0', id: 2, result: { displayName: 'Moonpool Explorer' } },
    ]);
  });

  it('installs usable storage while keeping the default bridge limited to profile', async () => {
    const replies: JsonValue[] = [];
    bridge.a.onMessage((message) => replies.push(message));
    await import('../src/main');
    const storage = vi.mocked(createHost).mock.calls[0]?.[0].capabilities?.storage;
    expect(storage).toBeDefined();
    if (storage === undefined) {
      throw new Error('mock-host must install its development storage provider');
    }
    await storage.set('com.example.hello', 'theme', 'dark');
    await expect(storage.get('com.example.hello', 'theme')).resolves.toBe('dark');

    bridge.a.send({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: PROTOCOL_VERSION },
    });
    await flush();
    bridge.a.send({ jsonrpc: '2.0', id: 2, method: 'storage.get', params: { key: 'theme' } });
    await flush();

    expect(replies).toEqual([
      expect.objectContaining({ result: expect.objectContaining({ grantedScopes: ['profile'] }) }),
      expect.objectContaining({
        id: 2,
        error: expect.objectContaining({ code: ERROR_CODES.PERMISSION_DENIED }),
      }),
    ]);
  });
});
