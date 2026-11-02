# T28 — Native origin and website-store supplementary verification

Date: 2026-11-03 (Asia/Seoul)
Status: Supplementary research complete for the recorded configurations; final
contract review/approval remains. This report does not amend SPEC or establish
production native SDK conformance. T28 is not yet marked complete.

The maintainer has since required equal cookie behavior on Android/iOS. The
[common cookie/HTTP design](native-cookie-http-contract.md) is a new proposal.
This report measures the prior WebView-cookie configuration, not its native
broker, equal cookie suppression or server-observed API-session behavior. Keep
these original results; new conformance gates remain open before T28 completion.


The maintainer selected the [T28 proposal](native-origin-contract.md) for bounded
supplementary probes after reviewing its scope. New standalone harnesses are in
[native-origin-contract-probe](../experiments/native-origin-contract-probe/README.md).
T23–T27 source and historical evidence remain unchanged. No pure kernel,
production transport, protocol version or root dependency was changed.

## Android result

Four final runs (first/repeat, each seed then process restart) contain 44 raw
snapshots. The independent verifier, 23 shared identity vectors, JVM admission
suite and seven verifier mutation tests pass. Build/lint and Biome pass; Android
lint retains 28 warnings with no errors. Exact categories and tools are recorded
in the [environment record](../experiments/native-origin-contract-probe/android/results/environment.json).

| Observation | Evidence and limit |
| --- | --- |
| Stable Android identity | Independently derived full SHA-256 / lowercase unpadded base32 matches the native mapping; exact loaded .invalid HTTPS origins retain the app-specific 55-character host label |
| Origin boundary | Same-origin loaded frame DOM/storage access succeeds, foreign loaded DOM throws SecurityError; a B-origin page in A's Profile sees no A or B marker while A retains its own data |
| Profile boundary | Every measured guest view selects its exact nondefault Profile before use; distinct A/B Profiles isolate localStorage, IndexedDB and cookie values |
| Same-app lifetime | Second A view, actual WebView.reload, recreated view and new app process retain A data; diagnostic document tokens distinguish replacement from a stale read |
| Local cookies | Host-only Secure/Max-Age cookies work and persist; Domain=invalid and sibling-host cookies are rejected, with native profile CookieManager corroboration |
| Common remote site | A/B/synthetic-host Profiles load the real https://example.com page and retain separate public cookie markers, including pre-write, same-A and process-restart controls |
| Unsupported/admission cases | Pure tests reject invalid ids, simulated unsupported features, missing registration/profile, remap and forced collisions; the actual provider reports MULTI_PROFILE support |
| API use ordering | getProfile before setProfile causes an actual IllegalStateException without guest load; getSettings alone is accepted by this provider, so it is not reported as a rejected case |

The Android device loads com.example.a and com.example.b. The shared vector
file additionally includes com.example.probe.a/b and unusual valid/invalid ids;
these are mapping/URI cases, not additional loaded Android documents. Version is
not an input to the mapping; no installed-package upgrade is measured.

The cross-frame test's combined DOM/storage access stops at the DOM exception.
It therefore proves foreign DOM denial, not an independently attempted foreign
frame storage read. The separate within-A-profile B-origin document provides
the origin-storage negative control. This distinction prevents a short-circuit
from being counted as two independent observations.

## iOS result

Four final runs contain 52 named local/HTTPS observations and 92 identity rows.
The independent verifier passes 1,344 assertions, with a passing baseline plus
five mutation tests. All 37 Swift registration/admission checks pass. Six further
minimal startup controls use the same signed executable/source set. See the
[iOS README](../experiments/native-origin-contract-probe/ios/README.md) and
[environment record](../experiments/native-origin-contract-probe/ios/results/environment.json).

