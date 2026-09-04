/**
 * SPEC §6.3 and ADR 0003 — the kernel supplies the mini app identity; the
 * provider receives that identity and the caller's key as separate arguments.
 *
 * Covers storage.get and storage.set, including ADR 0004's top-level null
 * restriction. Delete and the policy for unknown params fields (including a
 * forged miniAppId) are later steps. No request
 * field may select the storage owner, whether extra fields are ignored or
 * rejected. Tests here do not choose between those two policies.
 */
import { createHost, type HostConfig, type StorageProvider } from '@moonpool/host';
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
  permissions: ['storage'],
};

/** Deliberately loose response shape for assertions, as in permission-gate.test.ts. */
interface RpcResponse {
  jsonrpc: '2.0';
  id: number;
  result?: Record<string, JsonValue>;
  error?: { code: number; message: string; data?: JsonValue };
}

type SetupOptions = Partial<Pick<HostConfig, 'manifest' | 'grantedScopes'>> & {
  storage?: Partial<StorageProvider>;
};

function setup({ storage, ...overrides }: SetupOptions = {}) {
  const { a: miniAppEnd, b: hostEnd } = createLinkedTransports();
  // Tests supply the operations they exercise. Unexpected operations throw
  // rather than returning fake success; omitting storage still means no slot.
  const provider =
    storage === undefined
      ? undefined
      : {
          get: async () => {
            throw new Error('unexpected storage.get in test');
          },
          set: async () => {
            throw new Error('unexpected storage.set in test');
          },
          ...storage,
        };
  createHost({
    hostInfo: { name: 'test-host', version: '0.0.0', platform: 'browser' },
    manifest: HELLO_MANIFEST,
    grantedScopes: ['storage'],
    environment: { locale: 'ko-KR', colorScheme: 'light' },
    capabilities: { storage: provider },
    ...overrides,
  }).connect(hostEnd);

  const received: RpcResponse[] = [];
  miniAppEnd.onMessage((message) => received.push(message as unknown as RpcResponse));
  return {
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

async function callAfterHandshake(
  bridge: ReturnType<typeof setup>,
  params?: Record<string, JsonValue>,
  method = 'storage.get',
): Promise<RpcResponse | undefined> {
  bridge.send(request(1, 'portal.initialize', { protocolVersion: '0.1' }));
  await flush();
  bridge.send(request(2, method, params));
  await flush();
  return bridge.received[1];
}

describe('SPEC §6.3 — storage.get with a host-supplied app identity', () => {
  it('passes the manifest id and the unmodified key separately, returning the stored JSON value', async () => {
    // Catches a composed key, swapped arguments, or a result sent without
    // the §6.3 { value } envelope. The spy observes the real kernel boundary.
    const get = vi.fn(async (_miniAppId: string, _key: string) => ({
      colorScheme: 'dark',
      fontSize: 18,
    }));
    const bridge = setup({ storage: { get } });

    const reply = await callAfterHandshake(bridge, { key: 'settings:theme' });

    expect(reply).toEqual({
      jsonrpc: '2.0',
      id: 2,
      result: { value: { colorScheme: 'dark', fontSize: 18 } },
    });
    expect(get).toHaveBeenCalledExactlyOnceWith('com.example.hello', 'settings:theme');
    expect(bridge.received).toHaveLength(2);
  });

  it('returns { value: null } when the provider reports a missing key', async () => {
    // Catches an omitted result/value or treating absence as a host error.
    const bridge = setup({ storage: { get: async () => null } });

    const reply = await callAfterHandshake(bridge, { key: 'missing' });

    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: { value: null } });
  });

  it('reads different values for the same key through one shared provider serving two mini apps', async () => {
    // The fixture explicitly partitions data. This catches the kernel using
    // one hardcoded app id or rewriting the key; it does not certify every
    // future host's storage implementation.
    const contents = new Map<string, Map<string, JsonValue>>([
      ['com.example.hello', new Map([['theme', 'dark']])],
      ['com.example.other', new Map([['theme', 'light']])],
    ]);
    const storage = {
      get: async (miniAppId: string, key: string) => contents.get(miniAppId)?.get(key) ?? null,
    };
    const hello = setup({ storage });
    const other = setup({
      storage,
      manifest: { ...HELLO_MANIFEST, id: 'com.example.other' },
    });

    const helloReply = await callAfterHandshake(hello, { key: 'theme' });
    const otherReply = await callAfterHandshake(other, { key: 'theme' });

    expect(helloReply?.result).toEqual({ value: 'dark' });
    expect(otherReply?.result).toEqual({ value: 'light' });
  });

  it('waits for the provider before sending the storage response', async () => {
    // Catches forwarding a Promise as data or sending an early empty reply.
    let completeRead!: (value: JsonValue) => void;
    const pending = new Promise<JsonValue>((resolve) => {
      completeRead = resolve;
    });
    const bridge = setup({ storage: { get: () => pending } });
    bridge.send(request(1, 'portal.initialize', { protocolVersion: '0.1' }));
    await flush();
    bridge.send(request(2, 'storage.get', { key: 'theme' }));
    await flush();

    expect(bridge.received).toHaveLength(1);
    completeRead('dark');
    await flush();
    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual({ jsonrpc: '2.0', id: 2, result: { value: 'dark' } });
  });

  it('denies an ungranted storage read before reaching the provider', async () => {
    // Already passes before storage.get exists. Protects §9.3: adding its
    // branch above the existing permission gate must not bypass the gate.
    const get = vi.fn(async () => 'private');
    const bridge = setup({ storage: { get }, grantedScopes: [] });

    const reply = await callAfterHandshake(bridge, { key: 'theme' });

    expect(reply?.error).toEqual(
      expect.objectContaining({ code: ERROR_CODES.PERMISSION_DENIED, data: { scope: 'storage' } }),
    );
    expect(get).not.toHaveBeenCalled();
  });

  it('answers -32001 when storage is granted but no provider is installed', async () => {
    // Catches confusing a known, unavailable capability with an unknown one.
    const reply = await callAfterHandshake(setup(), { key: 'theme' });

    expect(reply?.error?.code).toBe(ERROR_CODES.CAPABILITY_UNAVAILABLE);
  });
});

