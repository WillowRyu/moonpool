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
import { cleanupWrappers, loadMockHost, mountCurrentWrapper } from './helpers/mock-host';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));
vi.mock('@moonpool/host', async (importOriginal) => {
  const original = await importOriginal<typeof import('@moonpool/host')>();
  return { ...original, createHost: vi.fn(original.createHost) };
});

let bridge: ReturnType<typeof createLinkedTransports>;
const extraBridges: Array<ReturnType<typeof createLinkedTransports>> = [];
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

afterEach(async () => {
  await cleanupWrappers();
  bridge.a.close();
  bridge.b.close();
  for (const extra of extraBridges.splice(0)) {
    extra.a.close();
    extra.b.close();
  }
  document.body.replaceChildren();
  navigation.disableChildFrameNavigation = originalChildNavigation;
});

describe('mock-host capability providers', () => {
  it('serves the example profile over the bridge while granting only profile', async () => {
    const replies: JsonValue[] = [];
    bridge.a.onMessage((message) => replies.push(message));

    await loadMockHost();
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
    await loadMockHost();
    const storage = vi.mocked(createHost).mock.calls[0]?.[0].capabilities?.storage;
    expect(storage).toBeDefined();
    if (storage === undefined) {
      throw new Error('mock-host must install its development storage provider');
    }
    // The wrapper facade cannot bypass this Portal's grants, even from host tests.
    await expect(storage.set('com.example.hello', 'theme', 'dark')).rejects.toThrow('not granted');

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

  it('replaces the Portal for each host configuration and keeps storage across connections', async () => {
    await loadMockHost();
    const storage = vi.mocked(createHost).mock.calls[0]?.[0].capabilities?.storage;
    if (storage === undefined) {
      throw new Error('storage must be installed');
    }
    const originalFrame = document.querySelector('iframe');
    const closeOriginal = vi.spyOn(bridge.b, 'close');
    const allowed = createLinkedTransports();
    extraBridges.push(allowed);
    const allowedReplies: JsonValue[] = [];
    allowed.a.onMessage((message) => allowedReplies.push(message));
    vi.mocked(createIframeTransport).mockReturnValueOnce(allowed.b);

    const allowButton = document.querySelector<HTMLButtonElement>('#with-storage');
    expect(allowButton).not.toBeNull();
    allowButton?.click();
    await mountCurrentWrapper();

    expect(closeOriginal).toHaveBeenCalledOnce();
    expect(originalFrame?.isConnected).toBe(false);
    expect(document.querySelector('iframe')).not.toBe(originalFrame);
    allowed.a.send({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: PROTOCOL_VERSION },
    });
    await flush();
    allowed.a.send({
      jsonrpc: '2.0',
      id: 2,
      method: 'storage.set',
      params: { key: 'settings', value: 'kept' },
    });
    await flush(40);
    allowed.a.send({ jsonrpc: '2.0', id: 3, method: 'storage.get', params: { key: 'settings' } });
    await flush();
    expect(allowedReplies).toEqual([
      expect.objectContaining({
        result: expect.objectContaining({ grantedScopes: ['profile', 'storage'] }),
      }),
      { jsonrpc: '2.0', id: 2, result: {} },
      { jsonrpc: '2.0', id: 3, result: { value: 'kept' } },
    ]);

    const allowedFrame = document.querySelector('iframe');
    const closeAllowed = vi.spyOn(allowed.b, 'close');
    const denied = createLinkedTransports();
    extraBridges.push(denied);
    const deniedReplies: JsonValue[] = [];
    denied.a.onMessage((message) => deniedReplies.push(message));
    vi.mocked(createIframeTransport).mockReturnValueOnce(denied.b);
    document.querySelector<HTMLButtonElement>('#profile-only')?.click();
    await mountCurrentWrapper();

    expect(closeAllowed).toHaveBeenCalledOnce();
    expect(allowedFrame?.isConnected).toBe(false);
    denied.a.send({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: PROTOCOL_VERSION },
    });
    await flush();
    denied.a.send({ jsonrpc: '2.0', id: 2, method: 'storage.get', params: { key: 'settings' } });
    await flush();
    expect(deniedReplies).toEqual([
      expect.objectContaining({ result: expect.objectContaining({ grantedScopes: ['profile'] }) }),
      expect.objectContaining({
        error: expect.objectContaining({ code: ERROR_CODES.PERMISSION_DENIED }),
      }),
    ]);
    await expect(storage.get('com.example.hello', 'settings')).rejects.toThrow('inactive');
  });
});
