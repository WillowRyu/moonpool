# T28 Android admission and native writer order

2026-11-24. Two fresh runs used the same APK on the dedicated Android 17
emulator (API 37), WebView 145.0.7632.218 and AndroidX WebKit 1.14.0.
This concerns SPEC §8 and §9.
[Probe and commands](../experiments/native-cookie-paths-probe/admission-writer-order/README.md)

## Measured order

The fixture routes admission and its authorized test writer through one
native owner queue per named profile. An operation keeps the reservation
until its own completion. The writer uses Android's asynchronous native
cookie callback. Each trial starts with a fresh profile reporting deny
and no stored browser cookie.
[Android CookieManager](https://developer.android.com/reference/android/webkit/CookieManager)

| Trial | Observations in both runs |
| --- | --- |
| Admission first | The real empty inspection pauses before it authorizes a load. The requested writer stays queued through the first guest script observation. At both checkpoints the native write count is zero and the cookie jar is empty. The fixture declines the queued write when it sees the admitted view is live. |
| Writer first | Admission is queued before the owner processes the write callback. The callback processing reads the test marker. The inspection finds a cookie and the gate refuses the candidate with zero guest loads. The final native state has a cookie. |

Both original reports replay from their archived sources. The host tests also pin stale completion
handling and the held reservation after the empty read and through the
guest observation. Android assemble and lint passed, and the fixture app
and owned emulator stopped.
[First Android report](../experiments/native-cookie-paths-probe/admission-writer-order/results/android-admission-writer-order.json),
[Repeat report](../experiments/native-cookie-paths-probe/admission-writer-order/results/android-admission-writer-order-repeat.json)

## Review follow-up

The reviewed probe records native callback arrival before posting the
owner's readback work. The verifier requires callback arrival, completed
readback and inspection entry in that order. It requires the exact
fixture cookie at the same URL after the gate refuses admission. Both
reviewed Android runs pass with zero writer-first guest loads and the
same final marker.
[Reviewed report](../experiments/native-cookie-paths-probe/admission-writer-order/results/android-admission-writer-order-review.json),
[Reviewed repeat](../experiments/native-cookie-paths-probe/admission-writer-order/results/android-admission-writer-order-review-repeat.json),
[Original report replay](../experiments/native-cookie-paths-probe/admission-writer-order/README.md#replay-the-original-reports)

## Scope

The observed exclusion applies to native callers using the fixture's
owner queue, including the test writer. The fixture's live-view refusal
is the controlled behavior for this experiment. The accepted baseline
requires integration evidence for all actual native writers. Production
writer exclusion and remaining document and locality checks stay open.
The paired iOS fixture reproduces the observed order and outcomes.
[Accepted ownership rule](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership),
[Android same-app ownership observations](android-profile-ownership-verification.md),
[Paired iOS evidence](ios-admission-writer-order-verification.md)
