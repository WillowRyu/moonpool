# T28 — Browser-cookie admission baseline and recovery proposal

Date: 2026-11-03
Status: Admission baseline and the §3 iOS presence-evidence rule accepted as design
directions on 2026-11-03. Cookie-only recovery remains proposed. [Bounded native inventory/control evidence](native-cookie-admission-verification.md)
is now recorded; production implementation and final normative changes remain gated.
Supplements [ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md)
and the [common cookie/HTTP contract](native-cookie-http-contract.md).

## 1. Accepted baseline and scope

The maintainer explicitly accepted the baseline: on both platforms, browser
cookies present or an unverified absence check block new admission and retire
existing Portals sharing that app's partition; preserve data and exclude automatic
cookie deletion/import. Do not request approval of that baseline again. Detailed
mechanisms and acceptance subcases below still require validation. Recovery,
final SPEC amendments and production implementation are separate decisions.

Require an SDK-owned website partition with **no engine-managed cookies** on
both Android and iOS. Install and verify the cookie/network policy before guest
execution, and admit only after a complete native cookie-presence check succeeds.
Reject a cookie-bearing partition or an unknown check result without modifying
stored data. Android follows the same rule even where its policy can suppress
existing cookies. Historical successful admission is not a reusable certificate.

The [paired experiment](native-cookie-suppression-verification.md) found that
iOS disallow blocks new writes but retains old HTTPS cookie reads/sends. Empty
partitions blocked before first load passed the bounded checks on both platforms.
Those results informed the accepted direction, not a claim that complete inventory,
admission races or production network containment already work.

The accepted initial baseline has **no automatic deletion or cookie import**.
An explicitly operated, cookie-only recovery can be evaluated separately under
§5; it is not a new guest capability or part of initial admission. Whole-store
replacement and generic data migration are not included. This choice concerns
SPEC §8 stability and §9.1–§9.7, especially credential isolation and async authority.
It does not accept the other origin, cookie-profile, schema or lifecycle proposals.

## 2. What is empty, and what is preserved

| Data / identity | Admission requirement | Effect of admission refusal |
| --- | --- | --- |
| WebView/Profile engine cookies | No stored cookie in the entire assigned partition, regardless of service URL or script visibility | Preserve them; do not delete, copy or expose values |
| localStorage and IndexedDB | May contain existing app data | Preserve data and its stable origin/store assignment |
| Other website state, including cached code and workers | Must satisfy the separate loader/network policy before execution | No automatic erasure; unsupported containment refuses admission |
| storage.* provider data | Independent host-owned app partition | Preserve it |
| Proposed native HTTP cookie jar | Independent authoritative SDK session store; may contain cookies | Preserve it; refusal is not http.resetSession or server logout |
| Host authentication and other apps | Never eligible sources or cleanup targets | Unchanged |

Thus an existing app with settings in localStorage and **zero browser cookies**
can be admitted if the other checks pass. An app with one HttpOnly browser cookie
is refused even if document.cookie is empty. A populated native HTTP jar does not
make the browser partition invalid; those are different stores and authorities.

Keep the exact manifest-id → origin → persistent website-store mapping from the
[origin proposal](native-origin-contract.md). A known missing/mismatched store or
lost registration is a recovery error, not permission to create a new empty one.
A new, unambiguous registration may create its owned partition using that proposal's
registration protocol; no default/shared/ephemeral guest-store fallback is added.
Ambiguous legacy shared-origin data cannot be adopted as one app's data.

## 3. Admission sequence and shared ownership

The trusted native app owner coordinates all Portals using the same partition.
Platform operations remain outside the pure kernel. At every new admission,
including recreation or restart, perform this sequence without guest authority:

1. Resolve and validate the trusted app registration, exact partition and feature
   support. Establish the measured safe engine startup order without loading guest
   content. This proposal does not authorize the stopped store-enumeration crashes.
2. Serialize admission against policy changes, recovery and all permitted native
   cookie writers for this partition. Enforce exclusive SDK ownership. A second
   process or native component that can write outside this coordination makes
   the configuration unsupported; a JavaScript lock cannot solve this.
3. Install the isolated cookie-deny and complete resource/navigation policies,
   await completion where applicable, and verify the selected partition's policy.
   A/B/host controls must prove locality for each claimed configuration.
4. Query cookie presence across the **entire native partition**. The check must
   include HttpOnly, unrelated domains/paths and supported partitioned-cookie
   storage. A document.cookie read, one service URL, or an allowlist scan is not
   sufficient. Treat errors, incomplete coverage and unresolved asynchronous
   operations as unknown; neither true nor unknown grants admission.
5. Before publishing admission, recheck that the native owner, registration,
   policies and writer exclusion still match the checked state. Discard late
   results from cancelled, retired or replaced owners. Do not reuse a stored
   passed flag or let an old callback open a replacement Portal.
6. Enable this Portal's authorized loader/bridge and guest execution under the
   same ownership boundary. Each caller keeps its own grantedScopes. A1/A2 may
   share a serialized check only while its exclusion boundary remains intact;
   a later admission needs a fresh check. Pending verification never permits load.

