# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-11-03. The maintainer switched to agent-led implementation
> and requested small tasks with an easy Korean explanation after each task.
> The agent now writes tests and implementation; manual typing and learning
> review are no longer prerequisites. Local study mode is off.
> T01–T21 complete: browser v0.1 milestone; see docs/v0.1-conformance.md.
> T20 baseline: 1131 tests / 39 files, root/lab typecheck, lint and both builds pass.
> Chrome 156 dev, isolated native transport, and final built-preview evidence recorded.
> Multi-Portal research published as 00c0c63 / 76bc212; remote confirmed in sync.
> ADR 0022 accepted revision published as 0397b70; remote confirmed in sync.
> Read docs/implementation-plan.md for T01–T21, dependencies, and spec decisions.
> Current checkpoint: T22–T27 complete; T27 private native runtime/facade model selected.
> Document-generation design direction selected on 2026-11-02; see accepted ADR 0024.
> T30/T31 detailed wire/bootstrap/lifetime contracts remain open; T32 not started.
> Isolated real-kernel probe: 2 controls pass / 3 safety assertions RED under current 0.1.
> Both Android and iOS are required; generic Swift/Kotlin SDK model selected in ADR 0025.
> Actual consumer app/framework remains T56; RN/Flutter bindings are not implemented.
> Read docs/native-implementation-plan.md for the 44 follow-up tasks and dependencies.
> Initial native plan published as 10d75d3; T22 published as db8d6ed.
> Read docs/native-target-matrix.md for tool versions, gaps and pre-code probe criteria.
> T23 found collapsed moonpool origins/shared A/B DOM and storage on WebView 145.
> Read docs/android-origin-probe-verification.md before native origin decisions.
> T24 resumed on request and completed on 2026-11-02; read docs/ios-origin-probe-verification.md.
> iOS 26.4.1 separates custom origins/DOM/storage; cookie limitations remain explicit.
> Five final runs / 55 snapshots; 790 control assertions pass. Owned simulator shut down.
> T25: actual Android listener origin/frame/instance metadata and initial port handoff observed.
> Port callbacks lack ongoing origin/frame provenance; origin-only replacement and delegation gaps remain.
> Four final T25 runs / 44 snapshots; 175 controls and 11 JVM admission cases pass.
> Read docs/android-message-probe-verification.md; only the session-owned Android emulator stopped.
> T26: four runs / 80 snapshots, 187 native controls and ten Swift admission cases pass.
> Captured WK reply closures exclude new documents; global and captured-frame execution can reach them.
> Read docs/ios-message-probe-verification.md and docs/native-document-lifetime-comparison.md.
> Similar-runtime findings are pinned public-source evidence, not vendor device testing.
> T28 origin evidence complete: Android 44 / iOS 52 samples, six iOS controls.
> Maintainer now requires matching cookie behavior; async SDK option 1 preferred
> with developer compatibility questions. ADR 0027/common-cookie design proposed;
> C01–C12 paired evidence and final contract approval remain. All devices stopped.
> T28 cookie research, accepted baseline and study progress are grouped in the
> latest Git publication checkpoint below. Package/tag release and T28 completion remain separate.
> Earlier publication through 921d42c was verified; development-environment cleanup
> completed on 2026-11-03. Common cookie/HTTP review and C01–C12 procedures are prepared.
> C09/C10 bounded checks explicitly resumed and completed: 200 samples / 400 HTTPS receipts.
> Android passes; iOS disallow leaves seeded cookies readable/sent. Fresh blocked stores pass.
> Read docs/native-cookie-suppression-verification.md for the unchanged measurements.
> Admission baseline accepted on 2026-11-03; see docs/native-cookie-store-admission.md.
> Refuse cookie-present/unknown state, retire same-app shared Portals, preserve data; no automatic cleanup/import.
> Do not ask again about this baseline. Recovery, final SPEC and implementation remain separate.
> Bounded admission follow-up: 48 samples / 76 HTTPS receipts / 9 controlled native callback scenarios.
> See docs/native-cookie-admission-verification.md; iOS partitioned coverage and real writer exclusion remain open.
> Both owned devices stopped. Full corpus/final approval remain; intentional crash controls stay stopped.
> The maintainer reported repeated crash dialogs. Do not rerun crash controls
> without an explicit request; routine verification reads retained reports.
> iOS partition/writer evidence complete: read docs/native-cookie-partition-writer-verification.md.
> BLOCKER: new-process first getAllCookies falsely reports empty (38/38 with no prior step).
> Policy/records/load first: 0/54. Undocumented, no root cause.
> iOS evidence rule accepted as a design direction on 2026-11-03. Do not ask again about it.
> Rule measured: 168/168 correct on one simulator configuration; read docs/native-cookie-empty-store-verification.md.
> Android hasCookies in a new process: 250/250 correct; read docs/native-cookie-android-restart-verification.md.
> Android does not retain deny across a process; deny must be reinstalled in every process.
> iOS rule as a process's first cookie question: 36/36 correct; read docs/native-cookie-first-question-verification.md.
> Older checkpoints moved verbatim to docs/handoff-archive.md on 2026-11-03.
> Pre-T24 cleanup: shared test/probe helpers, provider execution and regression tests added.
> Run pnpm run check; read docs/code-quality-workflow.md. Native task checks remain separate.
> Scheme discussion: docs/native-origin-options.md; Android HTTPS is a candidate, not approved policy.
> The earlier scheme discussion and cleanup were published through 4225453.
> The maintainer requested commit/push of the completed T24 research and study updates.
> T24 was published as 5bc8770 / 6c5576e.
> The maintainer requested publication of T25/T26/review/generation work, then T27.
> Source commits: 7327536 native probes; e2e3c72 shared tests; 328280d runtime/UI cleanup.
> T18 published as 4aab691 / ab98b58; remote confirmed in sync before T19.
> T19 published as e2354e6 / 8f98da9; clean remote sync confirmed before T20.
> T20/T21 published on 2026-10-26 as 321d09d / 1637e3d; remote sync confirmed.
> See the latest publication checkpoint for the T24 commit grouping and verification.
> Package/tag publication remains separate from this Git publication request.
> Clarification: one app/screen can contain Portals with different origins.
> No application-wide single-domain or single-Portal restriction is intended.
> Accepted ownership: wrapper-local kernel/API, outer-host retained app-partitioned provider.
> ADR 0022 is ACCEPTED. Do not ask again about the approved browser containment contract.
> T14 acceptance-before-dismissal policy is approved in SPEC §6.2 / ADR 0019.
> The per-connect async onCloseRequested hook is implemented. Do not ask again.
> T12 published as 1465d03 / f271a2f; remote confirmed in sync before T13.
> T13 local-error policy is approved in SPEC §4.6 / §4.7 and ADR 0018.
> The approved fixed -32603 / {phase:"send"} mapping is implemented. Do not ask again.
> T11 staged JSON validation is approved in SPEC / ADR 0016. Do not ask again.
> Policy questions: explain previous behavior → current problem → each option's consequences.
> The request-id policy is approved in SPEC / ADR 0015. Do not ask again.
> The method grammar and -32600 precedence are approved in SPEC / ADR 0014.
> The unencoded relative entry-path policy is approved in SPEC §7 / ADR 0011.
> Name length is approved: 1–40 Unicode code points. Do not ask again.
> The browser mini app now displays Moonpool Explorer after profile.get.
> Preserve prior lessons and explain each task in simple Korean with code.

