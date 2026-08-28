// @vitest-environment happy-dom
/**
 * SPEC §3.1 — the Transport contract, over `window.postMessage`.
 *
 * "A transport MUST deliver messages in order and MUST NOT modify payloads."
 *
 * The security-relevant inputs (`event.origin`, `event.source`) are supplied
 * by the test rather than produced by the DOM emulator: a synthetic
 * MessageEvent lets a test pose as a hostile frame, which is precisely what
 * an emulator's own postMessage will never do.
 */
import type { JsonValue } from '@moonpool/protocol';
import { createIframeTransport } from '@moonpool/transport-iframe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const PEER_ORIGIN = 'http://localhost:5174';
const PING: JsonValue = { jsonrpc: '2.0', id: 1, method: 'portal.ping' };

/** Delivers a frame to our window as if `source` had posted it from `origin`. */
function deliver(frame: JsonValue, from: { origin: string; source: unknown }): void {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: frame,
      origin: from.origin,
      source: from.source as Window,
    }),
  );
}

/** Listeners live on a window shared by the whole file, so every one is closed. */
const openTransports: Array<{ close: () => void }> = [];

afterEach(() => {
  for (const transport of openTransports.splice(0)) {
    transport.close();
  }
});

function setup() {
  /** The narrow slice of a Window this transport is allowed to need. */
  const peerWindow = { postMessage: vi.fn<(message: unknown, targetOrigin: string) => void>() };

  const transport = createIframeTransport({ peerWindow, peerOrigin: PEER_ORIGIN });
  openTransports.push(transport);

  const received: JsonValue[] = [];
  transport.onMessage((message) => received.push(message));

  return {
    transport,
    peerWindow,
    received,
    /** Poses as the real peer: right origin, right window. */
    fromPeer: (frame: JsonValue) => deliver(frame, { origin: PEER_ORIGIN, source: peerWindow }),
  };
}

describe('SPEC §3.1 — sending', () => {
  it('posts the frame to the peer window', () => {
    const { transport, peerWindow } = setup();

    transport.send(PING);

    expect(peerWindow.postMessage).toHaveBeenCalledTimes(1);
    expect(peerWindow.postMessage.mock.calls[0]?.[0]).toEqual(PING);
  });

  it('pins targetOrigin to the peer — never the "*" wildcard', () => {
    // The second argument is a browser-enforced delivery condition. With "*",
    // a Portal that had navigated to an attacker origin would still be handed
    // every frame the host sends, handshake results included.
    const { transport, peerWindow } = setup();

    transport.send(PING);

    expect(peerWindow.postMessage.mock.calls[0]?.[1]).toBe(PEER_ORIGIN);
  });
});

describe('SPEC §3.1 — receiving', () => {
  it('delivers a frame from the peer unmodified', () => {
    const { received, fromPeer } = setup();
    const frame: JsonValue = { jsonrpc: '2.0', id: 1, result: { nested: [1, 2, { deep: true }] } };

    fromPeer(frame);

    expect(received).toEqual([frame]);
  });

  it('preserves order', () => {
    const { received, fromPeer } = setup();

    for (const id of [1, 2, 3]) {
      fromPeer({ jsonrpc: '2.0', id, method: 'portal.ping' });
    }

    expect(received.map((message) => (message as { id: number }).id)).toEqual([1, 2, 3]);
  });
});

describe('SPEC §9.1 — everything else on the window is dropped', () => {
  it('drops a frame from another origin', () => {
    const { received, peerWindow } = setup();

    deliver(PING, { origin: 'http://localhost:5173', source: peerWindow });

    expect(received).toEqual([]);
  });

  it('drops a frame from another window on the peer origin', () => {
    const { received } = setup();

    deliver(PING, { origin: PEER_ORIGIN, source: { name: 'some other frame' } });

    expect(received).toEqual([]);
  });

  it('drops a frame from a sandboxed frame reporting origin "null"', () => {
    const { received, peerWindow } = setup();

    deliver(PING, { origin: 'null', source: peerWindow });

    expect(received).toEqual([]);
  });
});

describe('SPEC §3.1 — unsubscribing and closing', () => {
  it('stops delivering to a handler that unsubscribed', () => {
    const { transport, fromPeer } = setup();
    const seen: JsonValue[] = [];
    const unsubscribe = transport.onMessage((message) => seen.push(message));

    unsubscribe();
    fromPeer(PING);

    expect(seen).toEqual([]);
  });

  it('keeps delivering to the handlers that did not unsubscribe', () => {
    const { transport, received, fromPeer } = setup();
    const unsubscribe = transport.onMessage(() => undefined);

    unsubscribe();
    fromPeer(PING);

    expect(received).toEqual([PING]);
  });

  it('detaches from the window on close', () => {
    // A closed transport still holding a window listener is a leak, and on a
    // page that opens many Portals it is also a growing pile of dead frames
    // inspecting every message that arrives.
    const { transport, received, fromPeer } = setup();

    transport.close();
    fromPeer(PING);

    expect(received).toEqual([]);
  });
});

describe('SPEC §3.1 — one throwing handler must not disable the bridge', () => {
  // The re-throw is parked on the microtask queue, so these tests own that
  // queue: one lets it run and inspects what came out, the other never runs
  // it at all. `useRealTimers` then discards whatever is still parked, so a
  // deliberate failure here cannot leak into another test file.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['queueMicrotask'] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('keeps delivering to the handlers registered after the one that threw', () => {
    // The browser isolates every addEventListener listener from the others.
    // A transport that fans out from ONE listener must not offer less, or
    // registration order silently decides correctness: a bad bridge logger
    // registered first would stop the kernel from seeing another message.
    const { transport, fromPeer } = setup();
    const ran: string[] = [];

    transport.onMessage(() => {
      ran.push('before');
    });
    transport.onMessage(() => {
      ran.push('throwing');
      throw new Error('handler blew up');
    });
    transport.onMessage(() => {
      ran.push('after');
    });

    fromPeer(PING);

    expect(ran).toEqual(['before', 'throwing', 'after']);
  });

  it('does not swallow the error — it resurfaces on an empty stack', () => {
    // Isolating is only half the job. A try/catch that drops the error is the
    // silent-callback antipattern: handler bugs vanish without a trace, and
    // the bridge reports nothing while quietly doing nothing.
    const { transport, fromPeer } = setup();
    const boom = new Error('handler blew up');

    transport.onMessage(() => {
      throw boom;
    });

    // Nothing escapes the dispatch itself, matching the browser: a listener's
    // exception never reaches whoever fired the event.
    expect(() => fromPeer(PING)).not.toThrow();

    // But the error is not gone. Re-thrown with no caller above it, it is what
    // a real browser turns into an uncaught error / window.onerror.
    expect(() => vi.runAllTicks()).toThrow(boom);
  });
});
