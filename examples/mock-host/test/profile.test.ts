// @vitest-environment happy-dom
/**
 * T02 / SPEC §6.3 — the shipped example must supply a real profile provider.
 * Only the iframe transport is replaced; requests run through the actual host.
 * Real cross-origin browser wiring is verified separately.
 */
import { type JsonValue, PROTOCOL_VERSION } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import type { Window as HappyDomWindow } from 'happy-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createLinkedTransports,
  flush,
} from '../../../packages/host/test/helpers/memory-transport';

vi.mock('@moonpool/transport-iframe', () => ({ createIframeTransport: vi.fn() }));

let bridge: ReturnType<typeof createLinkedTransports>;
const browserWindow = window as unknown as HappyDomWindow;
const navigation = browserWindow.happyDOM.settings.navigation;
const originalChildNavigation = navigation.disableChildFrameNavigation;

beforeEach(() => {
  vi.resetModules();
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

describe('T02 — mock-host profile provider', () => {
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
});
