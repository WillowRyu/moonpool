# 22. Contain browser navigation per Portal with explicit ownership

Date: 2026-10-23
Revised: 2026-10-26
Status: Accepted — replacement contract approved by the maintainer on 2026-10-26

## Context

[T17](../navigation-investigation.md) found that message filtering does not
revoke a connection after a foreign excursion; load-based teardown also breaks
allowed reloads and misses earlier execution. A document-wide A/B allowlist
cannot bind A's frame to A alone. The original single-Portal proposal was
never approved and is replaced by this proposal, preserving multiple origins
in one app/screen/browser-development page.

[Follow-up measurements](../multi-portal-investigation.md) used served trusted
wrappers with independent CSP: revoking A preserved B's request/data/grants.
They also found that outer-realm objects fail wrapper-owned JSON validation
and wrapper-local storage disappears on wrapper replacement. These observations
cover selected scenarios in one engine, not a completed integration.

## Decision

Limit this contract to browser development under SPEC §8.1, referenced by §9.2.
Keep production moonpool:// origins and the pure kernel/Transport interface.
Production web hosting is a separate, unapproved scope decision.

| Owner | Responsibility |
| --- | --- |
| Outer host | Trusted app/origin/grant registry, Portal lifetime, provider instances and app-partitioned storage |
| Trusted served wrapper, one per Portal | Enforced CSP for that app origin, host kernel, HostConfig/HostConnection, provider facades and iframe transport in its own realm |
| Cross-origin mini app | Client and application code; no bootstrap authority or provider access |

1. Serve each wrapper from the host origin with host-selected enforcing
   frame-src restricted to its exact pinned app origin. Establish policy and
   guards before loading the guest. Preserve exact origin/source/targetOrigin
   checks. Do not substitute srcdoc or a combined A/B guest allowlist.
2. Bind bootstrap and later host-only operations to the host-created instance,
   actual wrapper Window, expected URL and bound Document. Same-URL Document
   replacement is not a restart authorization. Guest ids, URL parameters and
   messages cannot select identity, grants or another policy. Wrappers are
   trusted host code, not security boundaries against each other.
3. Keep raw HostConnection inside its wrapper. Outer controls and provider
   facades are asynchronous host-only adapters; exchange validated public JSON
   snapshots as text and reconstruct/validate in the receiving realm. Validate
   before encoding, retain the strict JSON validator and the guest validation
   order, and never stringify malformed guest traffic to repair it. No host
   credentials, executable configuration or live data objects cross this boundary.
4. Retain the storage provider outside disposable wrappers. The kernel supplies
   manifest.id (ADR 0003); a facade verifies its binding and the outer gateway
   selects the same host-held id, never a guest-selected owner. Same-app Portals
   share app storage, while connection state remains separate. Closing/replacing
   a Portal does not erase data. Memory storage still ends with its provider.
5. A trusted enforced frame-src violation terminally revokes only its Portal.
   Mark it inactive and invalidate host/provider handles before cleanup; block
   new dispatch and late sends, remove listeners and both frames, and release
   owned frame/control references even if cleanup fails. No automatic revival on return.
   Only an explicit host action creates a fresh instance. Already-dispatched
   provider side effects are not rolled back. Peer timeout behavior is unchanged.
6. Allowed inner navigation follows §5.1: repeat initialize resets only the
   specified document state, preserving grants and storage. Do not use load as
   an origin/epoch signal. A wrapper replacement instead requires a fresh binding.

## Consequences and implementation gate

This proposal **touches security requirement §9.2**. It defines browser prevention
plus revocation on an enforced violation, not universal current-URL observation
or synchronous cancellation. Origin filtering alone cannot claim conformance.
There is no application-wide single-Portal/domain limit. The cost is an extra
trusted iframe per Portal, explicit realm adapters and complete teardown.

[Integration details and acceptance checks](../browser-portal-ownership-proposal.md)
separate measured foundations from unimplemented provider/control adapters.
Those adapters, outer-frame removal and storage across wrapper restart still
need tests and browser evidence. Approval authorizes recording the development
contract in SPEC, deriving failing tests, and implementing T18 in small steps.
Unsupported/unverified configurations cannot claim
navigation conformance. SPEC §11 document epochs and peer disconnect stay open.

Keeping the current SPEC instead leaves browser containment unresolved. An
outer-host kernel with a wrapper relay could reduce API realm crossings, but
is unverified and is not this proposal. Neither alternative restores the old
single-Portal restriction. Acceptance does not by itself establish implementation
or browser conformance; the checks above remain required.
