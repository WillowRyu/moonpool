# T28 — Native cookie presence and admission-control verification

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. The admission baseline is
accepted; production admission, complete inventory/containment and T28 completion
remain gated. This work concerns SPEC §9 and does not amend the protocol.

## Results

The new [isolated experiment](../experiments/native-cookie-admission-probe/README.md)
connects a private native admission controller to the selected Android Profile's
hasCookies and the selected iOS store's getAllCookies. It does not implement a
production SDK or put platform calls into the shared kernel.

| Case | Independent observation | Admission on both tested platforms |
| --- | --- | --- |
| Empty browser cookie store, existing localStorage/IndexedDB data | Native absence; retained data and working host control | Candidate guest loads and executes its marker |
| Ordinary cookie | Server receives marker; native inventory sees it | Refused; zero candidate guest-resource deliveries |
| HttpOnly cookie | JS read is empty; native inventory and server see marker | Refused; cookie/data preserved |
| Cookie on /hidden/ | JS at /visible is empty; matching server request carries cookie | Refused; whole-store presence detects it |
| Cookie on 127.0.0.1, lookup at localhost | JS/address-specific lookup misses it; server/native inventory see it | Refused; whole-store presence detects it |
| Server-supplied Partitioned cookie candidate | Marker is received and inventoried; Android exposes the partitioned attribute, iOS does not | Refused for the observed stored cookie; full iOS partitioned coverage is unproven |

Each platform ran twice, with six cookie cases and initial/reopened observations:
**48 samples, 76 HTTPS requests, 644 verifier checks, and 36 native callback traces**
(nine distinct scenarios executed in four runs). Each run delivers exactly two
candidate guest resources: the empty case before and after reopening. Cookie-
bearing cases deliver none. Native loader observations supplement invocation
counts; a self-reported refusal flag alone is not accepted as evidence.

Retained raw reports:

- [Android first](../experiments/native-cookie-admission-probe/results/android-first.json)
  and [repeat](../experiments/native-cookie-admission-probe/results/android-repeat.json).
- [iOS first](../experiments/native-cookie-admission-probe/results/ios-first.json)
  and [repeat](../experiments/native-cookie-admission-probe/results/ios-repeat.json).

For Android, the native URL-specific cookie read also misses the off-path and
unrelated-host cases while hasCookies reports presence. HttpOnly is not hidden
from native CookieManager reads, only from script reads. The iOS experiment uses
whole-store enumeration directly; it does not invent a URL-filtering fallback.

## Data and ownership

Every cookie case has a distinct assigned persistent partition. Reopening retains
that exact Android Profile name or iOS identified-store UUID. localStorage and
IndexedDB public sentinels are read after each decision and after reopening.
Native cookie snapshots match before/after admission. The probe app's separate
host-control partition keeps its policy and exact public cookie value.

A trusted fixture observer prepares and reads the public data; this is not the
candidate guest. Candidate views are separately constructed without loading and
receive their first resource only through the gate's load callback. The setup/
observer exception is for measurement and is not a production containment rule.
No cookie deletion/import or whole-store replacement occurs. Separate native
HTTP/provider data preservation is a design requirement, not an implemented
broker/provider integration claim from this fixture.

## Controlled concurrency and stale callbacks

The same nine readable event oracles run through the Java and Swift controllers
both in host-toolchain tests and inside the native apps:

| Scenario | Required outcome |
| --- | --- |
| Queued A1/A2 | A2's inspection begins only after A1's inspection settles; neither loads before its own empty verdict |
| Present cookie with A1 active and A2/A3 pending | All A handles retire; independently admitted B remains active |
| Unknown result | Active/pending A handles retire without another guest load |
| Duplicate callback | An old completion cannot settle/clear the current inspection or retire its owner |
| Cancel then replace | The cancelled handle never loads; the replacement requires a fresh inspection |
| Invalidate then explicit retry | The old read drains before new inspection; its late verdict cannot block or admit new work |
| Terminal owner replacement | Old completions/retry cannot reopen the retired owner or load old content |
| Cleanup exception | Every handle is invalidated before cleanup; one throwing callback does not skip another cleanup |
| Reentrant retirement during load callback | The queued second Portal does not load |

