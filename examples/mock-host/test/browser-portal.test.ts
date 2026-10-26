// @vitest-environment happy-dom
/** SPEC §8.1.1 — host-selected bindings, independent disposal, retained storage. */
import type { StorageProvider } from '@moonpool/host';
import type { MiniAppManifest } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type BrowserHost, createBrowserHost } from '../src/browser-portal';
import { decodeJson, encodeJson } from '../src/json-boundary';
import { createMemoryStorageProvider } from '../src/memory-storage';
import { disableFrameNavigation } from './helpers/dom';

const APP_A = 'com.example.hello';
const APP_B = 'com.example.second';
const manifest = (id = APP_A): MiniAppManifest => ({
  manifestVersion: 1,
  id,
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
});
const origins = new Map([
  [APP_A, 'http://localhost:5174'],
  [APP_B, 'http://localhost:5175'],
]);
const hosts: BrowserHost[] = [];
let restoreNavigation: () => void;
beforeEach(() => {
  restoreNavigation = disableFrameNavigation();
  document.body.innerHTML = '<div id="portals"></div>';
});
afterEach(async () => {
  vi.restoreAllMocks();
  for (const host of hosts.splice(0)) {
    await host.close();
  }
  document.body.replaceChildren();
  restoreNavigation();
});

function setup(storage: StorageProvider = createMemoryStorageProvider()) {
  const host = createBrowserHost({
    origins,
    localWindow: window,
    hostInfo: { name: 'test-host', version: '0.1.0', platform: 'browser' },
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: {
      storage,
      profile: {
        async get() {
          return { displayName: 'Public user' };
        },
      },
    },
  });
  hosts.push(host);
  return { host, storage };
}

async function open(host: BrowserHost, id = APP_A, scopes = ['profile', 'storage']) {
  const container = document.querySelector<HTMLElement>('#portals');
  if (container === null) {
    throw new Error('missing portals');
  }
  const onClosed = vi.fn();
  const portal = host.open({ container, manifest: manifest(id), grantedScopes: scopes, onClosed });
  const child = portal.frame.contentWindow;
  const doc = portal.frame.contentDocument;
  if (child === null || doc === null) {
    throw new Error('missing wrapper');
  }
  // Synthetic URL/Document inputs test registry decisions, not real navigation enforcement.
  const url = vi.spyOn(child.location, 'href', 'get').mockReturnValue(portal.frame.src);
  const controls = {
    notifyLifecycle: vi.fn(async (_text: string) => {}),
    notifyEnvironmentChanged: vi.fn(async (_text: string) => {}),
    dispose: vi.fn(async () => {}),
  };
  const gateway = await host.bootstrap(child, doc, controls);
  return { portal, child, doc, url, controls, gateway, onClosed };
}

