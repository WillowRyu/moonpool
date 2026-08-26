/**
 * SPEC §9.1 — Origin binding, as a pure decision.
 *
 * "The host MUST verify that every inbound message originates from the
 *  expected Portal origin, and MUST drop messages that do not. The bridge
 *  MUST NOT be reachable from any other origin."
 *
 * `window`'s `message` event is a public mailbox: any frame, popup, or
 * embedder on the page can post to it. `isFromPeer` is the whole of the
 * bridge's answer to "did this actually come from the other end?", so it is
 * kept free of the DOM — a security decision should not be tested through an
 * emulator's approximation of postMessage.
 */
import { isFromPeer } from '@moonpool/transport-iframe';
import { describe, expect, it } from 'vitest';

/** Stand-ins for Window references; only their identity matters here. */
const PEER_WINDOW = { name: 'peer' };
const OTHER_WINDOW = { name: 'other' };

const PEER = { origin: 'http://localhost:5174', window: PEER_WINDOW };

describe('SPEC §9.1 — a message is from the peer only if BOTH checks pass', () => {
  it('accepts a message whose origin and source both match the peer', () => {
    expect(isFromPeer({ origin: 'http://localhost:5174', source: PEER_WINDOW }, PEER)).toBe(true);
  });

  it('rejects the right window speaking from the wrong origin', () => {
    // Navigation containment (§9.2): if the Portal navigated away, its window
    // reference is unchanged but its origin is not.
    expect(isFromPeer({ origin: 'http://localhost:5173', source: PEER_WINDOW }, PEER)).toBe(false);
  });

  it('rejects the wrong window speaking from the right origin', () => {
    // The check origin alone cannot make: a second frame on the peer's origin
    // is a different party. `event.origin` says which house, never which room.
    expect(isFromPeer({ origin: 'http://localhost:5174', source: OTHER_WINDOW }, PEER)).toBe(false);
  });

  it('rejects a message with no source at all', () => {
    // `source` is null for messages from a window that has since been closed,
    // and for some non-window senders.
    expect(isFromPeer({ origin: 'http://localhost:5174', source: null }, PEER)).toBe(false);
  });
});

describe('SPEC §9.1 — origins are compared exactly, never by prefix', () => {
  const PREFIX_ATTACKS = [
    // Passes `startsWith`, is a completely different site.
    'http://localhost:5174.evil.com',
    // Passes `startsWith`, is a different port — a different origin.
    'http://localhost:51740',
    // Passes `startsWith`, and the path is not part of an origin anyway.
    'http://localhost:5174@evil.com',
  ];

  it.each(PREFIX_ATTACKS)('rejects %s despite the shared prefix', (origin) => {
    expect(isFromPeer({ origin, source: PEER_WINDOW }, PEER)).toBe(false);
  });

  it('rejects a peer origin written with a trailing slash', () => {
    // A serialised origin never carries one, so this can only be a
    // misconfiguration — and a misconfigured origin check must fail closed
    // (nothing gets through) rather than fail open.
    const misconfigured = { origin: 'http://localhost:5174/', window: PEER_WINDOW };

    expect(
      isFromPeer({ origin: 'http://localhost:5174', source: PEER_WINDOW }, misconfigured),
    ).toBe(false);
  });
});

describe('SPEC §9.1 — "null" is not an identity', () => {
  it('rejects an opaque origin even when the source matches', () => {
    // Every sandboxed iframe on the web reports origin "null". Accepting it
    // would admit anonymous senders, not the peer.
    expect(isFromPeer({ origin: 'null', source: PEER_WINDOW }, PEER)).toBe(false);
  });

  it('refuses to match even if "null" is what was configured', () => {
    const anonymous = { origin: 'null', window: PEER_WINDOW };

    expect(isFromPeer({ origin: 'null', source: PEER_WINDOW }, anonymous)).toBe(false);
  });
});
