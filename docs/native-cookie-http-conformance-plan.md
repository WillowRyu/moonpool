# T28 — Common cookie/HTTP review and paired evidence plan

Date: 2026-11-03
Status: Review and test design complete; bounded C09/C10 measurements recorded in
the [verification report](native-cookie-suppression-verification.md), and a bounded
C01–C03 / C05–C08 broker subset in the [broker report](native-http-broker-verification.md).
The iOS retained-cookie failure, the iOS `Basic` 401 parity item, the full corpus and
final contract approval remain open.
This accompanies the [proposed contract](native-cookie-http-contract.md) and
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md).
It neither accepts a contract nor establishes native conformance. SPEC is unchanged.

The subsequent [accepted admission baseline and recovery draft](native-cookie-store-admission.md)
adds reviewable subcases for C09–C12: whole-partition presence, preserved non-cookie
data, same-app concurrency, stale callbacks and explicit recovery. These subcases
are pending despite baseline acceptance on 2026-11-03; recovery remains unapproved,
and the original seeded-cookie iOS failures remain recorded as failures.

[iOS partition and writer verification](native-cookie-partition-writer-verification.md) adds a C09 blocker: a new process's
first enumeration falsely reported empty. Its evidence rule is an accepted design direction,
and [a bounded run](native-cookie-empty-store-verification.md) measured it on cookie-free and cookie-bearing stores. [Android's new-process answer](native-cookie-android-restart-verification.md) was also
measured, as was [iOS's first question in a new process](native-cookie-first-question-verification.md). C09 stays open.

[Bounded admission verification](native-cookie-admission-verification.md) now covers
the prepared native presence/refusal/data-preservation cases and nine controlled
callback scenarios. Whole-backend iOS partitioned coverage and real writer/owner
exclusion remain open; do not mark the entire admission or C09/C10 corpus complete.

[Native HTTP transport evidence](native-http-transport-verification.md) is the first broker-side measurement. It covers transport prerequisites of
C02, C03, C06 and C08, not those cases. The maintainer accepted its transport rules as a design direction on
2026-11-03, and the procedures below reflect them.

[Android global handler evidence](native-http-global-handlers-verification.md) found a host's `CookieHandler` and `Authenticator`
reach `HttpURLConnection` with no per-request opt-out. [OkHttp evidence](native-http-okhttp-verification.md) measures the alternative the
maintainer accepted on 2026-11-04, pinned to 5.5.1. Android broker experiments for C01–C08 use that client.

[Broker evidence](native-http-broker-verification.md) is the first paired broker measurement, collected on 2026-11-05: 63 cases
drawn from the C01–C03 and C05–C08 subsets pass on both platforms, with identical guest-visible results, receipts and jar effects.
It answers both questions the transport report left open about the accepted iOS `Basic` 401 resend: the jar keeps the second
response's cookie, and the guest's own `Authorization` is replayed. The first of those broke parity, until [a later measurement](native-http-failure-response-verification.md) found the first cookie readable at the
challenge and the broker started committing it. It also measures that a comma in a cookie value can drop `HttpOnly` on both
platforms, which the contract now states.
C04 and C09–C12 remain untouched, and no procedure below is marked complete by it.

## 1. Review outcome and decisions still required

The async SDK direction and Android/iOS parity requirement are already recorded.
The following concrete consequences still need final contract approval. Proposed
behavior is an oracle for a future isolated experiment, not an existing SDK API.

| Existing behavior / constraint | Proposed behavior to review | Consequence and remaining evidence |
| --- | --- | --- |
| Browser cookie support differs in retained Android/iOS probes | Both guest WebViews have ineffective cookie writes and empty reads; native app-owned jars handle sessions | Legacy document.cookie code must migrate. C09/C10 must establish isolated suppression before this can be promised |
| The current capability set has no native HTTP client | Explicit http grant plus host-approved HTTPS origins; native first-party service context | Browser CORS/SameSite filtering is not reproduced. C01/C05 prove authorization and host credential separation; no host login reuse |
| No native credentials/redirect defaults exist | Include cookies by default; omit suppresses both send and store; return 3xx without following | Existing Fetch defaults and redirect login flows require adaptation. C02/C06/C12 measure the supported subset |
| Portal/provider data can outlive a document | One app jar shared across Portals; app-wide reset fences old writes; session cookies end on host-process restart | Closing a Portal is not logout. C07/C08/C11 separate document, session and server lifetimes |
| Current providers map throws to fixed -32603 | Typed provider outcomes for proposed native errors, plus explicit request/result schemas | T29/T31/T35 must define the public boundary. A native exception is not a working -32007 response |

This touches **SPEC §9.1–§9.7**, particularly credential separation, dispatch
authorization, asynchronous operation and schema validation. Service registration
restricts an existing grant; it never grants a capability by itself. Preserve
§4.2 validation order, §4.5 timeouts and §4.6/§4.7 first-settlement behavior.
The current §8 scheme requirement and §6.3 capability set remain normative.

The first technical uncertainty is suppression without collateral effects.
Android's [CookieManager reference](https://developer.android.com/reference/android/webkit/CookieManager#setAcceptCookie(boolean))
describes application-wide acceptance, while
[Profile.getCookieManager](https://developer.android.com/reference/androidx/webkit/Profile#getCookieManager())
returns a profile's manager. These do not alone establish policy isolation.
Apple exposes a per-store
[cookie-policy API](https://developer.apple.com/documentation/webkit/wkhttpcookiestore/setcookiepolicy(_:completionhandler:)),
but its existence is not evidence for pre-existing cookies, all request paths or
an unaffected host control. References reviewed on 2026-11-03; the initial review
ran no device. Subsequent explicit authorization permitted the bounded experiment.

## 2. Execution order and honest completion

1. **First bounded experiment: C09/C10 suppression feasibility.** Use only owned
   test partitions and public markers. Establish working host/control cookies,
   then disable only the candidate guest partitions. No native HTTP broker is
   needed to decide this prerequisite. A global side effect fails the candidate.
2. **After that prerequisite:** build a controlled HTTPS fixture and isolated
   native broker experiments for C01–C08 and applicable C11/C12 behavior. Write
   tests before helper/probe implementation. Keep experimental schemas distinct
   from future public SDK exports. Native runs need a separate explicit resume.
3. **Final contract and integration:** retain all C01–C12 requirements, resolve
   public schemas/lifetimes with T29/T31, and repeat the corpus through the real
   loaders, transport, dispatcher and providers in T38–T43 and T51/T52/T61.

This orders the work; it does not waive any T28 acceptance gate or mark C09/C10
complete after a narrow smoke test. C11 durability/resource promises still depend
on T48/T53. C12 cannot claim a public adapter before its schema is fixed. Record
pending subcases explicitly; a prototype pass is not production integration.
If prerequisite and acceptance work overlap T29/T31, surface that dependency in
the review rather than silently declaring T28 complete or implementing new wire
behavior under protocol 0.1.

## 3. Fixture and evidence contract

Use two simultaneous Portals A1/A2 for one full manifest id, B for another,
an owned host-control WebView H, and a separate cookie-enabled control U. H and U
simulate unrelated consumers using public sentinels; never use the maintainer's
real sessions. Separate native host-client and broker jars as well as WebView
stores. Record each platform's versions, feature checks, source/artifact hashes,
policy-install completion and first guest execution.

The full corpus needs a controlled HTTPS service with normal certificate and
hostname validation. Provision names/certificates for a parent, two subdomains
and a distinct forbidden origin; record the chosen fixture configuration before
execution. Placeholder example domains in this document are not test targets.
Do not disable TLS checks or install a machine-wide trust root to get a pass.
If trust needs provisioning, scope it to the dedicated fixture environment and
record it. A fixture-only HTTP test is not native HTTPS evidence.

The server must support these actions with run/case/request correlation:

| Action | Independent observation |
| --- | --- |
| Issue script-readable and HttpOnly public marker cookies | Separate Set-Cookie fields and status; ordinary bodies never reflect protected markers |
| Record received requests | Raw Cookie fields, method, target, arrival id and guest/native request correlation in host-only evidence |
| Return 3xx to a controlled target | Count hits on both original and redirect target |
| Hold before response headers | Runner confirms request arrival, performs reset, then releases headers |
| Send headers but hold the body | Broker confirms header processing, then runner resets or induces a body failure |
| Finish an observation window | Correlated server counters plus successful positive controls; absence of a JS result alone is not a negative pass |

Keep control/status/release endpoints on a separate unregistered control
origin/listener, unreachable through the guest's approved service surface;
another path on an approved origin is not isolation. No probe control token or native ownership handle crosses the
bridge. An HttpOnly marker may occur in restricted runner/server evidence but
must not be returned in the guest-visible fixture response. An optional deliberate
reflection control must be labeled as service disclosure, not broker disclosure.

Use event barriers, not arbitrary sleeps, for ordering cases. Record the server
arrival, native response-header queue entry, cookie commit, reset barrier and
guest settlement separately. Independent verification reads these raw events;
it must not trust an app-generated passed flag. Negative runs need a healthy
positive control and a bounded completion/timeout record to distinguish a broken
fixture from denial.

Each result records case/subcase, Android/iOS status, expected observation,
actual observation, evidence references and limitation. Allowed states are
pending, pass, fail and unsupported; unsupported is never a parity pass. Compare
the normalized public result and server/jar effects, retaining platform details.
Run the verifier against deliberately altered evidence to ensure missing controls,
cross-app markers, a redirect hit and a stale post-reset commit are rejected.

## 4. C01–C12 procedures and expected observations

### C01 — Ownership and dispatch

Seed A, B, H and the native host client with distinct public marker values for
the same service. A1/A2 observe the same app session; B and H retain theirs.
Try forged app/jar/context fields, an unapproved target, missing grants, a retired
owner and a valid authorized call. No rejected operation reaches a network or
cookie mutation. Even A1/A2 sharing a jar does not share grants: the Portal making
each operation needs its own grant. Only native binding selects the app.

Pin the §4.2 order: missing scope wins over malformed method-specific fields;
with the scope present, unknown app/jar/context fields receive proposed -32602.
A syntactically valid but unapproved service receives proposed -32000. Exact
URL/header normalization vectors remain a T29 prerequisite, not native defaults.

### C02 — Automatic login and credentials

Return a login Set-Cookie in include mode, await completion, then request the
service from A2. Server evidence must contain A's marker without a JS cookie read.
Repeat with omit on outgoing and incoming paths separately: no jar cookie sent,
no response cookie stored, and the previous jar value preserved. Omitted
credentials behaves as include under the proposal. A guest-owned Authorization
header remains explicit data in omit mode; omit is not an anonymity claim.
Reject caller-supplied Cookie and case variants before network dispatch.

### C03 — HttpOnly and response projection

Set an HttpOnly marker from the server. Confirm its later receipt at the server,
and absence from cookie reads, returned headers, request metadata, errors,
diagnostics and events exposed to the guest/private runtime. Attempt create,
overwrite and delete through script-cookie operations, including expiry-based
deletion of the protected identity. The protected value survives; ordinary
script-readable cookie operations still work. Multiple Set-Cookie lines reach the shared
parser through the same fold-then-split pipeline on both platforms and are not accidentally exposed. Same-name cookies at other paths are tested
separately; this is not a promise to prevent every server-side cookie-shadowing
or response-body reflection behavior.

### C04 — Cookie syntax and attributes

Use a versioned table of exact input, accepted/rejected cookie identities,
selected header pairs and expiry times. Cover host-only versus Domain,
public-suffix and sibling rejection, Path matching, same-name distinct paths,
replacement/deletion, Max-Age precedence, Secure, SameSite and prefix rules.
Use a controlled clock for algorithmic expiry tests and separate native clock
observations. Compare the ordered Cookie header as well as resulting identities.

Do not derive the oracle from either OS's cookie parser; they measurably disagree. Include the pipeline's
documented limit, where a value containing `, name=` becomes an extra cookie on both and the earlier pieces lose their
attributes, including `HttpOnly`. Exact parsing tolerance,
identity including host-only treatment, prefix case handling, header ordering,
public-suffix data revision, newer attributes and resource limits are unresolved
profile inputs. Freeze them before claiming this case passes. RFC 6265 and the
linked 6265bis draft are references, not interchangeable automatic specifications.
This review adds no new cookie profile or numeric product limits.

### C05 — Service context and authorization

Run the same approved requests from each physical guest scheme with Strict,
Lax, default and valid None cookies. The proposed first-party service context
selects the same cookies. Deny foreign service origins, insecure targets and
guest-supplied context claims without a server hit. Require an explicit grant
even where the server would allow browser CORS; absence of CORS permission does
not revoke granted native authority. Test distinct ports for service authorization
without treating cookie ports as jar partitions. H's credentials never appear.

### C06 — Redirects and HTTP status

Return 301/302/303/307/308 responses to both approved and forbidden controlled
targets. The original status and permitted headers are returned, while target
hit count remains zero. Include commits eligible original-response cookies;
omit does not. A later explicit request independently rechecks authorization.
Repeat cookie handling for 4xx/5xx normal results. No platform auto-follow, authentication
challenge credential reuse or SDK retry may hide a hit. An iOS resend after a `Basic` challenge is
OS behavior: count it from server receipts, require no credentials on it and a 401 result on both.

### C07 — Ordering and Portal lifetime

Await a script-cookie set in A1, then request/read in A2; repeat delete/read.
Start two requests and release their response headers in the opposite order.
Wait for the first header queue/commit barrier before releasing the second;
the final matching cookie follows native header-queue order, not start order.
Recreate a Portal and verify retained jar data and fresh connection grants.
Close a Portal with accepted HTTP work pending: document retirement excludes
late delivery, while accepted eligible cookie effects retain their independent
session lifetime. Final settlement details remain T30/T31 work.

### C08 — Reset and stale work

Exercise all three windows; count actual mutation events, not just UI results:

| Window | Sequence | Proposed expected effect |
| --- | --- | --- |
| Before headers | Server holds old request; await A's reset; release Set-Cookie | Old generation cannot commit or restore A's session; a still-pending native operation has the proposed sessionReset outcome |
| After headers, before body | Send one body byte so iOS delivers headers; confirm old header commit; hold the rest; reset; release | Reset removes the committed cookie; body completion cannot resurrect it or report a new old-session success |
| Already settled | Complete old request; reset; issue fresh request | Old settled Promise is unchanged; fresh request has no previous session cookie |

Run reset from A2 and observe A1; B and H continue normally. Repeat with a request
queued but not yet started, two resets and a fresh post-barrier login. Check the
post-reset generation's new cookie survives while the old one cannot return.
Client timeout/close may already have settled a Promise: never replace its first
outcome. Native cancellation is not assumed to undo a server effect. Inject reset
failure; session use stays unavailable, without restoring old credentials. Error
schema and recovery admission remain explicit T29/T31 decisions.

### C09 — Browser paths

Before enabling any guest bridge, verify policy completion precedes its first
script. Test document.cookie through the ordinary property, prototype access,
new same-origin frames and reload/recreation. Reads are empty and writes have no
effect, including with pre-seeded owned cookies. Test local and allowed remote
resource responses carrying Set-Cookie; no engine jar write or outgoing engine
Cookie is accepted as a fallback. Native broker cookies never enter these paths.

The full negative matrix includes fetch, XHR, sendBeacon, WebSocket, EventSource,
forms, subframes, popups, resource redirects, workers and retained service-worker
registrations where available. Keep same-app local assets and permitted static
resources as positive controls. A remote executable resource joins the app's
trust even though its resource request receives no broker cookie. Test initial
execution and an existing owned store; an empty fresh store alone cannot pass.
Unavailable features are labeled unsupported, not silently marked tested.

### C10 — Suppression locality

First prove H and U can set, read and send their cookies. Install the candidate
policy only on A; A1/A2 lose engine cookie access while H, U and B retain their
positive controls. Next apply B's policy and repeat H/U controls. Recreate the
owned views/stores and verify the intended policy before guest load again.

Compare policy reads, guest observations and server receipt. Do not use the
default CookieManager or an application-global switch as a substitute for a
selected Profile's manager. No unrelated app/profile or real host store is used.
If the selected public API changes H/U behavior, stop and report unsupported;
do not fix the experiment by deleting control cookies or weakening the oracle.

### C11 — Lifetime, unsupported states and failures

Distinguish Portal reload/recreation, renderer loss and native host-process
restart. The proposed session cookie survives the first two Portal operations
but not host-process restart; an unexpired persistent cookie survives a controlled
restart. Record native owner lifetime and store identity so renderer replacement
cannot masquerade as process restart. T48 still owns crash/power-loss durability.

Inject unavailable features, policy-install failure, TLS/network failure,
header success followed by body failure and reset failure. No guest loads under
an uninstalled policy and no ambient/default jar is selected. Received eligible
cookies need not roll back on later body failure. Exposed failures use the agreed
nonsecret schema, never raw native exceptions. Unsupported admission before a
bridge exists is host-local; it is not fabricated as a guest RPC response.
No intentional app crash or first-WebKit-call enumeration control is part of this
plan. Product size/eviction limits remain T53 work.

### C12 — Developer migration

Use a small fixture API client with an injected async request function: login,
read profile, receive 4xx, observe manual 3xx and reset. Run identical app code on
both OSes and enumerate changed call sites and supported body/header types.
No third-party library compatibility claim follows from this fixture. For any
named library, pin its version and test the actual adapter before claiming support.

Keep negative examples for direct document.cookie, unadapted global fetch/XHR,
redirect login and worker requests. Cookie writes must stay ineffective and
forbidden network paths must not reach the server. Do not promise a JS exception
for legacy cookie writes: silent no-op is the proposed raw behavior. A clear
development diagnostic can explain unsupported use; it is not an enforcement
mechanism or a transparent fallback.

## 5. Next bounded execution and stop conditions

The next device task, if explicitly resumed, is **C09/C10 suppression feasibility
only**, on one session-owned Android emulator and one session-owned iOS simulator.
Record existing device state first; protect unrelated devices. Use the retained
working iOS startup order without replaying the known crashing controls. An
unexpected crash ends that platform's run; retain evidence without automatic
retries. Shut down only newly task-owned devices and close fixture processes.

Deliver policy-order evidence, pre/post H/U controls, A/B local cookie behavior,
server-observed HTTPS cookie send/store controls and recreation observations.
This bounded result cannot close the full C09 network matrix or C01–C12 corpus.
If HTTPS fixture/trust is unavailable, report that gap; do not use an unrelated
public website as evidence of server receipt.

The maintainer subsequently explicitly authorized only the new cookie checks.
Four final runs retained 200 samples and 400 HTTPS receipts, including fresh-empty
and seeded-store controls. Both owned devices were stopped afterward. No broker,
final SPEC change, migration or publication was performed. Return to the decision
table with the measured iOS limitation; full C09/C10 and final normative approval
remain pending. Intentional crash controls remain excluded.
