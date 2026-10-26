# 22. Define a constrained browser navigation profile

Date: 2026-10-23
Status: Proposed — multi-Portal candidate measured; replacement contract still unapproved
Review: Deferred by the maintainer on 2026-10-23. Committing this proposal does not approve it.

## Scope clarification — 2026-10-26

The maintainer resumed review and clarified that one application or screen can
contain multiple Portals with different origins. This proposal must not be read
as requiring those Portals to share one domain or limiting an entire native app
or native screen to one Portal. Existing per-mini-app origin isolation remains
an architecture invariant.

The original one-Portal/one-origin condition below applies only to a single
browser-development host HTML document and its document-wide frame-src policy.
It is a constraint of the proposed simple browser fixture profile, not the
product-wide Portal/domain model. Supporting multiple different mini apps in
one browser host document is a separate requirement that this proposal does
not yet solve. No promise to remove that constraint later has been approved.
The proposal remains unapproved; distinguish these scopes before deciding T18.

## Follow-up evidence — 2026-10-26

The maintainer explicitly authorized investigating the multi-Portal direction.
[The follow-up](../multi-portal-investigation.md) now records a real-browser
candidate using two host-controlled served wrappers with separate CSP headers.
A/B initialized concurrently; revoking A left B's request, storage, and grants
intact. Wrong-source replies, guest bootstrap access, stale bootstrap, wrapper
URL substitution, and same-URL Document replacement were exercised.

A live outer-realm object failed the existing wrapper-owned JSON validator;
a wrapper-created payload worked. Kernel/data ownership and host provider
lifetime therefore need explicit integration design. The experiment retains
closed wrappers for late-send inspection; it is not full production disposal
or a memory/GC benchmark. No production transport relay was verified.

The old single-Portal restriction should not be adopted as the product model.
Prepare the replacement around independently policy-bound Portal instances,
trusted host-selected bootstrap, preserved origin/source checks, explicit realm
ownership, terminal disposal, and provider lifetime. Evidence is promising but
bounded to one engine and selected scenarios; this is not a conformance claim.
No normative change or T18 production implementation is approved by the
research authorization alone.

## Revised recommendation for investigation — 2026-10-26

Preserve multiple independently origin-bound Portals in one app/screen, and
investigate the same composition in one browser host document before adopting
a browser containment contract. Do not turn the single-Portal fixture into a
product-wide restriction or assume its limitation can simply be removed later.
The original proposal below is unapproved and is no longer the preferred
starting point for the multi-Portal goal.

The first browser candidate to evaluate is a host-controlled wrapper document
per Portal, each with its own narrow frame-src policy and bound bridge/lifetime.
This candidate now has bounded measurements below; it is not approved production integration.
The wrapper must be trusted host code; configuration/authority must stay bound
to the host-selected Portal rather than guest-provided identifiers or URLs.
Ordinary served wrapper documents and inherited-policy documents such as srcdoc
must not be assumed interchangeable. Message origin/source, bootstrap authority,
reload/replacement, teardown, and additional frame costs need explicit checks.

The bounded follow-up measured the core cases: A/B run concurrently with different
origins; A cannot navigate to B or a third origin through its own wrapper;
revoking A leaves B's pending calls and grants intact; allowed-origin reloads
still work; stale messages/configuration cannot gain another Portal's authority.
Only after that evidence should a replacement normative proposal be presented
for approval and T18 implementation begin. No replacement is approved now.

CSP reference: [frame-src](https://www.w3.org/TR/CSP3/#directive-frame-src).
This direction concerns browser validation first. SPEC currently defines browser
hosting as development and production origins as moonpool:// per app id;
production web hosting needs an explicit scope decision rather than an implied
promise or an unapproved relaxation of that invariant.

## Context

[T17 measurements](../navigation-investigation.md) show that foreign calls are
rejected, but an allowed-origin return can use the old connection. Parent src,
WindowProxy, and cross-origin access errors do not reveal the destination.
Closing on each load breaks allowed reloads and misses execution before load.
The tested parent CSP blocked foreign location, form, redirect, and silent-bounce
loads while allowing same-origin repeat handshakes. This does not prove a generic
post-navigation observer or complete cross-engine/navigation-scheme coverage.

## Original single-Portal proposal — unapproved, under reconsideration

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

If separately approved, T18 would implement this contract in the current single-Portal browser
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
