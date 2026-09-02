/**
 * SPEC §9.3 — scope enforcement at dispatch, and the first scoped method.
 *
 * "The host MUST check the granted scope immediately before invoking a
 * handler, not at registration time and not in the client." Until this step
 * nothing consulted `grantedScopes`: the handshake computed it and nothing
 * read it, because no method had a scope. `profile.get` (§6.3) is the first,
 * and it is here mostly to give the gate something to guard.
 *
 * Two decisions these tests pin (HANDOFF.md, 2026-09-02):
 *
 * 1. A call into a namespace the connection was not granted answers
 *    `-32000 PERMISSION_DENIED`, and the scope check runs BEFORE the method
 *    lookup. An ungranted namespace therefore answers -32000 for every name,
 *    real or not — it cannot be enumerated — while inside a granted namespace
 *    an unknown method is still `-32601`. `portal.*` needs no scope (§6.2),
 *    and that exemption is an exact match on the namespace, never a prefix.
 * 2. Capability handlers are injected. The kernel defines the provider
 *    interfaces; the embedding host supplies implementations through
 *    `HostConfig.capabilities`, one slot per §6.3 namespace. The kernel
 *    answers `-32001 CAPABILITY_UNAVAILABLE` when a slot is absent and
 *    `-32603 INTERNAL_ERROR` when a provider fails — without repeating the
 *    provider's own error text over the bridge, and re-throwing that error
 *    host-side on an empty stack so it is not swallowed (decision 3, the
 *    same shape as the transport's handler isolation in E2.1).
 *
 * Out of scope here: `storage.*` and the per-mini-app namespacing of its keys
 * (next step), and `-32602` for malformed `params` (the step after).
 *
 * Several tests below pass before the gate exists, because today every
 * non-portal method is -32601 and no provider is ever reached. They are kept
 * on purpose and say so: each fails if the gate lands in the wrong place —
 * above the -32005 gate, above `portal.*`, or after the provider call.
 */
import { createHost, type HostConfig } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type MiniAppManifest } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

const HELLO_MANIFEST: MiniAppManifest = {
  manifestVersion: 1,
  id: 'com.example.hello',
  name: 'Hello',
  version: '1.0.0',
  entry: 'index.html',
  protocolVersion: '0.1',
  permissions: ['profile', 'storage'],
};

/** What this host knows about its user. Fixed here; a real host reads its own session. */
const PROFILE = { displayName: 'Siwon Ryu', avatarUrl: 'https://example.com/siwon.png' };

/** Shape of a JSON-RPC response, loose on purpose — for assertions only. */
interface RpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: Record<string, JsonValue>;
  error?: { code: number; message: string; data?: JsonValue };
}

/** Boots a host on one end of an in-memory bridge; the test plays the mini app on the other. */
function setup(overrides: Partial<HostConfig> = {}) {
  const { a: miniAppEnd, b: hostEnd } = createLinkedTransports();

  const host = createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: HELLO_MANIFEST,
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    ...overrides,
  });
  host.connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));

  return {
    received,
    send: (message: JsonValue) => miniAppEnd.send(message),
  };
}

const request = (
  id: number,
  method: string,
  params: Record<string, JsonValue> = {},
): JsonValue => ({
  jsonrpc: '2.0',
  id,
  method,
  params,
});

const initialize = (id: number, protocolVersion = '0.1'): JsonValue => {
  return request(id, 'portal.initialize', { protocolVersion });
};

/** Completes the handshake as id 1, then sends `method` as id 2 and returns its reply. */
async function callAfterHandshake(
  bridge: ReturnType<typeof setup>,
  method: string,
  params?: Record<string, JsonValue>,
): Promise<RpcResponse | undefined> {
  bridge.send(initialize(1));
  await flush();
  bridge.send(request(2, method, params));
  await flush();
  return bridge.received[1];
}

