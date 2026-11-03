# T28 — Cookie-suppression feasibility evidence

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded C09/C10 research; the full common-cookie contract remains open.
This report concerns SPEC §9 isolation and credential handling. It does not amend
SPEC or accept ADR 0026/0027.

## Finding

In the measured configuration, Android's selected Profile cookie policy suppresses
both new and existing engine-cookie access without disabling host/control cookies.
iOS's per-store disallow policy blocks new cookie writes but leaves previously
stored HTTPS cookies readable and sends them to the controlled server. A policy
read returning disallow is therefore insufficient evidence of full suppression.

Both platforms suppress cookies in a **fresh empty owned partition** when the
policy is installed before its first document load. This is a narrower passing
control, not a repair or migration of the seeded-store failure.

| Observation | Android | iOS |
| --- | --- | --- |
| H/U cookie read/write/send controls remain working | Yes | Yes |
| Only A disabled; B remains working | Yes | Yes |
| New cookies blocked after policy completion | Yes | Yes |
| Previously stored HTTPS cookies hidden from ordinary/prototype/frame reads | Yes | **No** |
| Previously stored HTTPS cookies absent at the server | Yes | **No** |
| View/store-handle recreation changes the finding | No | No |
| Fresh A/B partitions disabled before first load stay empty | Yes | Yes |
| Local iOS moonpool cookie reads establish cookie isolation | Not applicable | No; they are empty even in the baseline |

The iOS failure is observed with first-party HTTPS diagnostic loads. Production
navigation containment is not implemented by this fixture; do not claim that a
production guest can navigate there, or infer host-credential leakage. These are
public cookies in this probe application's dedicated partitions. The result does
refute the proposal that the policy alone makes *all existing* WebView cookies
unavailable. Custom-scheme subresource/third-party behavior needs separate tests.

## Evidence and independent checks

The [source and reproduction guide](../experiments/native-cookie-suppression-probe/README.md)
defines all cases and ownership rules. Final paired reports are linked below:

- [Android first](../experiments/native-cookie-suppression-probe/results/android-confirmed-first.json)
  and [repeat](../experiments/native-cookie-suppression-probe/results/android-confirmed-repeat.json).
- [iOS first](../experiments/native-cookie-suppression-probe/results/ios-confirmed-first.json)
  and [repeat](../experiments/native-cookie-suppression-probe/results/ios-confirmed-repeat.json).

Each report contains native policy reads and partition identities, ordered
creation/policy/load events, 50 document/native-cookie snapshots and 100 HTTPS
server-receipt rows. A1/A2 share one app partition; A/B/H/U differ. The new empty
control replaces only A/B's selected fixture partitions and leaves seeded stores
intact. H/U remain in the same partitions, so replacing the control cannot hide
a global policy side effect.

Four final runs retain **200 samples and 400 HTTPS requests**. Each report has
765 behavioral checks plus native-event/source/artifact integrity checks.
Android has no contract violations in either run. Each iOS run has 56 failed
conditions: eight seeded, disabled HTTPS samples × three cookie read paths and
four server-received request paths. No new blocked-stage marker was stored.
All three fresh-disabled HTTPS samples per platform/run remain empty and send
no cookies. This is 16 repeated failing seeded iOS samples, not 56 distinct bugs.

The verifier checks current source hashes, installed/build artifact correspondence,
native binding and policy order, loaded frame controls and actual server receipts.
Contract checks remain strict: iOS retained-cookie access is reported as FAIL,
not ignored or converted into a parity pass. A report's `complete` flag means
observation collection finished, not that the proposed contract passed.

## Environment and test trust

| Component | Measured configuration |
| --- | --- |
| Android | API 37 / Android 17, WebView 145.0.7632.218, AndroidX WebKit 1.14.0, MULTI_PROFILE |
| Android build | Existing Gradle 9.6.1 wrapper / AGP 9.3.1, compile/target 36, build-tools 36.0.0; JBR 21.0.10 |
| iOS | Dedicated iPhone 17 Pro simulator / iOS 26.4.1 |
| iOS build | Xcode 26.4.1 / 17E202, simulator SDK 26.4, deployment target 17.0 |
| Server | Python standard-library loopback HTTPS, run/case-correlated request log, no browser cookie echo |
| Trust | Generated localhost CA scoped to this Android APK and the dedicated iOS simulator; normal TLS and hostname checks |

Installed tools differ from the previous T28 experiment; earlier tool versions
are not relabeled as current evidence. API availability does not establish an
SDK minimum OS or a broad provider support range. Android lint passes with zero
errors and 29 warnings: feature-check flow across methods (23), pinned dependency
versions (2), target API (1), deliberate JavaScript fixture (1), standalone backup
metadata (1) and icon metadata (1). All guest construction is preceded by the
onCreate MULTI_PROFILE gate. The warnings do not establish production support.

No host-machine trust root or global WebView cookie setting was changed. The
probe H view uses this new test app's default store with public markers, never
the maintainer's actual authenticated host app. Private certificate keys and
device identifiers are excluded from retained reports. No intentional crash,
first-call store enumeration, data wipe or automatic crash retry ran.

Both session-owned probe apps and devices were stopped after collection; the
owned adb reverse mapping and HTTPS fixture were closed. All 12 pre-existing iOS
simulator states remain unchanged; pre-existing Android AVDs were not booted or
modified. Task-created device configurations and ignored raw diagnostics remain.
Global ADB was not stopped because pre-task server ownership was not established.
No settings in the host's trust store or crash reporter changed.

The fixture/verifier/runner suite passes 21 tests, including independent server
receipt, untrusted-CA failure, negative evidence mutations, native binding/order
and collection regressions. Evidence-reporting mode preserves the expected iOS
contract FAIL. Runtime packages and historical native probes remain unchanged.

## Contract consequence and subsequent admission decision

Keep the parity requirement and the SDK-only cookie direction. Do not implement
an Android-only compatibility fallback or claim the iOS policy satisfies the
existing-data case. The evidence informed this bounded admission rule:

> Use an SDK-owned browser partition with the disallow policy installed before
> any guest or resource runs. If a retained partition contains engine cookies,
> reject guest admission until an explicitly approved migration resolves it.
> Do not silently delete cookies, swap the partition or erase browser storage.

The refusal/data-preservation baseline was subsequently **accepted as a design
direction on 2026-11-03**, not implemented. Initial emptiness and policy
installation must be serialized with admission, including same-app concurrent
Portals; preflight enumeration alone is not a complete proof against future native
writers or other network paths. The embedding host is trusted to honor ownership.

Compared with the previous unconditional suppression promise, this rule refuses
an existing-cookie configuration instead of pretending it is equivalent. It
preserves existing data and makes the migration cost explicit. Choosing automatic
cleanup, migration or a new partition would require a separate data-lifetime
decision, especially for retained localStorage/IndexedDB and stable origin/store
registrations. This task performed none of those operations on seeded stores.

The subsequent [admission baseline and recovery proposal](native-cookie-store-admission.md)
record cookie-specific emptiness, accepted shared refusal/retirement and data
preservation, and still-proposed recovery conditions. This decision preserves
the measurements and their failures; no later measurement or recovery approval
is implied.

T28 remains incomplete. C09's full network/worker/navigation matrix, migration
admission, process restart behavior and production-loader integration remain.
C01–C08/C11/C12 native broker behavior, public schemas, final normative approval,
T48 durability and T53 resource limits are not covered by these results.
