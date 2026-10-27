/** T16 — known notifications reach isolated subscribers, never pending calls. */
import { createClient } from '@moonpool/client';
import {
  ERROR_CODES,
  type HostNotification,
  type JsonValue,
  type ProfileGetResult,
  type Transport,
} from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from '../../../test-support/memory-transport';
import { createHost } from '../../host/src/index';

const cleanups: Array<() => void> = [];
let reports: Array<() => void>;
beforeEach(() => {
  vi.useFakeTimers();
  reports = [];
  vi.spyOn(globalThis, 'queueMicrotask').mockImplementation((callback) => {
    reports.push(callback);
  });
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) {
    cleanup();
  }
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function setup() {
  let receive: ((message: JsonValue) => void) | undefined;
  const send = vi.fn((_frame: JsonValue) => {});
  const unsubscribe = vi.fn(() => {});
  const close = vi.fn(() => {});
  const onMessage = vi.fn((handler: (message: JsonValue) => void) => {
    receive = handler;
    // Retain the callback to test delivery already queued before close.
    return unsubscribe;
  });
  const transport: Transport = { send, onMessage, close };
  const client = createClient({ transport, timeoutMs: 1_000 });
  function inject(value: unknown) {
    if (receive === undefined) {
      throw new Error('client receiver must be registered');
    }
    Reflect.apply(receive, undefined, [value]);
  }
  cleanups.push(() => {
    unsubscribe.mockReset();
    close.mockReset();
    client.close();
  });
  return { client, inject, send, onMessage, unsubscribe, close };
}

function lifecycle(state: unknown = 'paused') {
  return { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state } };
}
function environment(params: unknown = {}) {
  return { jsonrpc: '2.0', method: 'portal.environmentChanged', params };
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

describe('SPEC §6.4 — known notification delivery', () => {
  const valid: Array<[string, unknown, HostNotification]> = [
    [
      'paused',
      lifecycle(),
      { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'paused' } },
    ],
    [
      'resumed',
      lifecycle('resumed'),
      { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'resumed' } },
    ],
    [
      'empty change',
      environment(),
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: {} },
    ],
    [
      'omitted change',
      { jsonrpc: '2.0', method: 'portal.environmentChanged' },
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: {} },
    ],
    [
      'dark',
      environment({ colorScheme: 'dark' }),
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { colorScheme: 'dark' } },
    ],
    [
      'light',
      environment({ colorScheme: 'light' }),
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { colorScheme: 'light' } },
    ],
    [
      'locale',
      environment({ locale: 'ko-KR' }),
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { locale: 'ko-KR' } },
    ],
    [
      'empty locale',
      environment({ locale: '' }),
      { jsonrpc: '2.0', method: 'portal.environmentChanged', params: { locale: '' } },
    ],
    [
      'both fields',
      environment({ colorScheme: 'dark', locale: '  text 😀  ' }),
      {
        jsonrpc: '2.0',
        method: 'portal.environmentChanged',
        params: { colorScheme: 'dark', locale: '  text 😀  ' },
      },
    ],
  ];
  it.each(valid)(
    'delivers %s as a typed event without sending or creating timers',
    (_name, frame, expected) => {
      const h = setup();
      const listener = vi.fn((_event: HostNotification) => {});
      h.client.onNotification(listener);
      h.inject(frame);
      expect(listener).toHaveBeenCalledExactlyOnceWith(expected);
      expect(h.send).not.toHaveBeenCalled();
      expect(h.onMessage).toHaveBeenCalledOnce();
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('projects known fields from JSON extension members and accepts null prototypes', () => {
    const h = setup();
    const listener = vi.fn((_event: HostNotification) => {});
    h.client.onNotification(listener);
    const frame = {
      ...lifecycle(),
      params: { state: 'paused', extension: [null, false] },
      metadata: { version: 2 },
    };
    Object.setPrototypeOf(frame, null);
    Object.setPrototypeOf(frame.params, null);
    h.inject(frame);
    h.inject(environment({ locale: 'en', extension: { future: true } }));
    expect(listener.mock.calls).toEqual([
      [{ jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'paused' } }],
      [{ jsonrpc: '2.0', method: 'portal.environmentChanged', params: { locale: 'en' } }],
    ]);
  });

  it('gives each subscriber a fresh copy without mutating frozen transport input', () => {
    const h = setup();
    const frame = Object.freeze({
      jsonrpc: '2.0',
      method: 'portal.lifecycle',
      params: Object.freeze({ state: 'paused' }),
    });
    const first = vi.fn((event: HostNotification) => {
      if (event.method === 'portal.lifecycle') {
        event.params.state = 'resumed';
      }
    });
    const second = vi.fn((_event: HostNotification) => {});
    h.client.onNotification(first);
    h.client.onNotification(second);
    h.inject(frame);
    expect(first.mock.calls[0]?.[0]).not.toBe(second.mock.calls[0]?.[0]);
    expect(second).toHaveBeenCalledExactlyOnceWith({
      jsonrpc: '2.0',
      method: 'portal.lifecycle',
      params: { state: 'paused' },
    });
    expect(frame.params.state).toBe('paused');
    expect(reports).toEqual([]);
  });
});

