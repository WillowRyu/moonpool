/** T10 / SPEC §4.1, §5.1 — document-scoped ordering without duplicate execution. */
import { createHost } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type Transport } from '@moonpool/protocol';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createClient } from '../../client/src/index';
import { createLinkedTransports, flush } from './helpers/memory-transport';

const ends: Transport[] = [];
afterEach(() => {
  for (const end of ends.splice(0)) {
    end.close();
  }
});

function pair() {
  const bridge = createLinkedTransports();
  ends.push(bridge.a, bridge.b);
  return bridge;
}

function request(
  id: number,
  method = 'portal.ping',
  params: JsonValue = {},
): Record<string, JsonValue> {
  return { jsonrpc: '2.0', id, method, params };
}
function initialize(id = 1, version = '0.1') {
  return request(id, 'portal.initialize', { protocolVersion: version });
}
function sequenceError() {
  return {
    jsonrpc: '2.0',
    id: null,
    error: { code: ERROR_CODES.INVALID_REQUEST, message: expect.any(String) },
  };
}

function setup(grants = ['profile', 'storage'], provideProfile = true) {
  const bridge = pair();
  const received: JsonValue[] = [];
  bridge.a.onMessage((message) => received.push(message));
  const values = new Map<string, JsonValue>();
  const profile = { get: vi.fn(async () => ({ displayName: 'Original call' })) };
  const storage = {
    get: vi.fn(async (_app: string, key: string) => values.get(key) ?? null),
    set: vi.fn(async (_app: string, key: string, value: JsonValue) => {
      values.set(key, value);
    }),
    delete: vi.fn(async (_app: string, key: string) => {
      values.delete(key);
    }),
  };
  const host = createHost({
    hostInfo: { name: 'id-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.ids',
      name: 'Id test',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes: grants,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: { ...(provideProfile ? { profile } : {}), storage },
  });
  host.connect(bridge.b);
  async function send(frame: JsonValue) {
    bridge.a.send(frame);
    await flush();
    return received.at(-1);
  }
  return { host, bridge, received, values, profile, storage, send };
}

describe('SPEC §4.1 — increasing request ids', () => {
  it('permits gaps and a first initialization id other than one', async () => {
    const h = setup();
    expect(await h.send(initialize(3))).toMatchObject({
      id: 3,
      result: { protocolVersion: '0.1' },
    });
    expect(await h.send(request(7))).toEqual({ jsonrpc: '2.0', id: 7, result: { pong: true } });
    expect(await h.send(request(20))).toEqual({ jsonrpc: '2.0', id: 20, result: { pong: true } });
  });

  it.each([5, 3])(
    'rejects duplicate or backward id %s without executing another write',
    async (id) => {
      const h = setup();
      await h.send(initialize());
      await h.send(request(5, 'storage.set', { key: 'settings', value: 'original' }));
      expect(
        await h.send(request(id, 'storage.set', { key: 'settings', value: 'duplicate' })),
      ).toEqual(sequenceError());
      expect(h.storage.set).toHaveBeenCalledTimes(1);
      expect(h.values.get('settings')).toBe('original');
      expect(await h.send(request(6, 'storage.get', { key: 'settings' }))).toEqual({
        jsonrpc: '2.0',
        id: 6,
        result: { value: 'original' },
      });
    },
  );

  const FAILURES = [
    {
      label: 'version envelope',
      frame: { ...request(5), jsonrpc: '1.0' },
      code: ERROR_CODES.INVALID_REQUEST,
    },
    {
      label: 'method syntax',
      frame: request(5, 'profile..get'),
      code: ERROR_CODES.INVALID_REQUEST,
    },
    {
      label: 'params container',
      frame: request(5, 'profile.get', []),
      code: ERROR_CODES.INVALID_PARAMS,
    },
    {
      label: 'permission denial',
      frame: request(5, 'profile.get'),
      code: ERROR_CODES.PERMISSION_DENIED,
      grants: [],
    },
    {
      label: 'unknown method',
      frame: request(5, 'portal.unknown'),
      code: ERROR_CODES.METHOD_NOT_FOUND,
    },
    {
      label: 'method params',
      frame: request(5, 'storage.set', { key: 'settings' }),
      code: ERROR_CODES.INVALID_PARAMS,
    },
    {
      label: 'unavailable provider',
      frame: request(5, 'profile.get'),
      code: ERROR_CODES.CAPABILITY_UNAVAILABLE,
      provideProfile: false,
    },
  ];
  it.each(FAILURES)(
    'consumes a new id even after $label rejection',
    async ({ frame, code, grants, provideProfile }) => {
      const h = setup(grants, provideProfile);
      await h.send(initialize());
      expect(await h.send(frame)).toMatchObject({ id: 5, error: { code } });
      expect(await h.send(request(5))).toEqual(sequenceError());
      expect(await h.send(request(6))).toEqual({ jsonrpc: '2.0', id: 6, result: { pong: true } });
    },
  );

  it('consumes a request rejected before initialization', async () => {
    const h = setup();
    expect(await h.send(request(5))).toMatchObject({
      id: 5,
      error: { code: ERROR_CODES.NOT_INITIALIZED },
    });
    expect(await h.send(request(5))).toEqual(sequenceError());
    expect(await h.send(initialize(1))).toMatchObject({
      id: 1,
      result: { protocolVersion: '0.1' },
    });
    expect(await h.send(request(2))).toMatchObject({ id: 2, result: { pong: true } });
  });

  it('does not advance the counter for batches or notifications', async () => {
    const h = setup();
    await h.send(initialize());
    expect(await h.send([initialize(100), request(101)])).toEqual(sequenceError());
    const count = h.received.length;
    await h.send({
      jsonrpc: '2.0',
      method: 'portal.initialize',
      params: { protocolVersion: '0.1' },
    });
    expect(h.received).toHaveLength(count);
    expect(await h.send(request(2))).toMatchObject({ id: 2, result: { pong: true } });
  });

  it.each([0, -1, 2.5, Number.NaN, Number.POSITIVE_INFINITY])(
    'does not consume invalid numeric id %s',
    async (id) => {
      const h = setup();
      await h.send(initialize());
      expect(await h.send(request(id))).toMatchObject({
        error: { code: ERROR_CODES.INVALID_REQUEST },
      });
      expect(await h.send(request(2))).toMatchObject({ id: 2, result: { pong: true } });
    },
  );

  it('keeps sequence counters independent for two connections on the same host', async () => {
    const h = setup();
    await h.send(initialize());
    await h.send(request(10));
    const second = pair();
    const replies: JsonValue[] = [];
    second.a.onMessage((frame) => replies.push(frame));
    h.host.connect(second.b);
    second.a.send(initialize());
    second.a.send(request(2));
    await flush();
    expect(replies).toEqual([
      expect.objectContaining({ id: 1, result: expect.any(Object) }),
      { jsonrpc: '2.0', id: 2, result: { pong: true } },
    ]);
    expect(await h.send(request(11))).toMatchObject({ id: 11, result: { pong: true } });
  });
});

describe('SPEC §5.1 — initialization resets only document state', () => {
  it('starts a fresh sequence after a repeat handshake', async () => {
    const h = setup();
    await h.send(initialize());
    await h.send(request(10));
    expect(await h.send(initialize())).toMatchObject({ id: 1, result: { protocolVersion: '0.1' } });
    expect(await h.send(request(2))).toMatchObject({ id: 2, result: { pong: true } });
    expect(await h.send(request(2))).toEqual(sequenceError());
  });

  const FAILED_INITIALIZATIONS: Array<{ params: JsonValue; code: number }> = [
    { params: { protocolVersion: 'unsupported' }, code: ERROR_CODES.PROTOCOL_VERSION_UNSUPPORTED },
    { params: {}, code: ERROR_CODES.INVALID_PARAMS },
    { params: { protocolVersion: '0.1', extra: true }, code: ERROR_CODES.INVALID_PARAMS },
  ];
  it.each(FAILED_INITIALIZATIONS)(
    'resets the sequence even when initialization fields fail: $params',
    async ({ params, code }) => {
      const h = setup(['storage']);
      await h.send(initialize(10));
      await h.send(request(11, 'storage.set', { key: 'settings', value: 'kept' }));
      expect(await h.send(request(1, 'portal.initialize', params))).toMatchObject({
        id: 1,
        error: { code },
      });
      expect(await h.send(request(2))).toMatchObject({
        id: 2,
        error: { code: ERROR_CODES.NOT_INITIALIZED },
      });
      expect(await h.send(request(2))).toEqual(sequenceError());
      expect(await h.send(initialize(3))).toMatchObject({
        id: 3,
        result: { grantedScopes: ['storage'] },
      });
      expect(await h.send(request(4, 'storage.get', { key: 'settings' }))).toMatchObject({
        id: 4,
        result: { value: 'kept' },
      });
      expect(await h.send(request(5, 'profile.get'))).toMatchObject({
        id: 5,
        error: { code: ERROR_CODES.PERMISSION_DENIED },
      });
    },
  );

  it.each([
    {
      label: 'array params',
      method: 'portal.initialize',
      params: [],
      code: ERROR_CODES.INVALID_PARAMS,
    },
    {
      label: 'malformed name',
      method: 'portal.initialize ',
      params: {},
      code: ERROR_CODES.INVALID_REQUEST,
    },
  ])(
    'does not reset for $label, whether the id is old or new',
    async ({ method, params, code }) => {
      const h = setup();
      await h.send(initialize());
      await h.send(request(9));
      expect(await h.send(request(1, method, params))).toEqual(sequenceError());
      expect(await h.send(request(10, method, params))).toMatchObject({ id: 10, error: { code } });
      expect(await h.send(request(10))).toEqual(sequenceError());
      expect(await h.send(request(11))).toMatchObject({ id: 11, result: { pong: true } });
    },
  );
});

it('does not settle an in-flight client call when its id is reused, even with malformed syntax', async () => {
  vi.useFakeTimers();
  const h = setup();
  const client = createClient({ transport: h.bridge.a, timeoutMs: 1_000 });
  let complete: ((value: { displayName: string }) => void) | undefined;
  h.profile.get.mockImplementation(
    () =>
      new Promise((resolve) => {
        complete = resolve;
      }),
  );
  try {
    await client.initialize();
    let settled = false;
    const original = client.call('profile.get');
    original.then(
      () => {
        settled = true;
      },
      () => {
        settled = true;
      },
    );
    await flush();
    expect(await h.send(request(2, 'profile.get'))).toEqual(sequenceError());
    expect(await h.send(request(2, 'profile..get', []))).toEqual(sequenceError());
    expect(h.profile.get).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
    expect(vi.getTimerCount()).toBe(1);
    if (complete === undefined) {
      throw new Error('original provider must still be pending');
    }
    complete({ displayName: 'Original call' });
    await expect(original).resolves.toEqual({ displayName: 'Original call' });
    expect(vi.getTimerCount()).toBe(0);
  } finally {
    client.close();
    vi.useRealTimers();
  }
});
