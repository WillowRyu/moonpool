/**
 * SPEC §9.1 — origin binding, as a pure decision.
 *
 * Kept free of the DOM on purpose: this is the entire answer to "did this
 * message actually come from the other end of the bridge?", and a security
 * decision should not be verified through an emulator's approximation of
 * postMessage.
 */

/** An opaque origin. Every sandboxed iframe on the web reports it. */
const OPAQUE_ORIGIN = 'null';

export function isFromPeer(
  event: { origin: string; source: unknown },
  peer: { origin: string; window: unknown },
): boolean {
  // "null" is not an identity — accepting it would admit anonymous senders,
  // not the peer. Refused on both sides so a misconfigured peer origin
  // cannot opt in to it either.
  if (event.origin === OPAQUE_ORIGIN || peer.origin === OPAQUE_ORIGIN) {
    return false;
  }

  // Exact match, never a prefix: `startsWith` would accept
  // `http://localhost:51740` and `http://localhost:5174.evil.com`.
  if (event.origin !== peer.origin) {
    return false;
  }

  // `origin` says which house, never which room: a second frame on the peer's
  // origin is a different party.
  return event.source !== null && event.source === peer.window;
}
