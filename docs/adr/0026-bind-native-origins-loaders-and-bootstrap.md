# 26. Bind native origins, loaders and bootstrap to trusted app registrations

Date: 2026-11-02
Status: Direction selected on 2026-11-03; supplementary research complete. Final
contract approval follows evidence review, including the measured iOS startup
limit. This is not yet an accepted SPEC amendment; production behavior is unchanged.

Supplementary measurements and support limits are recorded in the
[T28 verification report](../native-origin-contract-verification.md).

The maintainer subsequently required matching cookie behavior on Android/iOS.
Origin/store measurements remain valid, but engine cookie unavailability alone
is no longer an acceptable product outcome. [Proposed ADR 0027](0027-unify-cookie-sessions-through-async-native-http.md)
adds the common async cookie/native-HTTP contract and its evidence gates; T28
cannot be finalized from this origin proposal alone.


## Context

SPEC §8 requires moonpool://<mini-app-id>/ on both native platforms. T23 measures
collapsed Android custom origins and shared A/B DOM/storage; T24 measures distinct
iOS custom origins but unavailable custom-scheme cookies. T25 shows that an
authenticated port handoff does not authenticate subsequent port senders. T27
already selects private native host runtimes; that decision is retained.

Distinct local origins alone also leave cookie domains and the integrating app's
default WebView cookie jar unresolved. The proposal therefore separates physical
origins, guest website-data stores and native bridge authority. The detailed
[contract draft](../native-origin-contract.md) defines the mapping, admission,
loader rules, evidence gaps and proposed SPEC amendments.

## Proposed decision

- Keep the exact manifest id as app/provider identity. Android uses a stable
  locally intercepted HTTPS origin: mp- plus the lowercase, unpadded base32 of
  SHA-256 of the exact ASCII id, directly under .invalid. iOS retains
  moonpool://<mini-app-id>/, admitting only ids whose native URL/security-origin
  representation is exact. Unsupported native ids fail registration; the shared
  manifest grammar is unchanged. Registrations reject collisions and remapping.
- Give each app a persistent guest-only website-data partition, shared by its
  Portals and separate from every other app and host-authenticated WebView.
  Require Android MULTI_PROFILE and an app-specific Profile; use an app-specific
  identified WKWebsiteDataStore on iOS. Never seed host cookies/credentials or
  fall back to the default store. Engine document.cookie is not the proposed
  portable surface: ADR 0027 proposes equal suppression and a common native API.
- Bind each loader to one registered package root. Resolve local assets without
  root escape, app switching or network fallback, including misses. Install
  navigation/resource guards before enabling guest execution or messaging.
- Admit bridge calls only from the active bound WebView's exact-origin main
  frame, checked on every inbound message. Prefer Android WebMessageListener
  with its actual native metadata; retain iOS WKScriptMessageHandlerWithReply.
  Transferable port possession is insufficient authority. Host-supplied public
  bootstrap data cannot be selected by guest claims. Generations remain T30.
- Reject unsupported configurations before guest load. Retire an affected Portal
  on containment failure; returning to its origin cannot revive it. T31 supplies
  exact pending/close behavior. No automatic data migration or storage deletion.

## Consequences and alternatives

This changes SPEC §3.1 / §8 / §9 and the origin invariant in CLAUDE.md only after
approval. It adds no wire field, version or native SDK in this draft. Browser
§8.1.1 and the pure Transport/kernel boundary remain intact.

The extra website-data partitions prevent a shared external service's cookies
from becoming a cross-app or host-to-guest shortcut. They add platform feature,
storage and lifecycle costs; a numeric support baseline and resource limits are
not established. The new namespace, profile/store APIs and parent/remote-cookie
cases now have bounded supplementary measurements. T28 still needs final contract approval.
The tested iOS26.4.1 store-enumeration-first path crashes; an empty nonpersistent
WebView initialization control succeeds without any guest load. Retain that
startup condition for the tested configuration and verify other configurations
independently; no universal workaround or underlying root cause is claimed.

Keeping Android moonpool origins would retain the measured isolation failure.
Sharing a default cookie store would leave credentials and remote-cookie
isolation unproven. A common HTTPS scheme on iOS would need a different loading
architecture; WKURLSchemeHandler cannot replace an already-handled scheme.
Changing iOS hosts to digests would cover more manifest ids but unnecessarily
change its existing origin rule; explicit native registration failure is chosen
instead. No global CookieManager switch, private API or per-app process fallback
is proposed.