## 2026-11-03 checkpoint — cookie evidence Git publication

The maintainer answered "네, 커밋하자" to committing and pushing. At publication start HEAD,
origin/master and live remote master were all 913347f. The series is on branch
t28-native-cookie-evidence, not master; merging it is the maintainer's separate decision. Earlier
statements below that nothing is committed describe their own moment. The series groups:

- Handoff archive and its four pointers, verified byte-equal against the previous HANDOFF.
- One evidence commit each for the partition/writer, empty-store, Android restart and first-question
  probes, with their sources, tests and retained reports.
- The accepted iOS evidence rule, verification reports and linked plan updates.
- This progress record with Korean lessons 39, 40 and 41 and the study index.

This does not mark T28 complete, adopt the rest of ADR 0026/0027, change SPEC or protocol 0.1, or
release a package or tag. Candidates were scanned for keys, build output, local paths, device ids
and emails with no hits; local-results stay ignored. No device ran for publication. The test CA
removal from the dedicated simulator is still undecided.

## 2026-11-03 checkpoint — iOS rule measured as a process's first cookie question

After a security explanation the maintainer said "그럼 계속진행라자". That was read as continuing the
verification work, not as commit/push approval: nothing is committed or pushed, and that question
and removal of the test CA from the dedicated simulator are still open. New isolated
experiments/native-cookie-ios-first-question-probe. Read docs/native-cookie-first-question-verification.md.

This closes the gap named in the checkpoint below. Each of 36 stores got its own new process: 12
without cookies were admitted and 24 with cookies were refused, including partitioned-only stores,
with no false admit or over-refusal. The false empty still reproduces before the policy on the same
store (4/4). "First question" means first cookie question: WebKit is still initialized with an empty
view first, because enumeration as the first WebKit call is the known crash path. The two sources
again never disagreed.

Remaining measurable evidence needs other hardware or broader scope: physical devices, other OS and
WebView versions, reboot, service workers, redirects, real Portal teardown. Full C01-C12, remaining
ADR 0026/0027, T29/T31, recovery and final SPEC work stay gated. T28 stays incomplete at 6/44.

Simulator off after detaching the panel, 13 baseline states match, fixture closed, no crash reports.
Reused the empty-store CA, so no new trust root. Retained: 2 reports, 100 receipt rows, 404 verifier
checks, 24 host tests.

## 2026-11-03 checkpoint — Android new-process check and iOS environment cleanup

The maintainer answered "진행하자 그리고 ios 환경은 정리하자". New isolated
experiments/native-cookie-android-restart-probe. Read docs/native-cookie-android-restart-verification.md and Korean lesson 41. Nothing is
committed or pushed; publication was not requested.

hasCookies() was correct in 250 of 250 stores: no false empty and no over-refusal, whether asked
with nothing before it, after a never-loaded view, after deny, or as a process's very first cookie
question. The iOS failure did not appear, so the iOS evidence rule stays iOS-only. Android has no
second whole-store source to compare with. Witnesses must run under allow, because Android's
deny withholds retained cookies; the verifier enforces this.

Android and iOS differ, on one configuration each: Android does not retain deny across a process
restart (96/96), stores cross-site partitioned cookies with no policy call, keeps session cookies
after force-stop (12/12), and loses cookies written just before exit even with deny (24/24).

Open: iOS has not been measured with a cookie-bearing store as a process's first question under
the accepted rule, a gap found reviewing this run. Android WebView updates separately from the OS,
so whether iOS-style per-version support claims fit Android is undecided. Physical devices, other
versions, reboot, service workers, redirects and real Portal teardown remain. T28 stays incomplete
at 6/44. SPEC, protocol and production packages are unchanged.

iOS cleanup: the dedicated simulator is shut down and all 13 simulators are off; it and its data
were not deleted. The Claude desktop app's simulator panel rebooted it after a plain shutdown, so
use the iOS simulator tool's detach action first, then shut down, and recheck the state.

Android cleanup: probe app stopped, adb reverse removed, dedicated emulator stopped, fixture closed,
adb device list matches baseline. Retained: 15 reports, 788 receipt rows, 1817 verifier checks, 45
host tests, lint 0 errors / 16 warnings. One earlier clean cycle stays in ignored local results.

