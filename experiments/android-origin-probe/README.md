# T23 Android origin probe

Experimental platform research, not a Moonpool native SDK or bridge. The pure
TypeScript packages and SPEC are unchanged. No host credentials or capability
dispatcher are installed in these WebViews. Java is used only for this small
platform harness, not as a replacement kernel.

## Observation criteria recorded before implementation

Use the T22 [P01–P10 checklist](../../docs/native-target-matrix.md). Run fixed
app ids com.example.probe.a/b under these separately labeled profiles:

- asset-loader-custom: pass moonpool URLs to the unmodified official
  WebViewAssetLoader. Record unsupported loading rather than assume success.
- intercept-custom: return bundled bytes for moonpool URLs through the public
  WebViewClient request interceptor. Observe actual browser origin, storage,
  fetch and cross-app access; delivery of bytes alone does not pass SPEC §8.
- https-control: use the official loader with fixed A/B .test domains as local
  intercepted controls. These domains never go to the internet. This is not
  approval to replace the normative production scheme.

Required observations: valid JS/CSS/image resources and self access; A/B origin
and storage access (localStorage, IndexedDB, cookies individually); same-app
sharing; reload/view/process recreation; cross-app DOM access with a loaded
positive control; same/foreign/external navigation; missing/wrong-app/escape
paths and network fallthrough; self/cross-app/loopback fetch and Origin header.
Keep raw callbacks and errors as well as the positive results. Every case starts
as not-run. Unsupported/custom-origin behavior is research evidence, not a test
to be made green by changing SPEC or disabling WebView protections.

The loopback fixture serves only public marker data and logs Origin headers.
Native-owned evaluateJavascript polling collects guest observations; it is not
sender authentication or a guest-callable bridge. T25 studies that separately.
Unknown hosts are blocked locally, except the explicit loopback fixture. The
navigation harness deliberately observes movement without granting capabilities.

## Pinned experiment tools

Gradle 9.6.1, AGP 9.3.1, JDK 21 (Studio bundled), compile/target SDK 36,
Build-Tools 36.0.0, AndroidX WebKit 1.14.0. The probe's minSdk 31 is a build
setting only, not a product support commitment. Tested device details and
actual results will be recorded after execution.

The existing API 37 ARM64 / 16KB AVD is used without wiping data. Only this
probe app's own public marker keys and files are touched. No SDK/image upgrade
or global shell configuration change is part of T23.

## Execution

Build with the pinned wrapper, start the existing AVD, start fixture_server.py
bound to 127.0.0.1:8877, and add an adb reverse for that port. Install the debug
APK only on the selected emulator. Launch ProbeActivity with profile and phase
extras; export its private report.json with adb run-as. Detailed repeatable
commands and pass/fail findings belong in the final T23 verification report.

Generated build/cache/local settings and raw local logs are ignored. Retained
results must omit device serials, personal paths and unrelated system logs.

The host-side HTTP controls now use experiments/probe_support with the iOS
Adapter. Run pnpm run test:probes from the repository root for simulator-free
HTTP regression checks. Native sources, APK fingerprints and measured results
are preserved; host tests are not a fresh emulator measurement.

## Measured outcome

See the [T23 verification report](../../docs/android-origin-probe-verification.md)
for exact versions, commands, retained results and scope. The official loader
rejects moonpool URLs; the public interceptor can display them but A/B origins,
DOM and storage collapse in the tested WebView. HTTPS controls stay isolated.
This finding completes research, not a compliant native loader. The verifier
expects six online seed/restart records and one HTTPS restart record with the
loopback server stopped. It checks 344 controls while retaining the incompatibility.
