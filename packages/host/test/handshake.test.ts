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

  it('does not service further calls after a failed negotiation', async () => {
    const bridge = setup();

    bridge.send(initialize(1, '9.9'));
    await flush();
    bridge.send(request(2, 'portal.ping'));
    await flush();

    // §5: after -32004 the host MUST NOT service further calls. The
    // connection never initialized, so the -32005 gate still applies —
    // the call must be rejected, never answered with a result.
    const second = bridge.received[1];
    expect(second?.result).toBeUndefined();
    expect(second?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
  });
});