## 2026-11-03 checkpoint — accepted iOS rule measured on cookie-free stores

The maintainer answered "네, 진행하자" to running the cookie-free test named as next evidence
below. New isolated experiments/native-cookie-empty-store-probe. Read docs/native-cookie-empty-store-verification.md and Korean
lesson 40. Nothing is committed or pushed; publication was not requested.

| Stores, written in one process and checked in a new one | Count | Verdict |
| --- | --- | --- |
| Cookie-free, including local data only; cookie gone or never stored | 104 | Admitted, no server witness |
| First-party cookie and partitioned-only cookie | 64 | Refused, server witness |

No false admit and no over-refusal in 168 stores, with both source orders. The two sources
never disagreed, so that safeguard is unexercised; do not claim it catches anything. The
original false empty still reproduces on the same store before the policy (8/8).

Side findings, causes unknown: a cross-site partitioned cookie is stored after explicit
setCookiePolicy(.allow) but not with no policy call, so the earlier partition table describes
explicitly allowed stores. A never-denied cookie written just before exit can be listed and
then not survive, while a following deny call kept it.

The verifier rejected the first collection because partitioned controls held no cookie. It
stays in ignored local results. Outcome criteria did not change.

Next evidence: Android hasCookies in a new process is the nearest gap and needs no new
hardware. Physical iPhone, other iOS versions and reboot remain. T28 stays incomplete at 6/44.
SPEC, protocol and production packages are unchanged.

The dedicated simulator was found booted with the Claude desktop app's simulator panel
attached and nothing else running on it. It was used and left booted as found; 13 baseline
states match, fixture closed, no crash reports. Retained: four reports, 472 receipt rows, 990
verifier checks, 42 host tests.

## 2026-11-03 checkpoint — iOS partition/writer evidence and new-process false empty

The maintainer asked to clean up the handoff and collect the iOS cookie evidence
("정리하면 좋은것은 정리하자. 그리고 ios 쿠키 증거 수집을 하자"). HANDOFF's older
checkpoints moved verbatim to docs/handoff-archive.md, with a byte-equality check and four
stale pointers updated. The stale type-it-yourself memory was replaced. Nothing is
committed or pushed; publication was not requested.

New isolated experiments/native-cookie-partition-probe (iOS only). Read
docs/native-cookie-partition-writer-verification.md and Korean lesson 39. This supersedes the "next evidence" items
in the two checkpoints below for iOS.

| Question | Measured on iOS 26.4.1 simulator |
| --- | --- |
| New-process first enumeration | **False empty** in 38/38 stores with no prior step; a repeated enumeration stays empty; complete at the 0.5 s sample |
| After awaited set/get policy, fetchDataRecords or a load | Correct in 54/54 |
| Partitioned cookies | Separated by top site, listed in inventory, no partition field; script writes in cross-site frames store nothing |
| In-flight Set-Cookie | Lands after an empty check without policy; nothing lands after awaited deny or teardown |
| Native setCookie under deny | Stored and sent, so the policy does not exclude native writers |
| Second store handle | Same object; shares policy and cookies, so owner exclusion is SDK discipline |

Accepted later the same day: the maintainer answered "그럼 지금 채택해서 추가 해둬야 겠다"
after a before/after explanation. The three-part iOS evidence rule is now a design direction
in ADR 0027 and docs/native-cookie-store-admission.md §3: enumeration counts only after
awaited policy completion, fetchDataRecords and getAllCookies must both report none, and
support is per measured iOS version. Do not ask for this approval again. It is not a SPEC
amendment or implementation. The ordering is undocumented and the cause is unknown, so do
not call it a fix. Unknown still refuses admission.

Next evidence: run the rule on cookie-free stores first. Neither API's "none" answer has been
measured under it, and a disagreement would refuse healthy stores. Android's hasCookies has
the same unmeasured new-process question.

Still unmeasured: physical device, other iOS versions, empty and never-denied stores under
the rule, reboot, service workers, redirects, real Portal teardown. T28 stays
incomplete at 6/44 native tasks. SPEC, protocol and production packages are unchanged.

Retained: seven reports, 497 receipt rows, 524 verifier checks, 64 host tests. Three earlier
collections stay in ignored local-results/preliminary; the report says why they are not
evidence. Only the dedicated simulator ran: shut down, 13 baseline states match, fixture
closed, no crash reports, no intentional crash or first-call enumeration. Note that killing
a backgrounded fixture needs the Python pid; pkill on the pattern left it running once.

## 2026-11-03 checkpoint — cookie research and admission baseline Git publication

The maintainer requested a progress summary and commit/push checkpoint before
continuing later. The working branch is master; at publication start HEAD,
origin/master and live remote master were all 921d42c. The publication groups are:

- 260f84e — paired cookie-suppression source/tests and retained observations.
- 2ba27a6 — native inventory/admission controllers, callback tests and evidence.
- 7223741 — accepted admission baseline, remaining contract proposals and reports.
- This final progress/study commit — HANDOFF plus Korean lessons 37/38 and index.

Current progress and restart point:

| Area | State |
| --- | --- |
| Browser v0.1 / T01–T21 | Complete |
| Native T22–T27 | Complete; 6 of 44 follow-up tasks |
| Cookie suppression | 200 samples / 400 HTTPS receipts; iOS existing cookies remain readable/sent after disallow; empty-store controls pass |
| Admission baseline | Accepted direction: refuse present/unknown cookies, retire same-app shared Portals, preserve data, no automatic deletion/import |
| Bounded admission evidence | 48 samples / 76 HTTPS receipts, 644 checks, nine distinct controlled native callback scenarios |
| Next evidence | iOS partitioned backend coverage and real writer/owner exclusion; continue from docs/native-cookie-admission-verification.md |
| Still gated | Full C01–C12, remaining ADR 0026/0027, T29/T31, recovery/durability, final SPEC amendments and production SDK integration |

