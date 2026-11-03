# Android and iOS follow-up implementation plan

Date: 2026-10-26
Last updated: 2026-11-03
Status: T22–T27 complete; T28 bounded origin/suppression and admission research recorded; admission baseline accepted; iOS new-process false-empty blocker found and evidence rule accepted as a design direction and correct on one simulator configuration; Android new-process answers correct on one emulator configuration; physical-device and version evidence, recovery, full corpus and final approval pending; T29–T65 planned. Private native host runtimes selected; origin/cookie, codec, document and lifecycle contract gates remain explicit.
Targets confirmed by the maintainer: Android (AOS) and iOS, both required.
SDK/reference-host model: framework-neutral Swift/Kotlin facade with private JavaScriptCore / JavaScriptSandbox runtimes (ADR 0025). Actual consumer app/framework remains a T56 decision.
Baseline: browser v0.1 complete, published through 91d7b46; 1131 tests / 39 files.
Normative source: SPEC.md and accepted ADRs. This plan does not amend them.

Maintenance before T24: the requested [code-quality pass](code-quality-workflow.md)
consolidates proven duplication and adds regression/loopback tests. The later
[T24 iOS experiment](ios-origin-probe-verification.md) resumed on request and
records independent simulator evidence; host-only tests remain separate.

The maintainer's [scheme/origin discussion](native-origin-options.md) records
the Android HTTPS candidate and remaining iOS/message/cookie checks. It does
not approve a SPEC change or complete T28. [T25 Android message evidence](android-message-probe-verification.md)
now records origin/frame-aware callbacks, port bootstrap and provenance gaps;
[T26 iOS message evidence](ios-message-probe-verification.md) now adds per-world
metadata and direct-reply versus generic-execution behavior. The separate
[runtime comparison](native-document-lifetime-comparison.md) is source research,
not vendor-device testing or a production contract decision.

After the comparison, the maintainer selected explicit document generations
in [ADR 0024](adr/0024-bind-rpc-work-to-document-generations.md). This accepts
the design direction for T30 and supplies an [isolated kernel regression probe](../experiments/document-generation-contract/README.md).
T30's versioned wire/bootstrap contract and T31's pending/close semantics remain
open; T32 implementation has not started. T27–T29 dependencies still apply.

T27 selects [private native host runtimes](adr/0025-own-native-kernels-in-private-runtimes.md)
after [paired common-kernel probes](trusted-runtime-verification.md). Native,
RN and Flutter apps can use the native facade; framework bindings are separate,
unimplemented work. The consumer app is not selected by this SDK model decision.

## Scope and completion levels

The maintainer requested detailed next-phase tasks for both mobile platforms.
This authorizes a post-v0.1 plan, not implementation, SDK installation, a protocol
change, package publication or app distribution in this planning turn. The
completed T01–T21 browser plan remains available separately.
Subsequent task requests authorize their bounded work: T23 adds an experimental
Android probe, not the native SDK implementation gated by the contracts below.

Use the existing TypeScript protocol/client/host kernel as the common authority.
Do not duplicate dispatch/permission/correlation logic in Kotlin and Swift as a
routine implementation shortcut. Where and how the trusted host kernel runs is
an explicit architecture gate. Native probes may use minimal platform apps;
they do not select the final host framework or public SDK packaging.

| Level | Tasks through | What completion permits |
| --- | --- | --- |
| M0 — browser baseline | T21, complete | Existing browser-development experiments |
| M1 — native contracts ready | T31 | Native implementation against measured, approved contracts |
| M2 — both-platform PoC | T45 | Development use in Android and iOS reference apps with public sample data and memory storage |
| M3 — integrated/device-verified candidate | T61 | Internal evaluation in the selected real app(s), with durable storage, lifecycle/security/pool checks |
| M4 — deployment decision | T65 | Evidence-based decision on a bounded pilot/release for the tested configuration |

M2 requires both Android and iOS tracks; one platform's result never closes its
counterpart. M2 is not customer-production readiness. M4 is a decision supported
by evidence, not automatic permission to publish or a guarantee for every device.
No v0.2/v1.0 number, minimum OS, engine dependency or release date is assigned here.

