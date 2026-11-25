# T28 C09 Android local generated frames

2026-11-24. Two runs used the same APK on the dedicated Android 17
(API 37) emulator, WebView 145.0.7632.218, and AndroidX WebKit 1.14.0.
The experiment concerns SPEC §8 and §9.
[Fixture and commands](../experiments/native-cookie-paths-probe/local-document-frames/README.md)

## Measured frame behavior

The native loader compares an unguarded control and a guarded profile
with the same script and local resource paths. The guarded loader
serves `frame-src 'self'` and `worker-src 'none'`. The fixture uses
the regular same-origin frame as a positive document control. It
records each child's script result and DOM `MessageEvent.origin` as
observed by the parent document. Worker scripts served by the native
loader provide a separate resource witness for the regular and blob
documents.
[CSP frame sources](https://www.w3.org/TR/CSP3/#directive-frame-src),
[CSP worker sources](https://www.w3.org/TR/CSP3/#directive-worker-src)

| Document | Control in each run | Guarded in each run |
| --- | --- | --- |
| Regular same-origin frame | The document reports the parent origin and its dedicated worker runs. | The document runs. An enforcing `worker-src` event identifies the worker script. The loader serves no worker script. |
| `blob:` frame | The generated document reports the parent origin and its dedicated worker runs. | An enforcing `frame-src` event identifies the blob scheme. The document gives no script result. |
| `data:` frame | The generated document runs and the message origin is opaque. | An enforcing `frame-src` event occurs during the isolated data-frame navigation. The document gives no script result. |

The initial parallel-frame diagnostic saw a data-frame refusal with a
redacted address in the WebView log and could not attribute that event
with the original verifier. The initial retained fixture attaches and
detaches one frame at a time in the same parent document. Those reports
record the enforced `frame-src` event during the data-frame window with
an absent scheme. The review follow-up isolates each frame in its own
parent document.
The control confirms the matching opaque document can execute in this
fixture when the frame policy is absent.

Both original reports replay against their archived sources. Android
assemble and lint and the three original host tests passed. The fixture
app stopped and the owned emulator shut down.
[First Android report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames.json),
[Repeat Android report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-repeat.json)

## Review follow-up

The reviewed fixture creates a fresh parent WebView and a distinct
`/entry/{kind}` document for each of the three frame cases. Each parent
starts a single frame navigation. It records all trusted or untrusted
frame-policy observations in the bounded window, along with the parent
URL read in native code and in the document. The verifier requires
an enforcing browser event for a refusal. The redacted data-frame
event is now observed in a parent that has exercised only that frame.

The child sends a ready message as its first action and reports its
worker result separately. The parent retains DOM message origins and
both observation types through the full window. The retained-report
check pins the blob frame refusal and one worker-script receipt for
each of the two control worker frames.

The reviewed APK passed twice on the same emulator and WebView version.
Both guarded generated frames report an enforcing event and zero child
starts. The ordinary guarded frame reports a child start and the
worker-policy rejection separately. The control loader receives one
worker script for each of the regular and blob control frames.
[Reviewed report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-review.json),
[Reviewed repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-review-repeat.json),
[Original report replay](../experiments/native-cookie-paths-probe/local-document-frames/README.md#replay-the-original-reports)

## Shared worker event follow-up

The shared script forwards the worker CSP event separately from the
worker result. The parent records both within its single-frame window.
The guarded ordinary frame reports a rejection and an enforcing worker
event. The guarded `blob:` and `data:` frame refusals and both control
worker receipts still verify. The initial and first reviewed reports
remain replayable against their respective source archives.
[Follow-up report](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-worker-events.json),
[Follow-up repeat](../experiments/native-cookie-paths-probe/local-document-frames/results/android-local-document-frames-worker-events-repeat.json),
[Earlier reviewed report replay](../experiments/native-cookie-paths-probe/local-document-frames/README.md#replay-the-reviewed-reports)

## Boolean trust and explicit frame source

The Android verifier requires the `trusted` field on a frame or worker
CSP event to be the JSON boolean `true`. The earlier worker event reports
pass the current check using their archived build inputs. Substituting
numeric `1` for either trust field in a copy of those reports fails.
[Worker event report replay](../experiments/native-cookie-paths-probe/local-document-frames/README.md#replay-the-worker-event-reports)

With the explicit synthetic HTTPS origin in `frame-src`, the guarded
ordinary frame starts and its worker is refused. The guarded `blob:` and
`data:` frames report enforcing CSP events and zero child starts. The
`data:` event's URL scheme is redacted in this configuration. This is
the same frame outcome reported by the explicit-origin iOS fixture.
[Paired explicit source evidence](ios-local-document-frames-verification.md#explicit-frame-source-follow-up)

## Remaining evidence

The result covers this Android WebView version and these three frame
creation paths with the tested header. The paired iOS fixture observes a
same-origin `blob:` start under the header and an enforcing worker
refusal inside it. The generated-document policy, other allowed document
paths and production writer exclusion remain open.
[Paired iOS evidence](ios-local-document-frames-verification.md),
[Earlier inherited-frame evidence](native-worker-contexts-verification.md),
[C09 conformance matrix](native-cookie-http-conformance-plan.md#c09--browser-paths)
