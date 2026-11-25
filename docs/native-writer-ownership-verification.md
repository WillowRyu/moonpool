# T28 native writer ownership checkpoint

2026-11-24. Repository audit at `68a5bc8` and integration evidence
checklist for T38/T39 and T56. This applies the existing admission
baseline and concerns SPEC §8 and §9.
[Accepted ownership rule](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership)

## Repository audit

All 76 tracked Java, Kotlin, Swift, Objective-C and Objective-C++ files
at this checkpoint are under `experiments/`. The native store selection
and engine cookie API calls found in this audit are in the experimental
tree. Native SDK loaders are scheduled for T38/T39, and T56 owns selection
of the host application and its integration contract.
[Native roadmap](native-implementation-plan.md)

| Source | Verified scope |
| --- | --- |
| [Android writer-order fixture](../experiments/native-cookie-paths-probe/admission-writer-order/android/app/src/main/java/org/moonpool/cookieadmission/AdmissionWriterOrderActivity.java) and [iOS writer-order fixture](../experiments/native-cookie-paths-probe/admission-writer-order-ios/Probe.swift) | The owner queue covers participating native writer and admission calls through first guest execution. Both platform verifiers check the ordered callback, readback and inspection events. |
| [Android ownership fixture](../experiments/native-cookie-paths-probe/profile-ownership/android/app/src/main/java/org/moonpool/profileownership/ProfileOwnershipActivity.java) and [iOS writer observations](native-cookie-partition-writer-verification.md#writer-exclusion) | Native API access can reach the same engine store independently of the fixture queue. The measured native writes reached the test store under browser-cookie deny. |
| [Android retirement fixture](android-profile-retirement-verification.md) and [iOS retirement fixture](ios-profile-retirement-verification.md) | Detection of an invalid shared store retires its owned views. The test-native write provides the detected condition. |

Android exposes named profile lookup and enumeration, and WebKit exposes
access to an identified store by UUID. Together with the measured
native writes, this supports treating exclusive use as a property of
the host integration. A verified identity and cookie policy establish
which store the admission check covers. The integration supplies evidence
of which native callers can reach that store.
[AndroidX ProfileStore](https://developer.android.com/reference/androidx/webkit/ProfileStore),
[WebKit website-data API](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKWebsiteDataStore.h)

## Evidence for a host integration

For the exact host build and each supported platform configuration,
record the app-to-origin-to-store binding, the native owner that can
change it, and the actual callers that can access the guest store.
The audit includes the app's own source, native bindings and included
components that create WebViews or access cookie and website-data APIs.

| Entry point | Evidence to obtain during integration |
| --- | --- |
| Store assignment and WebView creation | Trace creation and reuse to the trusted registration. Confirm that owned views bind that exact store before loading and that host-authenticated views use separate stores. |
| Cookie policy and admission reads | Identify the caller that installs and checks deny. Pin the current owner from the first inspection step through authorized guest execution. Reopening runs a fresh check. |
| Native store mutation | Enumerate allowed cookie writes, policy changes and data operations for the guest store. Connect every permitted caller to the same owner. The accepted initial baseline preserves data and excludes automatic cleanup and import. |
| View handles and native bindings | Review which host APIs, view objects and framework bindings can provide access to the underlying store. Account for any same-app lookup by profile name or store UUID. |
| Native HTTP and host authentication | Trace these callers to their separate native jar or host store. Preserve the app-scoped native HTTP session across guest refusal and keep host cookies and credential values outside the guest partition. |

The integration qualifies under the accepted ownership rule when every
permitted guest-store writer is accounted for and shares the admitted
owner boundary. An unaccounted write path makes the configuration
unsupported before guest load. Point-in-time emptiness and observations
after a change are separate evidence from writer exclusion.

## Acceptance evidence for T38/T39 and T56

Use the actual host calls in the selected integration to verify both
admission and write orderings, with distinct markers for the guest and
the host controls. Cover an unverified assignment before first execution,
a policy change under the managed owner, and a replacement or retirement
while admission is pending. Confirm zero guest loads for refused
candidates, and apply the accepted shared-partition retirement rule
when a live gate loses its eligibility. Record isolation of unrelated
host and app stores and preservation of their data.

This checkpoint establishes the repository-side boundary and evidence
requirements. Production writer exclusion remains pending the actual
loader adapters and selected host integration.
[C09/C10 verification plan](native-cookie-http-conformance-plan.md#c09--browser-paths),
[T38/T39 and T56](native-implementation-plan.md)
