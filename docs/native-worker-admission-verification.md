# T28 C09 Android worker evidence before guest load

2026-11-17. The Android 17 / API 37 emulator ran WebView 145.0.7632.218
with AndroidX WebKit 1.14.0. The probe evaluated host-supplied inspection
HTML as a way to read registrations before loading a guest. Both
inspection contexts rejected the enumeration in the tested configuration.
This concerns SPEC §8 and §9.
[Probe instructions](../experiments/native-cookie-paths-probe/worker-admission/README.md),
[Earlier retained-worker result](native-cookie-paths-follow-up-verification.md#retained-registration-on-android)

## Cold-process results

The seed process writes an IndexedDB marker in three owned profiles and
activates the configured root or off-path registration where applicable.
Each of the five checks then runs in its own app process. It opens the named
profile, disables engine cookies and worker network requests, verifies
policy readback, and loads fixed HTML from native with browser network
requests blocked. The HTML carries a native-generated nonce and receives
the expected origin when given an HTTPS base. The checker verifies that
zero requests for an inspection document reach the resource interceptor.

| Case | Inline `getRegistrations()` | Same-origin `srcdoc` child | Admission |
| --- | --- | --- | --- |
| Existing root worker | `InvalidStateError` | `InvalidStateError` | Unknown, zero guest loads |
| Existing off-path worker | `InvalidStateError` | `InvalidStateError` | Unknown, zero guest loads |
| Previously used profile with a data marker and zero seeded workers | `InvalidStateError` | `InvalidStateError` | Unknown, zero guest loads |
| Fresh profile | `InvalidStateError` | `InvalidStateError` | Unknown, zero guest loads |
| Opaque base origin | API unavailable | Skipped | Unknown, zero guest loads |

The IndexedDB marker is present on all three existing HTTPS profiles.
The fresh-profile read finds no fixture database. A rejected query
leaves the result field empty and carries an error. The native gate
requires valid origin, nonce and successful query evidence for an empty
verdict. Thus none of those empty arrays authorize a load.
[Retained Android report](../experiments/native-cookie-paths-probe/worker-admission/results/android-worker-admission.json)

The Android API documents origin assignment by the HTTPS base URL.
Chromium's current source loads host-supplied bytes through a synthetic
data URL for that API. Service Worker registration enumeration depends on
the service-worker client's storage key. The origin readback alone did
not establish that the observed document could enumerate that key.
[Android WebView](https://developer.android.com/reference/android/webkit/WebView#loadDataWithBaseURL(java.lang.String,%20java.lang.String,%20java.lang.String,%20java.lang.String,%20java.lang.String)),
[Chromium load path](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/android_webview/java/src/org/chromium/android_webview/AwContents.java),
[Service Worker enumeration](https://w3c.github.io/ServiceWorker/#service-worker-container-getregistrations)

## Scripts-disabled navigation still used the old worker

After refusal, the diagnostic views issue an ordinary navigation on the
owned retained profile, with the page's JavaScript disabled and the worker's
network blocked. Both scopes return the worker's cached document title,
including after the app-process restart. The root view's native evaluation
does not return its test nonce with scripts disabled. Ordinary navigation
has already invoked a worker by the time its cached document is visible.

## Verification and next decision

The host suite passes ten tests. Android assemble and lint pass. The
unavailable-observation verifier reports five inspections and zero evidence
failures. The worker-evidence hypothesis verifier returns 1 because no
valid list was obtained. The earlier direct-only and comparison runs remain
in local results. The owned emulator is stopped.

C09 stays open for trusted worker-absence evidence on existing stores.
The tested paths produce an unknown result under the accepted admission
baseline. The open design question is which native evidence or verified
ownership history can establish eligibility before guest execution.
The existing profile, fixture database and retained registrations are
preserved. Production loader integration remains T38/T39 work.
