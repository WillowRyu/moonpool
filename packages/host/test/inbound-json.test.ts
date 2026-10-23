/** T11 — exercise unknown inbound values without serialization or type assertions. */
import { createHost } from '@moonpool/host';
import { ERROR_CODES, type JsonValue, type Transport } from '@moonpool/protocol';
import { describe, expect, it, vi } from 'vitest';
import { flush } from './helpers/memory-transport';

function setup(grants = ['profile', 'storage'], provide = true) {
  let receive: ((message: JsonValue) => void) | undefined;
  const replies: JsonValue[] = [];
  const profile = { get: vi.fn(async () => ({ displayName: 'JSON test user' })) };
  const storage = {
    get: vi.fn(async () => null),
    set: vi.fn(async (_id: string, _key: string, _value: JsonValue) => {}),
    delete: vi.fn(async () => {}),
  };
  const transport: Transport = {
    send(message) {
      replies.push(message);
    },
    onMessage(handler) {
      receive = handler;
      return () => {
        receive = undefined;
      };
    },
    close() {
      receive = undefined;
    },
  };
  createHost({
    hostInfo: { name: 'json-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.json',
      name: 'JSON test',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile', 'storage'],
    },
    grantedScopes: grants,
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: provide ? { profile, storage } : {},
  }).connect(transport);
  async function inject(value: unknown) {
    if (receive === undefined) {
      throw new Error('host receiver must be attached');
    }
    // The test intentionally models a transport violating its compile-time promise.
    // Reflect.apply preserves the actual unknown value, including invalid members.
    Reflect.apply(receive, undefined, [value]);
    await flush();
    return replies.at(-1);
  }
  return { inject, replies, profile, storage };
}

function frame(id = 2, method = 'profile.get', params: unknown = {}) {
  return { jsonrpc: '2.0', id, method, params };
}
async function initialize(h: ReturnType<typeof setup>, id = 1) {
  expect(await h.inject(frame(id, 'portal.initialize', { protocolVersion: '0.1' }))).toMatchObject({
    id,
    result: { protocolVersion: '0.1' },
  });
}

describe('T11 — valid JSON remains usable', () => {
  it('accepts extra envelope JSON members without interpreting them as permission', async () => {
    const h = setup(['profile']);
    const extra = { nested: [null, false, 0, '', { enabled: true }] };
    expect(
      await h.inject({
        ...frame(1, 'portal.initialize', { protocolVersion: '0.1' }),
        extra,
        grantedScopes: ['storage'],
      }),
    ).toMatchObject({ result: { grantedScopes: ['profile'] } });
    expect(await h.inject({ ...frame(), extra })).toMatchObject({
      result: { displayName: 'JSON test user' },
    });
    expect(h.profile.get).toHaveBeenCalledOnce();
  });

  it('accepts null-prototype records and an own __proto__ data key', async () => {
    const h = setup();
    await initialize(h);
    const message = frame();
    Object.setPrototypeOf(message, null);
    Object.setPrototypeOf(message.params, null);
    Object.defineProperty(message, '__proto__', { enumerable: true, value: { legitimate: true } });
    expect(await h.inject(message)).toMatchObject({ result: { displayName: 'JSON test user' } });
  });

  it('preserves the original shared storage value', async () => {
    const h = setup();
    await initialize(h);
    const shared = { enabled: true };
    const value = { left: shared, right: shared, nested: [null, false, 0, ''] };
    expect(
      await h.inject({ ...frame(2, 'storage.set', { key: 'settings', value }), extra: shared }),
    ).toEqual({ jsonrpc: '2.0', id: 2, result: {} });
    expect(h.storage.set.mock.calls[0]?.[2]).toBe(value);
  });

  it('accepts deeply nested and repeatedly shared extra envelope data', async () => {
    const h = setup();
    await initialize(h);
    let deep: JsonValue = null;
    for (let i = 0; i < 10_000; i += 1) {
      deep = { next: deep };
    }
    let shared: JsonValue = { leaf: true };
    for (let i = 0; i < 30; i += 1) {
      shared = { left: shared, right: shared };
    }
    expect(await h.inject({ ...frame(), deep, shared })).toMatchObject({
      result: { displayName: 'JSON test user' },
    });
  });
});

function error(id: number | null, code: number) {
  return { jsonrpc: '2.0', id, error: { code, message: expect.any(String) } };
}

const INVALID_TREES: Array<{ label: string; make: () => unknown }> = [
  { label: 'undefined', make: () => undefined },
  { label: 'nested undefined', make: () => ({ value: undefined }) },
  { label: 'NaN', make: () => Number.NaN },
  { label: 'infinity', make: () => Number.POSITIVE_INFINITY },
  { label: 'Date', make: () => new Date(0) },
  { label: 'Map', make: () => new Map([['key', 'value']]) },
  { label: 'Set', make: () => new Set([1]) },
  { label: 'typed array', make: () => new Uint8Array([1]) },
  { label: 'bigint', make: () => 1n },
  { label: 'function', make: () => () => 'not data' },
  { label: 'symbol', make: () => Symbol('not data') },
  { label: 'sparse array', make: () => new Array(1) },
  {
    label: 'cycle',
    make: () => {
      const value: { self?: unknown } = {};
      value.self = value;
      return value;
    },
  },
];