describe('host-owned browser Portal', () => {
  it('pins metadata and gateway identity from the registry', async () => {
    const { host } = setup();
    const a = await open(host);
    expect(decodeJson(await a.gateway.configuration())).toMatchObject({
      manifest: { id: APP_A },
      origin: origins.get(APP_A),
      grantedScopes: ['profile', 'storage'],
    });
    expect(a.portal.frame.src).toContain('/portal-wrapper.html?app=com.example.hello&instance=');
    expect(await a.gateway.profile()).toBe('{"displayName":"Public user"}');
  });

  it('rejects unknown app ids before creating a frame', () => {
    const { host } = setup();
    expect(() =>
      host.open({
        container: document.body,
        manifest: manifest('com.example.unknown'),
        grantedScopes: [],
      }),
    ).toThrow('no development origin pinned');
    expect(document.querySelector('iframe')).toBeNull();
  });

  it('partitions different apps and shares data between instances of one app', async () => {
    const { host } = setup();
    const a = await open(host);
    const a2 = await open(host);
    const b = await open(host, APP_B);
    await a.gateway.set('same', encodeJson({ nested: [false, 0, null] }));
    await b.gateway.set('same', encodeJson('B'));
    expect(decodeJson(await a2.gateway.get('same'))).toEqual({ nested: [false, 0, null] });
    expect(decodeJson(await b.gateway.get('same'))).toBe('B');
    await a2.gateway.delete('same');
    expect(decodeJson(await a.gateway.get('same'))).toBeNull();
    expect(decodeJson(await b.gateway.get('same'))).toBe('B');
  });

  it('retains app data through close/recreation and does not reuse old handles', async () => {
    const { host } = setup();
    const a = await open(host);
    await a.gateway.set('saved', encodeJson('kept'));
    await a.portal.close();
    const fresh = await open(host);
    expect(decodeJson(await fresh.gateway.get('saved'))).toBe('kept');
    await expect(a.gateway.get('saved')).rejects.toThrow('inactive');
    await expect(a.portal.notifyEnvironmentChanged({ locale: 'ko' })).rejects.toThrow('inactive');
    await expect(host.bootstrap(a.child, a.doc, a.controls)).rejects.toThrow();
    expect(fresh.portal.frame.isConnected).toBe(true);
  });

  it('keeps B live while A is closed, including pending provider work', async () => {
    let finish: ((value: string) => void) | undefined;
    const provider = createMemoryStorageProvider();
    const get = vi.spyOn(provider, 'get').mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { host } = setup(provider);
    const a = await open(host);
    const b = await open(host, APP_B);
    const pending = b.gateway.get('pending');
    await a.portal.close();
    finish?.('B result');
    expect(decodeJson(await pending)).toBe('B result');
    expect(b.portal.frame.isConnected).toBe(true);
    expect(b.controls.dispose).not.toHaveBeenCalled();
    expect(get).toHaveBeenCalledExactlyOnceWith(APP_B, 'pending');
  });

  it('rejects new denied storage calls before provider access', async () => {
    const { host, storage } = setup();
    const get = vi.spyOn(storage, 'get');
    const denied = await open(host, APP_A, ['profile']);
    await expect(denied.gateway.get('x')).rejects.toThrow('not granted');
    expect(get).not.toHaveBeenCalled();
    expect(decodeJson(await denied.gateway.profile())).toEqual({ displayName: 'Public user' });
  });

  it('rejects invalid provider-bound data before writes, without repair', async () => {
    const { host, storage } = setup();
    const set = vi.spyOn(storage, 'set');
    const a = await open(host);
    for (const text of ['{', 'null', '{"x":1e999}']) {
      await expect(a.gateway.set('x', text)).rejects.toThrow(TypeError);
    }
    expect(set).not.toHaveBeenCalled();
  });

  it('does not return a late provider result to a disposed instance', async () => {
    let finish: ((value: string) => void) | undefined;
    const provider = createMemoryStorageProvider();
    vi.spyOn(provider, 'get').mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const { host } = setup(provider);
    const a = await open(host);
    const pending = a.gateway.get('x');
    const rejected = expect(pending).rejects.toThrow('inactive');
    await a.portal.close();
    finish?.('old value');
    await rejected;
  });

  it('passes notification data as text and validates before invoking controls', async () => {
    const { host } = setup();
    const a = await open(host);
    await a.portal.notifyEnvironmentChanged({ colorScheme: 'dark', locale: 'ko-KR' });
    expect(a.controls.notifyEnvironmentChanged).toHaveBeenCalledExactlyOnceWith(
      '{"colorScheme":"dark","locale":"ko-KR"}',
    );
    await a.portal.notifyLifecycle('paused');
    expect(a.controls.notifyLifecycle).toHaveBeenCalledExactlyOnceWith('"paused"');
    await expect(a.portal.notifyEnvironmentChanged(new Date())).rejects.toThrow(TypeError);
    expect(a.controls.notifyEnvironmentChanged).toHaveBeenCalledTimes(1);
  });

  it('rejects a wrong source, wrong Document, or repeated bootstrap', async () => {
    const { host } = setup();
    const a = await open(host);
    await expect(host.bootstrap(window, document, a.controls)).rejects.toThrow();
    await expect(host.bootstrap(a.child, a.doc, a.controls)).rejects.toThrow();
    const b = await open(host, APP_B);
    await expect(host.bootstrap(b.child, a.doc, b.controls)).rejects.toThrow();
    expect(b.portal.frame.isConnected).toBe(false);
    expect(a.portal.frame.isConnected).toBe(true);
  });

  it.each(['different URL', 'same URL new Document'])(
    'revokes an unauthorized wrapper replacement: %s',
    async (scenario) => {
      const { host } = setup();
      const a = await open(host);
      const b = await open(host, APP_B);
      if (scenario === 'different URL') {
        a.url.mockReturnValue(`${window.location.origin}/portal-wrapper.html?app=${APP_B}`);
      } else {
        vi.spyOn(a.portal.frame, 'contentDocument', 'get').mockReturnValue(
          document.implementation.createHTMLDocument('replacement'),
        );
      }
      await expect(a.gateway.get('x')).rejects.toThrow('inactive');
      expect(a.portal.frame.isConnected).toBe(false);
      expect(a.controls.dispose).toHaveBeenCalledOnce();
      expect(b.portal.frame.isConnected).toBe(true);
    },
  );

  it('does all cleanup despite a wrapper failure, and stays terminal', async () => {
    const { host } = setup();
    const a = await open(host);
    a.controls.dispose.mockRejectedValueOnce(new Error('wrapper cleanup failed'));
    const remove = vi.spyOn(a.portal.frame, 'remove');
    await expect(a.portal.close()).rejects.toThrow('wrapper cleanup failed');
    expect(remove).toHaveBeenCalledOnce();
    expect(a.portal.frame.isConnected).toBe(false);
    expect(a.onClosed).toHaveBeenCalledOnce();
    await expect(a.gateway.get('x')).rejects.toThrow('inactive');
    await a.portal.close();
    expect(a.controls.dispose).toHaveBeenCalledOnce();
  });

  it('reacts to an outer wrapper load without waiting for a provider call', async () => {
    const { host } = setup();
    const a = await open(host);
    const b = await open(host, APP_B);
    vi.spyOn(a.portal.frame, 'contentDocument', 'get').mockReturnValue(
      document.implementation.createHTMLDocument('new'),
    );
    a.portal.frame.dispatchEvent(new Event('load'));
    expect(a.portal.frame.isConnected).toBe(false);
    expect(b.portal.frame.isConnected).toBe(true);
    await expect(a.gateway.configuration()).rejects.toThrow('inactive');
  });

  it('rejects non-JSON provider results before returning boundary text', async () => {
    const provider = createMemoryStorageProvider();
    vi.spyOn(provider, 'get').mockResolvedValue(Infinity);
    const { host } = setup(provider);
    const a = await open(host);
    await expect(a.gateway.get('x')).rejects.toThrow(TypeError);
    expect(a.portal.frame.isConnected).toBe(true);
    expect(decodeJson(await a.gateway.profile())).toEqual({ displayName: 'Public user' });
  });

  it('releases an inserted wrapper if platform insertion subsequently fails', () => {
    const { host } = setup();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const append = container.appendChild.bind(container);
    const failure = new Error('insertion failed');
    vi.spyOn(container, 'appendChild').mockImplementationOnce((node) => {
      append(node);
      throw failure;
    });
    const remove = vi.spyOn(HTMLIFrameElement.prototype, 'removeEventListener');
    const onClosed = vi.fn();
    expect(() =>
      host.open({ container, manifest: manifest(), grantedScopes: [], onClosed }),
    ).toThrow(failure);
    expect(container.querySelector('iframe')).toBeNull();
    expect(remove).toHaveBeenCalledWith('load', expect.any(Function));
    // A construction failure never publishes a live Portal to its caller.
    expect(onClosed).not.toHaveBeenCalled();
  });
});
