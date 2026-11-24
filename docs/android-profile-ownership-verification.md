# T28 C09 Android same-process profile ownership

2026-11-24. Two collections ran the same APK on the dedicated Android 17
emulator (API 37), WebView 145.0.7632.218 and AndroidX WebKit 1.14.0.
This measurement concerns SPEC §8 and §9.
[Probe and commands](../experiments/native-cookie-paths-probe/profile-ownership/README.md)

## Measured native access

Each run creates three fresh named profiles. The independent control
holds a distinct public fixture cookie for the same synthetic HTTPS URL.
For the other two profiles, a second native lookup enumerates the name
and retrieves the same profile through `ProfileStore`. It receives the
name from fixture setup. The app uses native cookie APIs and has no guest
document, bridge or HTTP fixture.

| Trial | Observation in both runs |
| --- | --- |
| Native write under deny | Both lookups initially see deny and an empty jar. The second handle's native write callback returns true. The original and second handles still report deny and both observe the exact stored marker. |
| Policy mutation through the second lookup | The original handle immediately observes allow. After the marker is written and the original handle reinstalls deny, the marker is still present. |
| Separate control profile | Its allow policy and exact control marker remain intact after both trials. |

Both offline verifiers pass. They compare completed native callbacks with
the originating profile's state and verify locality against the control.
Android assemble and lint and the host regression test passed. The
collector stopped the fixture app and the owned emulator shut down.
[First report](../experiments/native-cookie-paths-probe/profile-ownership/results/android-profile-ownership.json),
[Repeat report](../experiments/native-cookie-paths-probe/profile-ownership/results/android-profile-ownership-repeat.json)

## Review follow-up

The retained-report command now requires `stored` as the expected native
write outcome. The collector still records either valid outcome when
running a new observation. A regression test uses a copy of a report with
a consistent refused write and verifies that it fails when the command
expects `stored`.

Current builds fingerprint the wrapper JAR and the declared probe build
inputs. The original reports retain their recorded hashes and use the
repository archive for those exact sources. Both reports passed the
stricter verification with that archive. The locally assembled APK hash
matches the installed artifact hash in both original reports.
[Replay commands](../experiments/native-cookie-paths-probe/profile-ownership/README.md#verify-the-retained-measurements)

## Admission implication

On the measured configuration, binding a WebView to a named profile
selects the app partition. Native code in that same app process can
retrieve the profile by name, change its policy and write to its cookie
store while browser cookie deny is active. The accepted admission
baseline therefore requires the host integration to coordinate all
native writers. A profile with a writable path outside that coordinator
is unsupported for admission.
[AndroidX named profiles](https://developer.android.com/reference/androidx/webkit/ProfileStore),
[Android CookieManager](https://developer.android.com/reference/android/webkit/CookieManager),
[Accepted admission baseline](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership)

These sequential native observations leave live Portal retirement and
writer exclusion in the production integration open. Other
processes, app packages and WebView versions are outside the
measured configuration. C09 and C10 remain open.
[C09 and C10 acceptance cases](native-cookie-http-conformance-plan.md#c09--browser-paths),
[Android live retirement follow-up](android-profile-retirement-verification.md)