describe('T11 — non-JSON data outside params', () => {
  it.each(INVALID_TREES)('rejects extra $label before any provider', async ({ make }) => {
    const h = setup();
    await initialize(h);
    const message = { ...frame(), extra: make() };
    expect(await h.inject(message)).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
    expect(h.profile.get).not.toHaveBeenCalled();
    expect(Object.hasOwn(message, 'extra')).toBe(true);
  });

  it.each(['jsonrpc', 'method', 'params', 'extra'])(
    'rejects the envelope accessor %s without evaluating it',
    async (key) => {
      const h = setup();
      await initialize(h);
      const get = vi.fn(() => {
        throw new Error('getter must not run');
      });
      const message = frame();
      Object.defineProperty(message, key, { enumerable: true, get });
      expect(await h.inject(message)).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
      expect(get).not.toHaveBeenCalled();
      expect(h.profile.get).not.toHaveBeenCalled();
    },
  );

  it('does not run an id getter to manufacture an addressable request', async () => {
    const h = setup();
    const get = vi.fn(() => 1);
    const message = frame(1, 'portal.initialize', { protocolVersion: '0.1' });
    Object.defineProperty(message, 'id', { enumerable: true, get });
    await h.inject(message);
    expect(h.replies).toEqual([]);
    expect(get).not.toHaveBeenCalled();
  });

  it.each(['hidden member', 'symbol member', 'nonordinary root', 'inherited method'])(
    'rejects %s envelope structure',
    async (label) => {
      const h = setup();
      await initialize(h);
      const message: Record<string, unknown> = frame();
      if (label === 'hidden member') {
        Object.defineProperty(message, 'extra', { value: 1 });
      }
      if (label === 'symbol member') {
        Object.defineProperty(message, Symbol('extra'), { value: 1, enumerable: true });
      }
      if (label === 'nonordinary root') {
        Object.setPrototypeOf(message, Date.prototype);
      }
      if (label === 'inherited method') {
        delete message.method;
        Object.setPrototypeOf(message, { method: 'profile.get' });
      }
      expect(await h.inject(message)).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
      expect(h.profile.get).not.toHaveBeenCalled();
    },
  );

  it('does not invoke toJSON or echo its invalid input', async () => {
    const h = setup();
    await initialize(h);
    const toJSON = vi.fn(() => frame());
    const reply = await h.inject({ ...frame(), toJSON, marker: 'private-input-marker' });
    expect(reply).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
    expect(toJSON).not.toHaveBeenCalled();
    expect(JSON.stringify(reply)).not.toContain('private-input-marker');
  });

  it('rejects a callable root with a recoverable own numeric id without calling it', async () => {
    const h = setup();
    await initialize(h);
    const callable = vi.fn();
    Object.assign(callable, frame());
    expect(await h.inject(callable)).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
    expect(callable).not.toHaveBeenCalled();
    expect(h.profile.get).not.toHaveBeenCalled();
  });

  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'uses a JSON null response id for %s',
    async (id) => {
      const h = setup();
      expect(await h.inject(frame(id))).toEqual(error(null, ERROR_CODES.INVALID_REQUEST));
    },
  );

  it('rejects reflection failure after safely recovering an id', async () => {
    const h = setup();
    await initialize(h);
    const message = new Proxy(frame(), {
      ownKeys() {
        throw new Error('inspection failed');
      },
    });
    expect(await h.inject(message)).toEqual(error(2, ERROR_CODES.INVALID_REQUEST));
    expect(h.profile.get).not.toHaveBeenCalled();
  });

  it('drops an uninspectable value without throwing or invoking a provider', async () => {
    const h = setup();
    const { proxy, revoke } = Proxy.revocable({}, {});
    revoke();
    await expect(h.inject(proxy)).resolves.toBeUndefined();
    expect(h.replies).toEqual([]);
    expect(h.profile.get).not.toHaveBeenCalled();
  });
});