describe('SPEC §4 / §6.4 — ignore unknown or malformed notifications without a reply', () => {
  const invalid: Array<[string, unknown]> = [
    ['unknown method', { jsonrpc: '2.0', method: 'portal.future', params: { future: true } }],
    ['wrong version', { ...lifecycle(), jsonrpc: '1.0' }],
    ['missing version', { method: 'portal.lifecycle', params: { state: 'paused' } }],
    ['missing method', { jsonrpc: '2.0', params: { state: 'paused' } }],
    ['wrong method spelling', { ...lifecycle(), method: 'portal.Lifecycle' }],
    ['numeric id', { ...lifecycle(), id: 1 }],
    ['null id', { ...lifecycle(), id: null }],
    ['undefined id', { ...lifecycle(), id: undefined }],
    ['batch', [lifecycle()]],
    ['null frame', null],
    ['scalar frame', true],
    ['missing state', { jsonrpc: '2.0', method: 'portal.lifecycle', params: {} }],
    ['omitted lifecycle params', { jsonrpc: '2.0', method: 'portal.lifecycle' }],
    ['unknown state', lifecycle('frozen')],
    ['numeric state', lifecycle(1)],
    ['array params', environment([])],
    ['null params', environment(null)],
    ['undefined params', { ...environment(), params: undefined }],
    ['unknown color scheme', environment({ colorScheme: 'auto' })],
    ['null color scheme', environment({ colorScheme: null })],
    ['numeric locale', environment({ locale: 42 })],
    ['undefined locale', environment({ locale: undefined })],
    ['non-JSON extra', { ...lifecycle(), extra: new Date(0) }],
    ['non-JSON extra param', environment({ locale: 'en', extra: undefined })],
    ['inherited frame', Object.create(lifecycle())],
    ['symbol member', { ...lifecycle(), [Symbol('extra')]: null }],
    ['hidden member', Object.defineProperty(lifecycle(), 'extra', { value: null })],
  ];
  it.each(invalid)(
    'ignores %s and retains pending calls and their timers',
    async (_name, frame) => {
      const h = setup();
      const listener = vi.fn();
      h.client.onNotification(listener);
      const pending = observe(h.client.call('portal.ping'));
      expect(() => h.inject(frame)).not.toThrow();
      await flush();
      expect(listener).not.toHaveBeenCalled();
      expect(pending.settled).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(1);
      expect(h.send).toHaveBeenCalledOnce();
      h.inject({ jsonrpc: '2.0', id: 1, result: false });
      expect(await pending.outcome).toEqual({ value: false });
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('does not evaluate accessors or toJSON and tolerates failed structural inspection', () => {
    const h = setup();
    const listener = vi.fn();
    const getter = vi.fn(() => {
      throw new Error('must not execute');
    });
    const toJSON = vi.fn(() => ({}));
    h.client.onNotification(listener);
    const accessor = Object.defineProperty(lifecycle(), 'method', {
      enumerable: true,
      get: getter,
    });
    const nested = Object.defineProperty({}, 'state', { enumerable: true, get: getter });
    const cycle: Record<string, unknown> = {};
    cycle.self = cycle;
    const revoked = Proxy.revocable({}, {});
    revoked.revoke();
    for (const frame of [
      accessor,
      { ...lifecycle(), params: nested },
      { ...lifecycle(), toJSON },
      { ...lifecycle(), extra: cycle },
      revoked.proxy,
    ]) {
      expect(() => h.inject(frame)).not.toThrow();
    }
    expect(getter).not.toHaveBeenCalled();
    expect(toJSON).not.toHaveBeenCalled();
    expect(listener).not.toHaveBeenCalled();
    expect(h.send).not.toHaveBeenCalled();
  });

  it('preserves valid response extras without dispatching them as notifications', async () => {
    const h = setup();
    const listener = vi.fn();
    h.client.onNotification(listener);
    const pending = observe(h.client.call('portal.ping'));
    h.inject({ ...lifecycle(), id: 1, result: 0 });
    expect(await pending.outcome).toEqual({ value: 0 });
    expect(listener).not.toHaveBeenCalled();
  });
});

describe('ADR 0021 — subscription lifetime and dispatch order', () => {
  it('does not replay earlier notifications and supports idempotent unsubscribe', () => {
    const h = setup();
    const listener = vi.fn();
    h.inject(lifecycle());
    const off = h.client.onNotification(listener);
    expect(listener).not.toHaveBeenCalled();
    h.inject(lifecycle());
    off();
    off();
    h.inject(lifecycle('resumed'));
    expect(listener).toHaveBeenCalledOnce();
    expect(h.send).not.toHaveBeenCalled();
  });

  it('keeps repeated registrations of one function independent', () => {
    const h = setup();
    const listener = vi.fn();
    const first = h.client.onNotification(listener);
    const second = h.client.onNotification(listener);
    h.inject(lifecycle());
    expect(listener).toHaveBeenCalledTimes(2);
    first();
    h.inject(lifecycle());
    expect(listener).toHaveBeenCalledTimes(3);
    second();
    h.inject(lifecycle());
    expect(listener).toHaveBeenCalledTimes(3);
  });

  it('skips removed registrations and delays additions until the next notification', () => {
    const h = setup();
    const order: string[] = [];
    let removeSecond = () => {};
    let added = false;
    h.client.onNotification(() => {
      order.push('first');
      removeSecond();
      if (!added) {
        added = true;
        h.client.onNotification(() => {
          order.push('added');
        });
      }
    });
    removeSecond = h.client.onNotification(() => {
      order.push('removed');
    });
    h.inject(lifecycle());
    expect(order).toEqual(['first']);
    h.inject(lifecycle());
    expect(order).toEqual(['first', 'first', 'added']);
  });

  it('allows a listener to unsubscribe itself', () => {
    const h = setup();
    const listener = vi.fn(() => {
      off();
    });
    const off = h.client.onNotification(listener);
    h.inject(lifecycle());
    h.inject(lifecycle());
    expect(listener).toHaveBeenCalledOnce();
  });

  it('detaches subscribers before adapter cleanup and ignores later registrations', () => {
    const h = setup();
    const listener = vi.fn();
    const off = h.client.onNotification(listener);
    h.unsubscribe.mockImplementation(() => {
      h.inject(lifecycle());
    });
    h.close.mockImplementation(() => {
      throw new Error('cleanup failed');
    });
    expect(() => h.client.close()).toThrow('cleanup failed');
    const later = vi.fn();
    const offLater = h.client.onNotification(later);
    h.inject(lifecycle());
    off();
    offLater();
    offLater();
    expect(listener).not.toHaveBeenCalled();
    expect(later).not.toHaveBeenCalled();
    expect(h.onMessage).toHaveBeenCalledOnce();
  });

  it('stops remaining callbacks when a listener closes the client', async () => {
    const h = setup();
    const pending = observe(h.client.call('portal.ping'));
    const first = vi.fn(() => h.client.close());
    const second = vi.fn();
    h.client.onNotification(first);
    h.client.onNotification(second);
    h.inject(lifecycle());
    expect(first).toHaveBeenCalledOnce();
    expect(second).not.toHaveBeenCalled();
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('rejects a non-function registration locally without changing the bridge', () => {
    const h = setup();
    expect(() => Reflect.apply(h.client.onNotification, undefined, [42])).toThrow(
      'notification listener must be a function',
    );
    expect(h.send).not.toHaveBeenCalled();
    expect(h.onMessage).toHaveBeenCalledOnce();
  });

  it('keeps subscriber sets separate for different clients', () => {
    const first = setup();
    const second = setup();
    const a = vi.fn();
    const b = vi.fn();
    first.client.onNotification(a);
    second.client.onNotification(b);
    first.inject(lifecycle());
    expect(a).toHaveBeenCalledOnce();
    expect(b).not.toHaveBeenCalled();
    first.client.close();
    second.inject(environment());
    expect(b).toHaveBeenCalledOnce();
  });
});

describe('ADR 0021 — subscriber failures remain local and isolated', () => {
  it.each([new Error('subscriber bug'), 'subscriber string', undefined])(
    'reports a synchronous throw without affecting peers or requests: %s',
    async (failure) => {
      const h = setup();
      const pending = observe(h.client.call('portal.ping'));
      h.client.onNotification(() => {
        throw failure;
      });
      const second = vi.fn();
      h.client.onNotification(second);
      expect(() => h.inject(lifecycle())).not.toThrow();
      expect(second).toHaveBeenCalledOnce();
      expect(reports).toHaveLength(1);
      let caught = false;
      let reported: unknown;
      try {
        reports[0]?.();
      } catch (error) {
        caught = true;
        reported = error;
      }
      expect(caught).toBe(true);
      expect(reported).toBe(failure);
      h.inject({ jsonrpc: '2.0', id: 1, result: 'matched' });
      expect(await pending.outcome).toEqual({ value: 'matched' });
      expect(h.send).toHaveBeenCalledOnce();
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it('observes async rejections without waiting for the listener', async () => {
    const h = setup();
    const failure = new Error('async subscriber bug');
    let reject: ((error: unknown) => void) | undefined;
    h.client.onNotification(
      () =>
        new Promise<void>((_resolve, rejectPromise) => {
          reject = rejectPromise;
        }),
    );
    const second = vi.fn();
    h.client.onNotification(second);
    const pending = observe(h.client.call('portal.ping'));
    h.inject(lifecycle());
    expect(second).toHaveBeenCalledOnce();
    h.inject({ jsonrpc: '2.0', id: 1, result: false });
    expect(await pending.outcome).toEqual({ value: false });
    if (reject === undefined) {
      throw new Error('subscriber must still be pending');
    }
    reject(failure);
    await flush();
    expect(reports).toHaveLength(1);
    expect(reports[0]).toThrow(failure);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('reports multiple failures individually while later listeners still run', async () => {
    const h = setup();
    const firstError = new Error('first');
    const secondError = new Error('second');
    h.client.onNotification(() => {
      throw firstError;
    });
    h.client.onNotification(async () => {
      throw secondError;
    });
    const last = vi.fn();
    h.client.onNotification(last);
    h.inject(lifecycle());
    await flush();
    expect(last).toHaveBeenCalledOnce();
    expect(reports).toHaveLength(2);
    expect(reports[0]).toThrow(firstError);
    expect(reports[1]).toThrow(secondError);
    expect(h.send).not.toHaveBeenCalled();
  });

  it('keeps the original deadline while a notification listener fails', async () => {
    const h = setup();
    h.client.onNotification(() => {
      throw new Error('subscriber failed');
    });
    const pending = observe(h.client.call('portal.ping'));
    await vi.advanceTimersByTimeAsync(500);
    h.inject(lifecycle());
    await vi.advanceTimersByTimeAsync(499);
    expect(pending.settled).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.TIMEOUT } });
    expect(vi.getTimerCount()).toBe(0);
  });
});

it('delivers real host notifications before and during a delayed capability without changing correlation', async () => {
  const bridge = createLinkedTransports();
  let finish: ((profile: ProfileGetResult) => void) | undefined;
  const connection = createHost({
    hostInfo: { name: 'subscriber-test-host', version: '0.1.0', platform: 'browser' },
    manifest: {
      manifestVersion: 1,
      id: 'com.example.subscribers',
      name: 'Subscribers',
      version: '1.0.0',
      entry: 'index.html',
      protocolVersion: '0.1',
      permissions: ['profile'],
    },
    grantedScopes: ['profile'],
    environment: { locale: 'en', colorScheme: 'light' },
    capabilities: {
      profile: {
        get: () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      },
    },
  }).connect(bridge.b);
  const client = createClient({ transport: bridge.a, timeoutMs: 1_000 });
  cleanups.push(() => {
    client.close();
    bridge.b.close();
  });
  const events: HostNotification[] = [];
  const off = client.onNotification((event) => {
    events.push(event);
  });
  await connection.notifyLifecycle('resumed');
  await client.initialize();
  const pending = observe(client.call('profile.get'));
  await flush();
  await connection.notifyEnvironmentChanged({ colorScheme: 'dark', locale: 'ko-KR' });
  await connection.notifyLifecycle('paused');
  await flush();
  expect(events).toEqual([
    { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'resumed' } },
    {
      jsonrpc: '2.0',
      method: 'portal.environmentChanged',
      params: { colorScheme: 'dark', locale: 'ko-KR' },
    },
    { jsonrpc: '2.0', method: 'portal.lifecycle', params: { state: 'paused' } },
  ]);
  expect(pending.settled).not.toHaveBeenCalled();
  expect(vi.getTimerCount()).toBe(1);
  if (finish === undefined) {
    throw new Error('profile request must be pending');
  }
  finish({ displayName: 'Correct response' });
  expect(await pending.outcome).toEqual({ value: { displayName: 'Correct response' } });
  off();
  await connection.notifyLifecycle('resumed');
  await flush();
  expect(events).toHaveLength(3);
  expect(vi.getTimerCount()).toBe(0);
});
