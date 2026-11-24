# T28 C10 Android WebView retirement on shared profile refusal

2026-11-24. Two fresh runs used the same APK on the dedicated Android 17
emulator (API 37), WebView 145.0.7632.218 and AndroidX WebKit 1.14.0.
This concerns SPEC §8 and §9.
[Probe and commands](../experiments/native-cookie-paths-probe/profile-retirement/README.md)

## Live WebView observations

Each run wires the existing research admission gate to actual WebViews.
A1 and A2 use the same named profile and synthetic HTTPS origin. B1 uses
a different profile and origin, with its own gate. All three load
after a native inspection under cookie deny finds an empty jar.
The first document in each profile writes an IndexedDB marker.
A2 reads the marker A1 wrote.

A test-owned native write adds a public fixture cookie to A while deny
is in effect. A3 requests admission and remains pending with zero loads.
Its asynchronous inspection reads the actual A cookie manager and returns
present. It triggers invalidation of all A handles before the first
WebView teardown. The fixture removes each affected WebView from the
view hierarchy and calls `destroy()` on the UI thread.
[Accepted shared-profile rule](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership),
[WebView lifecycle reference](https://developer.android.com/reference/android/webkit/WebView#destroy())

| Observation | Result in each run |
| --- | --- |
| A1 and A2 | Both handles became inactive before either admitted WebView was removed and destroyed. |
| A3 and A4 | A3 completed its inspection without a guest load. A4 was refused by the blocked gate before inspection or guest load. |
| B1 | The original WebView stayed attached. The original document token and storage marker matched, and its JavaScript counter advanced without reloading. |
| Stored data in A | Host-supplied HTML read the original IndexedDB marker on the original named profile after retirement. The fixture cookie also remained in the native store. |

The guest loader served only the three initially admitted documents.
Both reports pass all checks. Across two runs there were four admitted A
WebViews destroyed and four later A admission attempts with zero loads.
Android assemble and lint and both host regression tests passed. The
fixture app stopped and the dedicated emulator shut down.
[First report](../experiments/native-cookie-paths-probe/profile-retirement/results/android-profile-retirement.json),
[Repeat report](../experiments/native-cookie-paths-probe/profile-retirement/results/android-profile-retirement-repeat.json)

## Remaining evidence

This measures the response to a present-cookie result in one Android
configuration. The fixture deliberately permits a test native write and
observes the next gate inspection. Writer exclusion during the full
admission interval, the remaining C10 profile and host controls, and the
T31 pending-call contract remain open. The iOS follow-up reproduces this
fixture-level retirement scenario.
[Android native writer evidence](android-profile-ownership-verification.md),
[Paired iOS evidence](ios-profile-retirement-verification.md),
[C10 conformance plan](native-cookie-http-conformance-plan.md#c10--suppression-locality)
