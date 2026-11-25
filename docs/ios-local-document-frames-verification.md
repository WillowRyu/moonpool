# T28 C09 iOS local generated frames

2026-11-25. Two collections used the same signed app on the dedicated
iPhone 17 Pro simulator running iOS 26.4.1 with Xcode 26.4.1 (17E202)
and the iPhoneSimulator 26.4 SDK. The experiment concerns SPEC §8 and §9.
[Fixture and commands](../experiments/native-cookie-paths-probe/local-document-frames-ios/README.md)

## Fixture

The fixture serves the reviewed Android probe's scripts through a
`WKURLSchemeHandler` at an exact local `moonpool://` origin. Each mode
gets a fresh persistent store, and each frame case gets its own parent
`WKWebView` and `/entry/{kind}` document. The fixture first creates a
never-loaded nonpersistent WebView, then sets cookie deny on the
identified store, reads back the policy, and checks both native cookie
sources before starting any fixture document.
[Apple cookie store API](https://developer.apple.com/documentation/webkit/wkhttpcookiestore)

The guarded loader supplies the same CSP response header as the Android
probe. The parent listens for trusted enforcing frame events and
records the child's ready message separately from its worker result.
The parent reads the sender's DOM `MessageEvent.origin`. Native loader
receipts independently record each served script. Each parent observes
its single frame for the full 6.5-second window.
[CSP frame sources](https://www.w3.org/TR/CSP3/#directive-frame-src),
[CSP worker sources](https://www.w3.org/TR/CSP3/#directive-worker-src)

## Results

| Document | Control in both runs | Guarded in both runs |
| --- | --- | --- |
| Regular same-origin frame | The child starts at the parent origin. The worker returns its marker and the native loader serves `/worker.js` once. | The child starts at the parent origin. An enforcing `worker-src` event identifies `/worker.js`. The native loader serves no worker script. |
| `blob:` frame | The generated child starts at the parent origin. Its worker returns the marker with one native loader receipt. | The generated child starts at the parent origin. An enforcing `worker-src` event identifies `/worker.js`. The native loader serves no worker script. |
| `data:` frame | The generated child starts. Its document and message origins both serialize as `null`. | An enforcing `frame-src` event identifies `data`. The child sends no ready message. |

The iOS `moonpool://` configuration allows the same-origin `blob:`
document through `frame-src 'self'`. The tested Android synthetic HTTPS
configuration refuses that frame. Both configurations refuse the
guarded `data:` frame and allow the ordinary same-origin frame to start
while blocking its worker. These results cover the tested loader and
engine configurations. The generated-document policy for C09 remains
open, along with the remaining browser-path checks, locality controls,
and production writer ownership.
[Paired Android evidence](android-local-document-frames-verification.md),
[C09 conformance matrix](native-cookie-http-conformance-plan.md#c09--browser-paths)

The verifier pins the iOS `blob:` start, both positive worker controls
and their individual receipts, the enforcing worker refusals, and the
isolated `data:` refusal. The two reports carry the source fingerprints
and the digest of the installed app. The fixture app stopped and the
owned simulator shut down after collection.
[First iOS report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames.json),
[Repeat iOS report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-repeat.json)

## Review follow-up

The shared script now sends the dedicated worker result and each
`worker-src` event independently. The parent keeps both through its
6.5-second observation window and records the DOM origin of each
message. A JavaScript regression delivers the enforcement event 350 ms
after the worker rejection and checks that both reach the report. The
retained checks accept either delivery order within the frame window.

Paired iOS verification checks both reports together. It requires
distinct run tags, four distinct identified stores, equal verified
installed app digests, and matching runtime, device type, OS release,
Xcode and SDK. The verifier pins `data` as the scheme on the enforcing
frame event. The regression tests vary the native URL, document URL,
store binding, child start, worker result and worker event independently.

The follow-up reports use the same simulator configuration and repeat
the frame and worker outcomes above with separate worker events. The
earlier reports retain their exact verifier and source provenance.
[Follow-up report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-worker-events.json),
[Follow-up repeat](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-worker-events-repeat.json),
[Earlier report replay](../experiments/native-cookie-paths-probe/local-document-frames-ios/README.md#replay-the-earlier-reports)

## Explicit frame source follow-up

The guarded fixture selects the app's literal origin as the `frame-src`
source expression. The iOS loader uses its `moonpool://` origin and the
Android loader uses its synthetic HTTPS origin. The worker and script
directives, local scripts, and isolated parent documents follow the
previous fixture. Both control workers must return their markers and
have one native script receipt each. The Android verifier also checks
the boolean trust flag on the browser events.
[CSP frame sources](https://www.w3.org/TR/CSP3/#directive-frame-src)

| Guarded frame | iOS 26.4.1 | Android 17 and WebView 145.0.7632.218 |
| --- | --- | --- |
| Ordinary same-origin frame | The child starts and reports a worker rejection with an enforcing `worker-src` event. | The child starts and reports a worker rejection with an enforcing `worker-src` event. |
| `blob:` frame | An enforcing `frame-src` event identifies `blob`. The child sends no ready message. | An enforcing `frame-src` event identifies `blob`. The child sends no ready message. |
| `data:` frame | An enforcing `frame-src` event identifies `data`. The child sends no ready message. | An enforcing `frame-src` event with a redacted scheme occurs in the isolated `data:` case. The child sends no ready message. |

The initial Android collection recorded a rejected worker in the `blob:`
control despite a worker script receipt and an empty worker violation list.
The verifier refused that collection. Two fresh runs of the same APK
passed both control workers and the guarded frame checks. The first run
retains its guarded observations in the diagnostic report.
[Android control diagnostic](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-explicit-origin-control-refused.json)

Two iOS runs with the explicit origin pass paired verification. A third
run uses the same signed app and simulator with `frame-src 'self'`.
Its guarded `blob:` frame reports a ready message and an enforcing
worker refusal. The explicit origin runs record a frame refusal with
zero child starts. All three runs use separate identified stores.
[iOS same-app self comparison](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-explicit-origin-self.json)

The explicit-origin runs cover the tested local frame paths under SPEC
§8 and §9. The common generated-document policy and remaining C09
browser paths stay open for the production design.
[iOS explicit source report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-explicit-origin.json),
[iOS repeat](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-explicit-origin-repeat.json),
[Android explicit source report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-explicit-origin.json),
[Android repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-explicit-origin-repeat.json)
