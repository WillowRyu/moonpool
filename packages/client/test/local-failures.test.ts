/** T13 — terminal local close and synchronous send failures (ADR 0018). */
import { createClient, MoonpoolError } from '@moonpool/client';
import { ERROR_CODES, isJsonRpcRequest, type JsonValue, type Transport } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flush } from './helpers/memory-transport';

const cleanups: Array<() => void> = [];

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) {
    cleanup();
  }
  vi.useRealTimers();
});

function setup() {
  let receive: ((message: JsonValue) => void) | undefined;
  const send = vi.fn((_message: JsonValue) => {});
  const unsubscribe = vi.fn(() => {});
  const close = vi.fn(() => {});
  const transport: Transport = {
    send,
    onMessage(handler) {
      receive = handler;
      return unsubscribe;
    },
    close,
  };
  const client = createClient({ transport, timeoutMs: 1_000 });
  function deliver(value: unknown) {
    if (receive === undefined) {
      throw new Error('client receiver must be registered');
    }
    // Deliberately retain the callback to model an already queued delivery.
    Reflect.apply(receive, undefined, [value]);
  }
  cleanups.push(() => {
    unsubscribe.mockReset();
    close.mockReset();
    client.close();
  });
  return { client, transport, send, unsubscribe, close, deliver };
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

function requestId(message: JsonValue): number {
  if (!isJsonRpcRequest(message)) {
    throw new Error('expected a valid outbound request');
  }
  return message.id;
}

function success(id: number, result: JsonValue = null) {
  return { jsonrpc: '2.0', id, result };
}

describe('SPEC §4.6 — local close stays terminal', () => {
  it.each(['call', 'initialize'])(
    'rejects %s after close without sending or creating a timer',
    async (method) => {
      const h = setup();
      h.client.close();
      let promise: Promise<unknown> | undefined;
      expect(() => {
        promise = method === 'call' ? h.client.call('portal.ping') : h.client.initialize();
      }).not.toThrow();
      if (promise === undefined) {
        throw new Error('the API must return a Promise');
      }
      const outcome = observe(promise);
      expect(h.send).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
      expect(await outcome.outcome).toMatchObject({
        error: { code: ERROR_CODES.CONNECTION_CLOSED },
      });
      expect(h.unsubscribe).toHaveBeenCalledOnce();
      expect(h.close).toHaveBeenCalledOnce();
    },
  );

  it('runs unsubscribe and transport cleanup only once across repeated close', () => {
    const h = setup();
    h.client.close();
    h.client.close();
    h.client.close();
    expect(h.unsubscribe).toHaveBeenCalledOnce();
    expect(h.close).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each(['unsubscribe', 'close'])(
    'handles reentrant close from %s without repeating cleanup',
    (callback) => {
      const h = setup();
      let entries = 0;
      const cleanup = callback === 'unsubscribe' ? h.unsubscribe : h.close;
      cleanup.mockImplementation(() => {
        entries += 1;
        // Bound a broken implementation so the RED run does not overflow the stack.
        if (entries === 1) {
          h.client.close();
        }
      });
      h.client.close();
      expect(h.unsubscribe).toHaveBeenCalledOnce();
      expect(h.close).toHaveBeenCalledOnce();
    },
  );

  it('drains calls and marks closed before invoking adapter cleanup', async () => {
    const h = setup();
    const first = observe(h.client.call('portal.ping'));
    const second = observe(h.client.initialize());
    const duringCleanup: Array<ReturnType<typeof observe>> = [];
    const timersDuringCleanup: number[] = [];
    h.unsubscribe.mockImplementation(() => {
      timersDuringCleanup.push(vi.getTimerCount());
      duringCleanup.push(observe(h.client.call('profile.get')));
      h.deliver(success(1, 'must not win over close'));
    });
    h.close.mockImplementation(() => {
      timersDuringCleanup.push(vi.getTimerCount());
      duringCleanup.push(observe(h.client.initialize()));
    });
    h.client.close();
    expect(timersDuringCleanup).toEqual([0, 0]);
    expect(h.send).toHaveBeenCalledTimes(2);
    for (const pending of [first, second, ...duringCleanup]) {
      expect(await pending.outcome).toMatchObject({
        error: { code: ERROR_CODES.CONNECTION_CLOSED },
      });
      expect(pending.settled).toHaveBeenCalledOnce();
    }
    expect(vi.getTimerCount()).toBe(0);
  });

  it('ignores retained receive callbacks before inspecting their data', () => {
    const h = setup();
    h.client.close();
    const inspect = vi.fn(() => {
      throw new Error('must not inspect after close');
    });
    const value = new Proxy(success(1), { ownKeys: inspect });
    expect(() => h.deliver(value)).not.toThrow();
    expect(inspect).not.toHaveBeenCalled();
  });

  it.each(['unsubscribe', 'close', 'both', 'undefined'])(
    'drains pending calls even when %s cleanup throws',
    async (failure) => {
      const h = setup();
      const first = observe(h.client.call('portal.ping'));
      const second = observe(h.client.initialize());
      const unsubscribeFailure =
        failure === 'undefined' ? undefined : new Error('unsubscribe failed');
      const closeFailure = new Error('transport close failed');
      if (failure !== 'close') {
        h.unsubscribe.mockImplementation(() => {
          throw unsubscribeFailure;
        });
      }
      if (failure === 'close' || failure === 'both') {
        h.close.mockImplementation(() => {
          throw closeFailure;
        });
      }
      let caught = false;
      let thrown: unknown;
      try {
        h.client.close();
      } catch (error) {
        caught = true;
        thrown = error;
      }
      expect(caught).toBe(true);
      expect(thrown).toBe(failure === 'close' ? closeFailure : unsubscribeFailure);
      expect(h.unsubscribe).toHaveBeenCalledOnce();
      expect(h.close).toHaveBeenCalledOnce();
      expect(vi.getTimerCount()).toBe(0);
      expect(await first.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
      expect(await second.outcome).toMatchObject({
        error: { code: ERROR_CODES.CONNECTION_CLOSED },
      });
      expect(() => h.client.close()).not.toThrow();
      const later = observe(h.client.call('portal.ping'));
      expect(await later.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
      expect(h.send).toHaveBeenCalledTimes(2);
      expect(h.unsubscribe).toHaveBeenCalledOnce();
      expect(h.close).toHaveBeenCalledOnce();
    },
  );

  it('preserves a result completed before close and rejects only remaining calls', async () => {
    const h = setup();
    const finished = observe(h.client.call('portal.ping'));
    const pending = observe(h.client.call('profile.get'));
    h.deliver(success(1, false));
    h.client.close();
    h.deliver(success(2, 'late'));
    expect(await finished.outcome).toEqual({ value: false });
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
    await vi.advanceTimersByTimeAsync(1_000);
    expect(finished.settled).toHaveBeenCalledOnce();
    expect(pending.settled).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not close or drain another client', async () => {
    const first = setup();
    const second = setup();
    const abandoned = observe(first.client.call('portal.ping'));
    const active = observe(second.client.call('portal.ping'));
    first.client.close();
    expect(await abandoned.outcome).toMatchObject({
      error: { code: ERROR_CODES.CONNECTION_CLOSED },
    });
    expect(active.settled).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(1);
    second.deliver(success(1, true));
    expect(await active.outcome).toEqual({ value: true });
    expect(second.close).not.toHaveBeenCalled();
  });
});

describe('SPEC §4.7 — synchronous send failures are local to one call', () => {
  const failures: Array<[string, unknown]> = [
    ['Error', new Error('private transport details')],
    ['string', 'private transport details'],
    ['undefined', undefined],
    ['null', null],
    ['number', 42],
    ['symbol', Symbol('private transport details')],
    ['object', { code: -32007, message: 'not proof of remote health' }],
  ];
  it.each(failures)(
    'cleans up and maps a thrown %s without leaking its value',
    async (_name, failure) => {
      const h = setup();
      h.send.mockImplementation(() => {
        throw failure;
      });
      const pending = observe(h.client.call('portal.ping'));
      expect(vi.getTimerCount()).toBe(0);
      expect(await pending.outcome).toEqual({
        error: new MoonpoolError(ERROR_CODES.INTERNAL_ERROR, 'failed to send the bridge request', {
          phase: 'send',
        }),
      });
      expect(await pending.outcome).toMatchObject({
        error: {
          name: 'MoonpoolError',
          code: -32603,
          message: 'failed to send the bridge request',
          data: { phase: 'send' },
        },
      });
      h.deliver(success(1, 'late'));
      await vi.advanceTimersByTimeAsync(1_000);
      expect(pending.settled).toHaveBeenCalledOnce();
      expect(h.send).toHaveBeenCalledOnce();
      expect(h.unsubscribe).not.toHaveBeenCalled();
      expect(h.close).not.toHaveBeenCalled();
    },
  );

  it('uses the same local failure mapping for initialize', async () => {
    const h = setup();
    h.send.mockImplementation(() => {
      throw new Error('cannot send handshake');
    });
    const pending = observe(h.client.initialize());
    expect(await pending.outcome).toMatchObject({
      error: { code: -32603, data: { phase: 'send' } },
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not inspect or stringify an arbitrary thrown object', async () => {
    const h = setup();
    const inspect = vi.fn(() => {
      throw new Error('must not inspect');
    });
    const failure = new Proxy({}, { get: inspect, ownKeys: inspect, getPrototypeOf: inspect });
    // A plain function avoids the test spy inspecting the thrown Proxy itself.
    h.transport.send = () => {
      throw failure;
    };
    const pending = observe(h.client.call('portal.ping'));
    const outcome = await pending.outcome;
    // Avoid inspecting a raw error in the RED run: compare the reference first.
    expect('error' in outcome && outcome.error === failure).toBe(false);
    expect(outcome).toMatchObject({ error: { code: -32603, data: { phase: 'send' } } });
    expect(inspect).not.toHaveBeenCalled();
  });

  it('keeps other calls and future calls usable, without reusing ids or retrying', async () => {
    const h = setup();
    h.send.mockImplementation((message) => {
      if (requestId(message) === 2) {
        throw new Error('one local failure');
      }
    });
    const first = observe(h.client.call('profile.get'));
    await vi.advanceTimersByTimeAsync(400);
    const failed = observe(h.client.call('portal.ping'));
    const third = observe(h.client.call('portal.ping'));
    expect(await failed.outcome).toMatchObject({ error: { code: -32603 } });
    expect(h.send.mock.calls.map(([message]) => requestId(message))).toEqual([1, 2, 3]);
    expect(vi.getTimerCount()).toBe(2);
    h.deliver(success(2, 'discarded'));
    await flush();
    expect(first.settled).not.toHaveBeenCalled();
    expect(third.settled).not.toHaveBeenCalled();
    h.deliver(success(3, 0));
    expect(await third.outcome).toEqual({ value: 0 });
    await vi.advanceTimersByTimeAsync(599);
    expect(first.settled).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(await first.outcome).toMatchObject({ error: { code: ERROR_CODES.TIMEOUT } });
    expect(h.send).toHaveBeenCalledTimes(3);
    expect(h.close).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('ignores a queued response when send throws before it arrives', async () => {
    const h = setup();
    h.send.mockImplementation((message) => {
      void Promise.resolve().then(() => h.deliver(success(requestId(message), 'too late')));
      throw new Error('delivery status unknown');
    });
    const pending = observe(h.client.call('portal.ping'));
    expect(await pending.outcome).toMatchObject({
      error: { code: -32603, data: { phase: 'send' } },
    });
    await flush();
    expect(pending.settled).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each(['success', 'error'])(
    'retains a synchronous %s response even if send throws afterward',
    async (outcome) => {
      const h = setup();
      h.send.mockImplementation((message) => {
        const id = requestId(message);
        h.deliver(
          outcome === 'success'
            ? success(id, false)
            : { jsonrpc: '2.0', id, error: { code: -32000, message: 'Permission denied' } },
        );
        throw new Error('already settled');
      });
      const pending = observe(h.client.call('portal.ping'));
      expect(await pending.outcome).toEqual(
        outcome === 'success'
          ? { value: false }
          : { error: new MoonpoolError(-32000, 'Permission denied') },
      );
      expect(vi.getTimerCount()).toBe(0);
      expect(pending.settled).toHaveBeenCalledOnce();
      expect(h.close).not.toHaveBeenCalled();
    },
  );

  it('lets close during send win over a later send exception', async () => {
    const h = setup();
    h.send.mockImplementation(() => {
      h.client.close();
      throw new Error('closed during send');
    });
    const pending = observe(h.client.call('portal.ping'));
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
    expect(vi.getTimerCount()).toBe(0);
    const later = observe(h.client.initialize());
    expect(await later.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
    expect(h.send).toHaveBeenCalledOnce();
    expect(h.close).toHaveBeenCalledOnce();
  });

  it('can close normally after a failed send without settling it again', async () => {
    const h = setup();
    h.send.mockImplementationOnce(() => {
      throw new Error('failed');
    });
    const failed = observe(h.client.call('portal.ping'));
    expect(await failed.outcome).toMatchObject({ error: { code: -32603 } });
    const pending = observe(h.client.call('profile.get'));
    h.client.close();
    expect(await pending.outcome).toMatchObject({ error: { code: ERROR_CODES.CONNECTION_CLOSED } });
    expect(failed.settled).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });
});