| Current task range | State | Evidence |
| --- | --- | --- |
| T22 | Complete | [Local toolchain/target inventory and T23/T24 criteria](native-target-matrix.md); no native build/boot evidence |
| T23 | Research complete | [Android build/emulator observations](android-origin-probe-verification.md); custom-scheme app isolation fails in the tested configuration |
| T24 | Research complete | [iOS simulator observations](ios-origin-probe-verification.md); distinct custom origins/DOM/storage, unavailable custom cookies and observed HTTP session-cookie loss |
| T25 | Research complete | [Android message observations](android-message-probe-verification.md); metadata and authenticated initial port handoff work, origin-only replacement and transferable-port provenance gaps remain |
| T26 | Research complete | [iOS replies/worlds](ios-message-probe-verification.md); direct native replies stay with their original Promise; global/old-frame execution can reach the replacement document |
| T27 | Complete | [Accepted runtime/ownership model and paired evidence](trusted-runtime-verification.md); 12 native runtime owners, 180 kernel vectors, 120 evidence checks and two Node VM tests |
| T28 | In progress / expanded contract | [Origin evidence](native-origin-contract-verification.md): Android 44 / iOS 52 samples, six startup controls. Maintainer now requires cookie parity; [ADR 0027/common async cookie and HTTP design](native-cookie-http-contract.md) proposed; C01–C12 paired evidence and final approval pending |
| T29–T65 | Planned | No production native SDK verification yet |

## Decisions that precede implementation

1. **Target/host constraints:** framework, candidate OS/WebView versions, real
   host integration, required native build tooling/devices and supported features
   are recorded in T22. Unknown values stay unknown until evidence/maintainer input.
2. **Origin and loader:** SPEC §8 requires moonpool://<mini-app-id>/ and names
   WebViewAssetLoader for Android. Official Android documentation describes that
   loader using HTTP(S), and custom-scheme message allow rules do not include a
   host pattern. These are concrete feasibility risks, not proof that the current
   invariant works or permission to replace it. T23/T24 measure; T28 must resolve
   any conflict in an approved ADR/SPEC decision before implementation.
3. **Trusted kernel location:** T27 selected framework-neutral native facades,
   per-Portal private JSC VM/context on iOS and an isolate in one app-owned Android
   JavaScriptSandbox. Native owners serialize controls and retain credentials/
   providers outside the disposable runtime. The kernel must not share an
   untrusted guest context or receive authority from guest ids/URLs/objects.
4. **Wire/codec:** T29 assigns text encoding, decoding and error ownership. Native
   conversion must not silently repair invalid values or change JSON semantics,
   validation precedence, numbers/Unicode or the meaning of a send failure.
5. **Document identity:** T30 defines how old initialize replies, results, errors
   and notifications are kept out of a new document, including reused request ids.
   Field names/version changes are decided there, not invented in this plan.
6. **Termination/lifecycle:** T31 reconciles §11, ADR 0002 and dismissal acceptance.
   Graceful shutdown and sudden renderer loss have different possibilities.
   Sending paused does not prove persistence or receipt. Any new event, grace
   period, timeout or Transport change needs its explicit contract first.
7. **Durability and resources:** T48 and T53 define storage guarantees and measured
   pool/resource defaults before their implementations. Numeric limits and error
   mappings are not chosen just to make a test pass.

T28 now includes a common-cookie/HTTP substep under its existing id. The
maintainer requires the same application-facing behavior on Android/iOS and
prefers a common async SDK, with explicit developer compatibility review.
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md) proposes
native jar ownership, automatic sessions, browser-cookie suppression and C01–C12.
No raw iOS-cookie limitation may be treated as completion of this requirement.
The [paired evidence plan](native-cookie-http-conformance-plan.md) now defines
procedures, independent server observations, response-header/reset barriers and
remaining profile/schema decisions. The explicitly resumed
[bounded C09/C10 experiment](native-cookie-suppression-verification.md) retains
200 samples/400 HTTPS receipts: policy locality works; iOS seeded cookies remain
readable/sent, while fresh disabled stores pass on both. Retained-store admission
has an accepted baseline; migration requires review. Full cases and all acceptance gates remain open;
both owned devices are stopped and intentional crash controls remain excluded.
The [admission baseline](native-cookie-store-admission.md) was accepted as a direction
on 2026-11-03: common cookie-present/unknown refusal, data preservation and same-app
shared retirement, without automatic deletion/import. Cookie-only recovery remains
separately gated. This does not implement a loader or migration, accept the rest
of ADR 0027, or grant new device scope. Do not ask again about the accepted baseline.
[The requested bounded admission follow-up](native-cookie-admission-verification.md)
now records 48 native presence/admission samples, 76 HTTPS receipts and nine
controlled callback scenarios. Prepared cookie-bearing cases refuse and retain
data; empty controls execute. These experimental controllers are not production
SDKs. iOS partitioned coverage and real writer exclusion remain open; devices are
stopped and T28 completion is unchanged.
Cookie setters/HTTP requests are new capability proposals, not current exports
or manifest scopes. Keep SPEC, runtime and protocol version unchanged until the
contracts are approved. The bounded cookie authorization does not reopen crash controls.

