// @vitest-environment happy-dom
/** T14 — actual host entry wiring binds dismissal to its captured Portal. */
import { createHost } from '@moonpool/host';
import type { JsonValue } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { cleanupWrappers, loadMockHost, mountCurrentWrapper } from './helpers/mock-host';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));
vi.mock('@moonpool/host', async (importOriginal) => {
  const original = await importOriginal<typeof import('@moonpool/host')>();
  return {
    ...original,
    createHost: vi.fn((config: Parameters<typeof original.createHost>[0]) => {
      const host = original.createHost(config);
      return { ...host, connect: vi.fn(host.connect) };
    }),
  };
});

const bridges: Array<ReturnType<typeof createLinkedTransports>> = [];
let originalNavigation: boolean;

beforeEach(() => {
  vi.resetModules();
  vi.mocked(createHost).mockClear();
  document.body.innerHTML = '<div id="app"></div>';
  originalNavigation = setChildNavigationDisabled(true);
});

function setChildNavigationDisabled(disabled: boolean): boolean {
  // Inspect the test setting instead of asserting the entire window type.
  if (!('happyDOM' in window)) {
    throw new Error('missing happyDOM');
  }
  const api = window.happyDOM;
  if (typeof api !== 'object' || api === null || !('settings' in api)) {
    throw new Error('missing settings');
  }
  const settings = api.settings;
  if (typeof settings !== 'object' || settings === null || !('navigation' in settings)) {
    throw new Error('missing navigation');
  }
  const navigation = settings.navigation;
  if (
    typeof navigation !== 'object' ||
    navigation === null ||
    !('disableChildFrameNavigation' in navigation) ||
    typeof navigation.disableChildFrameNavigation !== 'boolean'
  ) {
    throw new Error('missing frame navigation setting');
  }
  const previous = navigation.disableChildFrameNavigation;
  navigation.disableChildFrameNavigation = disabled;
  return previous;
}

afterEach(async () => {
  await cleanupWrappers();
  for (const bridge of bridges.splice(0)) {
    bridge.a.close();
    bridge.b.close();
  }
  document.body.replaceChildren();
  setChildNavigationDisabled(originalNavigation);
  vi.restoreAllMocks();
});

function bridge() {
  const pair = createLinkedTransports();
  bridges.push(pair);
  vi.mocked(createIframeTransport).mockReturnValueOnce(pair.b);
  const replies: JsonValue[] = [];
  pair.a.onMessage((message) => replies.push(message));
  return { ...pair, replies };
}

async function initialize(pair: ReturnType<typeof bridge>) {
  pair.a.send({
    jsonrpc: '2.0',
    id: 1,
    method: 'portal.initialize',
    params: { protocolVersion: '0.1' },
  });
  await flush();
}

function closeHook(index = 0) {
  const host = vi.mocked(createHost).mock.results[index]?.value;
  const hook = host && vi.mocked(host.connect).mock.calls[0]?.[1]?.onCloseRequested;
  if (hook === undefined) {
    throw new Error('host must bind a close handler');
  }
  return hook;
}

describe('T14 — browser embedder dismissal', () => {
  it('acknowledges the close request and removes only the current iframe', async () => {
    const pair = bridge();
    const close = vi.spyOn(pair.b, 'close');
    await loadMockHost();
    await initialize(pair);
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'portal.close', params: { reason: 'finished' } });
    await flush();
    expect(pair.replies.at(-1)).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(close).toHaveBeenCalledOnce();
    expect(document.querySelector('iframe')).toBeNull();
    expect(document.querySelector('#configuration')?.textContent).toContain('Portal dismissed');
    expect(document.querySelector('#configuration')?.textContent).toContain('finished');
    expect(document.querySelector('#profile-only')?.getAttribute('aria-pressed')).toBe('false');
    expect(document.querySelector('#with-storage')?.getAttribute('aria-pressed')).toBe('false');
  });

  it('keeps the Portal open for uninitialized and invalid requests', async () => {
    const pair = bridge();
    await loadMockHost();
    const iframe = document.querySelector('iframe');
    pair.a.send({ jsonrpc: '2.0', id: 1, method: 'portal.close' });
    await flush();
    expect(pair.replies.at(-1)).toMatchObject({ error: { code: -32005 } });
    await initialize(pair);
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'portal.close', params: { reason: 42 } });
    await flush();
    expect(pair.replies.at(-1)).toMatchObject({ error: { code: -32602 } });
    expect(document.querySelector('iframe')).toBe(iframe);
  });

  it('makes repeated dismissal harmless and preserves storage when starting again', async () => {
    bridge();
    await loadMockHost();
    const allowed = bridge();
    document.querySelector<HTMLButtonElement>('#with-storage')?.click();
    await mountCurrentWrapper();
    const close = vi.spyOn(allowed.b, 'close');
    await initialize(allowed);
    allowed.a.send({
      jsonrpc: '2.0',
      id: 2,
      method: 'storage.set',
      params: { key: 'settings', value: 'kept' },
    });
    await flush(40);
    const dismiss = closeHook(1);
    await dismiss();
    await dismiss();
    expect(close).toHaveBeenCalledOnce();
    const next = bridge();
    document.querySelector<HTMLButtonElement>('#with-storage')?.click();
    await mountCurrentWrapper();
    await initialize(next);
    next.a.send({ jsonrpc: '2.0', id: 2, method: 'storage.get', params: { key: 'settings' } });
    await flush();
    expect(next.replies.at(-1)).toEqual({ jsonrpc: '2.0', id: 2, result: { value: 'kept' } });
    expect(close).toHaveBeenCalledOnce();
  });

  it('does not let an old handler dismiss a replacement Portal', async () => {
    bridge();
    await loadMockHost();
    const oldDismiss = closeHook();
    const replacement = bridge();
    const closeReplacement = vi.spyOn(replacement.b, 'close');
    document.querySelector<HTMLButtonElement>('#with-storage')?.click();
    await mountCurrentWrapper();
    const iframe = document.querySelector('iframe');
    await oldDismiss('late');
    expect(document.querySelector('iframe')).toBe(iframe);
    expect(closeReplacement).not.toHaveBeenCalled();
    expect(document.querySelector('#configuration')?.textContent).toBe(
      'Configuration: profile + storage',
    );
    await initialize(replacement);
    expect(replacement.replies.at(-1)).toMatchObject({
      result: { grantedScopes: ['profile', 'storage'] },
    });
  });

  it('renders a supplied reason as text', async () => {
    const pair = bridge();
    await loadMockHost();
    await initialize(pair);
    const reason = '<img src="x" onerror="alert(1)">';
    pair.a.send({ jsonrpc: '2.0', id: 2, method: 'portal.close', params: { reason } });
    await flush();
    expect(document.querySelector('#configuration')?.textContent).toContain(reason);
    expect(document.querySelector('#configuration img')).toBeNull();
  });
});