describe('SPEC §9.6 — storage.get validates its key before dispatch', () => {
  const INVALID_PARAMS: Array<[label: string, params: Record<string, JsonValue> | undefined]> = [
    ['omitted params', undefined],
    ['missing key', {}],
    ['non-string key', { key: 42 }],
  ];

  it.each(INVALID_PARAMS)(
    'answers -32602 for %s without calling the provider',
    async (_label, params) => {
      // These inputs pass the request-envelope guard. The new method guard
      // must prevent undefined or a number from reaching a platform provider.
      const get = vi.fn(async () => null);
      const bridge = setup({ storage: { get } });

      const reply = await callAfterHandshake(bridge, params);

      expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
      expect(get).not.toHaveBeenCalled();
    },
  );

  it('checks the key before checking whether a provider is installed', async () => {
    // Pins the approved order: params (-32602), then availability (-32001).
    const reply = await callAfterHandshake(setup(), {});

    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
  });
});

describe('SPEC §4.4 — storage.get isolates provider failures', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['queueMicrotask'] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it.each(['rejects', 'throws synchronously'] as const)(
    'answers once with -32603 and reports the original error only on the host when the provider %s',
    async (failure) => {
      // Catches a missing await/try boundary, a swallowed error, or copying
      // host-only error details into the wire response. Same contract as profile.get.
      const boom = new Error('storage failed: host-only-storage-detail');
      const get =
        failure === 'rejects'
          ? async () => {
              throw boom;
            }
          : () => {
              throw boom;
            };
      const bridge = setup({ storage: { get } });

      const reply = await callAfterHandshake(bridge, { key: 'theme' });

      expect(bridge.received).toHaveLength(2);
      expect(reply).toEqual({
        jsonrpc: '2.0',
        id: 2,
        error: expect.objectContaining({
          code: ERROR_CODES.INTERNAL_ERROR,
          message: expect.any(String),
        }),
      });
      expect(JSON.stringify(reply)).not.toContain('host-only-storage-detail');
      expect(() => vi.runAllTicks()).toThrow(boom);
    },
  );
});