| Observation | Evidence and limit |
| --- | --- |
| Exact identity | All 15 valid vectors retain native moonpool/exact-host/port-zero origins, including 63/64-character labels and 253/254/1028-character ids; eight invalid ids fail registration |
| URL representation | Three authorityless invalid diagnostics additionally record uppercase, explicit-port and percent-escape behavior; uppercase JS hostname and native securityOrigin host differ, so page text is not authoritative |
| Origin boundary | Loaded self/foreign frames have independently observed ready origins and delivered bytes; self DOM/storage works and foreign DOM/storage access fails; B-under-A-store stays empty while A retains its data |
| Store ownership | Native per-view configuration records the exact persistent store UUID; A/B/synthetic-host stores differ and a second A view reuses A's UUID |
| Lifetime | Actual reload uses a read-only seed=false URL, a fresh document token and new native report; view recreation and process restart retain localStorage/IndexedDB and HTTPS cookies |
| Common remote site | Real example.com pages have native HTTPS origins and HTTP 200 controls; JS/native pre-write and post-write cookies remain A/B/host-specific; Secure/Max-Age cookies persist and invalid parent/sibling cookies are absent |
| Custom cookies | document.cookie remains empty on custom origins; this is unavailable functionality, not a passing cookie-isolation result |
| Registration loss | Pure tests model missing/remapped/duplicate/zero UUIDs, unavailable API, missing platform store and complete metadata loss with retained stores; live runs enumerate existing UUIDs before reopening them |

Preparatory registration/seed work precedes the retained runs, using the same
final artifact for reproduction. Final snapshots prove reopening, sharing and
controlled lifetime after preparation; they do not prove fresh-install atomicity
or recovery from power loss. UUIDs are stable across all four retained processes.
A complete loss of both native metadata and every website store is not
independently distinguishable from a new installation in this fixture.

## iOS startup ordering finding

Store enumeration as the first WebKit operation crashes in this measured
configuration. Two fresh-process Swift-async controls and two explicit MainActor
completion-handler controls produce EXC_BAD_ACCESS / SIGSEGV with
fetchAllDataStoreIdentifiers, WTF::RunLoop::dispatch and os_unfair_lock_lock in
the stack. Each retained crash is matched locally to its exact launched process
and probe bundle; raw crash paths, process/device identifiers and unrelated data
are excluded. Absence of a report alone is not counted as a crash.

Two positive controls first construct an empty nonpersistent WKWebView, perform
no guest navigation, then enumerate successfully. The full runs use this working
order and release the temporary initialization view; every actual guest still
uses its assigned persistent store. There is no default/nonpersistent **guest**
store fallback and the private host kernel model from ADR 0025 is unchanged.

This establishes an initialization-order dependency for this iOS 26.4.1 simulator
with an Xcode/SDK 27 build. It does not establish an Apple-mandated universal
initializer or the internal root cause. The callback result also rules out a
failure limited to the Swift async overlay. Native implementation/support checks
must reproduce safe startup ordering before enabling a guest; T53 must account
for its cost. Other runtime/toolchain combinations and crash recovery are unproven.

The intentional failures caused visible macOS crash dialogs. The maintainer
reported the repeated dialogs; all crash-producing work is stopped, the probe
process/scripts are absent and the owned simulator is Shutdown. Reuse retained
reports for routine verification. Do not relaunch these crash controls unless
explicitly requested. The system notification UI denied computer-tool access,
so pending macOS alerts could not be dismissed automatically. No system crash
reporting preference was changed or background system service terminated.

## Environment and ownership

| Area | Actual configuration |
| --- | --- |
| Host | macOS 27.0.1 arm64; Node 22.19.0 / pnpm 11.1.3 for root checks |
| Android | Android 17/API 37; Google WebView 145.0.7632.218; AndroidX WebKit 1.14.0; emulator 37.1.11.0 |
| Android build | Gradle 9.6.1 / AGP 9.3.1; Studio JBR 25.0.3; compile/target SDK 36; probe minSdk 31 |
| iOS | New dedicated iPhone 17 Pro simulator, actual iOS 26.4.1; identified persistent stores |
| iOS build | Xcode 27.0 / 27A266a, Swift 6.4, simulator SDK 27.0, probe deployment target 17.0 |
| Ownership | Initially no adb devices and all existing iOS simulators Shutdown; only the owned Pixel_7_Pro and new iOS simulator used; both stopped afterward; all 25 pre-existing iOS states preserved |

