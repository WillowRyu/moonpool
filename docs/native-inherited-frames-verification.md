# T28 C09 inherited frames with an explicit frame source

2026-11-25. This follow-up uses the exact-origin `frame-src` candidate on
Android 17 (API 37, WebView 145.0.7632.218, AndroidX WebKit 1.14.0) and
an iPhone 17 Pro simulator running iOS 26.4.1 (Xcode 26.4.1, 17E202,
iPhoneSimulator 26.4 SDK). It concerns SPEC §8 and §9.
[Explicit frame-source evidence](ios-local-document-frames-verification.md#explicit-frame-source-follow-up)

## Fixture

The guarded loader serves the literal app origin in `frame-src` and
`worker-src 'none'`. The control uses the same scripts without the
header. Each mode uses a fresh cookie-denied store and each case opens
its own parent WebView. For the initial `about:blank` case, the parent
attaches an iframe with both navigation attributes absent and inserts the
script in its initial document. The `srcdoc` case supplies the same child
script through the iframe's `srcdoc` attribute. The loader serves the
parent HTML and its script, and the engine constructs the child document.
[HTML iframe creation](https://html.spec.whatwg.org/multipage/iframe-embed-object.html#the-iframe-element),
[CSP inheritance](https://www.w3.org/TR/CSP3/#csp-inheriting-to-avoid-bypasses)

The parent records the child's actual URL, origin and DOM message
origin. It keeps worker results and trusted CSP events as separate
observations through the 6.5-second window. Native loader receipts
verify that each positive worker control loaded `/worker.js`.

## Measured results

| Case | Control | Guarded |
| --- | --- | --- |
| Initial `about:blank` | The child starts with the parent origin and its worker returns the marker. The loader serves the worker script once. | The child starts with the parent origin. A trusted enforcing `worker-src` event identifies `/worker.js`, and the worker reports rejection. The loader records zero worker requests. |
| `about:srcdoc` | The child starts with the parent origin and its worker returns the marker. The loader serves the worker script once. | The child starts with the parent origin. A trusted enforcing `worker-src` event identifies `/worker.js`, and the worker reports rejection. The loader records zero worker requests. |

These outcomes hold in both runs on each platform. All children report
a secure context. Android exposes the service-worker registration method
and iOS records it as unavailable in the tested `moonpool://` context.
These fields record API exposure. The earlier Android experiment measured
registration behavior using its worker-only header.
[Earlier Android worker-context results](native-worker-contexts-verification.md)

The review follow-up verifies each platform's retained reports as a pair.
Android checks four distinct profile names, distinct run tags, a matching
valid APK digest, and matching SDK, OS and WebView versions. Both retained
checks require the observed secure-context and registration method values
for each child. Exploratory runs record the capability values they observe.
The retained checks use the original native build inputs in the shared
source archive.
[Android replay](../experiments/native-cookie-paths-probe/local-document-frames/README.md#verify-the-inherited-frame-reports),
[iOS replay](../experiments/native-cookie-paths-probe/local-document-frames-ios/README.md#verify-the-inherited-frame-reports)

One additional Android collection reports a worker rejection in the
initial `about:blank` control after one worker script receipt, with zero
worker CSP events. The strict verifier rejects that collection. A fresh
run of the same APK passes the control. The failed control and its other
frame observations are retained together.
[Android control diagnostic](../experiments/native-cookie-paths-probe/local-document-frames/results/android-inherited-document-frames-control-refused.json)

Each platform also checks the default document set on the same artifact.
The guarded ordinary frame starts with its worker blocked, and both
the `blob:` and `data:` frames report enforcing frame refusals.
[Android local frame recheck](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-recheck.json),
[iOS local frame recheck](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-local-document-frames-recheck.json)

The explicit frame source preserves these two inherited child documents
with dedicated-worker enforcement. C09 coverage remains open for other
document and browser paths, previously used stores, and the production
owner boundary.
[C09 conformance matrix](native-cookie-http-conformance-plan.md#c09--browser-paths)

[Android report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-inherited-document-frames.json),
[Android repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-inherited-document-frames-repeat.json),
[iOS report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-inherited-document-frames.json),
[iOS repeat](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-inherited-document-frames-repeat.json)

## Later navigation to about:blank

2026-11-25. The same Android and iOS configurations ran two fresh
collections each with the explicit frame source. The parent first loads
an ordinary same-origin `/before-blank` document. The loader records its
response without CSP and the parent checks its DOM marker. The parent
then assigns `about:blank` to the same iframe. The fixture inserts the
probe script only after observing the new URL and a different `Document`
object from the marked page.
[HTML iframe navigation](https://html.spec.whatwg.org/multipage/iframe-embed-object.html#the-iframe-element),
[CSP inheritance](https://www.w3.org/TR/CSP3/#csp-inheriting-to-avoid-bypasses)

Each run records this sequence in the control and guarded groups.

| Observation | Control | Guarded |
| --- | --- | --- |
| Replacement document | `about:blank` starts with the parent origin. | `about:blank` starts with the parent origin. |
| Dedicated worker | The worker returns the marker after one native script receipt. | An enforcing `worker-src` event identifies `/worker.js`. The child reports worker rejection and the loader records zero worker script receipts. |

The guarded parent is the only served document carrying CSP for this
case. Its `frame-src` names the app origin and its `worker-src` forbids
workers. The verifier requires the earlier response, the actual
replacement sequence and the separate worker observations. It also
checks two distinct runs with matching artifact and runtime evidence on
each platform. Both child contexts report `secureContext` as true in the
retained runs. The registration method is available on Android and
unavailable in the tested iOS custom-scheme context.
[Android report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-blank-navigation.json),
[Android repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-blank-navigation-repeat.json),
[iOS report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-blank-navigation.json),
[iOS repeat](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-blank-navigation-repeat.json)

Both artifacts also reproduce the initial `about:blank` and `srcdoc`
results with the `inherited` document set.
[Android inherited-frame recheck](../experiments/native-cookie-paths-probe/local-document-frames/results/android-inherited-document-frames-recheck.json),
[iOS inherited-frame recheck](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-inherited-document-frames-recheck.json)

This concerns SPEC §8 and §9 and covers a parent-initiated navigation
to `about:blank` after a served child. The remaining document paths and
existing-store admission stay open in C09.

### Navigation review fixes

The probe gives the two document loads a bounded 6.5-second navigation
window. Once it confirms the replacement, it inserts the probe script
and observes the child for a separate 6.5 seconds. A virtual-clock test
replaces the document after 2.5 seconds and delivers the worker marker
4.2 seconds later. The parent retains that response. A separate test
verifies cleanup when the replacement misses the navigation deadline.

Both validators require the control's `/worker.js` receipt to follow
`/before-blank`. They reject copies of the original reports with those
requests reversed. The original reports pass with their archived build
inputs.
[Android archived replay](../experiments/native-cookie-paths-probe/local-document-frames/README.md#replay-the-earlier-navigation-reports),
[iOS archived replay](../experiments/native-cookie-paths-probe/local-document-frames-ios/README.md#replay-the-earlier-navigation-reports)

Two fresh runs per platform pass with the revised script. Both replace
the document, receive the control worker marker after the earlier
document receipt, and record an enforcing worker event in the guarded
case with zero worker script receipts. The initial `about:blank` and
`srcdoc` rechecks also pass with the same native artifacts.
[Android reviewed report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-blank-navigation-review.json),
[Android reviewed repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-blank-navigation-review-repeat.json),
[iOS reviewed report](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-blank-navigation-review.json),
[iOS reviewed repeat](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-blank-navigation-review-repeat.json),
[Android inherited-frame recheck](../experiments/native-cookie-paths-probe/local-document-frames/results/android-inherited-document-frames-review-recheck.json),
[iOS inherited-frame recheck](../experiments/native-cookie-paths-probe/local-document-frames-ios/results/ios-inherited-document-frames-review-recheck.json)
