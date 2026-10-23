/** T12 — invalid responses cannot consume a pending call or its timeout. */
import { createClient, type MoonpoolClient, MoonpoolError } from '@moonpool/client';
import { ERROR_CODES, type JsonValue, type Transport } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createHost } from '../../host/src/index';
import { createLinkedTransports, flush } from './helpers/memory-transport';

const clients: MoonpoolClient[] = [];

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  for (const client of clients.splice(0)) {
    client.close();
  }
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function setup() {
  let receive: ((message: JsonValue) => void) | undefined;
  const sent: JsonValue[] = [];
  const transport: Transport = {
    send(message) {
      sent.push(message);
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
  const client = createClient({ transport, timeoutMs: 1_000 });
  clients.push(client);
  function inject(value: unknown) {
    if (receive === undefined) {
      throw new Error('client receiver must be attached');
    }
    // Exercise the runtime boundary with the original value, without casting or encoding.
    Reflect.apply(receive, undefined, [value]);
  }
  return { client, sent, inject };
}

function observe(promise: Promise<unknown>) {
  const settled = vi.fn();
  const outcome = promise.then(
    (value) => {
      settled();
      return { value };
    },
    (error: unknown) => {
      settled();
      return { error };
    },
  );
  return { settled, outcome };
}

function success(id = 1, result: unknown = null) {
  return { jsonrpc: '2.0', id, result };
}

const malformed: Array<[string, () => unknown]> = [
  ['wrong version', () => ({ ...success(), jsonrpc: '1.0' })],
  ['string id', () => ({ ...success(), id: '1' })],
  ['batch', () => [success()]],
  ['notification', () => ({ jsonrpc: '2.0', method: 'portal.pause' })],
  ['neither outcome', () => ({ jsonrpc: '2.0', id: 1 })],
  ['both outcomes', () => ({ ...success(), error: { code: -32603, message: 'Internal error' } })],
  ['undefined error', () => ({ ...success(), error: undefined })],
  [
    'undefined result',
    () => ({ ...success(), result: undefined, error: { code: -32603, message: 'Internal error' } }),
  ],
  ['non-JSON result', () => success(1, { nested: undefined })],
  ['Date result', () => success(1, new Date(0))],
  ['non-JSON extra', () => ({ ...success(), extra: Number.NaN })],
  [
    'fractional error code',
    () => ({ jsonrpc: '2.0', id: 1, error: { code: -32603.5, message: 'Invalid code' } }),
  ],
  ['missing error message', () => ({ jsonrpc: '2.0', id: 1, error: { code: -32603 } })],
  [
    'non-JSON error data',
    () => ({
      jsonrpc: '2.0',
      id: 1,
      error: { code: -32603, message: 'Internal error', data: new Map() },
    }),
  ],
  ['inherited fields', () => Object.create(success())],
  [
    'cycle',
    () => {
      const result: Record<string, unknown> = {};
      result.self = result;
      return success(1, result);
    },
  ],
];

describe('SPEC §4.3 / §4.5 — validate before correlation', () => {
  it.each(malformed)(
    'ignores %s and still accepts a later matching response',
    async (_name, make) => {
      const h = setup();
      const first = observe(h.client.call('portal.ping'));
      const second = observe(h.client.call('profile.get'));
      h.inject(make());
      await flush();
      expect(first.settled).not.toHaveBeenCalled();
      expect(second.settled).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(2);
      expect(h.sent).toHaveLength(2);

      h.inject(success(2, { displayName: 'Second reply first' }));
      expect(await second.outcome).toEqual({ value: { displayName: 'Second reply first' } });
      expect(first.settled).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(1);
      h.inject(success(1, false));
      expect(await first.outcome).toEqual({ value: false });
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('keeps the original deadline after repeated malformed responses', async () => {
    const h = setup();
    const pending = observe(h.client.call('portal.ping'));
    await vi.advanceTimersByTimeAsync(500);
    h.inject(success(1, new Date(0)));
    await vi.advanceTimersByTimeAsync(499);
    h.inject({ ...success(), error: undefined });
    await flush();
    expect(pending.settled).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.TIMEOUT } });
    expect(pending.settled).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
    h.inject(success());
    await flush();
    expect(pending.settled).toHaveBeenCalledOnce();
  });

  it('does not execute getters or toJSON, and stays usable after inspection failures', async () => {
    const h = setup();
    const pending = observe(h.client.call('portal.ping'));
    const getter = vi.fn(() => {
      throw new Error('must not execute');
    });
    const toJSON = vi.fn(() => null);
    const accessor = Object.defineProperty(success(), 'id', { enumerable: true, get: getter });
    const revoked = Proxy.revocable(success(), {});
    revoked.revoke();
    for (const frame of [accessor, success(1, { toJSON }), revoked.proxy]) {
      expect(() => h.inject(frame)).not.toThrow();
    }
    await flush();
    expect(getter).not.toHaveBeenCalled();
    expect(toJSON).not.toHaveBeenCalled();
    expect(pending.settled).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);
    h.inject(success(1, true));
    expect(await pending.outcome).toEqual({ value: true });
  });

  it.each([null, false, 0, '', [], {}])(
    'resolves the valid result %j exactly once',
    async (result) => {
      const h = setup();
      const pending = observe(h.client.call('portal.ping'));
      h.inject(success(1, result));
      expect(await pending.outcome).toEqual({ value: result });
      h.inject({ jsonrpc: '2.0', id: 1, error: { code: -32603, message: 'Duplicate reply' } });
      await flush();
      expect(pending.settled).toHaveBeenCalledOnce();
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it.each([undefined, null, false, 0, '', { scope: 'profile' }])(
    'maps valid errors with data %j without changing their code or message',
    async (data) => {
      const h = setup();
      const pending = observe(h.client.call('profile.get'));
      const error: Record<string, JsonValue> = { code: 1234, message: '' };
      if (data !== undefined) {
        error.data = data;
      }
      h.inject({ jsonrpc: '2.0', id: 1, error });
      expect(await pending.outcome).toEqual({ error: new MoonpoolError(1234, '', data) });
      expect(await pending.outcome).toMatchObject({
        error: { name: 'MoonpoolError', code: 1234, message: '', data },
      });
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('ignores unknown, duplicate, and expired ids while another call is pending', async () => {
    const h = setup();
    const expired = observe(h.client.call('portal.ping'));
    await vi.advanceTimersByTimeAsync(500);
    const active = observe(h.client.call('profile.get'));
    await vi.advanceTimersByTimeAsync(500);
    expect(await expired.outcome).toMatchObject({ error: { code: ERROR_CODES.TIMEOUT } });
    for (const id of [1, 0, -1, 1.5, 999]) {
      h.inject(success(id));
    }
    h.inject({ jsonrpc: '2.0', id: null, error: { code: -32600, message: 'Invalid Request' } });
    await flush();
    expect(active.settled).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);
    h.inject(success(2, { displayName: 'Still waiting' }));
    expect(await active.outcome).toEqual({ value: { displayName: 'Still waiting' } });
    h.inject(success(2, 'duplicate'));
    await flush();
    expect(active.settled).toHaveBeenCalledOnce();
    expect(h.sent).toHaveLength(2);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('preserves host-sanitized provider errors through a real connection', async () => {
    const scheduled: Array<() => void> = [];
    vi.spyOn(globalThis, 'queueMicrotask').mockImplementation((callback) => {
      scheduled.push(callback);
    });
    const bridge = createLinkedTransports();
    const client = createClient({ transport: bridge.a });
    clients.push(client);
    const secret = new Error('private host credential: test-secret');
    createHost({
      hostInfo: { name: 'response-test-host', version: '0.1.0', platform: 'browser' },
      manifest: {
        manifestVersion: 1,
        id: 'com.example.responses',
        name: 'Responses',
        version: '1.0.0',
        entry: 'index.html',
        protocolVersion: '0.1',
        permissions: ['profile'],
      },
      grantedScopes: ['profile'],
      environment: { locale: 'en', colorScheme: 'light' },
      capabilities: {
        profile: {
          get: async () => {
            throw secret;
          },
        },
      },
    }).connect(bridge.b);
    try {
      await client.initialize();
      const pending = observe(client.call('profile.get'));
      const outcome = await pending.outcome;
      expect(outcome).toMatchObject({
        error: {
          code: ERROR_CODES.INTERNAL_ERROR,
          message: 'profile.get failed inside the host',
          data: undefined,
        },
      });
      expect(JSON.stringify(outcome)).not.toContain('test-secret');
      expect(scheduled).toHaveLength(1);
      expect(scheduled[0]).toThrow(secret);
      expect(vi.getTimerCount()).toBe(0);
    } finally {
      bridge.b.close();
    }
  });
});