describe('SPEC §9.3 — scope enforcement at dispatch (-32000)', () => {
  it('denies profile.get with -32000 when the connection was not granted profile', async () => {
    const bridge = setup({
      grantedScopes: [],
      capabilities: { profile: { get: async () => PROFILE } },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({
        code: ERROR_CODES.PERMISSION_DENIED,
        message: expect.any(String),
      }),
    });
  });

  it('never reaches the provider on a denied call', async () => {
    // Passes vacuously today: nothing dispatches to a provider yet. It is the
    // test that fails if the gate is placed AFTER the provider call — §9.3's
    // "immediately before invoking a handler" is exactly this line.
    const get = vi.fn(async () => PROFILE);
    const bridge = setup({ grantedScopes: [], capabilities: { profile: { get } } });

    await callAfterHandshake(bridge, 'profile.get');

    expect(get).not.toHaveBeenCalled();
  });

  it('treats a host grant the manifest never declared as no grant at all', async () => {
    // §5: grantedScopes is the INTERSECTION of manifest permissions and host
    // grants, and "the authoritative permission set for the connection". A
    // gate that reads the host's grant list directly would let this call
    // through; a gate that reads what the handshake computed denies it.
    const bridge = setup({
      manifest: { ...HELLO_MANIFEST, permissions: [] },
      grantedScopes: ['profile'],
      capabilities: { profile: { get: async () => PROFILE } },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply?.error?.code).toBe(ERROR_CODES.PERMISSION_DENIED);
  });

  it('checks the scope before the method lookup: an ungranted namespace answers -32000 even for a method that does not exist', async () => {
    // Decision 1's ordering. Answered -32601 here, the difference between
    // storage.get and storage.doesNotExist would let a mini app without the
    // storage scope enumerate which storage methods exist. Answered -32000
    // for both, it learns nothing it was not already told at the handshake.
    const bridge = setup({ grantedScopes: [] });

    const reply = await callAfterHandshake(bridge, 'storage.doesNotExist');

    expect(reply?.error?.code).toBe(ERROR_CODES.PERMISSION_DENIED);
  });

  it('answers -32601 for an unknown method inside a granted scope', async () => {
    // The scope is granted, so "this method does not exist" reveals nothing
    // the mini app is not entitled to. Passes today (every non-portal method
    // is -32601); fails if the gate starts denying granted scopes, or if
    // "provider present" (-32001) is checked before "method known" (-32601).
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, 'profile.doesNotExist');

    expect(reply?.error?.code).toBe(ERROR_CODES.METHOD_NOT_FOUND);
  });

  it('still serves portal.ping with no scopes granted at all', async () => {
    // §6.2: the portal namespace needs no scope. Passes today; fails if the
    // gate is placed above the core methods.
    const bridge = setup({ grantedScopes: [] });

    const reply = await callAfterHandshake(bridge, 'portal.ping');

    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: { pong: true } });
  });

  it('does not mistake portalx.hack for a core method', async () => {
    // The exemption is an exact match on the namespace. A prefix test
    // (`startsWith('portal')`) would route this past the gate — the same
    // shape as the origin check's `startsWith` trap in transport-iframe.
    const bridge = setup({ grantedScopes: [] });

    const reply = await callAfterHandshake(bridge, 'portalx.hack');

    expect(reply?.error?.code).toBe(ERROR_CODES.PERMISSION_DENIED);
  });

  it('answers -32005, not -32000, for a scoped method sent before the handshake', async () => {
    // grantedScopes is established BY the handshake; before it there is
    // nothing to check against. Passes today; fails if the gate is placed
    // above the -32005 gate.
    const bridge = setup({ grantedScopes: [] });

    bridge.send(request(1, 'profile.get'));
    await flush();

    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
  });
});

