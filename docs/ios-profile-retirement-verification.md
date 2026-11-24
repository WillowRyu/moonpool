# T28 C10 iOS WebKit retirement on shared-store refusal

2026-11-24. Two collections ran the same signed fixture app on the
dedicated iOS 26.4.1 simulator, built with Xcode 26.4.1 (17E202)
and the iPhone Simulator 26.4 SDK. This concerns SPEC §8 and §9.
[Probe and commands](../experiments/native-cookie-paths-probe/profile-retirement-ios/README.md)

## Live WKWebView observations

The app first creates a never-loaded, nonpersistent initializer view.
The actual fixture views use identified persistent WebKit stores. A1 and
A2 share A's store and origin, and B1 has a separate store and origin.
The existing Swift gate sets cookie deny, verifies its readback and
compares cookie data records and the cookie list before each admission.
Both sources report empty before the first three views load their local
`moonpool://` pages. A2 reads the IndexedDB marker A1 wrote.
[Accepted iOS evidence ordering](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership)

A test-owned native writer adds a public fixture cookie to A. A3
requests admission and remains pending without starting a load.
After its deny-policy call completes, both `fetchDataRecords` and
`getAllCookies` report cookies on A and the readback finds the
fixture value. The gate declares A present and invalidates its
handles before releasing its views.

| Observation | Result in both iOS runs |
| --- | --- |
| A1 and A2 | Both handles became inactive before either view was removed and released. The weak references to both views were empty by the end of measurement. |
| A3 and A4 | A3 completed the inspection without a guest load. A4 was refused before inspection and before any load. |
| B1 | Its original view stayed attached. Its document token stayed the same and its JavaScript counter advanced without reloading. Its follow-up inspection completed under deny and both cookie sources reported empty. |
| A data | A host-owned witness on the original identified store read the IndexedDB marker. The two native sources still reported the test cookie after retirement. |

Only the three initially admitted guest documents reached the loader.
Both original reports pass with their archived sources. Their ordered
events match both Android runs when cleanup is expressed as iOS view release or Android
view destruction. Each platform used its accepted native cookie
inspection. The iOS build, signing check and both host tests passed.
The fixture app and owned simulator stopped after collection.
[First iOS report](../experiments/native-cookie-paths-probe/profile-retirement-ios/results/ios-profile-retirement.json),
[Repeat iOS report](../experiments/native-cookie-paths-probe/profile-retirement-ios/results/ios-profile-retirement-repeat.json),
[Paired Android evidence](android-profile-retirement-verification.md)

## Review follow-up

Retained-report verification now requires both weak references to clear.
The capture command records the observed lifetime for later review.
A host regression uses a copy with a live weak reference and confirms that
it fails the stricter check. The original reports replay against their
bundled source archive.

The gate now calls the same Swift cookie presence function exercised by
the host tests. Missing policy or cookie evidence and disagreement
produce `unknown`. The fixture JavaScript generates its document token
when the page executes. A host test runs the same script in two document
contexts with identical inputs and observes distinct tokens.

Both reviewed iOS collections passed the stricter check. The six initial
documents have distinct tokens, and each B1 retains its original token
and advances its counter after A retires. The observed order still
matches the paired Android runs. The reviewed app build and signature
passed and the owned simulator stopped.
[Reviewed report](../experiments/native-cookie-paths-probe/profile-retirement-ios/results/ios-profile-retirement-review.json),
[Reviewed repeat](../experiments/native-cookie-paths-probe/profile-retirement-ios/results/ios-profile-retirement-review-repeat.json),
[Original report replay](../experiments/native-cookie-paths-probe/profile-retirement-ios/README.md#replay-the-original-reports)

## Remaining evidence

Both measured configurations now have evidence of the reaction to a
present-cookie recheck with live views. Writer exclusion during the
admission interval, the remaining C10 locality controls, and the T31
pending-call contract stay open. The measurements use the fixture's
local admission gate and direct JavaScript observations.
[C10 conformance plan](native-cookie-http-conformance-plan.md#c10--suppression-locality)