describe('SPEC §6.3 — storage.set with a host-supplied app identity', () => {
  it('passes the manifest id, unmodified key, and value separately and answers with an empty result', async () => {
    // Catches a composed key, swapped arguments, discarded value, or an
    // acknowledgement carrying the stored value instead of the §6.3 {} result.
    const set = vi.fn(async (_miniAppId: string, _key: string, _value: JsonValue) => undefined);
    const bridge = setup({ storage: { set } });

    const reply = await callAfterHandshake(
      bridge,
      { key: 'settings:theme', value: { colorScheme: 'dark', nickname: null } },
      'storage.set',
    );

    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(set).toHaveBeenCalledExactlyOnceWith('com.example.hello', 'settings:theme', {
      colorScheme: 'dark',
      nickname: null,
    });
    expect(bridge.received).toHaveLength(2);
  });

  it('writes and reads independent values for the same key through one provider shared by two apps', async () => {
    // The fixture partitions data; the real kernel must preserve identity
    // on both write and read. A fixed id or rewritten key breaks this round trip.
    const contents = new Map<string, Map<string, JsonValue>>();
    const storage = {
      get: async (miniAppId: string, key: string) => contents.get(miniAppId)?.get(key) ?? null,
      set: async (miniAppId: string, key: string, value: JsonValue) => {
        let app = contents.get(miniAppId);
        if (app === undefined) {
          app = new Map();
          contents.set(miniAppId, app);
        }
        app.set(key, value);
      },
    };
    const hello = setup({ storage });
    const other = setup({ storage, manifest: { ...HELLO_MANIFEST, id: 'com.example.other' } });

    const helloWrite = await callAfterHandshake(
      hello,
      { key: 'theme', value: 'dark' },
      'storage.set',
    );
    const otherWrite = await callAfterHandshake(
      other,
      { key: 'theme', value: 'light' },
      'storage.set',
    );
    expect(helloWrite?.result).toEqual({});
    expect(otherWrite?.result).toEqual({});

    hello.send(request(3, 'storage.get', { key: 'theme' }));
    other.send(request(3, 'storage.get', { key: 'theme' }));
    await flush();

    expect(hello.received[2]?.result).toEqual({ value: 'dark' });
    expect(other.received[2]?.result).toEqual({ value: 'light' });
  });

  const VALID_VALUES: Array<[label: string, value: JsonValue]> = [
    ['false', false],
    ['zero', 0],
    ['empty string', ''],
    ['null inside an object', { nickname: null }],
    ['null inside an array', [null]],
  ];

  it.each(VALID_VALUES)('stores %s without changing the value', async (_label, value) => {
    // Catches a truthiness check that rejects false/0/"", or a recursive
    // no-null rule that accidentally forbids legitimate nested null data.
    let saved: JsonValue = 'previous';
    const bridge = setup({
      storage: {
        get: async () => saved,
        set: async (_miniAppId: string, _key: string, next: JsonValue) => {
          saved = next;
        },
      },
    });

    const reply = await callAfterHandshake(bridge, { key: 'value', value }, 'storage.set');
    expect(reply).toEqual({ jsonrpc: '2.0', id: 2, result: {} });

    bridge.send(request(3, 'storage.get', { key: 'value' }));
    await flush();
    expect(bridge.received[2]?.result).toEqual({ value });
  });

  it('waits for the write to finish before acknowledging success', async () => {
    // Catches acknowledging a write that the provider has not completed yet.
    let completeWrite!: () => void;
    const pending = new Promise<void>((resolve) => {
      completeWrite = resolve;
    });
    const bridge = setup({ storage: { set: () => pending } });
    bridge.send(request(1, 'portal.initialize', { protocolVersion: '0.1' }));
    await flush();
    bridge.send(request(2, 'storage.set', { key: 'theme', value: 'dark' }));
    await flush();

    expect(bridge.received).toHaveLength(1);
    completeWrite();
    await flush();
    expect(bridge.received).toHaveLength(2);
    expect(bridge.received[1]).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
  });

  it.each([
    ['valid params', { key: 'theme', value: 'dark' }],
    ['invalid params', { key: 'theme', value: null }],
  ] as const)(
    'denies an ungranted write with %s before reaching the provider',
    async (_label, params) => {
      // Already green before set exists. Pins §9.3 and the approved order:
      // permission denied must precede both params validation and invocation.
      const set = vi.fn(async () => undefined);
      const bridge = setup({ storage: { set }, grantedScopes: [] });

      const reply = await callAfterHandshake(bridge, params, 'storage.set');

      expect(reply?.error).toEqual(
        expect.objectContaining({
          code: ERROR_CODES.PERMISSION_DENIED,
          data: { scope: 'storage' },
        }),
      );
      expect(set).not.toHaveBeenCalled();
    },
  );

  it('rejects a write before initialization without calling the provider', async () => {
    // Already green. Adding the set branch must not bypass the §5 gate.
    const set = vi.fn(async () => undefined);
    const bridge = setup({ storage: { set } });

    bridge.send(request(1, 'storage.set', { key: 'theme', value: 'dark' }));
    await flush();

    expect(bridge.received).toHaveLength(1);
    expect(bridge.received[0]?.error?.code).toBe(ERROR_CODES.NOT_INITIALIZED);
    expect(set).not.toHaveBeenCalled();
  });

  it('answers -32001 when storage is granted but no provider is installed', async () => {
    const reply = await callAfterHandshake(setup(), { key: 'theme', value: 'dark' }, 'storage.set');

    expect(reply?.error?.code).toBe(ERROR_CODES.CAPABILITY_UNAVAILABLE);
  });
});