describe('SPEC §6.3 — profile.get', () => {
  it('returns the profile the host provider supplies when the scope is granted', async () => {
    const bridge = setup({
      grantedScopes: ['profile'],
      capabilities: { profile: { get: async () => PROFILE } },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: PROFILE });
  });

  it('forwards only the §6.3 fields, even when the provider hands back more', async () => {
    // The realistic provider is `get: async () => session.user`, and a user
    // record carries far more than a display name. Structural typing lets
    // that object satisfy ProfileProvider (it is not a fresh literal, so no
    // excess-property check), which makes the kernel the only place the
    // extra fields can be stopped. §9.4 in miniature: allowlist on the way out.
    const record = { displayName: 'Siwon Ryu', email: 'siwon@example.com', sessionToken: 'tok' };
    const bridge = setup({
      grantedScopes: ['profile'],
      capabilities: { profile: { get: async () => record } },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply?.result).toStrictEqual({ displayName: 'Siwon Ryu' });
  });

  it('omits avatarUrl rather than sending it as undefined', async () => {
    // `avatarUrl?: string` accepts `undefined` at the provider, but JSON has
    // no undefined. A JSON-serialising transport would drop the key and a
    // structured-clone transport (postMessage) would deliver it — the same
    // provider would look different through different transports unless the
    // kernel normalises here.
    const bridge = setup({
      grantedScopes: ['profile'],
      capabilities: {
        profile: { get: async () => ({ displayName: 'Siwon Ryu', avatarUrl: undefined }) },
      },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply?.result).toStrictEqual({ displayName: 'Siwon Ryu' });
  });

  it('answers -32001 when this host has no profile provider', async () => {
    // §4.4: "Method exists but is unavailable on this host/platform". The
    // scope is granted and the method is real; what is missing is an
    // implementation on this particular host.
    const bridge = setup({ grantedScopes: ['profile'] });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({
        code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
        message: expect.any(String),
      }),
    });
  });
});

describe('SPEC §6.3 — profile.get when the provider fails', () => {
  // The kernel replies -32603 to the mini app AND re-throws the provider's
  // error on an empty stack, so the host sees it as an uncaught error
  // (window.onerror, an error collector) instead of nothing at all. Same
  // decision as the transport's handler isolation (E2.1): isolate without
  // swallowing. queueMicrotask is faked so the re-throw can be asserted;
  // `useRealTimers` then discards whatever is still parked, which is also
  // what keeps a parked throw from failing the run as an unhandled error.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['queueMicrotask'] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const FAILING_PROVIDERS: Array<[label: string, get: () => Promise<typeof PROFILE>]> = [
    [
      'rejects',
      async () => {
        throw new Error('db down at /var/lib/host/secret.db');
      },
    ],
    [
      'throws synchronously',
      () => {
        throw new Error('db down at /var/lib/host/secret.db');
      },
    ],
  ];

  it.each(FAILING_PROVIDERS)(
    'answers -32603, exactly once, when the provider %s',
    async (_label, get) => {
      // §4: every id-bearing request gets exactly one reply. A provider
      // failure must not become silence (the client would sit out its §4.5
      // timeout) or an unhandled rejection. Both shapes are covered because
      // `await` inside `try` catches both, while `.then()` chaining catches
      // only the first.
      const bridge = setup({ grantedScopes: ['profile'], capabilities: { profile: { get } } });

      const reply = await callAfterHandshake(bridge, 'profile.get');

      expect(bridge.received).toHaveLength(2);
      expect(reply?.error?.code).toBe(ERROR_CODES.INTERNAL_ERROR);
    },
  );

  it('does not repeat the provider error text over the bridge', async () => {
    // §4.4: error.data MUST NOT carry host internals, and the message is no
    // different. A provider's Error.message can name file paths, hosts, or
    // queries; the mini app gets a fixed sentence instead.
    const bridge = setup({
      grantedScopes: ['profile'],
      capabilities: {
        profile: {
          get: async () => {
            throw new Error('db down at /var/lib/host/secret.db');
          },
        },
      },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');

    expect(reply?.error?.code).toBe(ERROR_CODES.INTERNAL_ERROR);
    expect(reply?.error?.message).not.toContain('secret.db');
  });

  it('re-throws the provider error on an empty stack, after the reply', async () => {
    // Order matters. A synchronous `throw` inside the catch would reject the
    // un-awaited invoke promise (an unhandled rejection — a different event
    // from an uncaught error) and the mini app would never get its -32603.
    // Re-thrown from a microtask instead, the reply is already on its way.
    const boom = new Error('db down at /var/lib/host/secret.db');
    const bridge = setup({
      grantedScopes: ['profile'],
      capabilities: {
        profile: {
          get: async () => {
            throw boom;
          },
        },
      },
    });

    const reply = await callAfterHandshake(bridge, 'profile.get');
    expect(reply?.error?.code).toBe(ERROR_CODES.INTERNAL_ERROR);

    expect(() => vi.runAllTicks()).toThrow(boom);
  });
});
