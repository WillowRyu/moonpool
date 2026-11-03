# 27. Unify cookie sessions through asynchronous native HTTP

Date: 2026-11-03
Status: Proposed overall; admission baseline and iOS presence-evidence rule accepted as
design directions on 2026-11-03 (see the accepted sections below). Cross-platform cookie parity is a maintainer requirement;
option 1 is preferred, while its compatibility cost is under review. No SPEC,
capability, SDK implementation or new native measurement is adopted here.

## Context

T28 measured working Android local HTTPS cookies and unavailable iOS custom-
scheme cookies. The maintainer explicitly requires the same application-facing
behavior on Android and iOS. Recording the difference does not satisfy that
requirement. Portals/Capacitor supplies native cookie/HTTP support, but its
document.cookie compatibility path includes synchronous native calls. Moonpool's
all-async bridge and host-credential isolation remain binding constraints.

The maintainer prefers a common asynchronous API and asked whether migration
would inconvenience developers. The [contract proposal](../native-cookie-http-contract.md)
defines automatic session handling, explicit API migration and the remaining gates.
The [paired evidence plan](../native-cookie-http-conformance-plan.md) records
the review, C01–C12 procedures and C09/C10 as the first feasibility experiment.
The subsequent [bounded C09/C10 evidence](../native-cookie-suppression-verification.md)
shows isolated policy effects but retained-cookie read/send on iOS. Empty stores
blocked before load pass. The maintainer subsequently accepted the
[admission baseline](../native-cookie-store-admission.md); recovery/migration,
the remaining HTTP contract and final normative approval stay open.

## Accepted admission baseline — 2026-11-03

On both platforms, require verified absence of browser cookies under trusted
per-app ownership before admission. Refuse cookie-present or unverified stores
without clearing data or remapping origins/stores. A failed shared gate retires
that app's Portals; other apps and the host remain independent. Preserve browser
and provider data and the separate native HTTP session. No automatic cookie
deletion or import. A future explicit host recovery needs separate approval/proof.

The maintainer accepted this design direction, not all of ADR 0027. Complete
inventory, concurrency, native integration, T29/T31 details and final SPEC work
remain gated. The retained iOS failure is unchanged; no implementation is implied.

Subsequent [bounded admission research](../native-cookie-admission-verification.md)
checks native presence, preserved data and private request/owner identity guards.
These experimental controllers are not a production scheduler or a wire change.
Complete iOS partitioned inventory and real writer exclusion remain open.

## Accepted iOS presence-evidence rule — 2026-11-03

[iOS partition and writer verification](../native-cookie-partition-writer-verification.md) found that a new process's first
`getAllCookies` can report empty for a store holding cookies. The maintainer accepted this
rule as a design direction, in addition to the baseline above:

1. An enumeration counts as evidence only after the same process has awaited cookie-policy
   completion for that store. An enumeration before that point is never evidence.
2. `fetchDataRecords` and `getAllCookies` must both report no cookies. Any disagreement is
   unknown and refuses admission.
3. Support is claimed per measured iOS version. An unmeasured or failing version is unknown
   and refuses admission.

This is a stricter condition for trusting "empty", not a fix: the ordering is undocumented
and its cause is unknown. [A later bounded run](../native-cookie-empty-store-verification.md) gave the correct verdict for all 168
cookie-free and cookie-bearing stores on one iOS simulator configuration, and
[another](../native-cookie-first-question-verification.md) did for all 36 stores asked about first in a new process. No SPEC text or
implementation is adopted. [Android's `hasCookies`](../native-cookie-android-restart-verification.md) was correct in all 250 stores on one
emulator configuration, so this rule stays iOS-only.

## Proposed decision

- Provide the same Promise-based http.request and cookies.get/set/delete
  contracts on both native platforms. Native HTTP automatically consumes and
  attaches app-owned cookies; ordinary login requests require no JS cookie read.
- Keep one native-owned authoritative cookie jar per full manifest id, shared
  by that app's Portals. Isolate it from WebView jars, host HTTP clients and
  other apps. The broker never directly projects HttpOnly cookie values; public
  header results exclude Set-Cookie. A service can still reflect its own data.
- Use an explicitly granted native service-client capability with host-approved
  HTTPS service origins. This is not Fetch/CORS emulation. Each approved initial
  service request has the declared first-party session context on both OSes;
  no automatic redirects or guest-supplied same-site claims are permitted.
- Disable engine-managed WebView cookies on both platforms before guest load.
  Raw document.cookie is unavailable on both; authenticated API traffic uses
  the SDK. Remote browser connections/forms to APIs are blocked in this profile;
  separately allowed resource requests never receive broker cookies. Permitted
  remote scripts join app trust and can invoke the app's granted SDK methods.
  Platform-local suppression and network policy must be proven, not assumed.
- Serialize native jar operations and fence actual cookie writes on app-wide
  http.resetSession. A late old response cannot restore the cleared session.
  Keep storage.* and browser data lifetimes independent of session reset.
- Offer an explicit request adapter for clients supporting injected transports.
  Do not patch global fetch/XHR or emulate synchronous document.cookie with an
  eventually synchronized cache. Document the supported adapter subset.

## Consequences

New mini apps get one API and automatic cookie sessions. Existing applications
must migrate their transport boundary; libraries directly reading document.cookie,
browser redirect login, forms, workers and arbitrary global-fetch integrations
are not drop-in compatible. An adapter reduces changes only where a client accepts
one. An async API does not alter the server's HTTP Cookie/Set-Cookie format.

The service-client context intentionally permits its own Strict/Lax/default
cookies on approved native requests. It does not recreate browser SameSite CSRF
gating; authority comes from the http grant, trusted endpoint configuration and
app-isolated credentials. This security/compatibility choice needs final review.

Native default jars, CORS bypass hidden behind a fetch label, global cookie
switches and JS-only guards cannot establish this contract. New public methods,
scope validation, protected-cookie/error handling and provider outcomes require
explicit SPEC/implementation work after approval. The current host maps provider
throws to fixed -32603; the proposed error mapping is not available automatically.

T28 remains open for this contract and paired conformance evidence. Preserve its
original measurements as evidence of the previous configuration. T29/T31/T35,
native integration, T48 durability and T53 resource defaults retain their gates.
No device or crash experiment is resumed by this design task.
