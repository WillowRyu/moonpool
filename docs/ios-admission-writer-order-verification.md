# T28 iOS admission and native writer order

2026-11-24. Two fresh runs used the same signed app on the dedicated iOS
26.4.1 simulator. The app was built with Xcode 26.4.1 (17E202) and the
iPhone Simulator 26.4 SDK. This experiment concerns SPEC §8 and §9.
[Probe and commands](../experiments/native-cookie-paths-probe/admission-writer-order-ios/README.md)

## Measured order

The fixture uses one native owner queue per identified
`WKWebsiteDataStore`. It initializes WebKit with a never-loaded,
nonpersistent view before any identified-store operation. It applies and
reads back cookie deny, then reads data records and the cookie list.
The fixture reuses the established Swift admission gate and cookie
presence classifier.
[Accepted iOS evidence order](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership)

| Trial | Observations in both iOS runs |
| --- | --- |
| Admission first | The native check reports an empty store. The requested writer stays queued through the first observed guest script. Both cookie sources still report empty and native write calls remain at zero. The fixture refuses the queued write once it sees the live view. |
| Writer first | Admission is requested while the native callback is pending. The callback's readback then reports cookies under deny and includes the test marker. The completed admission inspection refuses the candidate before any guest load. |

Both original reports replay from their archived sources. The recorded event sequences, write
outcomes and guest-load counts match the paired Android runs. The iOS
app build and signature check passed, the fixture app stopped, and the
owned simulator shut down.
[First iOS report](../experiments/native-cookie-paths-probe/admission-writer-order-ios/results/ios-admission-writer-order.json),
[Repeat iOS report](../experiments/native-cookie-paths-probe/admission-writer-order-ios/results/ios-admission-writer-order-repeat.json),
[Paired Android evidence](android-admission-writer-order-verification.md)

## Review follow-up

The reviewed inspector records its entry synchronously before starting the
asynchronous WebKit inspection. Callback arrival and completed readback
are separate events on the native writer. The stricter verifier rejects
an inspection start that precedes readback completion.

Both reviewed iOS runs pass with the same event sequence as the reviewed
Android runs. The two cookie sources confirm the test cookie at recheck,
and the writer-first candidate has zero guest loads.
[Reviewed iOS report](../experiments/native-cookie-paths-probe/admission-writer-order-ios/results/ios-admission-writer-order-review.json),
[Reviewed repeat](../experiments/native-cookie-paths-probe/admission-writer-order-ios/results/ios-admission-writer-order-review-repeat.json),
[Original report replay](../experiments/native-cookie-paths-probe/admission-writer-order-ios/README.md#replay-the-original-reports)

## Scope

This establishes the measured order for cooperating native callers
using the fixture queue on each platform. The live-view refusal is a
fixture behavior. The production admission interval still requires
evidence that every permitted writer uses the same owner boundary. The
remaining locality and document controls stay open.
[Accepted ownership rule](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership),
[C10 conformance plan](native-cookie-http-conformance-plan.md#c10--suppression-locality)