This publication does not mark T28 complete or accept the rest of ADR 0027.
It does not release a package/tag, change protocol 0.1 or resume device work.
The earlier iOS suppression failure remains explicit. Session-owned devices and
servers were stopped after the experiment; routine publication validation uses
retained reports and host tests only. Intentional crash controls remain stopped.

Fresh publication checks pass: pnpm run check (1134 TS tests/40 files, nine Python
tests, both typechecks, Biome 302 files and both browser builds), the suppression
suite's 21 tests and the admission suite's 14 tests. Retained verifiers validate
source/artifact integrity: 3060 suppression checks with the same 112 expected iOS
contract violations, and 644 admission checks. The known Vite warning remains.

All 675 local study references across 39 pages resolve; prior scripts/ids, all 44
task ids and instruction symlinks are preserved. Publication candidates exclude
build outputs, private keys, local user paths, owned/protected device ids, local
logs and machine settings. SPEC, production packages and dependencies are unchanged.
After committing this record, push the four-commit series and confirm live remote
master equals HEAD with a clean working tree; then stop this publication-only task.

## 2026-11-03 checkpoint — bounded native admission verification complete

The maintainer requested the next verification step after baseline acceptance.
Bounded follow-up is isolated in experiments/native-cookie-admission-probe:
native whole-store presence for empty/ordinary/HttpOnly/off-path/unrelated-host/
Partitioned-header cases, same-partition reopening/data preservation, and nine
controlled native callback traces for concurrency/cancellation/retry/retirement.
Four final runs retain 48 inventory/admission samples, 76 HTTPS receipts and
36 native callback traces (nine distinct scenarios). Empty-store candidates load;
observed cookie-bearing cases refuse with zero candidate-resource deliveries.
Cookies, localStorage/IndexedDB and exact partition identities survive refusal
and within-process reopening; the separate public host cookie/policy survives.
Java/Swift callbacks test queuing, unknown/present refusal, B independence,
cancellation, duplicate completion, retry, owner replacement, cleanup failure
and reentrancy. They are controlled injections, not exhaustive OS/network races.

Tests preceded helpers; host suite now passes 14 tests. Four reports pass 644
checks plus complete source/installed-artifact integrity. Android builds/lints
with zero errors and 31 recorded warnings; iOS build/signature checks pass.
Observed versions remain API 37 / WebView 145.0.7632.218 / AndroidX 1.14.0 and
iOS 26.4.1 / Xcode 26.4.1 / SDK 26.4. Android exposes the candidate cookie's
partitioned attribute; iOS exposes the cookie but no partition attribute. Do
not claim full iOS partitioned storage/inventory coverage. Unknown coverage
still prohibits production admission under the accepted policy.

This continues the requested cookie verification, not a production native SDK or
an implementation of the remaining wire/lifecycle contracts. Native callback
injection is distinct from a measured WebView/network race; a server Partitioned
attribute alone is not proof of partitioned storage support. Preserve those limits.
Historical suppression-probe hashes are pinned locally before work. Only the
prior session-owned devices were resumed, and both are stopped again with all
13 baseline simulator states restored. Owned reverse/HTTPS fixture are closed;
global ADB and unrelated AVDs are preserved. No cookie deletion/import, data wipe,
cold store enumeration or intentional crash ran. Local test trust is scoped to
the probe APK and owned simulator; no host-machine trust/TLS bypass was used.

Read docs/native-cookie-admission-verification.md and new Korean lesson 38.
The next evidence gaps are iOS partitioned backend coverage and actual writer/
owner exclusion; remaining C01–C12/T29/T31/T38/T39 gates still apply. T28 remains
incomplete at 6/44 native tasks. SPEC, protocol, runtime packages and historical
measurements are unchanged. No commit/push or package/tag publication requested.
Final pnpm run check passes with Node 22.19.0 / pnpm 11.1.3: 1134 TS tests/40
files, nine existing Python tests, both typechecks, Biome 302 files and both builds;
the known Vite warning remains. New host/native-language tests separately pass
14 cases. All four final reports pass 644 checks and native source/artifact
integrity; 24 historical suppression files remain byte-for-byte unchanged.
All 675 local links across 39 study pages resolve; prior scripts/ids, 44 task ids
and instruction symlinks are preserved. Four new JSON reports exclude private
paths, keys and device ids. Browser-reviewed lesson 38's cookie comparison and
callback explanation; temporary tab/server closed. Final git diff --check passes.

## 2026-11-03 checkpoint — admission baseline accepted as the design direction

The maintainer explicitly answered "그렇게 하자" to the concrete baseline approval
question. Record acceptance on both OSes: browser cookies present or an unverified
absence check block new admission and retire existing Portals sharing that app's
partition; preserve data and exclude automatic cookie deletion/import. Other apps
and the host remain independent. Do not ask for this same baseline approval again.

ADR 0027 now separates an accepted admission section from its remaining proposed
HTTP/cookie contract. The admission document, linked contracts/evidence plan/report,
roadmap and Korean guide distinguish direction acceptance from implementation.
Cookie-only host recovery, migration/durability, final normative amendments and
production implementation remain separately gated. T28 is not complete; 6/44 native
tasks remain complete and the retained iOS cookie failure is unchanged.

This turn records the decision only. No SPEC, protocol, runtime/native code,
measurements, device state or stored data changed. No new device/crash execution,
commit/push or package/tag publication is requested.

pnpm run check passes: 1134 TS tests/40 files, nine Python tests, both typechecks,
Biome 294 files and both builds; the known Vite warning remains. All 662 study
links and 65 reviewed Markdown targets resolve; previous scripts/ids, 44 task ids
and instruction symlinks are preserved. Status review confirms only the baseline
is accepted and remaining recovery/contracts stay gated. git diff --check passes.