describe('T11 — deep params validation after grants', () => {
  it.each(INVALID_TREES)(
    'rejects $label in granted unknown-method params before lookup',
    async ({ make }) => {
      const h = setup();
      await initialize(h);
      expect(await h.inject(frame(2, 'profile.unknown', { value: make() }))).toEqual(
        error(2, ERROR_CODES.INVALID_PARAMS),
      );
      expect(h.profile.get).not.toHaveBeenCalled();
    },
  );

  it.each(['portal.ping', 'profile.get', 'storage.get', 'storage.set', 'storage.delete'])(
    'does not invoke a params getter for %s',
    async (method) => {
      const h = setup();
      await initialize(h);
      const get = vi.fn(() => 'computed');
      const params = Object.defineProperty({}, 'key', { enumerable: true, get });
      expect(await h.inject(frame(2, method, params))).toEqual(
        error(2, ERROR_CODES.INVALID_PARAMS),
      );
      expect(get).not.toHaveBeenCalled();
      expect(h.profile.get).not.toHaveBeenCalled();
      expect(h.storage.get).not.toHaveBeenCalled();
      expect(h.storage.set).not.toHaveBeenCalled();
      expect(h.storage.delete).not.toHaveBeenCalled();
    },
  );

  it('distinguishes explicit undefined params from omission', async () => {
    const h = setup();
    await initialize(h);
    expect(await h.inject({ ...frame(), params: undefined })).toEqual(
      error(2, ERROR_CODES.INVALID_PARAMS),
    );
    expect(await h.inject({ jsonrpc: '2.0', id: 3, method: 'profile.get' })).toMatchObject({
      id: 3,
      result: { displayName: 'JSON test user' },
    });
  });

  it('keeps initialization and permission errors before deep params errors', async () => {
    const h = setup([]);
    expect(await h.inject(frame(1, 'profile.get', { bad: new Date(0) }))).toEqual(
      error(1, ERROR_CODES.NOT_INITIALIZED),
    );
    await initialize(h, 2);
    expect(await h.inject(frame(3, 'profile.get', { bad: new Date(0) }))).toMatchObject({
      id: 3,
      error: { code: ERROR_CODES.PERMISSION_DENIED },
    });
  });

  it('checks deep params before provider availability', async () => {
    const h = setup(['profile'], false);
    await initialize(h);
    expect(await h.inject(frame(2, 'profile.get', new Date(0)))).toEqual(
      error(2, ERROR_CODES.INVALID_PARAMS),
    );
  });
});

describe('T11 — id and initialization boundaries', () => {
  it('consumes a new invalid-envelope id and rejects reuse without echoing it', async () => {
    const h = setup();
    await initialize(h);
    expect(await h.inject({ ...frame(5), extra: undefined })).toEqual(
      error(5, ERROR_CODES.INVALID_REQUEST),
    );
    expect(await h.inject({ ...frame(5), extra: new Date(0) })).toEqual(
      error(null, ERROR_CODES.INVALID_REQUEST),
    );
    expect(await h.inject(frame(6))).toMatchObject({ result: { displayName: 'JSON test user' } });
  });

  it('does not reset a document for invalid envelope data on initialize', async () => {
    const h = setup();
    await initialize(h, 9);
    expect(
      await h.inject({
        ...frame(1, 'portal.initialize', { protocolVersion: '0.1' }),
        extra: undefined,
      }),
    ).toEqual(error(null, ERROR_CODES.INVALID_REQUEST));
    expect(
      await h.inject({
        ...frame(10, 'portal.initialize', { protocolVersion: '0.1' }),
        extra: undefined,
      }),
    ).toEqual(error(10, ERROR_CODES.INVALID_REQUEST));
    expect(await h.inject(frame(10))).toEqual(error(null, ERROR_CODES.INVALID_REQUEST));
    expect(await h.inject(frame(11))).toMatchObject({ result: { displayName: 'JSON test user' } });
  });

  it('resets a general-shaped initialize before rejecting its deep params without evaluating getters', async () => {
    const h = setup(['profile']);
    await initialize(h, 9);
    const get = vi.fn(() => '0.1');
    const params = Object.defineProperty({}, 'protocolVersion', { get, enumerable: true });
    expect(await h.inject(frame(1, 'portal.initialize', params))).toEqual(
      error(1, ERROR_CODES.INVALID_PARAMS),
    );
    expect(get).not.toHaveBeenCalled();
    expect(await h.inject(frame(2))).toEqual(error(2, ERROR_CODES.NOT_INITIALIZED));
    expect(await h.inject(frame(2))).toEqual(error(null, ERROR_CODES.INVALID_REQUEST));
    await initialize(h, 3);
    expect(await h.inject(frame(4))).toMatchObject({ result: { displayName: 'JSON test user' } });
  });

  it('retains batch rejection and notification silence without inspecting their members', async () => {
    const h = setup();
    expect(await h.inject([new Date(0)])).toEqual(error(null, ERROR_CODES.INVALID_REQUEST));
    await h.inject({ jsonrpc: '2.0', method: 'profile.get', extra: new Date(0) });
    expect(h.replies).toHaveLength(1);
  });

  it('validates frozen inputs without changing them', async () => {
    const h = setup();
    await initialize(h);
    const message = Object.freeze(frame(2, 'profile.get', Object.freeze({})));
    expect(await h.inject(message)).toMatchObject({ result: { displayName: 'JSON test user' } });
    expect(Object.isFrozen(message)).toBe(true);
  });
});
