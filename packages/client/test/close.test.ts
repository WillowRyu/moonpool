/**
 * SPEC §4.6 — Connection teardown.
 *
 * "On close a client MUST discard every pending entry, clear its §4.5 timer,
 *  and reject the caller with `-32008`. A client MUST NOT leave a request
 *  pending across a close."
 *
 * The whole point is immediacy: once the transport is shut no response can
 * arrive, so waiting out the §4.5 timeout would be waiting for a certainty.
 * Fake timers here exist to prove the clock never has to move.
 */
import { createClient } from '@moonpool/client';
import { ERROR_CODES, type Transport } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

describe('SPEC §4.6 — closing the connection', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('rejects every in-flight request with -32008', async () => {
    // Nothing is listening on the host end: both calls are still in flight.
    const { a: clientEnd } = createLinkedTransports();
    const client = createClient({ transport: clientEnd });

    const first = expect(client.call('profile.get')).rejects.toMatchObject({
      code: ERROR_CODES.CONNECTION_CLOSED,
    });
    const second = expect(client.call('storage.get')).rejects.toMatchObject({
      code: ERROR_CODES.CONNECTION_CLOSED,
    });

    client.close();

    await first;
    await second;
  });

  it('settles them without waiting out the §4.5 timeout', async () => {
    const { a: clientEnd } = createLinkedTransports();
    const client = createClient({ transport: clientEnd, timeoutMs: 30_000 });

    let settled = false;
    client.call('profile.get').catch(() => {
      settled = true;
    });

    client.close();
    // Microtasks only — the fake clock is never advanced by a single tick.
    await flush();

    expect(settled).toBe(true);
  });

  it('clears the §4.5 timer of every discarded request', async () => {
    const { a: clientEnd } = createLinkedTransports();
    const client = createClient({ transport: clientEnd, timeoutMs: 30_000 });

    const first = expect(client.call('profile.get')).rejects.toMatchObject({
      code: ERROR_CODES.CONNECTION_CLOSED,
    });
    const second = expect(client.call('storage.get')).rejects.toMatchObject({
      code: ERROR_CODES.CONNECTION_CLOSED,
    });
    expect(vi.getTimerCount()).toBe(2);

    client.close();

    // A timer armed for a request nobody is waiting on keeps a device awake
    // for no reason — on mobile that is the difference the user feels.
    expect(vi.getTimerCount()).toBe(0);

    await first;
    await second;
  });

  it('closes the underlying transport', () => {
    const { a } = createLinkedTransports();
    const closed = vi.fn();
    const clientEnd: Transport = {
      send: a.send,
      onMessage: a.onMessage,
      close: () => {
        closed();
        a.close();
      },
    };

    createClient({ transport: clientEnd }).close();

    expect(closed).toHaveBeenCalledTimes(1);
  });
});
