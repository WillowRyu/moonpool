import { createHost, type HostConfig } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type MiniAppManifest } from '@moonpool/protocol';
import { describe, expect, it } from 'vitest';
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

describe('createHost', () => {
  it('returns a host that can accept one bridge connection', () => {
    const host = createHost({
      hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
      manifest: HELLO_MANIFEST,
      grantedScopes: ['profile', 'storage'],
      environment: { locale: 'ko-KR', colorScheme: 'light' },
    });

    expect(typeof host.connect).toBe('function');
  });
});

describe('SPEC §5 — portal.initialize happy path', () => {
  it('answers with the negotiated version, both identities, granted scopes, and environment', async () => {
    const bridge = setup();

    bridge.send(initialize(1));
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: 1,
        result: {
          protocolVersion: '0.1',
          miniApp: { id: 'com.example.hello', version: '1.0.0' },
          host: { name: 'test-host', version: '0.0.0', platform: 'browser' },
          grantedScopes: ['profile', 'storage'],
          environment: { locale: 'ko-KR', colorScheme: 'light' },
        },
      },
    ]);
  });

  it('reports grantedScopes as the intersection of manifest permissions and host grants', async () => {
    // Manifest declares [profile, storage]; the host grants [storage, camera].
    // Only the overlap is authoritative for the connection (SPEC §5).
    const bridge = setup({ grantedScopes: ['storage', 'camera'] });

    bridge.send(initialize(1));
    await flush();

    expect(bridge.received[0]?.result?.grantedScopes).toEqual(['storage']);
  });
});

describe('SPEC §5 — NOT_INITIALIZED gate (-32005)', () => {
  it('rejects portal.ping sent before portal.initialize with -32005', async () => {
    const bridge = setup();

    bridge.send(request(1, 'portal.ping'));
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: 1,
        error: expect.objectContaining({
          code: ERROR_CODES.NOT_INITIALIZED,
          message: expect.any(String),
        }),
      },
    ]);
  });
});

describe('SPEC §5 — version negotiation failure (-32004)', () => {
  it.each(['9.9', '0.2'])(
    'rejects protocolVersion "%s" with -32004 (negotiation is exact-match in 0.x)',
    async (version) => {
      const bridge = setup();

      bridge.send(initialize(1, version));
      await flush();

      expect(bridge.received).toEqual([
        {
          jsonrpc: '2.0',
          id: 1,
          error: expect.objectContaining({
            code: ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED,
            message: expect.any(String),
          }),
        },
      ]);
    },
  );

  it('still gates every other method with -32005 after a failed negotiation', async () => {
    const bridge = setup();

    bridge.send(initialize(1, '9.9'));
    await flush();
    bridge.send(request(2, 'portal.ping'));
    await flush();

    // §5: a failed negotiation leaves the connection uninitialized, and an
    // uninitialized connection answers everything but the handshake with
    // -32005. What it does NOT do is poison the connection — see the retry
    // test below.
    const second = bridge.received[1];
    expect(second?.result).toBeUndefined();
    expect(second?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
  });

  it('accepts a corrected portal.initialize after -32004', async () => {
    // §5: `-32004` describes one unsupported version, not a poisoned
    // connection. A mini app that guessed wrong and guesses right on the
    // second try MUST be answered on the merits.
    const bridge = setup();

    bridge.send(initialize(1, '9.9'));
    await flush();
    bridge.send(initialize(2, '0.1'));
    await flush();

    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED);
    expect(bridge.received[1]?.result).toMatchObject({ protocolVersion: '0.1' });
  });
});

describe('SPEC §5.1 — repeat handshake', () => {
  // A Portal's document can be replaced while its transport stays alive: a
  // reload, a link in a multi-page mini app, a web view recovering from
  // renderer termination (ADR 0002). Each replacement is a new client with no
  // memory, and its handshake is the only signal the host can act on — the
  // transport carries frames and nothing else.

  it('answers a second portal.initialize exactly as it answered the first', async () => {
    const bridge = setup();

    bridge.send(initialize(1));
    await flush();
    // The new document restarts its ids at 1, the way any fresh client does.
    bridge.send(initialize(1));
    await flush();

    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual(bridge.received[0]);
  });

  it('leaves the connection usable after a repeat handshake', async () => {
    const bridge = setup();

    bridge.send(initialize(1));
    await flush();
    bridge.send(initialize(1));
    await flush();
    bridge.send(request(2, 'portal.ping'));
    await flush();

    // Deliberately a weak assertion, and it passes both before and after
    // §5.1: the pre-§5.1 host answered the repeat handshake with -32601 but
    // kept serving everything else, because `initialized` was still true. The
    // test that actually catches the defect is the one above. This one guards
    // the other direction — that accepting a repeat handshake does not leave
    // the connection unusable.
    expect(bridge.received[2]).toEqual({ jsonrpc: '2.0', id: 2, result: { pong: true } });
  });

  // The rest of §5.1's reset boundary is not observable here yet. "Reset
  // initialization state" and "re-set it" happen inside one handshake, so no
  // message can catch the connection in between; and the preserved rows
  // (rate-limit counters, consent records) name state this host does not keep
  // yet. Those rows bind the implementations that add them — they are not
  // covered by a test today, and saying so beats a test that only looks like
  // coverage.
});

describe('SPEC §6.2 — portal.ping (core method, no scope required)', () => {
  it('answers { pong: true } once the connection is initialized', async () => {
    const bridge = setup();

    bridge.send(initialize(1));
    await flush();
    bridge.send(request(2, 'portal.ping'));
    await flush();

    expect(bridge.received[1]).toEqual({
      jsonrpc: '2.0',
      id: 2,
      result: { pong: true },
    });
  });
});

describe('SPEC §4 — every request gets exactly one response', () => {
  it('rejects an unknown method after initialize with -32601, never silence', async () => {
    const bridge = setup();

    bridge.send(initialize(1));
    await flush();
    bridge.send(request(2, 'portal.doesNotExist'));
    await flush();

    expect(bridge.received[1]).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({
        code: ERROR_CODES.METHOD_NOT_FOUND,
        message: expect.any(String),
      }),
    });
  });
});