describe('SPEC §6.3 / §9.6 — storage.set validates before changing data', () => {
  const INVALID_PARAMS: Array<[label: string, params: Record<string, JsonValue> | undefined]> = [
    ['omitted params', undefined],
    ['missing key', { value: 'dark' }],
    ['non-string key', { key: 42, value: 'dark' }],
    ['missing value', { key: 'theme' }],
    ['top-level null', { key: 'theme', value: null }],
  ];

  it.each(INVALID_PARAMS)(
    'answers -32602 for %s without calling the provider',
    async (_label, params) => {
      // Catches dispatching invalid input, especially a missing/null value,
      // to a provider that would otherwise mutate storage.
      const set = vi.fn(async () => undefined);
      const bridge = setup({ storage: { set } });

      const reply = await callAfterHandshake(bridge, params, 'storage.set');

      expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
      expect(set).not.toHaveBeenCalled();
    },
  );

  it('rejects null before checking whether a provider is installed', async () => {
    // Same approved params-before-availability order as storage.get.
    const reply = await callAfterHandshake(setup(), { key: 'theme', value: null }, 'storage.set');

    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
  });

  it('leaves the existing value intact when rejecting a null write', async () => {
    // An error reply after invoking set would be too late. Neither an
    // implicit delete nor a write of null may happen before rejection.
    let saved: JsonValue = 'dark';
    const bridge = setup({
      storage: {
        get: async () => saved,
        set: async (_miniAppId: string, _key: string, next: JsonValue) => {
          saved = next;
        },
      },
    });

    const reply = await callAfterHandshake(bridge, { key: 'theme', value: null }, 'storage.set');
    expect(reply?.error?.code).toBe(ERROR_CODES.INVALID_PARAMS);
    bridge.send(request(3, 'storage.get', { key: 'theme' }));
    await flush();

    expect(bridge.received[2]?.result).toEqual({ value: 'dark' });
  });
});

describe('SPEC §4.4 — storage.set isolates provider failures', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['queueMicrotask'] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it.each(['rejects', 'throws synchronously'] as const)(
    'answers once with -32603 and reports the original error only on the host when the provider %s',
    async (failure) => {
      const boom = new Error('write failed: host-only-write-detail');
      const set =
        failure === 'rejects'
          ? async () => {
              throw boom;
            }
          : () => {
              throw boom;
            };
      const bridge = setup({ storage: { set } });

      const reply = await callAfterHandshake(
        bridge,
        { key: 'theme', value: 'dark' },
        'storage.set',
      );

      expect(bridge.received).toHaveLength(2);
      expect(reply).toEqual({
        jsonrpc: '2.0',
        id: 2,
        error: expect.objectContaining({
          code: ERROR_CODES.INTERNAL_ERROR,
          message: expect.any(String),
        }),
      });
      expect(JSON.stringify(reply)).not.toContain('host-only-write-detail');
      expect(() => vi.runAllTicks()).toThrow(boom);
    },
  );
});
