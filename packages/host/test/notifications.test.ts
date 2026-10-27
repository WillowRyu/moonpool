/** T15 — typed, connection-bound host notifications carry no request id. */
import { createHost, type HostConfig } from '@moonpool/host';
import {
  ERROR_CODES,
  type JsonValue,
  type PortalEnvironmentChangedParams,
  type PortalLifecycleState,
  type ProfileGetResult,
  type Transport,
} from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { createClient } from '../../client/src/index';

function config(): HostConfig {
  return {
    hostInfo: { name: 'notification-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.notifications',
      name: 'Notifications',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: [],
    },
    grantedScopes: [],
    environment: { locale: 'en', colorScheme: 'light' },
  };
}

function setup(host = createHost(config())) {
  let receive: ((message: JsonValue) => void) | undefined;
  const sent: JsonValue[] = [];
  const send = vi.fn((frame: JsonValue) => {
    sent.push(frame);
  });
  const onMessage = vi.fn((handler: (message: JsonValue) => void) => {
    receive = handler;
    return () => {
      receive = undefined;
    };
  });
  const close = vi.fn();
  const transport: Transport = { send, onMessage, close };
  const connection = host.connect(transport);
  function inject(frame: JsonValue) {
    if (receive === undefined) {
      throw new Error('host receiver must be registered');
    }
    receive(frame);
    return sent.at(-1);
  }
  return { host, connection, transport, send, onMessage, close, sent, inject };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const states: PortalLifecycleState[] = ['paused', 'resumed'];
const changes: PortalEnvironmentChangedParams[] = [
  {},
  { colorScheme: 'light' },
  { colorScheme: 'dark' },
  { locale: 'ko-KR' },
  { locale: '' },
  { locale: '  arbitrary host text 😀  ' },
  { colorScheme: 'dark', locale: 'ko-KR' },
];

describe('SPEC §6.4 — exact outbound notification frames', () => {
  it.each(states)('sends %s lifecycle state without an id or timer', async (state) => {
    const h = setup();
    await expect(h.connection.notifyLifecycle(state)).resolves.toBeUndefined();
    expect(h.sent).toEqual([{ jsonrpc: '2.0', method: 'portal.lifecycle', params: { state } }]);
    expect(h.send).toHaveBeenCalledOnce();
    expect(h.onMessage).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each(changes)('sends environment changes %j with only present fields', async (change) => {
    const h = setup();
    await expect(h.connection.notifyEnvironmentChanged(change)).resolves.toBeUndefined();
    expect(h.sent).toEqual([
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: change },
    ]);
    expect(h.send).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('preserves invocation order without waiting for a peer response', async () => {
    const h = setup();
    const first = h.connection.notifyLifecycle('paused');
    const second = h.connection.notifyEnvironmentChanged({ colorScheme: 'dark' });
    const third = h.connection.notifyLifecycle('resumed');
    await Promise.all([first, second, third]);
    expect(h.sent).toEqual([
      { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'paused' } },
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { colorScheme: 'dark' } },
      { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'resumed' } },
    ]);
    expect(h.onMessage).toHaveBeenCalledOnce();
    expect(h.close).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('copies environment fields before transport delivery so later caller mutation cannot alter them', async () => {
    const h = setup();
    const change: PortalEnvironmentChangedParams = { locale: 'en', colorScheme: 'dark' };
    const submitted = h.connection.notifyEnvironmentChanged(change);
    change.locale = 'ko-KR';
    change.colorScheme = 'light';
    await submitted;
    expect(h.sent).toEqual([
      {
        jsonrpc: '2.0',
        method: 'portal.environmentChanged',
        params: { locale: 'en', colorScheme: 'dark' },
      },
    ]);
  });

  it('accepts frozen and null-prototype records without modifying them', async () => {
    const h = setup();
    const change = { locale: 'ko-KR' };
    Object.setPrototypeOf(change, null);
    Object.freeze(change);
    await h.connection.notifyEnvironmentChanged(change);
    expect(h.sent).toEqual([
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { locale: 'ko-KR' } },
    ]);
    expect(Object.isFrozen(change)).toBe(true);
    expect(Object.getPrototypeOf(change)).toBeNull();
  });
});

describe('ADR 0020 — runtime validation of local sender arguments', () => {
  it.each([undefined, null, false, 0, '', 'Paused', 'stopped', { state: 'paused' }])(
    'rejects invalid lifecycle state %j before sending',
    async (state) => {
      const h = setup();
      // Pass the original unknown value across the JavaScript boundary without assertions.
      const call = () => Reflect.apply(h.connection.notifyLifecycle, undefined, [state]);
      let result: unknown;
      expect(() => {
        result = call();
      }).not.toThrow();
      await expect(result).rejects.toEqual(new TypeError('invalid portal.lifecycle state'));
      expect(h.send).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  const invalidChanges: Array<[string, unknown]> = [
    ['undefined', undefined],
    ['null', null],
    ['scalar', 'dark'],
    ['array', []],
    ['invalid color scheme', { colorScheme: 'automatic' }],
    ['null color scheme', { colorScheme: null }],
    ['undefined color scheme', { colorScheme: undefined }],
    ['numeric locale', { locale: 42 }],
    ['null locale', { locale: null }],
    ['undefined locale', { locale: undefined }],
    ['extra field', { locale: 'en', token: 'host-secret' }],
    ['forged id', { locale: 'en', id: 123 }],
    ['Date', new Date(0)],
    ['inherited fields', Object.create({ locale: 'en' })],
    ['symbol field', { [Symbol('invalid')]: 'hidden' }],
    ['hidden field', Object.defineProperty({}, 'locale', { value: 'en' })],
  ];
  it.each(invalidChanges)(
    'rejects %s before transport access without echoing input',
    async (_name, change) => {
      const h = setup();
      let result: unknown;
      expect(() => {
        result = Reflect.apply(h.connection.notifyEnvironmentChanged, undefined, [change]);
      }).not.toThrow();
      await expect(result).rejects.toEqual(
        new TypeError('invalid portal.environmentChanged params'),
      );
      expect(h.send).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('does not run getters, toJSON, or state conversion', async () => {
    const h = setup();
    const getter = vi.fn(() => 'en');
    const toJSON = vi.fn(() => ({}));
    const stringifyState = vi.fn(() => 'paused');
    const accessor = Object.defineProperty({}, 'locale', { enumerable: true, get: getter });
    await expect(
      Reflect.apply(h.connection.notifyEnvironmentChanged, undefined, [accessor]),
    ).rejects.toBeInstanceOf(TypeError);
    await expect(
      Reflect.apply(h.connection.notifyEnvironmentChanged, undefined, [{ toJSON }]),
    ).rejects.toBeInstanceOf(TypeError);
    await expect(
      Reflect.apply(h.connection.notifyLifecycle, undefined, [{ toString: stringifyState }]),
    ).rejects.toBeInstanceOf(TypeError);
    expect(getter).not.toHaveBeenCalled();
    expect(toJSON).not.toHaveBeenCalled();
    expect(stringifyState).not.toHaveBeenCalled();
    expect(h.send).not.toHaveBeenCalled();
  });

  it('rejects uninspectable params and stays usable afterward', async () => {
    const h = setup();
    const revoked = Proxy.revocable({}, {});
    revoked.revoke();
    await expect(
      Reflect.apply(h.connection.notifyEnvironmentChanged, undefined, [revoked.proxy]),
    ).rejects.toBeInstanceOf(TypeError);
    await h.connection.notifyEnvironmentChanged({});
    expect(h.send).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe('SPEC §3.1 / §4 / §6.4 — connection and request isolation', () => {
  it("sends only through the handle's transport when one host has multiple connections", async () => {
    const host = createHost(config());
    const first = setup(host);
    const second = setup(host);
    await first.connection.notifyLifecycle('paused');
    expect(second.sent).toEqual([]);
    await second.connection.notifyEnvironmentChanged({ locale: 'ko-KR' });
    expect(first.sent).toEqual([
      { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'paused' } },
    ]);
    expect(second.sent).toEqual([
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { locale: 'ko-KR' } },
    ]);
  });

  it('does not initialize the connection or change its request-id floor', async () => {
    const h = setup();
    await h.connection.notifyLifecycle('resumed');
    expect(h.inject({ jsonrpc: '2.0', id: 1, method: 'portal.ping' })).toMatchObject({
      error: { code: ERROR_CODES.NOT_INITIALIZED },
    });
    h.inject({
      jsonrpc: '2.0',
      id: 1,
      method: 'portal.initialize',
      params: { protocolVersion: '0.1' },
    });
    await h.connection.notifyLifecycle('paused');
    expect(h.inject({ jsonrpc: '2.0', id: 1, method: 'portal.ping' })).toMatchObject({
      id: null,
      error: { code: ERROR_CODES.INVALID_REQUEST },
    });
    expect(h.inject({ jsonrpc: '2.0', id: 2, method: 'portal.ping' })).toEqual({
      jsonrpc: '2.0',
      id: 2,
      result: { pong: true },
    });
  });

  it('does not mutate host configuration or grant a capability', async () => {
    const hostConfig = config();
    Object.freeze(hostConfig.environment);
    const h = setup(createHost(hostConfig));
    await h.connection.notifyEnvironmentChanged({ locale: 'ko-KR', colorScheme: 'dark' });
    expect(hostConfig.environment).toEqual({ locale: 'en', colorScheme: 'light' });
    expect(
      h.inject({
        jsonrpc: '2.0',
        id: 1,
        method: 'portal.initialize',
        params: { protocolVersion: '0.1' },
      }),
    ).toMatchObject({
      result: { environment: { locale: 'en', colorScheme: 'light' }, grantedScopes: [] },
    });
    expect(h.inject({ jsonrpc: '2.0', id: 2, method: 'profile.get' })).toMatchObject({
      error: { code: ERROR_CODES.PERMISSION_DENIED },
    });
  });

  it.each(['lifecycle', 'environment'])(
    'rejects a local send failure for %s without retries or timers',
    async (kind) => {
      const h = setup();
      const failure = new Error('local transport failure');
      h.send.mockImplementationOnce(() => {
        throw failure;
      });
      let result: Promise<void> | undefined;
      expect(() => {
        result =
          kind === 'lifecycle'
            ? h.connection.notifyLifecycle('paused')
            : h.connection.notifyEnvironmentChanged({ colorScheme: 'dark' });
      }).not.toThrow();
      await expect(result).rejects.toBe(failure);
      expect(h.send).toHaveBeenCalledOnce();
      expect(h.close).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
      await h.connection.notifyLifecycle('resumed');
      expect(h.send).toHaveBeenCalledTimes(2);
    },
  );

  it('cannot settle a real client request or clear its timer', async () => {
    const bridge = createLinkedTransports();
    let finish: ((result: ProfileGetResult) => void) | undefined;
    const hostConfig = config();
    hostConfig.manifest.permissions = ['profile'];
    hostConfig.grantedScopes = ['profile'];
    hostConfig.capabilities = {
      profile: {
        get: () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      },
    };
    const connection = createHost(hostConfig).connect(bridge.b);
    const client = createClient({ transport: bridge.a, timeoutMs: 1_000 });
    const requests: JsonValue[] = [];
    bridge.b.onMessage((frame) => {
      requests.push(frame);
    });
    try {
      await client.initialize();
      const settled = vi.fn();
      const pending = client.call('profile.get');
      pending.then(settled, settled);
      await flush();
      await connection.notifyLifecycle('paused');
      await connection.notifyEnvironmentChanged({ locale: 'ko-KR' });
      await flush();
      expect(settled).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(1);
      expect(requests).toHaveLength(2);
      if (finish === undefined) {
        throw new Error('profile must still be waiting');
      }
      finish({ displayName: 'Still matched' });
      await expect(pending).resolves.toEqual({ displayName: 'Still matched' });
      expect(vi.getTimerCount()).toBe(0);
    } finally {
      client.close();
      bridge.b.close();
    }
  });

  it('leaves the original client deadline intact when only notifications arrive', async () => {
    const bridge = createLinkedTransports();
    const hostConfig = config();
    hostConfig.manifest.permissions = ['profile'];
    hostConfig.grantedScopes = ['profile'];
    hostConfig.capabilities = { profile: { get: () => new Promise<ProfileGetResult>(() => {}) } };
    const connection = createHost(hostConfig).connect(bridge.b);
    const client = createClient({ transport: bridge.a, timeoutMs: 1_000 });
    try {
      await client.initialize();
      let settled = false;
      const outcome = client.call('profile.get').catch((error: unknown) => {
        settled = true;
        return error;
      });
      await vi.advanceTimersByTimeAsync(500);
      await connection.notifyLifecycle('paused');
      await vi.advanceTimersByTimeAsync(499);
      expect(settled).toBe(false);
      expect(vi.getTimerCount()).toBe(1);
      await vi.advanceTimersByTimeAsync(1);
      expect(await outcome).toMatchObject({ code: ERROR_CODES.TIMEOUT });
      expect(vi.getTimerCount()).toBe(0);
    } finally {
      client.close();
      bridge.b.close();
    }
  });
});