## 2026-11-03 checkpoint — admission and data-preserving recovery policy reviewed

The maintainer requested progressing the next review proposal. Added
docs/native-cookie-store-admission.md with a concrete common admission baseline:
only the WebView engine cookie store must be empty, not localStorage/IndexedDB,
storage.* or the separate native HTTP jar. Cookie presence or an unknown result
refuses admission on both OSes, preserving all data and stable registrations.
Serialize the complete native inventory/policy check with app ownership, reject
stale callbacks, and retire the affected app's Portals on a failed shared gate
while preserving B/host. Existing grants and accepted remote effects remain separate.

Recommended initial scope has no automatic deletion or browser-to-native cookie
import. A separately approved host-only cookie recovery is described for review:
exclude writers, retain recovery intent before deletion, delete only this owned
partition's engine cookies, recheck emptiness and keep interrupted/partial recovery
blocked. It is not a guest capability, resetSession operation, full website reset,
implemented migration or T48 durability guarantee. API inventory coverage,
partitioned-cookie handling and races need paired tests before support claims.

Reviewed primary API docs and WebKit's fixed partitioned-cookie deletion issue;
do not infer the measured iOS version is affected or fixed. This concerns SPEC §8
stability and §9 authority/credentials/lifetime. The subpolicy remains PROPOSED
pending explicit maintainer approval, independently of the remaining ADR 0026/0027
and T28 gates. No normative amendment or production implementation is requested
or performed in this review. T28 stays incomplete at 6/44 native tasks.

Linked the proposal from ADR 0027, origin/cookie contracts, the evidence plan/report
and native roadmap. Expanded Korean lesson 37 and the current guide, preserving
prior lessons. No native source/results, device state or data were changed; the
earlier iOS contract failure remains RED. No new device/crash experiment,
commit/push or package/tag publication was requested.

Final pnpm run check passes with Node 22.19.0 / pnpm 11.1.3: 1134 TS tests/40
files, nine Python tests, both typechecks, Biome 294 files and both builds; the
known Vite warning remains. Retained native evidence still validates its 3060
checks/source/artifact/bindings and records the same 112 iOS contract violations.
All 662 local references across 38 study pages and 65 reviewed Markdown targets
resolve; prior scripts/ids, all 44 task ids and instruction symlinks are preserved.
Browser-reviewed the data-preservation table, admission flow and recovery table;
the temporary tab/server are closed. Fixed the flow's semantic HTML lint issue;
final git diff --check passes. SPEC, runtime packages, native probes and dependencies
remain unchanged. This validation does not implement or prove the proposed gate.

## 2026-11-03 checkpoint — bounded cookie suppression measured; retained iOS cookies block the contract

The maintainer explicitly answered "새 쿠키 검사만 재개" after reviewing the
C09/C10 plan. Completed only that bounded experiment under
experiments/native-cookie-suppression-probe. Four final runs retain 200 native/
document samples and 400 controlled HTTPS receipt rows. Both Android and iOS
leave H/U controls and the other app working when only A is disabled.

Android API 37 / WebView 145.0.7632.218 passes the bounded suppression cases.
iOS 26.4.1 disallow blocks new writes but retains existing HTTPS cookie reads
through ordinary/prototype/frame access and sends the cookies to the server.
Each iOS run has eight such samples and 56 failed conditions. Do not relabel
this as success: 765 checks per report plus source/artifact/native-binding checks
validate evidence; the strict iOS contract remains RED. Fresh A/B partitions
disabled before first load pass on both. Seeded stores were not deleted/migrated.

Read docs/native-cookie-suppression-verification.md for evidence, exact support
limits and the proposed admission rule: use owned empty browser stores, install
policy before guest execution, and refuse a cookie-bearing retained store pending
an explicit migration decision. This is not approved/implemented. No SDK broker,
SPEC, protocol, instruction invariant or old experiment changed. Full C09 network
coverage, migration admission, C01–C08/C11/C12 and final T28 approval remain open;
native task completion stays 6/44. This concerns SPEC §9.

Actual tools differ from prior probes: Xcode 26.4.1 / SDK 26.4 / iOS 26.4.1;
JBR 21.0.10; retained Gradle 9.6.1 / AGP 9.3.1 / AndroidX 1.14.0. Both native
builds/signature checks pass. Android lint has zero errors and 29 recorded fixture/
toolchain warnings. The new test suite has 21 passing tests, including evidence
mutations and regressions for partial report writes and stale fixture case lists.
Preliminary/incomplete runs stay ignored locally; final reports use distinct tags.

Created only a dedicated simulator and AVD from installed runtimes/images. The
local HTTPS CA is trusted only by the test APK and that dedicated simulator;
no host-machine trust/TLS bypass or real credentials were used. Both probe apps,
owned devices, owned adb reverse mapping and HTTPS fixture are stopped/closed.
All 12 pre-existing simulator states and existing AVDs are preserved. Global ADB
was retained because its pre-task ownership was not established. Device configs,
private keys, raw diagnostics and ownership records remain ignored locally.
No intentional crash or store-enumeration control ran; do not resume them.

Updated the contract/ADR/roadmap, evidence plan and Korean lesson 37/current guide.
Final pnpm run check passes with Node 22.19.0 / pnpm 11.1.3: 1134 TS tests/40 files,
nine existing Python tests, both typechecks, Biome 294 files and both browser builds;
the existing Vite warning remains. The new probe suite separately passes 21 tests.
All four retained reports pass source/artifact/binding validation with 3060 total
behavior checks while retaining 112 expected iOS contract violations. All 659 local
references across 38 study pages resolve; prior scripts/ids, 44 task ids and
instruction symlinks remain intact. Four retained JSON files exclude local user
paths, private keys and owned/protected device ids. Browser-reviewed the final
results table; temporary documentation tab/server are closed. Historical native
sources, production packages, SPEC and dependencies remain unchanged. Final
git diff --check passes. No commit/push or release requested.