**Accepted iOS presence-evidence rule (design direction, 2026-11-03).** The
[first enumeration in a new process](native-cookie-partition-writer-verification.md) falsely reported empty until a policy call,
`fetchDataRecords` or a load preceded it. For step 4 on iOS:

- An enumeration counts as evidence only after step 3's policy has completed for that store
  in the same process. An enumeration before that point is never evidence.
- `fetchDataRecords` and `getAllCookies` must both report no cookies. Any disagreement is
  unknown and refuses admission.
- Support is claimed per measured iOS version. An unmeasured or failing version is unknown.

The measured ordering is undocumented and its cause is unknown, so this rule narrows the
risk rather than fixing it. [A bounded run](native-cookie-empty-store-verification.md) gave the correct verdict for all 168
cookie-free and cookie-bearing stores on one iOS simulator configuration, and
[another](native-cookie-first-question-verification.md) did for all 36 stores asked about first in a new process. The sources never
disagreed, so that safeguard is unexercised. Separately, native
`setCookie` is stored and sent under the deny policy, so step 2 must cover native writers in
the SDK. A second store handle for the same identifier shares the policy, so private
identifiers and exclusive ownership are SDK discipline. [Android's `hasCookies`](native-cookie-android-restart-verification.md) was
correct in a new process on one emulator configuration, so this rule stays iOS-only. Android does
not retain deny across a process restart, so step 3 must run before any web content in every
process.

Existing admitted Portals may remain live during another check only if the proven
policy prevents every engine-cookie writer throughout that interval. Otherwise
they must be quiesced before checking, or the configuration is unsupported. This
is a requirement to prove, not a claim that a cookie snapshot or stopLoading
alone excludes outstanding engine work.

If a shared partition gate finds cookies, loses policy validity, or cannot establish
its required evidence while Portals are active, block new admissions for that
**app partition**, retire all Portals sharing it, and invalidate their handles
before cleanup. Preserve other apps and the host.
This wider retirement is accepted because the failed resource is shared; ordinary
closure of one healthy Portal remains independent. T31 must specify the resulting
pending-call behavior. Accepted remote effects are not rolled back, and the
separate native HTTP jar is not reset implicitly.

An unverified result is not evidence that a leak occurred; it is loss of the basis
for continued admission. Observers can report a breach but cannot guarantee
prevention before their callback arrives. Initial cookies being absent does not
prove worker, resource-redirect or cached-execution confinement. The full C09
matrix remains mandatory.

## 4. Outcomes and retry

These are host-local outcome categories for review, **not** new RPC codes,
public method names or a finalized facade schema. Before a guest bridge exists,
there is no guest RPC call to reject.

| Condition | Host outcome | Subsequent action |
| --- | --- | --- |
| Exact owned partition, verified policy/containment, complete check finds no cookies | Admit this current Portal | Keep ownership/policy in force |
| Any browser cookie present | Refuse admission; preserve data | Explain retained browser-session data; no automatic cleanup or retry loop |
| Presence check incomplete, timed out, unavailable or its native sources disagree | Refuse admission as unverified | Host may explicitly retry the complete sequence if the configuration can be supported |
| Wrong/missing registration, shared/default guest store or unsupported isolation | Refuse as unsupported/recovery-required | Repair the approved configuration; never silently re-key the app |
| Recovery in progress or interrupted | Refuse admission for the app | Finish or explicitly reconcile recovery before a new complete check |
| Stale/cancelled owner result | Ignore the result for admission | A replacement owner starts its own verification |

Diagnostics can identify the host-known app and a fixed reason, without cookie
names, domains, values, native exceptions or another app's data. No cookie snapshot
crosses into the guest or private JS host runtime merely to decide emptiness.
An explicit host retry does not delete data, revive retired handles or bypass any
gate. Policy confirmation by the maintainer is not authorization to erase an
integrator's data during a future run.

## 5. Recovery and migration choices

| Option | Consequence | Recommendation |
| --- | --- | --- |
| Refuse and preserve | The affected app cannot launch until its configuration/data condition is resolved; nothing is erased | Accepted initial default |
| Explicit cookie-only recovery in the same owned partition | Browser sessions/settings stored in cookies are lost; localStorage/IndexedDB and other stores must remain | Separate future host-operated workflow after approval and paired proof |
| Copy browser cookies into the native HTTP jar | Imports credentials and browser context whose authority/partition semantics may differ | No automatic import in this profile; authenticate through the app-scoped SDK service flow instead |
| Replace/reset the entire website partition | Can lose or re-key localStorage/IndexedDB and other browser data | Not a recovery fallback; requires a distinct migration/data-lifetime decision |

If cookie-only recovery is later approved, its minimum contract is:

1. An explicit trusted host operation names the known SDK-owned app partition and
   explains the loss of its browser cookies. A guest request, URL or arbitrary
   store identifier cannot initiate recovery. Do not reuse cookies.delete or
   http.resetSession: they operate on the separate native jar.
2. Verify ownership again, block new admissions and retire the app's current
   Portals. Exclude queued/in-flight engine and native cookie writes before deletion;
   merely finishing a JS callback or asking a view to stop is insufficient.
3. Record recovery intent before destructive work. If that record cannot be safely
   retained, do not delete. The persistence/restart mechanism and its guarantees
   require T48 evidence; this proposal adds no power-loss/atomicity promise.
4. Keep cookie-deny policy installed and delete **only engine cookies in that
   exact partition**. Do not clear all website data, rotate identifiers, touch
   provider/native-session stores or alter host/other-app settings. No export of
   cookie values to JS, logs or a generic backup is needed.
5. Await platform completion, then independently check the whole partition again.
   A completion callback or a boolean saying that some cookies were deleted is
   not the emptiness postcondition. Partial deletion cannot be rolled back by
   promise; keep admission blocked on any unresolved result.
6. Mark recovery complete only after the verified postcondition is safely recorded.
   Interruptions stay pending across restart. Recovery success permits a new full
   admission check; it never revives old Portals automatically. Repeated host
   recovery must be bounded/idempotent against the same binding, with no automatic
   retry that broadens deletion scope.

No such cleanup or durable recovery coordinator is implemented by this review.
The initial refusal policy is accepted independently of adding that workflow.

## 6. Platform candidates and limitations

Android exposes [hasCookies and asynchronous removeAllCookies](https://developer.android.com/reference/android/webkit/CookieManager)
and [Profile.getCookieManager](https://developer.android.com/reference/androidx/webkit/Profile).
The selected Profile's manager is the candidate for partition-wide presence;
getCookie(url) is URL-scoped and its partitioned results depend on the supplied
top-level URL. A removal callback reports whether cookies were removed, not a
replacement for verifying an empty result. [Bounded evidence](native-cookie-android-restart-verification.md) covers restart and partitioned
cookies on one emulator configuration; physical-device and version coverage remain unmeasured.

On iOS, [WKHTTPCookieStore](https://developer.apple.com/documentation/webkit/wkhttpcookiestore?changes=_1&language=objc)
provides asynchronous whole-store enumeration and individual deletion. Consume
enumeration inside the native owner and retain only the admission verdict. A
[fixed upstream partitioned-cookie deletion issue](https://bugs.webkit.org/show_bug.cgi?id=313708)
is an additional reason to test the selected deletion path and partitioned data;
it does **not** establish that the measured iOS build is affected or fixed.

References were reviewed on 2026-11-03. Public APIs are candidates, not a proof
that all backend states are observable or safely removable. Do not independently
filter out records by expiry, domain, HttpOnly or unknown attributes to manufacture
an empty result. Unsupported inventory/recovery semantics remain unsupported.

## 7. Acceptance additions and roadmap

These are subcases of the existing C01–C12 corpus, not new T-task identifiers.
Write failing tests before implementation after the relevant contract is approved.

| Existing case | Required new observation |
| --- | --- |
| C09 admission-empty | Fresh and reused cookie-free partitions admit with first guest execution after verified policy; localStorage/IndexedDB sentinels survive |
| C09 admission-present | Script-readable, HttpOnly, unrelated-domain/path and partitioned cookies each prevent any guest load; Android and iOS return the same category |
| C09 new-process presence | In a process that did not write the store, seeded and cookie-free stores each give the correct verdict under the iOS rule; enumeration before policy completion and native-source disagreement never grant admission; each claimed iOS version is measured |
| C09 presence-unknown | Missing API, delayed callback, unsupported coverage and check failure never grant authority; no URL-only shortcut |
| C09 admission-race | A1/A2 concurrent creation, policy change, queued native write and owner replacement cannot use a stale successful check |
| C10 shared-retirement | A's cookie-present, invalid-policy or unverified shared gate blocks/retires A1/A2 only; B and host control retain working cookies and storage |
| C10 preserved-data | Refusal never deletes cookies or changes origin/store ids, localStorage, IndexedDB, storage.* or native HTTP sessions |
| C11 restart/retry | Restart/recreation repeats the gate; registry loss and interrupted recovery stay closed; explicit retry cannot revive old handles |
| C11 recovery, if approved | Host-only cookie deletion with actual HttpOnly/partitioned cases, independent empty check, late-write exclusion and partial-failure/restart controls |
| C12 migration | Existing settings survive refusal/recovery; browser-cookie login loss is explained; no automatic credential import or guest cleanup authority |

The [bounded presence/admission experiment](native-cookie-admission-verification.md)
now records 48 observations, 76 HTTPS receipts and nine controlled native callback
scenarios across two runs per platform. It covers the prepared hidden-cookie,
refusal/preservation and within-process reopening cases. Complete iOS partitioned
inventory, real writer exclusion and production integration remain unverified;
an unknown backend is still ineligible for production admission. Historical
source/evidence and the iOS suppression failure are preserved. Destructive recovery
is not part of this evidence or the accepted initial scope.
T28 stays open. T29/T31 retain facade errors and lifetime details; T38/T39 own
loader/admission integration; T48 owns durable recovery; C01–C12 and T51/T52/T61
still require paired production-path evidence. This baseline acceptance is not final
SPEC approval or native release readiness.