Current tools differ from the historical probes. No SDK/runtime or global Xcode
selection was changed. Android used official dependency resolution for its
isolated experiment. Source, common-vector, asset, installed APK/executable and
signature checks identify the final captures. Native API availability and probe
minimum targets are not product minimum-OS or broad provider support promises.

## O01–O06 disposition

| Gate | What the evidence supports | Retained limitation |
| --- | --- | --- |
| O01 identity/lifetime | Stable origin/store identity and same-app sharing/reload/recreation/process restart | Version-independent derivation, not an installed-package upgrade; preparatory registration is explicit |
| O02 parsing | Shared 23-vector mapping/validation; actual iOS origins and invalid aliases; actual Android A/B origins | Android unusual ids are JVM/URI vectors; finite iOS vectors do not define all supported ids |
| O03 origin/storage | Loaded self/foreign DOM controls plus separate origin and store storage controls | Android foreign frame storage read is not independently attempted after DOM failure |
| O04 cookies | Working persistent HTTPS controls, parent/sibling rejection; explicit iOS custom-cookie unavailability | No custom-cookie parity or general cookie policy inferred |
| O05 shared remote origin | First-party cookie partitions for A/B/synthetic host and controlled persistence | No server-header receipt, guest cross-origin fetch/ITP or real host-auth integration |
| O06 failures | Modeled unsupported/lost/conflicting registration tests; actual Android misuse and iOS startup failures | No real unsupported Android provider or old iOS target; no production recovery/durability claim |

These results support the selected design in the recorded configuration, with the
iOS startup limitation attached. Final contract approval remains necessary before
SPEC/CLAUDE.md changes or T28 completion. O07–O10 stay with their planned tasks.

## Interpretation boundaries

The remote cookie experiment uses separate top-level HTTPS documents and native
cookie-store reads, with only public t28_ sentinel values. It establishes
first-party cookie partitioning at that remote origin. It does not measure the
Cookie header received by the server, cross-origin guest fetch, third-party/ITP
policy, authenticated APIs or host session transfer. No actual host credentials
enter any probe store. HTTP caching is not a cookie delivery receipt.

The local research resolvers deliberately allow public foreign app frame bytes
to measure browser origin enforcement. That exception is not the proposed
production per-Portal loader. O07 loader confinement, O08 production sender
admission, O09 integrated navigation and O10 document/pending semantics remain
their existing T29–T45 gates. Website profiles are data partitions, not a claim
of independent OS processes, fault recovery or storage durability under power loss.

## Reproduction

From the repository root, use the platform README commands and explicit device
ownership. Offline retained-evidence verification does not start a device:

```sh
python3 experiments/native-origin-contract-probe/android/test_contract.py
python3 experiments/native-origin-contract-probe/android/verify_results.py experiments/native-origin-contract-probe/android/results
python3 -m unittest discover -s experiments/native-origin-contract-probe/android -p test_verifier.py
python3 experiments/native-origin-contract-probe/ios/verify_results.py experiments/native-origin-contract-probe/ios/results
python3 -m unittest discover -s experiments/native-origin-contract-probe/ios -p test_verifier.py
pnpm run check
```

Read [the Android README](../experiments/native-origin-contract-probe/android/README.md)
and [iOS README](../experiments/native-origin-contract-probe/ios/README.md) for
artifact/source checks, native unit commands and explicit ownership procedures. Do not
rerun historical probes, overwrite their results or resume a device just to
validate this documentation.

## Final repository validation

The final root pnpm run check passes 1,134 TypeScript tests in 40 files, nine
Python tests, both typechecks, Biome (288 files) and both browser builds. The
known Vite config warning remains. Both native retained-evidence verifiers pass
after result-only JSON formatting; frozen source/artifact hashes remain intact.
All 636 local references across 37 study pages resolve, with prior scripts,
unique ids, all 44 roadmap task ids and instruction symlinks preserved. Sixteen
retained JSON files were checked for parseability and local path/device-id
exclusion. The study results table was reviewed in the browser; temporary
preview resources are closed. Final validation did not boot a device or execute
a crash control. git diff --check passes; all current work remains uncommitted.
