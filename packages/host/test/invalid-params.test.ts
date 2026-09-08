/**
 * SPEC §4.2 — params must be an object or omitted. A valid request envelope
 * with a non-object params value gets -32602, not -32600.
 *
 * This is the general wire-shape check. Per-method required fields still
 * follow the permission gate (§9.3 / §9.6). Unknown fields, recursive JSON
 * validation, and size limits remain separate E4.4 steps.
 */
import { createHost, type HostConfig } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type MiniAppManifest } from '@moonpool/protocol';
import { describe, expect, it, vi } from 'vitest';
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

/** Loose response shape for assertions, matching the other host suites. */
interface RpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: Record<string, JsonValue>;
  error?: { code: number; message: string; data?: JsonValue };
}

function setup(overrides: Partial<HostConfig> = {}) {
  const { a: miniAppEnd, b: hostEnd } = createLinkedTransports();
  createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: HELLO_MANIFEST,
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    ...overrides,
  }).connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));
  return {
    received,
    send: (message: JsonValue) => miniAppEnd.send(message),
  };
}

// Accept arbitrary JSON params so tests can send frames the public client
// correctly refuses to construct. The real host receives every test frame.
const request = (id: number, method: string, params?: JsonValue): JsonValue => ({
  jsonrpc: '2.0',
  id,
  method,
  ...(params === undefined ? {} : { params }),
});

async function initialize(bridge: ReturnType<typeof setup>) {
  bridge.send(request(1, 'portal.initialize', { protocolVersion: '0.1' }));
  await flush();
  expect(bridge.received[0]?.result?.protocolVersion).toBe('0.1');
}

describe('SPEC §4.2 — reject non-object params with -32602', () => {
  const INVALID_PARAMS: Array<[label: string, params: JsonValue]> = [
    ['an empty array', []],
    ['positional arguments', ['theme']],
    ['null', null],
    ['a string', 'theme'],
    ['a number', 42],
    ['a boolean', false],
  ];

  it.each(INVALID_PARAMS)('answers once with -32602 for %s', async (_label, params) => {
    // Catches treating bad params as a bad envelope (-32600), or letting
    // portal.ping bypass validation because it does not consume any params.
    const bridge = setup();
    await initialize(bridge);

    bridge.send(request(2, 'portal.ping', params));
    await flush();

    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({
        code: ERROR_CODES.INVALID_PARAMS,
        message: expect.any(String),
      }),
    });
  });

  it.each(['profile.get', 'storage.get', 'storage.set', 'storage.delete'])(
    'rejects array params for %s without invoking a capability provider',
    async (method) => {
      // Catches validating only portal methods, or replying with an error
      // after a provider has already read or changed host data (§9.6).
      const profileGet = vi.fn(async () => ({ displayName: 'Jane' }));
      const storageGet = vi.fn(async () => null);
      const storageSet = vi.fn(async () => undefined);
      const storageDelete = vi.fn(async () => undefined);
      const bridge = setup({
        capabilities: {
          profile: { get: profileGet },
          storage: { get: storageGet, set: storageSet, delete: storageDelete },
        },
      });
      await initialize(bridge);

      bridge.send(request(2, method, []));
      await flush();

      expect(bridge.received).toHaveLength(2);
      expect(bridge.received[1]?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
      expect(profileGet).not.toHaveBeenCalled();
      expect(storageGet).not.toHaveBeenCalled();
      expect(storageSet).not.toHaveBeenCalled();
      expect(storageDelete).not.toHaveBeenCalled();
    },
  );

  it('rejects array params on initialize without initializing or preventing a valid retry', async () => {
    // Catches checking params only after the handshake branch. An array
    // is malformed params, not a request to negotiate a different version.
    const bridge = setup();

    bridge.send(request(1, 'portal.initialize', ['0.1']));
    await flush();
    expect(bridge.received).toHaveLength(1);
    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);

    bridge.send(request(2, 'portal.ping'));
    await flush();
    expect(bridge.received[1]?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);

    bridge.send(request(3, 'portal.initialize', { protocolVersion: '0.1' }));
    await flush();
    expect(bridge.received[2]?.result?.protocolVersion).toBe('0.1');
    bridge.send(request(4, 'portal.ping'));
    await flush();
    expect(bridge.received).toHaveLength(4);
    expect(bridge.received[3]).toEqual({ jsonrpc: '2.0', id: 4, result: { pong: true } });
  });
});

describe('SPEC §4.1 / §4.2 — preserve the surrounding request rules', () => {
  it.each([
    ['omitted params', undefined],
    ['an empty object', {}],
  ] as const)('continues to accept %s for portal.ping', async (_label, params) => {
    // Already green. Catches treating omission as invalid or accidentally
    // rejecting ordinary objects while tightening the shape check.
    const bridge = setup();
    await initialize(bridge);

    bridge.send(request(2, 'portal.ping', params));
    await flush();

    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual({ jsonrpc: '2.0', id: 2, result: { pong: true } });
  });

  it('keeps -32600 for a malformed envelope even when params is an array', async () => {
    // Already green. Catches replacing the existing rejection code wholesale
    // or checking params before proving this is a JSON-RPC 2.0 request.
    const bridge = setup();

    bridge.send({ jsonrpc: '1.0', id: 7, method: 'portal.ping', params: [] });
    await flush();

    expect(bridge.received).toEqual([
      {
        jsonrpc: '2.0',
        id: 7,
        error: expect.objectContaining({ code: ERROR_CODES.INVALID_REQUEST }),
      },
    ]);
  });

  it('stays silent for an id-less frame with array params', async () => {
    // Already green. The new params error must not invent a reply to a
    // notification; the no-id rule still applies before request validation.
    const bridge = setup();

    bridge.send({ jsonrpc: '2.0', method: 'portal.ping', params: [] });
    await flush();

    expect(bridge.received).toEqual([]);
  });
});
