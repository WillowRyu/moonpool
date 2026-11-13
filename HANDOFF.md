# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-11-13. The maintainer switched to agent-led implementation
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
> Native HTTP transport: three iOS conflicts; rules accepted as a design direction; read docs/native-http-transport-verification.md.
> Principle: follow OS behavior unless what a mini app sees differs per platform. Do not ask again.
> Android global handlers reach HttpURLConnection with no per-request opt-out; read docs/native-http-global-handlers-verification.md.
> Android broker client accepted: OkHttp pinned to 5.5.1, following ProxySelector, reviewed at T56; see ADR 0027. Do not ask again.
> Broker review findings fixed and collected again on 2026-11-05: 63 cases pass on both platforms, four collections.
> Read docs/native-http-broker-verification.md and Korean lessons 45-48. Guest-visible results are identical across platforms.
> A comma in a cookie value can drop HttpOnly on both platforms: accepted on 2026-11-05 and stated in the contract. Do not ask again.
> iOS commits a Basic challenge's first response from failureResponse: accepted on 2026-11-05 in ADR 0027. Do not ask again.
> The second attempt, the Authorization replay and a body from that attempt remain, and the contract states them.
> The jar parity item is closed: iOS now keeps the first response's cookie, as Android does, in all 63 cases.
> Broker work is merged into master by fast-forward and pushed, through f964f76; the branch stays at that commit.
> Both devices stopped; T28 stays at 6/44 with C04 and C09-C12 conformance open. Test keys are in the Trash for the maintainer.
> C04 profile `c04-1` frozen on 2026-11-11: docs/native-cookie-c04-profile.md.
> Initial PSL: official published version 2026-11-10_11-23-57_UTC, commit 3db7776.
> D1 accepted as A (ASCII-only lines).
> Parser comparison (docs/native-cookie-parser-comparison.md): Android and iOS differ on 13 of 61; of 12 common shapes only the 400-day cap.
> X accepted on 2026-11-09: keep the shared cookie parser (ADR 0027).
> D2-A accepted on 2026-11-11: both SDKs ship the same pinned Public Suffix List revision. New revisions ship through SDK releases.
> The exact-IP `Domain` rule was accepted as host-only on 2026-11-11.
> D5 expiry processing and the 400-day lifetime cap were accepted on 2026-11-11.
> D3-B accepted on 2026-11-11: cookie identity includes name, canonical domain, path and host-only.
> D4-A accepted on 2026-11-11: use the percent-encoded request path for matching and defaults.
> D6 accepted on 2026-11-11: check both cookie prefixes case-insensitively.
> D8 accepted on 2026-11-11: sort matching cookies by path length and original creation order.
> D9 accepted on 2026-11-11: ignore unsupported attributes, including Partitioned and Priority, and keep eligible cookies.
> C04 review fixes verified: 102 cases / 236 assertions, with 50 cases failing on the retained broker.
> C04 Java reference parser (JDK only) passes 102/102 on 2026-11-13; Swift port and broker ports remain.
> OPEN: the retained iOS split treats Unicode spaces as `\s`; the reference uses ASCII. Maintainer's decision.
> Keep the profile review to one decision at a time.
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

## 2026-11-13 checkpoint — C04 reference parser passes the corpus