Request-object identity and a private owner revision distinguish current from
retired work. Completion releases only its own in-flight slot. This is local
native-control state, not a new JSON-RPC field or the T30 document-generation ABI.
The code is confined to one native owner executor (MainActor on Swift); it is not
a general multi-thread-safe coordinator or a validated production scheduler.

The traces inject controlled completion order and present/unknown results. They
do not reproduce every OS/network race, missing callback, native exception or
queued cookie writer. In particular, the gate does not establish exclusion of
engine writes while a real shared store is being inspected. Full writer exclusion,
actual multi-Portal teardown and T31 pending-call integration remain required.

## Partitioned-cookie limitation

Android GET_COOKIE_INFO retains `partitioned` on the observed server cookie and
hasCookies detects it after deny policy. This is one stored partitioned record
in the tested context, not a proof covering every partition key or backend state.

iOS enumerates and refuses the cookie sent with Partitioned, but its public
HTTPCookie property-key snapshot does not expose a partition attribute in these
runs. We have not independently distinguished partitioned storage from a record
whose attribute was ignored or omitted by the projection. Do not promote that
sample to complete partitioned-inventory proof. Header input alone is insufficient.
The current [Cookie Store API dictionary](https://cookiestore.spec.whatwg.org/#dictdef-cookielistitem)
also does not provide a general native partition inventory; JS visibility is not
the admission authority.

An empty result from this bounded research adapter is therefore not approval of
a production configuration with unknown backend coverage. The accepted policy
still requires such uncertainty to refuse admission. The next evidence work must
establish iOS partitioned-store coverage and real writer/owner exclusion before
claiming the full gate.

## Environment, verification and cleanup

Android: API 37 / Android 17, WebView 145.0.7632.218, AndroidX WebKit 1.14.0;
existing Gradle 9.6.1 / AGP 9.3.1, compile/target SDK 36. iOS: iOS 26.4.1 on the
session-owned iPhone 17 Pro simulator, Xcode 26.4.1 / SDK 26.4, deployment 17.0.
These are measured configurations, not product minimums or a support matrix.

Both native builds and iOS signature verification pass. Android lint has zero
errors and 31 recorded warnings: feature-check flow across methods (25), pinned
dependencies (2), target API, deliberate JS, backup metadata and icon metadata
(one each). onCreate checks MULTI_PROFILE before constructing guest partitions.
The host suite has 14 tests, including both native-language trace runners,
HTTP fixture controls and negative evidence mutations. Tests were RED before
helpers; later verifier gaps for guest-resource delivery, host-cookie values,
native errors and omitted source fingerprints were also pinned RED before fixes.

The verifier checks complete native source fingerprints, installed/built artifact
equality, native snapshots, server receipts, data preservation and callback traces.
Native load/TLS errors or missing controls cannot be accepted as clean evidence.
The local HTTPS CA is scoped to this probe APK (localhost/127.0.0.1) and the owned
simulator; normal TLS validation remains enabled. Private keys, local paths,
ownership records and raw process logs are excluded from retained results.

Only the prior session-owned devices were resumed. Both apps/devices, the owned
adb reverse mapping and the fixture are stopped. All 13 baseline iOS simulator
states are restored; unrelated Android AVDs and global ADB are preserved. No data
wipe, recovery/deletion experiment, cold store enumeration or intentional crash
was run. Historical suppression source/evidence remain byte-for-byte unchanged,
including the old iOS suppression failures.

T28 stays incomplete at 6/44 native tasks. SPEC, production packages, public API,
wire version, automatic recovery and release state are unchanged.
