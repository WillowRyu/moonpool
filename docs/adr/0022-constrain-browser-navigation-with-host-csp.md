# 22. Define a constrained browser navigation profile

Date: 2026-10-23
Status: Proposed — awaiting maintainer approval before T18 / SPEC changes
Review: Deferred by the maintainer on 2026-10-23. Committing this proposal does not approve it.

## Context

[T17 measurements](../navigation-investigation.md) show that foreign calls are
rejected, but an allowed-origin return can use the old connection. Parent src,
WindowProxy, and cross-origin access errors do not reveal the destination.
Closing on each load breaks allowed reloads and misses execution before load.
The tested parent CSP blocked foreign location, form, redirect, and silent-bounce
loads while allowing same-origin repeat handshakes. This does not prove a generic
post-navigation observer or complete cross-engine/navigation-scheme coverage.

## Recommended decision for approval

Add an explicit browser-development profile to SPEC §8.1, referenced from §9.2:

- Use one active Portal and one allowed mini-app origin per host document.
  Before creating it, the host document must enforce host-owned CSP frame-src
  restricted to that exact pinned origin. Report-only, wildcard, and a list of
  unrelated app origins are not this profile. Preserve distinct host/app origins.
- Define browser behavior as preventing foreign document loads and terminally
  disposing the Portal on a browser-generated, enforced frame-src violation.
  Close its bridge, remove its frame, and suppress later sends/receives. Do not
  automatically reconnect because the allowed origin returns. A host action may
  create a fresh Portal. Keep exact origin/source/targetOrigin checks as well.
- Preserve allowed-origin navigation and §5.1 repeat handshakes; do not use load
  alone to infer an origin change. Kernel code remains platform-independent;
  CSP and violation handling belong to the browser server/embedder/transport.
- State this prevention-and-revocation contract explicitly, rather than claiming
  that ordinary iframe JavaScript can observe every departure/current URL.
  Unrestricted iframe hosts cannot claim §9.2 conformance from message filtering.
  Production §9.2 remains unchanged. Other engines/compositions require validation
  before claiming support; T17's single-engine observations are not certification.

T18 would implement this approved contract in the current single-Portal browser
example and its transport lifecycle. The proposal does not add native cores,
a navigation RPC, peer-close events, or an epoch protocol. Nor does it promise
to revoke already-dispatched work before an asynchronous violation is observed.

## Consequences and alternative

The recommendation keeps normal internal navigation and gives the browser a
preventive enforcement mechanism, with a clear deployment constraint. Unrelated
embedded frames/multiple app origins in one host document are outside this
simple profile. CSP alone is not the complete change: disposal and recovery
still need T18 tests. The current fixture only observes violations.

Alternatively, retain the existing general wording and leave unrestricted
browser navigation conformance open pending a different proven mechanism.
The SDK may continue as a development prototype, but T18 / v0.1 navigation
completion must not be declared. Closing on every load is rejected as an
alternative because the measurements show both breakage and a timing gap.

No normative edit or production implementation is authorized by this proposed
ADR alone. Present prior behavior, the current problem, and these consequences
to the maintainer before asking approval.