The maintainer answered "네, 시작" to building the Java reference parser on the
desktop, without touching either broker or any device. The parser is in
`experiments/native-cookie-profile/reference/java/src` and uses only the JDK. It takes
the request host, percent-encoded path and time in epoch seconds, and
implements D1-D9 with the pinned PSL. `check.py` now requires
`--subject reference` or `--subject baseline`.
[Reference parser and result](experiments/native-cookie-profile/README.md#reference-parser)

**All 102 cases and 236 assertions passed in two identical runs.** A self-test
runs first and passed 552 checks. It covers RFC 3492 samples, all 493 Unicode PSL
labels against `java.net.IDN`, rule counts, RFC 6265 dates, the calendar against
`java.time`, and the split against the brokers' regex with 200,000 seeded inputs.
Eleven mutated copies, each breaking one rule, all failed the expected cases.
The baseline still gives 52/102. No device, network or broker file was touched.

Found while writing it, both portability points for the Swift port:

- `java.net.IDN` in default mode rejects one pinned label, Balinese `ᬩᬮᬶ`,
  because its IDNA2003 tables stop at Unicode 3.2. With `ALLOW_UNASSIGNED` all
  493 labels agree with the reference's own RFC 3492 encoder. iOS has no IDNA API,
  so both SDKs should carry this encoder.
- **OPEN, the maintainer's decision.** Both brokers split folded fields with
  `,\s*(?=[^;,=\s]+=)`, but `NSRegularExpression` treats U+00A0, U+2003 and U+3000
  as `\s`. On macOS Foundation, Swift 6.3.1, the retained iOS split turns
  `a=1,<U+00A0>b=2` into a storable `b=2`. Java keeps `<U+00A0>b=2`, which D1
  rejects. The reference uses Java's ASCII whitespace. The question is whether to
  state that in contract §4 and ADR 0027 rule 1. This affects whether a cookie is
  stored, so it concerns SPEC §9. It was not measured on a device, and whether
  `URLSession` delivers U+00A0 is unknown.

**Next step.** Port the reference to Swift as a Foundation-only file, then run the
same corpus and self-test checks with `swiftc` on macOS, without the simulator.
Porting either broker changes the fingerprinted sources of the four retained
63-case collections, so that waits for the paired device step and its explicit
resume. C04 and C09-C12 stay open, and T28 stays at 6/44.

Root `pnpm run check` passed 1,134 TypeScript tests in 40 files, nine Python
tests, typechecks, lint and both browser builds. The experiment's three Python
tests pass, and all 145 local links in the study index resolve.

## 2026-11-11 checkpoint — C04 test review fixes

E01a and E08a/b seed a cookie at `T0` and replace it at `T0+30s`. E01a checks
selection at `T0+89s` and removal at `T0+90s`. Both E08 variants check the
400-day cap from replacement receipt. P06b sends two fields in one response
and expects only the line with an ASCII value and attributes to survive.
The verifier rejects empty and receive-only cases, and a receive-only CLI
fixture exits with status 2. The regression test passed after reproducing the
old false pass. The Astra High follow-up review closed all three findings.

The updated corpus covers 102 cases and 236 assertions. Two JVM runs using
the pinned PSL digest produced identical output (52 cases passed, 50 failed,
139 assertions passed, 97 failed). C04 stays open for the reference parser
and paired native evidence. [Updated baseline](experiments/native-cookie-profile/README.md#baseline-result)

Root `pnpm run check` passed 1,134 TypeScript tests, nine Python tests,
typechecks, lint and both browser builds. All 157 local study index links resolve.

## 2026-11-11 checkpoint — C04 vectors and failing tests

The `c04-1` corpus turns the 70 profile rows into 101 isolated cases and
231 assertions, with the frozen PSL commit, SHA-256 and UTC clock inputs.
The desktop JVM adapter exercises the retained Android research broker's
cookie operations. Two runs gave identical results (52 cases passed,
49 failed, with 136 assertions passed and 95 failed). E01 passes at 59 seconds
and shows the stale cookie in the header and script read at 60 seconds.
A05 and X09b expose the encoded-path and prefix gaps that affect cookie
scope and integrity under SPEC §9.
[Corpus and rerun instructions](experiments/native-cookie-profile/README.md)

The P01, P11, D05, D06a and O01 controls pass individually. A wrong PSL digest
and unknown case ID stop as setup errors. All 42 retained OS comparison harness
tests and root `pnpm run check` passed (1,134 TypeScript tests, nine Python
tests, typechecks, lint and both browser builds).

**Next step.** Implement the reference parser using the verified PSL and
injected clock and make the same corpus pass. Then run the corpus against both
probe brokers. C04 and the remaining T28 evidence gates stay open. Paired device
collection needs its separate explicit resume.

## 2026-11-11 checkpoint — C04 profile frozen

Profile `c04-1` fixes the D1–D9 rules and the initial Public Suffix List data.
The official download served on 2026-11-11 (KST) identifies version
`2026-11-10_11-23-57_UTC` and commit
`3db7776283b0874634fea8b01168f785360d64f2`. The pinned upstream source and
the official download have identical ordered rules in each section
(6,951 ICANN and 3,463 PRIVATE). The profile records the immutable source,
SHA-256 and a retrieval command for the common SDK input.
[C04 snapshot](docs/native-cookie-c04-profile.md#public-suffix-list-snapshot)

The expected cases include an ICANN suffix, a PRIVATE hosting suffix,
wildcard and exception rules, an A-label lookup, the implicit wildcard,
and a PRIVATE entry added in the pinned revision. These rules govern
cookie scope under SPEC §9. The broader native cookie and HTTP contract
still needs final approval.

**Next step.** In `experiments/native-cookie-profile/`, turn the expected
cases into a `c04-1` JSON corpus labeled with the PSL revision and SHA-256.
Use an injected clock and isolated jars to assert exact identities,
expiry, ordered headers and script-visible results. Run the tests and
record the expected failures before writing the reference parser. The
retained OS comparison uses its historical `c04-draft-1` corpus.
[Expected vectors](docs/native-cookie-c04-profile.md#4-expected-vectors-for-c04-1)

C04 and C09–C12 remain open. Paired device collection needs the separate
explicit resume recorded in the conformance plan. T28 remains at 6/44.

Verification passed for the documented PSL retrieval and checksum command,
the section counts and rule examples, and all 156 local links in the study
index. Root `pnpm run check` passed 1,134 TypeScript tests in 40 files,
nine Python tests, both typechecks, lint and both browser builds.

## 2026-11-11 checkpoint — C04 decisions through D9

The maintainer chose D2-A after confirming that Android and iOS will bundle the same pinned Public Suffix List revision,
including ICANN and PRIVATE rules. Both SDKs adopt a new revision through SDK releases. ADR 0027 and the C04 draft record the
decision about cookie scope under SPEC §9.

The maintainer also accepted storing an exact-IP `Domain` as host-only. An IP request host accepts a nonempty `Domain` only
when it matches that IP exactly. This gives the cookie the same scope and stored flag as a cookie issued without `Domain`.
The C04 draft records the browser sources and the D06 expectation.

The maintainer set the D5 lifetime cap at 400 days after receipt. E08 covers both
`Max-Age` and `Expires` when the requested expiry exceeds the cap. T53 uses
measurements to set cookie count and size limits and eviction rules.

The maintainer chose D3-B. Each mini app's jar keys cookies by `(name, canonical domain, path, host-only)`. Approved subdomains
issuing the same domain key replace that domain entry and preserve the parent host-only entry. Both entries can match the parent
request. The C04 draft vectors cover replacement, expiry and duplicate read results. T29 defines the public deletion selector.

The maintainer chose D4-A. Compare `Path` with the percent-encoded path sent in the request and derive the default from that same
path. A literal `/` is the path separator. C04 cases A03, A05 and A06 cover default and explicit paths with `%2F`.

The maintainer accepted the remaining D5 expiry rules. Prefer the last valid `Max-Age`, then fall back to the last valid `Expires`
or a session cookie. A valid server response expiring at or before receipt deletes the matching D3-B entry, whether script-readable
or `HttpOnly`. Remove due entries before forming a request header or `cookies.get` result. C04 records invalid, repeated and
conflicting attributes.

The maintainer accepted D6. Check `__Secure-` and `__Host-` with ASCII case-insensitive matching. Both require `Secure` on an HTTPS
response. `__Host-` additionally requires explicit `Path=/` and omission of `Domain`. Preserve the full name for D3-B identity.
Apply prefix validation before storage and expiry commits. The proposed `cookies.set` rejects both prefixes.

The maintainer accepted D8. Order matching cookies by longer `Path` first and earlier creation order for equal lengths.
Keep creation order on same-identity replacement. Deletion followed by reissue gets a new order. Serialize each matching
cookie as `name=value`, with `; ` between pairs, including duplicate names. C04 cases I02 and O01–O03 record the expected order.

The maintainer accepted D9. Ignore unsupported `Set-Cookie` attributes, including `Partitioned` and `Priority`, and store eligible
cookies in the requesting mini app's jar. Variants with the same D3-B identity address one entry for replacement and expiry.
The C04 draft vectors also check that the supported validation rules apply.

This checkpoint handed off the initial Public Suffix List selection and profile
freeze to the checkpoint above.

Root `pnpm run check` passed with 1,134 TypeScript tests, nine Python tests, typechecks, lint and both browser builds.
All 154 local links in the study index resolve.

## 2026-11-09 checkpoint — shared parser kept (X)

The maintainer chose X: "최대한 OS 의 동작을 따르고 싶은데 android 와 ios 의 동작이 다르다고 하면 우리 규칙으로 미니앱을 넣었을때 다르게
동작하면 안될것 같아", accepting the code-maintenance cost. Recorded in ADR 0027 ("Shared parser reaffirmed over OS parsers"), the
contract's accepted amendments, the comparison report and the C04 draft. Do not ask again. Nothing is implemented, and SPEC is unchanged.

Reasons recorded: the 400-day cap differs and is common; OkHttp has no prefix rules; iOS's API cannot express `SameSite=None`; the
Android jar is Moonpool code under any option; under W an iOS update changes behavior before an SDK update can align Android; and
OkHttp 5.5.1's public-suffix list is unchanged since 2024-12-31 while iOS's moves with the OS. Code review fixes are in eefeec3 / a22f971.

The next decision at this checkpoint was C04 D2, explained one decision at a time in easy Korean, as the maintainer asked. Evidence gathered for D2: the public-suffix
list changed 204 times in the last year and 358 times since 2025-01-01, mostly hosting platforms in the PRIVATE section; Chrome refreshes
it by hand a few times a year and Firefox by bot every few days, both shipping it per release; Firefox removed runtime updates in
version 136. So D2-A means a pinned list refreshed per SDK release, about 130 KB, the same model as browsers. D5 (400-day cap) and the
IP-host case under D2 also remain open.

Notes from the discussion, not decisions, and not to be built without a request:
- Same-service login: under isolation a mini app logs in separately even to the host's service. Open platforms instead let the host
  vouch for the user (Toss login over OAuth2, Telegram's signed `initData`, LINE ID tokens, `wx.login`). A host-approved login handoff
  is a future design topic outside the current scope.
- App Store guideline 4.7: 4.7.2 forbids exposing native platform APIs to mini apps without Apple's permission, and 4.7.3 requires
  explicit user consent each time data or permissions go to a mini app. Check the capability and permission model, including
  `profile.get`, against both before native release. Google Play exempts JavaScript in a WebView from its downloaded-code rule.
- Remote delivery (live updates, CDN, signing, developer portal) stays out of scope, as CLAUDE.md and the native plan say. The origin,
  `protocolVersion` handshake and manifest permissions do not depend on where the files come from, so it can be added later without
  breaking stored data. RN CodePush cannot update Moonpool mini apps; the App Center service behind it ended on 2025-03-31.
- Capacitor and Portals share one app-global cookie store with the host, so their web content can ride the host's session; they
  target a company's own web teams. Moonpool's isolation invariant is the difference.

## 2026-11-09 checkpoint — iOS parser compared with OkHttp

The maintainer answered "ios 2단계 진행". The probe feeds the 61 vectors to `HTTPCookie.cookies(withResponseHeaderFields:for:)` and a
fresh in-memory `HTTPCookieStorage` per vector, on the dedicated `Moonpool Cookie Suppression` simulator, iOS 26.4.1, Xcode 26.4.1.
Two runs, identical. Read docs/native-cookie-parser-comparison.md. 32 harness tests pass. An earlier step-2 collection was discarded
before retention because its analysis judged `Max-Age=0` against the runner's clock; iOS results now keep raw data only.

**Android and iOS differ on 13 of 61; of the 12 common server shapes, only the 730-day cookie, because iOS caps at 400 days and
OkHttp does not.** iOS also enforces prefix rules (case-sensitively) and a 4096-octet limit, keeps a public-suffix host's cookie
host-only, and never sends a cookie whose `Path` lacks `/`; OkHttp does none of these. Malformed rows: `Max-Age=abc` deletes on
iOS, `a=é` is stored on iOS only, and a folded field splits on iOS only.

A Sonnet 5.5 code review of the harness, requested by the maintainer ("전부 수정"), found seven harness gaps and a draft inconsistency;
all have regression tests and fixes (42 harness tests). Recomparing the retained results changes no platform difference and adds four
rows where `SameSite=None` or an unknown value is unobservable through iOS's API. D06a (IP host, `Domain=` itself) departs from
RFC 6265 §5.3 and is now listed under D2. No device was started for the fixes.

The choice it left open, X, W or W', was decided on 2026-11-09; see the checkpoint above.

Devices: only the dedicated simulator ran; it was shut down, booted by this task and shut down again, and all 12 simulator states
match the baseline. No emulator or `adb` server was started. No network, certificate or fixture was used.

## 2026-11-06 checkpoint — OkHttp parser compared with the C04 draft

Reviewing D2, the maintainer asked how Capacitor and Ionic Portals handle cookies and whether the broker's own parser is worth
its maintenance. Capacitor delegates parsing and storage to the OS and shares one app-global store with the host; its Android
plugin installs a global `CookieHandler`. Portals' own code was not inspected. Moonpool's isolation invariant rules that model
out, so the choice is X (current shared parser), W (per-app jars that keep each OS's parser) or Y (no cookie support). The
maintainer's stated goals: host and mini app run independently and safely even when they are different services, the same
service also works, and the result is easy to use. Under isolation, a mini app logs in separately even to the host's service;
a host-approved login handoff is a separate design question, not built.

The maintainer answered "1단계부터 진행" and approved downloading okhttp-jvm-5.5.1.jar from Maven Central (SHA-1 checked).
experiments/native-cookie-parser-comparison: 61 vectors, 17 harness tests, results/okhttp-5.5.1-jvm.json. Read
docs/native-cookie-parser-comparison.md. 13 of 61 differ from the draft; of 12 common server shapes only the 730-day cookie
does. OkHttp has no 400-day cap (common), no prefix rules and no `SameSite=None` check (rare, §9). Desktop JVM only; no
device was started.

Step 2 was then deferred ("나중에") and resumed on 2026-11-09; see the checkpoint above.
This work is committed and pushed to origin/master. Asked whether to run step 2, the maintainer answered "나중에", so it was
deferred until a new request. When resumed, build an iOS probe that feeds the vectors to
`HTTPCookie.cookies(withResponseHeaderFields:for:)` and a per-app cookie storage, writes results/ in the same schema, and is
compared with `compare.py`; no WebView and no crash controls. Then present X against W with both platforms' differences.

## 2026-11-06 checkpoint — C04 cookie profile draft

The maintainer chose "C04 초안 시작". The first C04 draft proposed the profile inputs C04 had to freeze
(D1-D9) and 43 draft vectors that follow the recommendations; the conformance plan links it. Nothing is accepted and this
concerns SPEC §9. No test, probe, SPEC, protocol or package changed, and no device was started.

Found while writing it: both broker probes match cookie paths against the percent-decoded request path. D4 proposes the
encoded path; the 63 retained cases use no encoded path, so their results stand.

The maintainer then accepted D1 as A on 2026-11-06, after confirming that raw UTF-8 cookie lines are dropped whole and
encoded values work. The maintainer is reviewing the decisions one at a time, with an easy Korean explanation of each.

The open decisions at this checkpoint were the D2 domain policy, the D5 timing of the 400-day cap, and whether to accept
D3, D4, D6, D8 and D9 as recommended. After approval, vectors and failing tests come before parser code.

## 2026-11-05 checkpoint — first response committed on iOS

The maintainer answered "커밋 후 브로커 적용". The measurement and its documents are committed through 00ab6bb on branch t28-native-http-broker.
The maintainer then answered "네, 커밋" and "푸시도 해둬", so everything below in this checkpoint is committed there too and the branch is pushed to
origin. The maintainer then answered "pr 필요없고 master 에 바로 넣어줘", so it is merged into master by fast-forward and pushed, with the branch kept
at the same commit. "Not pushed" and "not merged" in the checkpoints below describe their own moment. This supersedes the checkpoints below where they give 58 cases,
or call the cookie after the iOS `Basic` resend open.

The iOS research broker now passes a challenge's `failureResponse` to the normal commit path, at most one batch per guest request and under
the same reset fence. Android's code is unchanged. Contract §5 and ADR 0027 record it as an amendment to "commit at header delivery", and now
also state the guest's `Authorization` on both attempts and that a guest's status and body come from the last attempt. Read Korean lesson 48.

**All 63 cases met the oracle on both platforms in all four collections, and guest-visible results, receipts and jar effects are identical
across platforms and runs.** 1790 verifier checks, 474 TLS receipt rows (444 arrivals, 30 hold releases, no hold timeout), 67 host tests,
Android lint 0 errors / 3 warnings. Before the change, the scenarios failed 4 cases on iOS, kept in ignored local-results/red.

Remaining, by design: the server sees two attempts on iOS, the guest's own `Authorization` goes on both, and a guest's status and body come
from the second, which shows only if a server changes its 401 body between attempts. This relies on a behavior the SDK header does not
promise, measured on one OS version and for `Basic` only, so T56-era work must rerun it per supported OS. C04, C09-C12, real Portals and the
bridge remain uncovered; T28 stays at 6/44, and SPEC, protocol and production packages are unchanged.

Devices: the same dedicated AVD and simulator were booted by this task and are stopped. The 25 other simulators and the unrelated AVD were
never started, and all 26 simulator baseline states match. The `adb` server was not running before and is stopped. Fixture closed, no crashes,
nothing added to a trust store. Test keys went to the Trash, so the maintainer still empties it.

## 2026-11-05 checkpoint — comma limit stated, `failureResponse` measured

The maintainer answered "추천대로 진행". The 58-case work is committed through 693dbaf on branch t28-native-http-broker, not pushed or
merged. The maintainer then answered "커밋 후 브로커 적용", so everything below in this checkpoint is committed on that branch too.

**The comma limit is decided.** The pipeline stays, and the contract, ADR 0027 and the C04 procedure now say that the pieces before the
last lose every attribute, including `HttpOnly`. This concerns SPEC §9. SPEC itself is unchanged.

**`failureResponse` carries the first response's `Set-Cookie`.** New experiments/native-http-failure-response-probe, iOS only, kept apart
so the 58-case evidence stays valid. All 8 `Basic` cases in both runs matched what the fixture served on arrival 1, which meets the
criteria written before collection. 22 observations, 38 TLS receipt rows, 64 checks per run, 25 host tests. Read
docs/native-http-failure-response-verification.md and Korean lesson 47.

OPEN, the maintainer's decision, not made: whether to apply it to the research broker. It would refine the accepted "commit at header
delivery" rule on iOS, needs the reset fence at the challenge too, and means collecting all 58 cases again on both platforms. It would not
remove the second attempt, the `Authorization` replay, or a body that comes from the second attempt.

Limits: one OS version, HTTP/1.1 over loopback, `Basic` only, and the SDK header promises nothing about the header fields. Devices: only the
dedicated simulator ran and it is stopped, with all 26 baseline states matching; no emulator or `adb` server was started. Fixture closed, no
crash, nothing added to a trust store. Test keys went to the Trash, so the maintainer still empties it. T28 stays at 6/44.

## 2026-11-05 checkpoint — review findings fixed and collected again

The maintainer answered "수정 진행" to fixing the review findings and collecting again. Read the code review section of
docs/native-http-broker-verification.md and Korean lesson 46 (study/46-native-http-broker-review.html). The maintainer then answered
"추천대로 진행": these changes are committed on branch t28-native-http-broker, not pushed or merged. This supersedes the
checkpoint below where it gives 44 cases, 15 unfixed findings or the broker's behavior.

**All 58 cases met the oracle on both platforms in all four collections, and guest-visible results including response headers,
receipts and jar effects are identical across platforms and runs.** 1658 verifier checks, 426 TLS receipt rows (402 arrivals, 24
hold releases, no hold timeout), 64 host tests, Android lint 0 errors / 3 warnings. Before the fixes, the 14 new scenarios failed
11 cases on Android and 6 on iOS; those reports stay in ignored local-results/red. Inputs that could crash iOS or abort a
collection were guarded before that run, so they were not seen failing. That run also found that an iOS HEAD with a body had not
finished after the 40-second barrier.

OPEN, the maintainer's decisions, not made:

1. **The cookie after the accepted iOS `Basic` 401 resend.** Unchanged: iOS keeps the second response's cookie and Android the
   first. Recommended next is one bounded iOS run reading `URLAuthenticationChallenge.failureResponse`; that was not part of
   this request and was not run.
2. **The comma limit.** `sid=abc, x=y; Path=/; Secure; HttpOnly` leaves `sid=abc` readable by the guest on both platforms. The
   pipeline is accepted and unchanged, and this concerns SPEC §9. The question is whether stating it in the contract is enough.

The method list and the script cookie grammar are choices made for this probe, not contract text. Not recorded: headers a
client adds itself, such as `User-Agent` or a default `Content-Type`. C04, C09-C12, real Portals and the bridge remain uncovered;
T28 stays at 6/44, and SPEC, protocol and production packages are unchanged.

Devices: the same dedicated AVD and simulator were booted by this task and are stopped. The 25 other simulators and the unrelated
AVD were never started, and all 26 simulator baseline states match. The `adb` server was not running before and is stopped.
Fixture closed, no crashes, nothing added to a trust store. New test keys went to the Trash, so the maintainer still empties it.

## 2026-11-05 checkpoint — broker experiment resumed and collected

The maintainer answered "브로커 실험 재개" to the paused work below. Four collections, two per platform, are retained in
experiments/native-http-broker-probe/results. Read docs/native-http-broker-verification.md and Korean lesson 45
(study/45-native-http-broker.html). The maintainer answered "네, 커밋": this work is committed on branch t28-native-http-broker in three commits. It is not
pushed or merged; that was not requested. This supersedes the
checkpoint below only where it describes missing evidence; its scope limits still hold. The ignored preliminary
output it mentions, local-results/preliminary/android-prelim.json, was no longer on disk when this work resumed,
so nothing from the interrupted attempt was reused or verified.

**All 44 cases met the oracle on both platforms in all four collections, and the normalized guest-visible result, server
receipts and jar effects are identical across platforms and runs.** No host cookie and no host credential reached a
broker request in any case, while the same process kept both live for its own client. 1218 verifier checks, 354 TLS
receipt rows (330 arrivals, 24 hold releases), 41 host tests, Android lint 0 errors / 3 warnings.

The one platform difference answers both questions docs/native-http-transport-verification.md left open about the
accepted iOS `Basic` 401 resend, which is not reopened here:

| Measured on a `Basic` 401 | Android, OkHttp 5.5.1 | iOS, `URLSession` |
| --- | --- | --- |
| Attempts the server received | 1 | **2** |
| Responses that reached the broker's response callback | 1 | 1, **the second attempt's** |
| The guest's preset `Authorization` on the extra attempt | — | **Resent unchanged** |
| Cookie left in the jar | `attempt=1` | **`attempt=2`** |
| Host credential at the server | Never | Never |
| Status the guest saw | 401 | 401 |

OPEN, the maintainer's decision, not made: how to handle the cookie difference. The first 401 arrives as a challenge and
never reaches the response callback, and the probe already commits once per request, so a "first response only" rule cannot
help. Recommended next: one bounded iOS run measuring whether `URLAuthenticationChallenge.failureResponse` carries the first
401's `Set-Cookie`. The alternative is to accept and document the difference. It shows when a server's cookie differs between
the two attempts, which the fixture does on purpose. The `Authorization` replay has no measured remedy under the accepted
resend decision, so the contract can state the doubled attempt. The iOS broker session was already ephemeral with cookie
storage, accept policy, cookie sending, cache and credential storage all off, and its task-level challenge handler answered
`.rejectProtectionSpace`, so this is not a configuration mistake.

Devices: the dedicated `Pixel_7_Pro` AVD and the dedicated `Moonpool T28 Origin Contract` simulator were booted by this
task and are stopped again. The 25 other simulators and the unrelated `HereThere_Push_API36` AVD were never started,
and all simulator baseline states match. The `adb` server was not running before this task and is stopped again.
Fixture closed, no crashes, no crash control run, nothing added to a device trust store. Test keys went to the Trash,
so the maintainer still empties it. The probe's app stays installed on the owned emulator and simulator, as in earlier
runs. iOS was built with Xcode 27.0 / SDK 27.0 and ran on 26.4.1, while earlier retained iOS evidence used Xcode 26.4.1 / SDK 26.4;
the paused attempt's toolchain is unknown because nothing from it was retained. C04, C09-C12, real Portals and the bridge
remain uncovered; SPEC, protocol and production packages are unchanged.

A code review of the probe followed at the maintainer's request: 15 findings, read from the code, not run on a device and
none fixed. The most serious: `cookies.set` accepts `;` and CR/LF in name and value, comma splitting can drop `HttpOnly`, iOS
treats a non-string `credentials` as include, Android refuses default-port URLs and a POST without a body. The 44 cases do not
exercise these, so the results hold for those cases only. Changing Broker.java, Probe.swift, build.py, fixture.py or cases.json
changes the source fingerprints, so the four retained collections stop passing `integrity` and must be collected again.
`pnpm run check` passes with 1134 tests; the four results are Biome-formatted, with parsed data unchanged.

## 2026-11-04 checkpoint — broker experiment paused by the maintainer

The maintainer stopped this work mid-run ("다 중단하고 나중에") and asked to shut the devices down. Resume only when asked.
Unfinished experiments/native-http-broker-probe is committed as work in progress at the maintainer's request and holds C01-C03 and C05-C08 subsets: 44 cases, a research broker on OkHttp 5.5.1 and
URLSession, fixture, verifier and 41 passing host tests. No final collection exists. Preliminary output is in its ignored local-results/preliminary.

Preliminary only, not evidence yet: iOS passed all 44 cases once. On a `Basic` 401, iOS resent a guest's preset `Authorization` and the jar kept the
second response's cookie; that iOS report file is gone, because the interrupted rerun deleted it first. Android's first attempt was stopped by the harness at
a false "process exited" while the emulator was busy. The rerun left local-results/preliminary/android-prelim.json, which nobody has read or verified.
To resume: rebuild iOS (Probe.swift was edited after the iOS pass), run two collections per platform, then write the report and
Korean lesson. Not covered: C04 (needs a frozen cookie profile), C09-C12, real Portals or the bridge.

## 2026-11-04 checkpoint — OkHttp accepted as the Android broker's client

The maintainer answered "그렇게 확정하자" to: OkHttp pinned to exactly 5.5.1, reviewed at T56. This is a design direction recorded in ADR 0027,
and it supersedes the client and version items left open in the checkpoints below. No dynamic version; rerun the probe before raising
the pin. The accepted "SDK never retries" rule also needs the network interceptor that hides `Retry-After`. `compileSdk` 37 is a host
build requirement only; the package declares `minSdk` 21, with only API 37 run.

The maintainer then answered "네, 따르기로": the broker follows `ProxySelector` and does not set `Proxy.NO_PROXY`. Real proxies and proxy
authentication are not measured yet.

Still OPEN: a host's newer OkHttp replacing the pin. Next, after the maintainer's go-ahead: isolated broker experiments C01-C08, with the
remaining transport items measured alongside them. Android C01-C08 broker experiments no
longer wait on the client. No production dependency or broker exists, T28 stays at 6/44, and the SPEC is unchanged. This work and the two
checkpoints below are merged into master by fast-forward and pushed, with branch t28-android-http-client kept at the same commit.
"Nothing is committed" below describes its own moment.

## 2026-11-04 checkpoint — OkHttp measured as the Android broker's client

The maintainer answered "OkHttp 측정". New isolated experiments/native-http-okhttp-probe, Android only, with OkHttp 5.5.1 a dependency
of that probe alone. Read docs/native-http-okhttp-verification.md and Korean lesson 44. Nothing is committed or pushed; publication
was not requested. The checkpoint below keeps its own statements, and this one supersedes what it says about no candidate being measured.

| Measured, broker configuration | Result |
| --- | --- |
| Global `CookieHandler`, `Authenticator`, `ResponseCache`, default TLS factory and verifier | Not used, while the same run shows each applying to `HttpURLConnection` |
| Global `ProxySelector` | Called, unless `Proxy.NO_PROXY` is set |
| Android transport requirements | Same as `HttpURLConnection`: all hold |
| 503 `Retry-After: 0` | **Sent twice, POST body included, despite `retryOnConnectionFailure(false)`** |
| Network interceptor renaming `Retry-After` | One attempt, GET and POST, value kept |
| One-shot body | One attempt, POST only |

OPEN, the maintainer's decisions, not made: the Android client, whether to follow `ProxySelector`, and the OkHttp version. Version sets a
`compileSdk` burden on hosts: 37 for 5.5.x, 36 for 5.4.0, none for 5.3.2 and earlier checked. C01-C08 Android broker experiments
wait on the client. Not measured: HTTP/2 and its 421 path, real proxies, a host's own OkHttp version, older OkHttp versions.

Reused the dedicated AVD; it is stopped and adb matches baseline, with the adb server left running as found. Fixture closed, no
crashes, nothing added to a trust store. Test keys went to the Trash, so the maintainer still empties it. Retained: 2 reports, 140
receipt rows, 426 verifier checks, 31 host tests, lint 0 errors / 3 warnings. T28 stays incomplete at 6/44. SPEC, protocol and
production packages are unchanged.

## 2026-11-04 checkpoint — Android global handlers conflict with the contract

The maintainer answered "1번 전역 설정 측정 먼저 진행하자". New isolated experiments/native-http-global-handlers-probe,
Android only. Read docs/native-http-global-handlers-verification.md and Korean lesson 43. Nothing is committed or pushed;
publication was not requested. This concerns SPEC §9 and the host-credentials invariant.

A host's global `CookieHandler` and `Authenticator` both reach `HttpURLConnection` requests. There is no per-request opt-out:
`setAuthenticator` and `Authenticator.getDefault` are desktop Java, absent from `android.jar` and at run time. So "disable
ambient handlers" and "never modify application-global settings" cannot both hold on this client while a host set either one.

| Measured | Result |
| --- | --- |
| Handler returning a cookie | Reaches the server; beside a broker cookie it is a second `Cookie` field |
| `Set-Cookie` including `HttpOnly` | Reaches the handler, even on a returned 302 |
| `Basic` 401 with an answering authenticator | Host credentials reach the server, and the client sees 200 |
| Server that keeps rejecting | 21 attempts, 20 with credentials, `ProtocolException`, no status |
| `Bearer`, `Digest`, no challenge header | One attempt, authenticator not called |
| Timing | Handler fixed at `openConnection`; authenticator read when the challenge arrives |

OPEN, the maintainer's decision, not made: which Android client the broker uses. The report lists four options and recommends
a different client with one bounded measurement first. None of those clients was measured. C01-C08 Android broker
experiments wait on this. The accepted transport rules are not reopened by this note.

The maintainer then asked how Ionic Portals and similar projects handle this ("조사를 먼저 해보자") before any OkHttp measurement,
so no candidate has been measured. A source comparison at pinned commits is in the report: no surveyed project defends on purpose,
Capacitor and Portals inherit the problem and set a global `CookieHandler`, and React Native, Expo, Flutter and Tauri avoid it by
using other clients. OkHttp needs `followRedirects` and `retryOnConnectionFailure` set false. Nothing was run.

Correction for later readers: an early check ran `javap` with `-cp android.jar` and showed `setAuthenticator`, but that read the
JDK's own class. Reading the class out of `android.jar` shows it is absent, and the compiler agreed. Do not repeat that check.

Reused the dedicated AVD; it is stopped and adb matches baseline, with the adb server left running as found. Fixture closed, no
crashes, nothing added to a trust store. Test keys went to the Trash, so the maintainer still empties it. Retained: 2 reports, 110
receipt rows, 216 verifier checks, 38 host tests, lint 0 errors / 4 warnings. One earlier collection with the same findings stays
in ignored local results. T28 stays incomplete at 6/44. SPEC, protocol and production packages are unchanged.

## 2026-11-03 checkpoint — local build outputs moved to the Trash

The maintainer answered "네, 옮겨줘" to moving regenerable ignored files. 42 paths went to the macOS Trash: probe `build`,
`app/build`, `.gradle` and `__pycache__`, example `dist`, and `.DS_Store`; experiments/ dropped from 97 MB to 11 MB.
local-results and node_modules were kept. Afterwards pnpm run check passes (1134 TS tests / 40 files, nine Python tests)
and every retained-evidence verifier passes, with the suppression report's expected iOS contract violations unchanged.
No device ran. Re-running a probe now needs its build script first; a rebuilt artifact may not match retained hashes.
The maintainer still empties the Trash.

## 2026-11-03 checkpoint — native HTTP transport Git publication

The maintainer answered "커밋 푸시 해" after being told this goes directly to master without a branch. At publication
start HEAD, origin/master and live remote master were all 4169c67. The series groups the transport probe evidence, the
accepted rules with report and linked plans, and this progress record with Korean lesson 42. Earlier statements below that
nothing is committed describe their own moment. Candidates were scanned for keys, build output, local paths, device ids
and emails with no hits. This does not mark T28 complete, accept the rest of ADR 0027 or release a package or tag. Next
work is listed in docs/native-http-transport-verification.md under "Before building on this", then C04 cookie profile
decisions and the broker experiments for C01-C08. The maintainer still empties the Trash holding test keys and references.

## 2026-11-03 checkpoint — native HTTP transport rules accepted

The maintainer questioned the Basic 401 proposal ("왠만하면 OS 의 기본 동작을 따르는게 좋지 않을까?"). Retained results
showed both platforms give the app a 401 and a body, so the proposal to cancel and return a fixed error was withdrawn.
The maintainer then accepted the revised set ("네, 그렇게 하자"). Do not ask for this approval again. It supersedes the
open decision in the checkpoint below.

Principle: follow OS behavior unless it changes what a mini app sees differently per platform.

1. One cookie pipeline: each adapter folds with `, `, both split the same way, one shared parser, no native parsers.
2. A 401 stays a normal result and the SDK never retries. The iOS resend after Basic is documented OS behavior. Ambient
   credential and cookie stores stay disabled, so host credentials are never exposed.
3. Cookies commit at header delivery by the client. C08 sends one body byte before holding.

Recorded in ADR 0027, the contract and C03, C04, C06 and C08. This accepts no other part of ADR 0027, changes no SPEC and
implements nothing. Measure before building: Android global Authenticator and CookieHandler set by a host, a Basic 401 that
also sets cookies, a preset Authorization on the iOS resend, other auth schemes, HTTP/2, mid-body failure and cancellation.

A source comparison at pinned commits is in the report: Capacitor and Portals inherit URLSession behavior, while Tauri
(reqwest) and Electron (Chromium) do not. A shared Rust HTTP layer is a recorded deferred alternative, conflicting with
ADR 0025 and the ordering of native cores after v0. Downloaded reference files went to the Trash. Nothing is committed.

## 2026-11-03 checkpoint — native HTTP transport primitives measured

The maintainer asked to continue T28 ("T28 이어서 진행하자"). That was read as authorizing one bounded broker
prerequisite run on the dedicated devices. New isolated experiments/native-http-transport-probe, on master and
uncommitted; commit was not requested. Read docs/native-http-transport-verification.md and Korean lesson 42.

Android HttpURLConnection and iOS URLSession both send no ambient cookies, deliver an attached Cookie unchanged,
return every 3xx without following it, return 4xx/5xx as results, do not cache and validate TLS. iOS conflicts with
the proposed contract in three ways:

| Finding | Measured | Contract text affected |
| --- | --- | --- |
| Set-Cookie folded into one value | A value containing `, name=` cannot be split back; the OS parsers disagree | Preserve separate fields, reject without repair |
| Basic 401 sends the request twice, POST body included | reject, default and useCredential nil all resend; cancel sends once but loses the response; Bearer and plain 401 send once | Never retry automatically |
| Headers delivered only with the first body byte | Android shows them at once | Commit at header time, C08 window |

OPEN AT THIS POINT, since decided in the checkpoint above: the report proposed one fold-then-split pipeline with one shared parser, treating HTTP
auth challenges as a fixed unsupported error, and defining the commit point as header delivery by the client. Do not
treat these as accepted, and do not build a jar against them. Fold-then-split gave identical lines in all 34 cases.
Digest, NTLM and Negotiate, HTTP/2, mid-body failure and cancellation are unmeasured. Most of C01-C08 still needs the
broker itself. T28 stays incomplete at 6/44. SPEC, protocol and production packages are unchanged.

Nothing was added to any device trust store: iOS pins to a CA bundled in the probe, and Android scopes it in the APK.
TLS negatives were refused with no receipt on both. Both devices are off after detaching the simulator panel, 13
baseline states match, fixture closed, no crashes. This experiment's keys went to the Trash, so the maintainer still
empties it. Retained: 4 reports, 164 receipt rows, 184 verifier checks, 49 host tests, lint 0 errors / 4 warnings. Two
earlier collections stay in ignored local results.

## 2026-11-03 checkpoint — cookie evidence Git publication

The maintainer answered "네, 커밋하자" to committing and pushing. At publication start HEAD,
origin/master and live remote master were all 913347f. The series went to branch
t28-native-cookie-evidence first, then the maintainer answered "네, 합치자" and master was
fast-forwarded to it. The branch is kept. Earlier statements below that nothing is committed
describe their own moment. The series groups:

- Handoff archive and its four pointers, verified byte-equal against the previous HANDOFF.
- One evidence commit each for the partition/writer, empty-store, Android restart and first-question
  probes, with their sources, tests and retained reports.
- The accepted iOS evidence rule, verification reports and linked plan updates.
- This progress record with Korean lessons 39, 40 and 41 and the study index.

This does not mark T28 complete, adopt the rest of ADR 0026/0027, change SPEC or protocol 0.1, or
release a package or tag. Candidates were scanned for keys, build output, local paths, device ids
and emails with no hits; local-results stay ignored. No probe ran for publication.

The maintainer also asked to delete the test certificates ("시험용 인증서도 삭제하자"). The four
Moonpool roots are removed from the dedicated simulator's trust store, which now holds none.
`simctl keychain reset` does not touch that store: it only cleared that simulator's general keychain
(41 to 19 generic items, 2 keys to 0). So the four rows were deleted from TrustStore.sqlite3 with the
simulator shut down. Local CA, key and server certificate files from six probes went to the macOS
Trash, not permanent deletion; emptying it is the maintainer's step. requests.jsonl receipts stay. Android
probe APKs on the dedicated AVD still bundle their public CA, trusted only by those apps, and it expires
2026-11-10 with its private key gone. Retained verifiers do not need these files. Re-running a probe
needs build.py to generate a new CA and, on iOS, `simctl keychain <device> add-root-cert`.

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

- **Host-named capabilities — review after T28 (recorded 2026-11-04, not
  approved):** the maintainer wants an option for hosts that cannot add token
  issuing: the host registers narrow methods such as `orders.list`, calls its
  own API with its own credentials and returns only the needed data, as
  `profile.get` already does. Conditions from that discussion: the namespace is
  the scope; no generic call-anything method such as `host.fetch`, which would
  equal sharing the host's login; the host validates params and authorizes each
  call (SPEC §9.6). `HostCapabilities` has fixed slots today, and this is a small
  plugin system, out of scope for v0 in CLAUDE.md, so it needs explicit approval
  and a SPEC §6 change. Do not scaffold it before that review.
- **Delivering a mini-app-scoped token (SPEC §9.4):** the spec requires a
  separate short-lived token where a mini app needs authenticated access, but no
  v0.1 capability delivers one. For a host of service A opening a mini app of
  service B, B issues the token, and A's credentials never go to B; at most a
  one-time proof does, by agreement between the two services.

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
