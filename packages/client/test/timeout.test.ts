/**
 * SPEC §4.5 — Timeouts.
 *
 * "Clients MUST apply a timeout to every request. Default: 30 000 ms.
 *  On expiry the client MUST reject with `-32003` and discard the pending
 *  entry. A late response for a discarded id MUST be ignored."
 *
 * Fake timers throughout: the clock is an input to these tests, not a wait.
 * A bridge call that can hang forever is a hung mini app, so this is the one
 * client behaviour that must hold even when the host misbehaves entirely.
 */
import { createClient } from '@moonpool/client';
import { ERROR_CODES, type JsonValue } from '@moonpool/protocol';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createLinkedTransports, flush } from './helpers/memory-transport';

/** Shape of a JSON-RPC request, loose on purpose — for assertions only. */
interface RpcRequest {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: Record<string, JsonValue>;
}

describe('SPEC §4.5 — every request is on a clock', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('rejects with -32003 when the host never answers', async () => {
    // Nothing is listening on the host end: the request goes out into silence.
    const { a: clientEnd } = createLinkedTransports();
    const client = createClient({ transport: clientEnd, timeoutMs: 1_000 });

    const settled = expect(client.call('profile.get')).rejects.toMatchObject({
      code: ERROR_CODES.TIMEOUT,
    });

    await vi.advanceTimersByTimeAsync(1_000);
    await settled;
  });

  it('defaults the timeout to 30 000 ms', async () => {
    const { a: clientEnd } = createLinkedTransports();
    const client = createClient({ transport: clientEnd });

    let rejectedWith: unknown;
    client.call('profile.get').catch((reason: unknown) => {
      rejectedWith = reason;
    });

    await vi.advanceTimersByTimeAsync(29_999);
    expect(rejectedWith).toBeUndefined();

    await vi.advanceTimersByTimeAsync(1);
    expect(rejectedWith).toMatchObject({ code: ERROR_CODES.TIMEOUT });
  });

  it('discards the timer once the response arrives in time', async () => {
    const { a: clientEnd, b: hostEnd } = createLinkedTransports();
    hostEnd.onMessage((message) => {
      const { id } = message as unknown as RpcRequest;
      hostEnd.send({ jsonrpc: '2.0', id, result: { pong: true } });
    });

    const client = createClient({ transport: clientEnd, timeoutMs: 1_000 });

    await expect(client.call('portal.ping')).resolves.toEqual({ pong: true });
    // A timer left armed for a request that already settled is a leak, and on
    // a long-lived connection it is also a device wakeup nobody asked for.
    expect(vi.getTimerCount()).toBe(0);
  });

  it('ignores a late response for an id it already timed out', async () => {
    const { a: clientEnd, b: hostEnd } = createLinkedTransports();
    const seen: RpcRequest[] = [];
    hostEnd.onMessage((message) => {
      seen.push(message as unknown as RpcRequest);
    });

    const client = createClient({ transport: clientEnd, timeoutMs: 1_000 });
    const timedOut = expect(client.call('profile.get')).rejects.toMatchObject({
      code: ERROR_CODES.TIMEOUT,
    });

    await vi.advanceTimersByTimeAsync(1_000);
    await timedOut;

    // The host answers anyway, long after the client gave up on that id.
    hostEnd.send({ jsonrpc: '2.0', id: seen[0]?.id ?? -1, result: { late: true } });
    await flush();

    // The connection survives it: the next request is still served normally.
    hostEnd.onMessage((message) => {
      const { id } = message as unknown as RpcRequest;
      hostEnd.send({ jsonrpc: '2.0', id, result: { pong: true } });
    });

    await expect(client.call('portal.ping')).resolves.toEqual({ pong: true });
  });
});