## 2026-11-03 checkpoint — cookie/HTTP review and paired evidence procedures

Subsequent explicit answer: "새 쿠키 검사만 재개" authorizes the bounded C09/C10
Android/iOS device experiment described in the evidence plan. Work is starting in
experiments/native-cookie-suppression-probe; historical probes remain unchanged.
Inspect actual current device/tool state, use dedicated owned fixtures, and keep
the intentional crash controls stopped. The review-only notes below describe the
completed earlier part of this continuation, not a renewed device restriction.

The maintainer requested proceeding with the next task after the status review.
Started from clean master 921d42c, equal to the live remote. Reviewed SPEC,
ADR 0027 and the proposed contract; added
docs/native-cookie-http-conformance-plan.md with C01–C12 procedures, expected
observations, independent HTTPS-server evidence and explicit pending decisions.
Current API references still require measured policy-locality proof; API existence
does not establish host/control isolation. The review concerns SPEC §9.

The first bounded future device experiment is C09/C10 cookie-suppression feasibility
using A1/A2, B and owned public host/control fixtures. C08 separately covers reset
before headers, after header commit with a held body, and after Promise settlement.
Preserve first settlement and test actual native writes. Exact cookie profile,
public schemas, error projections, durability and resource gates remain open.
All new C01–C12 observations are pending; T28 stays incomplete at 6/44 native
tasks. Experimental feasibility and later production integration are distinct;
no acceptance criterion or T29/T31 dependency was silently waived.

Updated the contract/ADR/roadmap links and expanded study lesson 37 plus the guide's
current section. Earlier lessons and native evidence remain intact. SPEC,
CLAUDE.md, production packages, dependencies and protocol 0.1 are unchanged.
No simulator, emulator, native app or crash control ran. The prior explicit
device/crash stop remains; the bounded execution plan is ready for an explicit
device-work resume, without rerunning intentional crash controls. No commit/push
or package/tag publication is requested for this continuation.

Validation passes with Node 22.19.0 / pnpm 11.1.3: pnpm run check reports 1134
TypeScript tests / 40 files, nine Python tests, both typechecks, Biome 289 files
and both browser builds. The previously recorded Vite warning remains. All 656
local references across 38 study pages resolve; prior ids/scripts, all 44 task
ids and instruction symlinks are preserved. Browser inspection confirms the new
control table and reset timing explanation render and the section links work;
the temporary tab/server are closed. Final diff review and git diff --check pass.
These are documentation/repository checks, not new native cookie evidence.

## 2026-11-03 checkpoint — publication verified and development environment cleaned

The maintainer requested commit/push and development-environment cleanup. The
four T28 commits through 05c6974 were already pushed; HEAD, origin/master and the
live remote master matched, with a clean working tree, before this cleanup note.
The earlier source/contract/study publication is preserved without reaccepting
ADR 0026/0027 or marking T28 complete.

Checked repository-owned process/listener state and device ownership. No Vite,
Python preview/fixture server, Gradle daemon, native probe or probe runner remained.
The dedicated iOS simulator is Shutdown; no simulator is Booted and no Android
device was attached. No simulator, emulator or native app was launched for cleanup.
The task-started ADB server had no devices or connected clients; stopped it and
verified port 5037 closed without invoking adb again. Computer-use temporary tabs
were already absent; reset this task's computer-use session and verified its two
helper processes exited. Existing user apps/tabs and unrelated services were kept.

No build cache, dependency, raw crash file, owned device configuration or retained
evidence was deleted. No global setting or system crash reporter was changed.
Native crash experiments remain stopped and must not be resumed automatically.
This note is the only repository change for cleanup. Runtime/source validation
from the preceding publication remains applicable; git diff --check passes.
Push this cleanup record and verify remote equality/clean tree as the final step.
Then stop; next work remains review of the proposed common cookie/HTTP contract
and C01–C12 evidence gates, subject to the existing scope and device restrictions.

## 2026-11-03 checkpoint — T28 research and cookie-design Git publication

The maintainer requested committing and pushing the current work before
continuing later. Retained Android source/evidence and shared criteria/vectors
are committed as e40b95c; iOS source/evidence is 44b5550. Origin and async-cookie
contract proposals/reports are committed as b7c25fc. This following progress/study
checkpoint records the publication grouping and the preserved pending decisions.
Verify live origin/master equals HEAD and the working tree is clean after push.

Publication does not accept ADR 0026/0027 or complete T28. The maintainer requires
matching Android/iOS cookie behavior and prefers a common async SDK, with developer
compatibility questions retained. Resume at final cookie/HTTP contract review and
C01–C12 planning/evidence; T29–T31 and implementation gates remain. No protocol,
SPEC, instruction invariant or production runtime changed. No further native
implementation, package/tag release or new task is requested in this checkpoint.

Fresh publication validation passes pnpm run check with Node 22.19.0 / pnpm 11.1.3:
1134 TypeScript tests in 40 files, nine Python tests, both typechecks, Biome 289
files and both browser builds; the known Vite warning remains. Android retained
verification passes four runs/44 samples and seven mutation tests. iOS retained
verification passes 1344 assertions/52 samples/92 identity rows/six startup controls
and six verifier tests. These commands read existing evidence and never boot a
device or rerun a crash control. Existing stopped-device/crash restrictions remain.

All 652 local references across 38 study pages resolve, and prior scripts, unique
ids, all 44 task ids and instruction symlinks are preserved. Sixteen retained JSON
files parse and exclude local paths/owned or protected device ids. Publication
excludes ignored builds, raw crash files, ownership records, local logs and
machine settings. Final git diff --check passes. Finish the requested Git push
and remote/clean-tree verification, then stop this publication-only task.

