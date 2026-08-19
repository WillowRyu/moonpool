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
