# T28 C09 redirect and retained service-worker verification

2026-11-16. The follow-up ran on the owned Android 17 / WebView 145.0.7632.218
emulator and then on the iOS 26.4.1 simulator. It covers the isolated loader
configuration and the two browser engines observed here. This concerns
SPEC §8 and §9.
[Probe instructions](../experiments/native-cookie-paths-probe/follow-up/README.md)

## Static redirects

The earlier C09 pair logged six requests to a denied path after a same-host
302. In the follow-up the browser requests a local image name. The native
loader resolves that name to a registered HTTPS URL and disables automatic
redirects. It checks the next origin and exact encoded path before it
issues each request. It passes the image bytes back with the local URL.
[Earlier server receipts](native-cookie-paths-verification.md#same-host-redirect-reached-the-denied-path),
[Loader decision](adr/0029-check-static-resource-redirects-in-the-native-probe.md)

| Redirect case | Android | iOS |
| --- | --- | --- |
| Direct approved image | Loaded | Loaded |
| Approved relative redirect to `/static/final.gif` | Loaded after both requests | Loaded after both requests |
| Same-host redirect to `/denied` | Zero target receipts | Zero target receipts |
| Redirect to another hostname | Zero target receipts | Zero target receipts |
| Redirect to encoded alias `/static/%66inal.gif` | Zero target receipts | Zero target receipts |

The independent server records six image-stage requests per platform. Every
request carries an empty Cookie header and no Authorization. The image and
redirect responses carry fixture Set-Cookie instructions. The browser reads
an empty cookie string and native inventory remains empty. The earlier
failing pair stays available as evidence of the initial-resource boundary.

## Retained registration on Android

The seed view installs a real service worker associated with the selected
profile and its synthetic HTTPS origin. The worker caches a test HTML entry
and performs a control fetch that reaches the fixture. Then the seed view
is destroyed and the profile's worker network loading is disabled.

In a diagnostic WebView on the same profile and origin, the retained
registration supplies the cached HTML. Its script runs and its network probe
is rejected, with zero receipts for that blocked fetch. The native entry
loader reports zero calls. A separate candidate admission with that known
retained worker is refused before any guest load. The registration and cache
remain in the owned store.
[Android profile service-worker controller](https://developer.android.com/reference/androidx/webkit/Profile#getServiceWorkerController())

The iOS image page reports that the service-worker API is unavailable in
the tested `moonpool://` context. The Android observation concerns
recreation within the same native process. A trusted way to establish
worker absence for arbitrary existing stores and production loader
integration remain C09 gates.
[Android pre-admission follow-up](native-worker-admission-verification.md)

## Verification and cleanup

The strict checker reports zero failures, with seven Android and six iOS
HTTPS receipts. Android's extra receipt is the worker network control.
The 11 host tests cover fixture framing, exact receipts, and refusal and
unsupported-capability evidence. The fixture uses HTTP/1.1 framing for
successive requests. Android's collector waits for activity launch before
polling. Both builds pass, including Android lint and the iOS signature check.

The session-owned Android emulator stopped before iOS started. Both owned
devices and the HTTPS fixture are stopped. The fixture private keys were
retired to the local Trash. App-scoped TLS anchors preserved certificate and
host validation in the native clients.
[Android report](../experiments/native-cookie-paths-probe/follow-up/results/android-c09-paired.json),
[iOS report](../experiments/native-cookie-paths-probe/follow-up/results/ios-c09-paired.json)