## 2026-11-03 checkpoint — common cookie/HTTP behavior required; design proposed

The maintainer explicitly requested designing cookie support with matching
Android/iOS behavior. The previous raw iOS-cookie limitation is evidence, not an
acceptable final product difference. Do not ask again whether parity is required.
After comparing an async SDK with transparent document.cookie/fetch support, the
maintainer prefers option 1 and asked about developer friction and async validity.
Explained that centralized request adapters can reduce migration where supported;
automatic native session handling avoids manual login-cookie reads; arbitrary
browser libraries do not become compatible automatically.

Proposed ADR 0027 and docs/native-cookie-http-contract.md now define one native
jar per app, automatic HTTP Cookie/Set-Cookie flow, protected HttpOnly handling,
scoped/approved HTTPS services, deterministic include/omit, returned 3xx without
following, explicit native first-party service context (not browser CORS/SameSite
CSRF behavior), serialized response-header commits and app-wide session reset
that fences actual stale writes. Browser cookies must be equally unavailable;
per-profile/store suppression and managed network paths require new proof.
A JS cookie wrapper is diagnostic only; allowed executable resources join app
trust. Protected-cookie promises exclude server-controlled body reflection.

All details are PROPOSED. User preference for option 1 is not final approval of
the native HTTP context, API schemas, resource limits or compatibility costs.
No new capabilities/manifest scopes, runtime, SPEC/protocol changes or native
measurements are implemented. T28 has a cookie-parity substep under the same id;
T29/T31/T35 and native integration/durability/resource gates are updated. The
current Host maps provider throws to fixed -32603; proposed -32007 native-error
outcomes need explicit later dispatch/provider-result work, not throwing today.

Independent read-only review corrected HttpOnly/body-reflection wording, executable
resource trust, target-free reset authorization, mandatory eligible 3xx cookie
commit and the received-response-header queue order. Original T23–T28 source and
measurements are preserved; they do not test this new broker or cookie policy.
Study lesson 37 explains API migration, async use, automatic login, trust and
limits; index, roadmap and old T28 proposal link to it. No device, native app or
crash control was launched. Do not resume stopped crash controls. All work remains
local/uncommitted; no commit/push or publication requested.

Final design validation: Node 22.19.0 / pnpm 11.1.3 pnpm run check passes 1134 TS
in 40 files, nine Python tests, both typechecks, Biome 289 files and both builds;
the known Vite warning remains. All 652 local references across 38 study pages
resolve; prior scripts, unique ids, all 44 task ids and instruction symlinks are
preserved. Independent final read-only review found no remaining material
contradiction. The new guide's migration table, async login example and ownership
diagram were inspected in the browser; temporary tab/server closed. SPEC,
CLAUDE.md, runtime packages, dependencies and historical native probes remain
unchanged; git diff --check passes. No new cookie conformance or device execution
is implied by these documentation checks.

## 2026-11-03 checkpoint — T28 evidence complete; crash experiments stopped

Supplementary research is complete in experiments/native-origin-contract-probe/.
Android retains four runs/44 raw snapshots, shared 23 identity vectors, JVM
admission tests and seven verifier mutation tests. iOS retains four runs/52
snapshots/92 identity rows, six no-guest startup controls, 37 Swift checks,
1,344 independent raw assertions and six verifier tests. Main and independent
reviewer reran retained-evidence checks successfully. Both native builds and
artifact/source/asset/signature checks pass; Android lint has 28 recorded warnings.

The measured Android .invalid origin/Profile and iOS moonpool/identified-store
models isolate local storage and shared remote first-party cookies, retaining
same-app data across controlled reload/recreation/process restart. Remote tests
load example.com with public sentinel cookies only; they do not establish server
Cookie-header receipt, cross-origin guest fetch, ITP or real host authentication.
Android unusual ids are JVM/URI cases; iOS 15 valid vectors have actual exact
native origins, with 8 invalid registration cases and 3 authorityless diagnostics.
Native production loader/navigation/transport, wire/close and durability gates
remain unchanged. Existing T23–T27 source/evidence is untouched.

The iOS 26.4.1 / Xcode 27 SDK 27 first-WebKit-call store-enumeration path crashes:
cold async two and explicit MainActor callback two controls retain launch-correlated
EXC_BAD_ACCESS/SIGSEGV stacks. Two empty-nonpersistent-WebView initialization
controls succeed with no guest loads. Full runs use that observed working order;
all guests still use assigned persistent stores. Do not claim an Apple-wide
workaround, crash recovery or internal root cause. Preparatory same-artifact
registration precedes final reopening/persistence evidence; no fresh-install
atomicity or power-loss guarantee is asserted.

The maintainer reported repeated OriginContractProbe unexpected-quit dialogs.
Crash reproduction has ended. Verified no probe app or execution-script process
remains; the owned iOS simulator is Shutdown and owned Android serial absent.
All 25 pre-existing simulator states are preserved. Do not rerun intentional
crash controls without an explicit request. Computer use denied access to
com.apple.UserNotificationCenter, so queued system dialogs could not be dismissed;
the user was told they can close remaining alerts. No global crash setting or
system crash-reporting service was changed. Continue only retained verification
and documentation unless new device work is explicitly requested.

Read docs/native-origin-contract-verification.md, updated ADR 0026/contract and
study lesson 36 for results, exact support limits and O01–O06 coverage. Direction/probe
work was authorized; final normative contract review/approval remains before
SPEC/CLAUDE changes or T28 completion (six of 44 native tasks remain complete).
All work is local/uncommitted; no commit/push or package publication was requested.

