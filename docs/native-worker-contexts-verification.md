# T28 C09 worker policy in Android inherited documents

2026-11-24. Two fresh collections used the same APK on Android 17
(API 37), WebView 145.0.7632.218 and AndroidX WebKit 1.14.0. This
probe concerns SPEC §8 and §9.
[Probe commands](../experiments/native-cookie-paths-probe/worker-contexts/README.md)

The native loader serves the entry with `worker-src 'none'` only
in the guarded profile. The entry creates an initial `about:blank`
iframe and a `srcdoc` iframe. Neither child has a loader response.
Each context executes its own worker calls and reports its own URL,
origin and CSP events. The control uses the same code and a separate
fresh profile and synthetic HTTPS origin. This exercises the policy
inheritance described by CSP and HTML.
[CSP inheritance](https://www.w3.org/TR/CSP3/#csp-inheriting-to-avoid-bypasses),
[HTML policy containers](https://html.spec.whatwg.org/multipage/browsers.html#policy-containers)

## Repeated measurements

Both collections show the following outcomes. Each child reports the
entry's exact origin and a secure context.

| Document | Control | Guarded |
| --- | --- | --- |
| Loader entry | Dedicated worker ran and service worker activated | Enforcing `worker-src` event for each script |
| Initial `about:blank` | Dedicated worker ran. Service-worker registration rejected with `InvalidStateError`. | Enforcing `worker-src` event for the dedicated worker. Service-worker registration again rejected with `InvalidStateError`. |
| `about:srcdoc` | Dedicated worker ran and service worker activated | Enforcing `worker-src` event for each script |

The guarded profiles received zero worker-script requests at the
loader and their top-level registration inventories were empty. The
initial `about:blank` service-worker call has no positive control
and no service-worker CSP event in this fixture. Its dedicated-worker
result establishes inheritance for that document.

Both retained verifiers pass and report the missing service-worker
control explicitly. Android assemble and lint passed. The collector
stopped its app and the dedicated emulator was shut down.
[First report](../experiments/native-cookie-paths-probe/worker-contexts/results/android-worker-contexts.json),
[Repeat report](../experiments/native-cookie-paths-probe/worker-contexts/results/android-worker-contexts-repeat.json)

## Remaining evidence

The measurement covers these frame creation paths and one WebView
configuration. An eligibility rule for production still requires
coverage for every executable document the loader permits and evidence
of exclusive profile ownership. AndroidX exposes named profile
enumeration and assignment to a WebView. From those APIs, name binding
establishes which profile a view uses, while the SDK and host still
have to establish which native components can use it. C09 remains open.
[AndroidX ProfileStore](https://developer.android.com/reference/androidx/webkit/ProfileStore),
[AndroidX WebViewCompat](https://developer.android.com/reference/androidx/webkit/WebViewCompat),
[Earlier admission evidence](native-worker-prevention-verification.md),
[Android ownership follow-up](android-profile-ownership-verification.md)

The paired follow-up measures dedicated workers in both inherited frames
on Android and iOS with the explicit frame source and separate parents.
[Paired inherited frame evidence](native-inherited-frames-verification.md)
