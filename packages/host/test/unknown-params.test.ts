/**
 * SPEC §4.2 / ADR 0006 — reject unsupported top-level params names.
 * Permission and initialization gates remain in front of per-method checks;
 * rejected calls never reach providers. Nested storage values remain data.
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
  // Observe the real kernel's boundary. These providers succeed if called,
  // so a missing rejection produces an ordinary wrong response, not a crash.
  const providers = {
    profileGet: vi.fn(async () => ({ displayName: 'Jane' })),
    storageGet: vi.fn(async () => null),
    storageSet: vi.fn(async () => undefined),
    storageDelete: vi.fn(async () => undefined),
  };
  createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: HELLO_MANIFEST,
    grantedScopes: ['profile', 'storage'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    capabilities: {
      profile: { get: providers.profileGet },
      storage: {
        get: providers.storageGet,
        set: providers.storageSet,
        delete: providers.storageDelete,
      },
    },
    ...overrides,
  }).connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));
  return {
    providers,
    received,
    send: (message: JsonValue) => miniAppEnd.send(message),
  };
}

const request = (id: number, method: string, params?: Record<string, JsonValue>): JsonValue => ({
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

async function callAfterHandshake(
  bridge: ReturnType<typeof setup>,
  method: string,
  params?: Record<string, JsonValue>,
) {
  await initialize(bridge);
  bridge.send(request(2, method, params));
  await flush();
  return bridge.received[1];
}

function expectNoProviderCalls(bridge: ReturnType<typeof setup>) {
  expect(bridge.providers.profileGet).not.toHaveBeenCalled();
  expect(bridge.providers.storageGet).not.toHaveBeenCalled();
  expect(bridge.providers.storageSet).not.toHaveBeenCalled();
  expect(bridge.providers.storageDelete).not.toHaveBeenCalled();
}

const SCOPED_METHODS: Array<[method: string, params: Record<string, JsonValue>]> = [
  ['profile.get', {}],
  ['storage.get', { key: 'theme' }],
  ['storage.set', { key: 'theme', value: 'dark' }],
  ['storage.delete', { key: 'theme' }],
];

describe('SPEC §4.2 — unknown params names on known methods', () => {
  it.each([['portal.ping', {}], ...SCOPED_METHODS] as Array<
    [method: string, params: Record<string, JsonValue>]
  >)('rejects an extra field on %s without invoking a provider', async (method, params) => {
    // Catches checking only required fields, or deleting unsupported fields
    // and continuing. A false value still counts as a present unknown field.
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, method, { ...params, extra: false });

    expect(bridge.received).toHaveLength(2);
    expect(reply).toEqual({
      jsonrpc: '2.0',
      id: 2,
      error: expect.objectContaining({
        code: ERROR_CODES.INVALID_PARAMS,
        message: expect.any(String),
      }),
    });
    expectNoProviderCalls(bridge);
  });

  it('rejects extra initialize params before initialization and allows a valid retry', async () => {
    // Catches validating only methods below initialize. A supported version
    // must not hide an unsupported option or initialize a rejected request.
    const bridge = setup();

    bridge.send(request(1, 'portal.initialize', { protocolVersion: '0.1', extra: true }));
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

  it.each([
    ['storage.get', { key: 'theme' }],
    ['storage.set', { key: 'theme', value: 'dark' }],
    ['storage.delete', { key: 'theme' }],
  ] as const)('rejects a forged miniAppId on %s before provider access', async (method, params) => {
    // ADR 0003 forbids selecting identity from params. ADR 0006 now chooses
    // rejection rather than silently ignoring this unsupported field.
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, method, {
      ...params,
      miniAppId: 'com.example.other',
    });

    expect(bridge.received).toHaveLength(2);
    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    expectNoProviderCalls(bridge);
  });

  it.each(['constructor', 'toString'])('rejects %s as an unsupported params name', async (name) => {
    // Catches treating inherited Object.prototype names as allowed entries
    // in an object-based allowlist. These are ordinary but unsupported JSON keys.
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, 'storage.get', {
      key: 'theme',
      [name]: 'unsupported',
    });

    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    expectNoProviderCalls(bridge);
  });
});

describe('SPEC §4.2 / §9.3 / §9.6 — preserve rejection order', () => {
  it.each(SCOPED_METHODS)(
    'checks extra fields before provider availability for %s',
    async (method, params) => {
      // With no provider, availability-first would incorrectly answer -32001.
      const bridge = setup({ capabilities: undefined });

      const reply = await callAfterHandshake(bridge, method, { ...params, extra: true });

      expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    },
  );

  it.each(SCOPED_METHODS)(
    'denies %s before inspecting its extra params',
    async (method, params) => {
      // Already green. Adding this check globally above the scope gate would
      // expose method-specific input rules to a caller without permission.
      const bridge = setup({ grantedScopes: [] });

      const reply = await callAfterHandshake(bridge, method, { ...params, extra: true });

      expect(reply?.error?.code).toBe(ERROR_CODES.PERMISSION_DENIED);
      expectNoProviderCalls(bridge);
    },
  );

  it('preserves -32005 for an uninitialized write with extra params', async () => {
    // Already green. Method-specific validation stays below the §5 gate.
    const bridge = setup();

    bridge.send(request(1, 'storage.set', { key: 'theme', value: 'dark', extra: true }));
    await flush();

    expect(bridge.received).toHaveLength(1);
    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
    expectNoProviderCalls(bridge);
  });

  it('preserves -32601 for an unknown method in a granted namespace', async () => {
    // Already green. There is no schema to validate for an unknown method;
    // the new check must not treat it as a known method with zero allowed keys.
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, 'storage.doesNotExist', { extra: true });

    expect(reply?.error?.code).toBe(ERROR_CODES.METHOD_NOT_FOUND);
    expectNoProviderCalls(bridge);
  });

  it('does not answer an id-less frame with extra params', async () => {
    // Already green. New validation must not reply to notifications (§4.1).
    const bridge = setup();
    await initialize(bridge);

    bridge.send({ jsonrpc: '2.0', method: 'storage.get', params: { key: 'theme', extra: true } });
    await flush();

    expect(bridge.received).toHaveLength(1);
    expectNoProviderCalls(bridge);
  });
});

describe('SPEC §4.2 — limit the restriction to params names', () => {
  it('preserves arbitrary object keys inside storage.set value through a write/read round trip', async () => {
    // Already green. Catches recursively applying the params allowlist to
    // application data or stripping fields rather than preserving the value.
    let saved: JsonValue = null;
    const bridge = setup({
      capabilities: {
        storage: {
          get: async () => saved,
          set: async (_miniAppId: string, _key: string, value: JsonValue) => {
            saved = value;
          },
          delete: async () => {
            throw new Error('unexpected delete in value-preservation test');
          },
        },
      },
    });

    const reply = await callAfterHandshake(bridge, 'storage.set', {
      key: 'settings',
      value: {
        miniAppId: 'application data',
        constructor: 'also data',
        nested: [{ extra: false, nickname: null }],
      },
    });
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    bridge.send(request(3, 'storage.get', { key: 'settings' }));
    await flush();

    expect(bridge.received[2]?.result).toEqual({
      value: {
        miniAppId: 'application data',
        constructor: 'also data',
        nested: [{ extra: false, nickname: null }],
      },
    });
  });

  it.each([
    ['omitted params', undefined],
    ['an empty object', {}],
  ] as const)('continues to serve profile.get with %s', async (_label, params) => {
    // Already green. A method with no required params accepts both forms;
    // rejecting extras must not make omission an error.
    const bridge = setup();

    const reply = await callAfterHandshake(bridge, 'profile.get', params);

    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: { displayName: 'Jane' } });
    expect(bridge.providers.profileGet).toHaveBeenCalledExactlyOnceWith();
  });

  it('does not apply the params restriction to extra envelope members', async () => {
    // Already green. Catches enumerating the entire request instead of its
    // params object. ADR 0006 does not introduce an envelope-member restriction.
    const bridge = setup();
    await initialize(bridge);

    bridge.send({ jsonrpc: '2.0', id: 2, method: 'portal.ping', params: {}, extra: true });
    await flush();

    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual({ jsonrpc: '2.0', id: 2, result: { pong: true } });
  });
});