[iOS partition and writer verification](native-cookie-partition-writer-verification.md) measured partitioned listing and
separation, and web-writer exclusion by the deny policy. It also found a blocker: a new
process's first enumeration falsely reported empty in 38 of 38 stores with no prior step,
and 0 of 54 after a policy call, `fetchDataRecords` or a load. The maintainer accepted its
iOS evidence rule as a design direction on 2026-11-03. [A later bounded run](native-cookie-empty-store-verification.md) gave the
correct verdict for all 168 cookie-free and cookie-bearing stores, and
[Android's `hasCookies`](native-cookie-android-restart-verification.md) was correct in all 250 stores. On iOS,
[all 36 stores asked about first in a new process](native-cookie-first-question-verification.md) also got the correct verdict. T28 stays incomplete.

[Native HTTP transport evidence](native-http-transport-verification.md) is the first broker-side measurement: both platforms' standard clients support
most broker needs, but iOS folds `Set-Cookie`, resends a request after a `Basic` challenge and delivers headers only with
the first body byte. The maintainer accepted one cookie pipeline and otherwise following OS behavior as a design
direction on 2026-11-03; items to measure before building are listed in that report.

Decision tasks finish when the concrete outcome is recorded and the required
maintainer approval is explicit. A proposed ADR alone does not open a dependent
implementation gate. Present previous behavior, the new problem and each option's
consequences in Korean when asking. Keep unrelated work moving while a gate waits.
Use the next free ADR number when the task runs; do not create placeholder ADRs.

## A. Target evidence and shared contracts — T22–T31

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T22 | Both/shared | Completed 2026-10-27: target/toolchain inventory and host-framework decision points. | Existing ARM64 API 37 AVD and iOS 26.4 simulator candidates recorded, with tool warnings, unknown WebView/support/device details and P01–P10 probe criteria. [Evidence and handover](native-target-matrix.md). No native build or SDK install. | T21 |
| T23 | Android | Completed 2026-10-27: bounded origin/local-content probe with two app ids. | Real API 37/WebView 145 observations: official loader rejects moonpool; public interception loads assets but collapses A/B origin, DOM and storage. HTTPS positive/negative controls, process restart and fallback observations recorded. [Evidence](android-origin-probe-verification.md). T28 resolution remains required. | T22 |
| T24 | iOS | Completed 2026-11-02: matching WKWebView origin/local-content probe. | Five final runs / 55 observations: distinct A/B custom origins, DOM/storage denial, localStorage/IndexedDB persistence, cookie limitations, offline delivery and started-task cancellation. [Evidence](ios-origin-probe-verification.md). T26/T28 remain open. | T22 |
| T25 | Android | Completed 2026-11-02: native message-channel/authentication probe. | Four runs / 44 snapshots, 175 controls and 11 JVM gate cases. Actual listener origin/frame/instance metadata, exact injection, native/guest-created ports, replacement/reload/late reply, proof/delegation and retirement observations. [Evidence](android-message-probe-verification.md). No production authentication or transport approval. | T23 |
| T26 | iOS | Completed 2026-11-02: native message/reply/world probe. | Four runs / 80 snapshots, 187 controls and ten Swift admission cases. Native view/origin/frame/world checks, direct versus global/old-frame replies, replacement/reload, isolated globals/shared DOM and retirement/removal observations. [Evidence](ios-message-probe-verification.md). No production epoch/runtime decision. | T24 |
| T27 | Both/shared | Completed 2026-11-02: accepted ADR 0025 for trusted runtime/native facade ownership. | Maintainer selected the generic Swift/Kotlin SDK model. Unchanged common kernel passes in iOS JSC / Android JavaScriptSandbox, with explicit executor, lifetime, credential and bundle ownership. [Evidence](trusted-runtime-verification.md): four runs, 12 owners / 180 vectors, 120 checks, two Node tests. Production scheduler/providers, framework bindings and real consumer app remain later work. | T22–T26 |
| T28 | Both/shared | Proposed ADR 0026 origin/loader/bootstrap plus [ADR 0027 common cookie/HTTP contract](native-cookie-http-contract.md); not complete. | Keep origin evidence; finalize shared async API and compatibility cost, cookie/native-network authority, equal browser-cookie policy and C01–C12 acceptance. Paired evidence and explicit SPEC approval precede implementation. | T23–T27 |
| T29 | Both/shared | ADR for lossless native JSON/text boundary and errors. | Define codec ownership, invalid-data handling, parse-error correlation, send/receive failures and compatibility, including proposed cookie/HTTP body/header/error schemas. Cover finite numbers, large-number behavior, Unicode edge cases, null/falsy values and getters/toJSON without coercive repair. | T25–T28 |
| T30 | Both/shared | Document generations selected on 2026-11-02; full contract pending. | ADR 0024 accepts explicit generation ownership, retirement and captured work identity. Real-kernel regression probe has two controls passing and three safety assertions red under 0.1. Finalize authoritative bootstrap, metadata/validation, retry/reentry and version migration after prerequisites; coordinate pending/close rules with T31. | T25–T29 |
| T31 | Both/shared | ADR for close, renderer loss and lifecycle/eviction semantics. | Define pending-call disposition, local versus peer close, restart authority, notification/receipt limits and orderly versus abrupt teardown; coordinate native HTTP session-reset rejection without confusing it with terminal bridge close. Reconcile ADR 0002 and §11 using both native probes. | T25–T30 |

T22's first output is a small target matrix and the T23/T24 experiment checklists.
It retained the then-undecided host framework. T27 subsequently selected a
concrete generic native SDK model, without choosing T56's consumer app or adding
RN/Flutter bindings. Probe code is experimental evidence, not a production core.
If a candidate channel lacks origin/frame metadata on each message, T25/T26
must demonstrate authenticated channel bootstrap and document binding. A cached
URL or load callback alone is not an authority check.

## B. Shared implementation foundations — T32–T35

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T32 | Shared | Implement the approved document-identity contract in the pure kernel. | Failing tests first for stale initialization/results/errors/notifications and reused ids; implement only approved wire/version semantics; retain permission/storage state correctly. | T29–T31 |
| T33 | Shared | Implement the approved terminal-close/pending-call contract. | Close/reentrancy/failure/peer-loss tests pass; all pending work is settled as specified, old callbacks cannot reach replacements, and browser regression behavior follows the approved migration. | T31, T32 |
| T34 | Shared | Implement the approved native codec boundary and reusable conformance vectors. | JSON round trips and malformed-input/error cases have normative expected outcomes usable by TypeScript and both native test harnesses. No platform API enters the kernel. | T29, T32, T33 |
| T35 | Shared | Produce the trusted host/client bundle and native-facing entry contract. | Reproducible artifacts run in the selected trusted execution model; public data/callback boundaries, source maps/types and version metadata are documented without exposing host credentials; define explicit provider outcomes for proposed native HTTP errors rather than relying on throws. | T27, T34 |

## C. Android/iOS reference PoCs — T36–T45

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T36 | Android | Boot the selected trusted host runtime in a minimal native module/reference app. | Clean build and create/destroy cycle; common bundle executes in the trusted owner; no live guest authority before configuration. | T28, T35 |
| T37 | iOS | Matching trusted host runtime/reference app. | The same ownership and create/destroy checks pass with explicit actor/thread handling. | T28, T35 |
| T38 | Android | Implement the approved manifest/asset loader and pinned app origins. | Valid bundled app loads; traversal, wrong app, missing resource and unintended network fallback fail closed; policy hooks, including approved cookie suppression/network rules, are verified before enabling the guest bridge. | T23, T28, T36 |
| T39 | iOS | Matching native resource/scheme loader. | Same admission/confinement cases plus approved store-specific cookie suppression, network guards and cancellation/cleanup of outstanding resource tasks; no file:// fallback. | T24, T28, T37 |
| T40 | Android | Implement native Transport with authenticated instance/frame binding. | Actual messages preserve order/data and use approved codec/authentication; unsupported features fail closed; stale or unauthorized senders cannot dispatch. | T25, T28, T34, T38 |
| T41 | iOS | Matching authenticated native Transport. | Same vector outcomes and sender/document binding with actual WKWebView replies; no unguarded string interpolation or stale reply delivery. | T26, T28, T34, T39 |
| T42 | Android | Connect the real kernel to sample profile and app-partitioned memory providers. | First initialize, ping, profile, storage success/denial and all specified producer errors run through actual native transport; no duplicate native dispatcher; after contract approval integrate the proposed app-owned native cookie/HTTP providers and C01–C12 controls. | T40 |
| T43 | iOS | Matching capability integration. | Same observable results, grants and app identity as Android, including two distinct app ids and the approved native cookie/HTTP provider vectors. | T41 |
| T44 | Android | Complete native navigation containment and guest-requested dismissal. | Redirect/form/subframe/foreign and same-origin reload cases follow the approved contract; close acceptance/teardown order, stale handles and A/B independence pass. | T31, T42 |
| T45 | iOS | Matching containment/dismissal verification. | Equivalent negative/positive cases and cleanup pass; new instances never inherit retired authority. Record iOS evidence for the joint M2 gate. | T31, T43 |

M2 gate: both reference apps build and run the same minimal feature/security
flow. Label emulator/simulator evidence honestly; physical-device coverage is
mandatory before the pilot gate. Partial native branches remain experimental.
Browser wrappers/CSP are not automatically the native containment mechanism.

## D. Lifecycle, data and native safety — T46–T55

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T46 | Android | Implement renderer-loss, background/resume and exception-safe teardown behavior. | Handle the affected WebView(s), remove owned references/listeners/ports and settle work per T31; surface/recover through a fresh authorized instance without taking down the host. | T44 |
| T47 | iOS | Matching process/lifecycle handling. | Termination, repeated close, queued callbacks and recreation tests pass; no assumption that an abrupt loss can deliver a final guest notification. | T45 |
| T48 | Both/shared | ADR for retained durable storage and host/account ownership boundaries. | Define per-app partitioning, acknowledged-write durability, ordering/failure semantics and explicit reset behavior. Host account transitions remain explicit app integration concerns, never guest-selected identities. | T27, T44, T45 |
| T49 | Android | Implement/adapt the approved persistent storage provider. | Data survives Portal and app-process recreation as specified; same-app sharing, cross-app denial, null/falsy JSON, delete and interrupted-write behavior are tested. | T46, T48 |
| T50 | iOS | Matching persistent provider. | The same storage contract and failure cases pass on its real backend. | T47, T48 |
| T51 | Android | Complete native security/adversarial integration cases. | Wrong frame/origin/instance, forged grants, invalid native JSON, stale document traffic, path escapes and private provider errors do not cross the approved boundary. Release-mode settings are checked. | T44, T49 |
| T52 | iOS | Matching native security integration cases. | Same contract/corpus and platform-specific negative controls pass without relaxing checks to match platform behavior. | T45, T50 |
| T53 | Both/shared | Measure owned-view capacity and approve ADR 0002 pool/resource defaults. | Decide active cap/LRU, prewarming, memory-pressure response, reuse/reset rules and any numeric/error policy from both platforms' evidence. No app-wide memory manager or telemetry. | T46, T47, T49, T50 |
| T54 | Android | Implement approved owned-WebView pool mechanisms. | Cap/LRU/prewarm/pressure behavior and per-instance cleanup follow T53; eviction/reuse cannot leak grants, callbacks or another app's data. | T51, T53 |
| T55 | iOS | Matching pool mechanisms. | Equivalent lifecycle/eviction contract and cleanup evidence; distinguish released owned references from immediate OS memory reclamation. | T52, T53 |

ADR 0002 remains part of the native lifecycle/pool target. Its sample numbers
are not chosen defaults for this plan. Do not promise B survives a renderer
termination that the OS actually reports as affecting both A and B; isolate
handling per affected instance and retain data in its independent owner.

## E. Real-app integration and parity — T56–T61

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T56 | Both/shared | Select the real host app(s), one useful screen and integration contract. | Identify actual repositories/host framework, public data/provider bindings, durable storage needs, lifecycle owner and supported matrix. If no real host is selected, real-app readiness stays pending. | T27, T48 |
| T57 | Android | Integrate the selected app screen with the native SDK. | Useful mini-app flow runs in the actual host app; framework-specific bindings are limited to the selected host model; credentials stay host-side. | T54, T56 |
| T58 | iOS | Matching real-app screen integration. | Equivalent function/data/lifetime behavior in the selected iOS host, with explicit platform differences documented. | T55, T56 |
| T59 | Android | Verify the declared real-device/OS/WebView matrix. | Physical-device evidence covers lifecycle, process loss, storage, navigation, sender identity and unsupported-feature paths, with exact versions and reproducible traces. | T57 |
| T60 | iOS | Verify the declared real-device/OS matrix. | Physical-device evidence covers the same contract, memory/termination conditions and current/minimum supported versions; simulator results are labeled separately. | T58 |
| T61 | Both/shared | Reconcile cross-platform conformance and run browser/native regressions. | Both device matrices, shared vectors (including approved C01–C12 cookie/HTTP cases) and existing browser tests agree with the approved versioned contract; differences and failures are resolved or explicitly exclude a configuration. | T34, T59, T60 |

T56 can be prepared once its prerequisites are ready; it need not wait for
all later-numbered implementation work. Independent platform tasks may be
scheduled separately, but this plan does not request multi-agent delegation.

## F. Artifacts and deployment decision — T62–T65

| ID | Target | Task / deliverable | Acceptance | Depends on |
| --- | --- | --- | --- | --- |
| T62 | Android | Package a reproducible consumable native/JS artifact. | The selected packaging route imports/builds in a clean consumer; assets, types/API metadata and kernel/protocol versions are consistent. Public registry publication is not required. | T61 |
| T63 | iOS | Matching consumable artifact and clean-consumer build. | The selected packaging route includes the same contract/bundle and documented integration, without requiring this repository's undeclared paths. | T61 |
| T64 | Both/selected apps | Prepare and run a bounded pilot acceptance exercise. | Use the intended artifacts and declared device matrix; collect pass/fail evidence for real user flows and recovery. External distribution requires the maintainer's chosen destination/audience, not this planning request. | T62, T63 |
| T65 | Both/shared | Write native readiness/conformance record and release recommendation. | Every promised requirement maps to both-platform evidence; unresolved blockers stay visible; document compatibility, integration and recovery procedures. A maintainer can make a concrete deployment decision. | T64 |

## Working rules

- Keep the browser v0.1 baseline and previous task ids/lessons. T22–T65 are 44
  follow-up tasks; use the progress ledger for their actual state. Split a task further
  if evidence warrants it; retain its id and record the substeps/dependency change.
- One task ends with a small verified result and a Korean explanation with code.
  Add failing tests before functional implementation; write observation criteria
  before probes and record actual device/simulator results separately.
- Update HANDOFF, this plan and study/ as tasks complete. Commit/push when asked.
- A design task can be awaiting_decision; dependent implementation must not run
  on an unapproved draft. A probe may complete with evidence of incompatibility,
  while the implementation gate remains closed until an approved resolution.
- Never infer one OS's success from the other's result. Keep exact OS, WebView,
  SDK/toolchain and device versions in evidence. Do not invent minimum versions,
  performance guarantees, completion dates or task-duration estimates now.
- Keep JSON-RPC, async capabilities, host-held identity/grants and the pure kernel.
  The production origin invariant changes only through explicit approval.
- Select the first useful app flow within the approved capability set. New
  domain methods/scopes need their own explicit contract; real-app integration
  is not implicit authorization to introduce a plugin system or generic registry.
- Dynamic updates/CDN distribution, bundle signing, developer portal, plugin
  systems, Flutter wrappers, analytics and capability discovery are not added by
  this follow-up plan. Inter-Portal messaging is not required for native PoC.
- If a new automated browser runner is later adopted, follow the existing
  reportError/diagnostic decision requirement. Native test tooling must likewise
  be chosen explicitly; no runner or SDK is installed by this planning task.

## Primary documentation checked for planning

These references inform experiment design; they are not device verification.

- [Android in-app content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content): WebViewAssetLoader serves local assets through HTTP(S) origins; this is why the current production-scheme assumption needs a probe.
- [Android WebViewCompat](https://developer.android.com/reference/androidx/webkit/WebViewCompat): message APIs have runtime feature checks and origin restrictions; custom-scheme allow rules have different matching semantics from HTTP(S).
- [Android message listener](https://developer.android.com/reference/androidx/webkit/WebViewCompat.WebMessageListener): native callbacks expose the WebView, sender origin and main-frame information; a candidate still needs instance/document binding.
- [Android renderer termination](https://developer.android.com/reference/android/webkit/WebViewClient#onRenderProcessGone(android.webkit.WebView,%20android.webkit.RenderProcessGoneDetail)): an affected view needs cleanup and multiple views may share a renderer.
- [Apple scheme registration](https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/seturlschemehandler(_:forurlscheme:)): custom handler registration is constrained; registering an already handled scheme is not a general HTTPS interception route.
- [Apple script message](https://developer.apple.com/documentation/webkit/wkscriptmessage) and [frame security origin](https://developer.apple.com/documentation/webkit/wkframeinfo/securityorigin): sender WebView/frame metadata exists; actual custom-scheme semantics still require measurement.

## Current checkpoint

T22–T27 are complete (six of 44 tasks). T23–T26 retain independent native origin,
message and document-lifetime evidence. T27 accepts the generic native facade
and private host engines in ADR 0025; actual providers, authenticated guest
transport and framework bindings are not implemented by its compatibility probe.
T28 is in progress. [The review draft](native-origin-contract.md) proposes Android
local HTTPS, retained iOS custom origins, persistent per-app guest website stores
and per-message native sender admission. The new namespace/store/cookie cases
now have [bounded supplementary evidence](native-origin-contract-verification.md).
Android four runs/44 samples and iOS four runs/52 samples plus six startup controls
are independently verified. Retain the measured iOS enumeration/startup ordering
limit. The maintainer reported disruptive crash dialogs; all device/crash work is
stopped and future routine verification reads retained evidence only. Final
evidence/contract approval remains required before
T28 completion or SPEC changes. T29 and native SDK loaders stay gated; protocol
0.1 and the pure kernel are unchanged.

The subsequent cookie discussion adds [ADR 0027](native-cookie-http-contract.md):
common async SDK preferred, same behavior required on both OSes. The origin
measurements do not test the new native broker or cookie suppression. T28 is
open for final cookie/HTTP design and C01–C12 evidence, not only a publication
or origin-approval checkpoint. No new task ids were added.


The maintainer requested Git publication of the current T28 research and cookie
proposal on 2026-11-03. Android/shared probes are e40b95c; iOS probes are 44b5550;
contracts/reports are b7c25fc. The following study/progress checkpoint records
this grouping. Publication preserves proposed status and does not complete T28,
authorize new device experiments or publish packages/tags. Resume at the open
common-cookie/HTTP design and evidence gates after the requested Git handoff.

The requested T25/T26/generation publication is confirmed through b4b7721 after
four logical commits. The maintainer subsequently requested T27 publication:
42ece91 retains probes/evidence, followed by the decision/study documentation
checkpoint f585961. The current session resumed T28 as a proposal; no package/tag
release, new Git publication or production native implementation is implied.

## Earlier publication checkpoints

The initial planning checkpoint was committed/pushed as 10d75d3 at the
maintainer's request. The maintainer also requested committing and pushing the
completed T22 documentation checkpoint on 2026-10-27, published as db8d6ed.
The maintainer requested Git publication of T23, paused T24 preparation and the
cleanup checkpoint on 2026-10-27. T24 was paused without iOS measurements then;
it resumed and completed on 2026-11-02.
That batch is published as 9f6f300. The additional scheme discussion and study
notes are also explicitly requested for Git publication; no origin policy is
approved by publishing them.