Final root check passes: 1134 TS tests/40 files, nine Python tests, both typechecks,
Biome 288 files and both browser builds (the known Vite config warning remains).
After result-only JSON formatting, both native evidence verifiers pass with source
fingerprints unchanged. All 10 Python scripts compile. All 636 local references
across 37 study pages resolve; previous scripts, unique ids, all 44 task ids and
instruction symlinks remain intact. Sixteen retained JSON files parse and contain
no local user paths or owned/protected device identifiers. Browser-reviewed the
new results table and status; temporary documentation tab/server closed. Final
git diff --check passes. No device or crash control ran during final validation.

## 2026-11-03 checkpoint — T28 supplementary probes authorized and started

After reviewing the T28 explanation, the maintainer explicitly requested that
T28 proceed. The proposed direction is authorized for bounded O01–O06 native
probes; do not ask for that same authorization again. Final normative contract
approval follows review of the new evidence. SPEC/CLAUDE.md and production
packages remain unchanged during this research.

New work is isolated under experiments/native-origin-contract-probe/ with
platform-owned android/ and ios/ harnesses. Shared identity-vectors.json supplies
23 public normal/boundary/invalid ids; platform tests precede helper code.
Historical T23–T27 source/results and the pre-existing local T28 documentation
are preserved. Read the platform READMEs for build/test/ownership commands.

The current checkout lacks old ignored device/build ownership files. All listed
iOS simulators were Shutdown and adb initially listed no devices. iOS gets a
new dedicated simulator with the installed iOS26.4 runtime; Android records the
explicit shutdown Pixel_7_Pro AVD before any boot. Other devices are protected.
Actual installed tools differ from prior evidence and must be recorded afresh.
Do not reuse historical source/artifact hashes as new measurements.

## 2026-11-02 checkpoint — T28 origin/loader/bootstrap proposal prepared

The maintainer asked to inspect the latest commit and continue. HEAD f585961
records T27 completion, with a clean tree at session start. Resumed T28 as a
concrete proposal in docs/adr/0026-bind-native-origins-loaders-and-bootstrap.md
and docs/native-origin-contract.md; no normative or production code changed.

The recommended draft uses stable per-app .invalid HTTPS origins on Android,
retains iOS moonpool origins with exact native-id admission, and requires
persistent per-app guest website-data stores separate from host authentication.
The store requirement addresses both parent-domain cookies and shared remote API
cookies, which different local origins alone do not isolate. Proposed Android
per-message ingress is WebMessageListener with actual origin/frame/instance checks;
port possession and guest claims cannot grant authority. Loader path confinement,
local misses, navigation, bootstrap ownership, migration and unsupported cases
are specified with O01–O10 acceptance criteria and exact SPEC amendment locations.

ADR 0026 is PROPOSED, not accepted. T28 remains in progress (six of 44 tasks
complete). Select the concrete direction before bounded supplementary namespace,
profile/store and cookie probes. Review those new measurements and obtain explicit
contract approval before marking T28 complete or changing SPEC/CLAUDE.md. The
existing T23/T24 shared-store evidence does not verify these new store APIs.
T29–T31 and production loaders remain gated. T27/ADR 0025 and ADR 0024 are retained.
No device was resumed, no dependency installed, and no commit/push requested.
Study lesson 36, the guide, roadmap and origin discussion reflect proposal status.

Final verification (handoff 2026-11-03): Node 22.19.0 / pnpm 11.1.3 root
pnpm run check passes 1134 TS tests / 40 files, nine Python tests, typechecks,
Biome (267 files) and both builds; the existing Vite config warning remains.
The new diagram's ARIA lint issue was corrected using a semantic section before
this passing run. All 633 local references across 37 study pages resolve; unique
ids, 44 roadmap task ids, prior scripts and instruction symlinks are preserved.
Independent read-only review clarified remote-script/same-origin-frame app trust
and pinned the distinction between cancelled host-handled external links and
terminal containment violations. Browser review confirmed the lesson, diagram
and guide's proposed status. Temporary tab/server closed. SPEC, CLAUDE.md,
runtime packages, dependencies and historical experiment evidence are unchanged;
git diff --check passes. All T28 work is local and uncommitted.

## Older history

Checkpoints through T27 and the v0.1 working notes are preserved verbatim in
[docs/handoff-archive.md](docs/handoff-archive.md). Pointers elsewhere to a
HANDOFF note dated before the T28 work resolve there.

The git remote uses a personal SSH host alias
(`git@github.com-personal:WillowRyu/moonpool.git`), which must exist in
`~/.ssh/config` on a new machine.

## Open decisions (maintainer's call, not made yet)

- **Receiver behavior on id reuse (§4.1):** the spec says senders MUST NOT
  reuse ids (positive, monotonically increasing) but never says what a
  receiver replies when they do. Needs a spec decision (likely `-32600`, but
  do not resolve by editing SPEC.md without approval). Enforcement would be
  host-side per-connection state, not the pure guard.

- **ADR candidate:** Moonpool targets BOTH full-screen mini apps and web
  components embedded inside native screens; the protocol stays
  embedding-agnostic (screen size/placement is a host-UI concern). Arbitrary
  remote URLs are explicitly out: no identity → conflicts with SPEC §8/§9.
- ~~Retry after `-32004`, and a second `portal.initialize`~~ — **resolved
  2026-08-28** in SPEC §5 and the new §5.1 (`225fd21`). Both are allowed.
- **Language question (asked 2026-08-19):** could the kernel be Rust or Go?
  Discussed in session: the client must be JS — it runs inside the mini
  app's web view (Rust→WASM still needs a JS shim for postMessage and the
  bridge is I/O-bound, not compute-bound, so it buys nothing). Rust becomes
  a real option for a SHARED native core after the protocol stabilizes
  (post-v0, per the CLAUDE.md ordering); Go does not fit mobile embedding.
  Possible ADR when native cores start.
