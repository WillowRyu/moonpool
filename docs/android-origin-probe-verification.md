# T23 — Android origin/local-content verification

Date: 2026-10-27 (Asia/Seoul)
Status: Research complete for the recorded configuration; required native-origin
isolation failed. This is not native SDK conformance or an approved scheme change.
Baseline: db8d6ed (T22 published). Git publication of T23 was requested on 2026-10-27.

## Result and consequence

On this Android WebView, delivering bytes at moonpool://com.example.probe.a/
and moonpool://com.example.probe.b/ does not create two isolated app origins.
The public request interceptor can load HTML/JS/CSS/images, but both pages
report location.origin as moonpool://. The server-observed Origin header and
frame-message origins also omit the app host. A can read B's loaded frame DOM;
localStorage and IndexedDB markers collide. Cookies remain empty and fetch of
bundled custom-scheme JSON fails. SPEC §8 / §9.1 cannot be claimed for this setup.

The unmodified WebViewAssetLoader does not accept moonpool URLs at all. The
separate HTTPS control loads the same assets and demonstrates distinct A/B
origins, storage partitioning, cross-frame DOM denial and normal self-access.
This control is research evidence, not permission to replace the normative
production scheme. No SPEC, protocol, pure kernel or shipped browser API changed.
T24 must obtain independent iOS evidence; T28 resolves the native-origin/loader
contract with an explicit approved ADR/SPEC decision before native SDK loaders.
Native message authentication remains T25/T26.

## Recorded environment and scope

| Item | Measured / pinned value |
| --- | --- |
| Host | macOS 26.6.2 arm64; existing Pixel 7 Pro AVD, no data wipe |
| Emulator | 36.6.11.0; API 37, Android 17, build CP21.260330.012, arm64-v8a |
| Actual page size | getconf PAGE_SIZE → 16384 |
| Actual WebView | com.google.android.webview 145.0.7632.218, targetSdk 36 |
| Build | Gradle 9.6.1, AGP 9.3.1, Studio JDK 21.0.10, Build-Tools 36.0.0 |
| Probe app | org.moonpool.originprobe; compile/target SDK 36, minSdk 31; debug APK |
| AndroidX | androidx.webkit:webkit:1.14.0 |
| Fixture network | Host loopback 127.0.0.1:8877 via selected emulator's adb reverse |
| Native access | No Moonpool bridge, dispatcher, providers, credentials or JavascriptInterface |

The probe uses ordinary WebView, WebViewClient.shouldInterceptRequest and
WebViewAssetLoader APIs without private engine switches, file:// loading or
certificate bypass. Java is only a standalone platform harness. Its native-owned
evaluateJavascript polling gathers diagnostics; page values never grant native
authority and are not authenticated sender metadata. This does not choose the
trusted TypeScript host runtime or final host framework.

Both control hosts end in .test and are intercepted locally. Unknown hosts and
unmapped paths receive a harness-local 451 response, preventing internet
fallback. Only the explicit loopback fixture can fall through to the network;
cleartext permission is limited to that address. Request callbacks are recorded.
The harness's fixed app roots/path guards are experimental controls, not the
future production loader or proof that the official loader supplies those guards.

## Evidence matrix

P01–P10 were recorded before probe implementation in
[T22](native-target-matrix.md). Profile-specific limitations remain failures or
unavailable observations, rather than being marked green by a fallback.

| Case | Official loader + moonpool | Public interceptor + moonpool | HTTPS control |
| --- | --- | --- | --- |
| P01 build/boot | App builds/launches; pages fail | App and pages run | App and pages run |
| P02 two app origins | Loader lookup null; unknown-scheme load errors | Both location.origin and observed Origin header are moonpool:// | Distinct https://com.example.probe.a.test and b.test origins |
| P03 bundled assets/fetch | No fixture report before deadline | HTML/JS/CSS/SVG load; fetch of bundled JSON fails | Assets load and same-origin JSON fetch succeeds |
| P04 storage isolation | Unavailable | B reads A's marker, then overwrites the shared localStorage/IndexedDB key; cookies empty | Separate localStorage, IndexedDB and cookie markers |
| P05 lifetime/sharing | Unavailable | Shared data survives reload/view/process recreation; that is persistence without app isolation | Same-app second instance, reload, view recreation and process restart retain the correct app marker |
| P06 loaded frame access | Unavailable | Cross-app frame loads and DOM read succeeds: isolation failure | Self-frame read succeeds; loaded cross-app frame throws SecurityError |
| P07 navigation | Only failed initial loads observed | Same-app, other-app, loopback external and return loads observed | Same matrix observed; no bridge installed, so no containment conformance claimed |
| P08 confinement/fallback | Initial loader miss/error | Custom fetch is unavailable; do not call this a traversal-test pass | Missing file 404, plain/encoded parent-path attempts blocked, unknown app unreadable; explicit loopback network positive control |
| P09 CORS/origin | Unavailable | Loopback CORS response sees Origin: moonpool://; no-CORS fetch denied | Server sees exact A/B origin; CORS-enabled fetch succeeds and missing-CORS fetch fails |
| P10 repetition | Initial load failures repeat after process restart | Collapsed origins/shared storage repeat | Positive/negative controls repeat after process restart |

An additional HTTPS run with the loopback fixture stopped keeps bundled JSON
available and missing/escape paths local, while network fetch/external navigation
fail. This separates genuine local resources from the network positive control.

The seed phase writes only public t23-<profile> marker keys. Before each restart
phase the runner force-stops only the probe package, then starts a new process
without clearing app data. It does not reset the AVD or erase browser/user data.
Cookie/browser persistence observations do not establish storage.* provider
durability, power-loss guarantees or another device's behavior.

Each loaded profile has eleven snapshots: initial A/B, A/B rereads, a second
same-app view, reload, recreated view, same-app navigation, foreign-app navigation,
external navigation and return. The official-loader custom profile retains its
two initial failures. Reports preserve errors, request/navigation callbacks,
public page observations, actual WebView version and the APK SHA-256.

## Reproduction

The [standalone harness](../experiments/android-origin-probe/README.md) is outside
the shipped workspaces. Start a specifically selected existing emulator without
wiping its data. Substitute its actual serial; never select an arbitrary device.

```sh
cd experiments/android-origin-probe
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
  ./gradlew --no-daemon :app:assembleDebug :app:lintDebug
python3 fixture_server.py
```

In another terminal, with the fixture still running:

```sh
adb -s emulator-5560 reverse tcp:8877 tcp:8877
adb -s emulator-5560 install -r app/build/outputs/apk/debug/app-debug.apk
python3 run_probe.py --serial emulator-5560 --profile https-control \
  --phase seed --output local-results/https-control-seed.json
python3 run_probe.py --serial emulator-5560 --profile https-control \
  --phase restart --output local-results/https-control-restart.json
```

Repeat both phases with asset-loader-custom and intercept-custom. The native
runner exports only this app's report through adb run-as, not system logs or
personal device metadata. Run python3 verify_results.py local-results. The
assertions verify the HTTPS positive/negative controls; custom-scheme observations
are retained as incompatibilities, not redefined as a compliant behavior.

Before verification, also stop the loopback fixture and run the https-control
restart command with --output local-results/https-control-offline.json. The
verifier requires that offline record along with all six online phase records.

The retained [results directory](../experiments/android-origin-probe/results/)
contains the measured seed/restart records. Preserve the reports' tested-version
scope; do not generalize this single emulator to every Android release/provider.

## Build and verification notes

The first offline Gradle attempt lacked plugin-marker metadata. Online official
repository resolution produced the pinned build; the later offline build works.
The Android lint tool also required an initial dependency download. No SDK image,
platform upgrade or global Java configuration change was needed. The wrapper
pins the official Gradle distribution SHA-256.

Android lint found a missing includeSubdomains attribute in the loopback network
configuration; the harness now explicitly sets it false. The control verifier
also exposed an image-timing race: the fixture originally read image.complete
before loading finished. It now awaits load/error before recording the result.
Final observations are rerun from the rebuilt APK, not reused from that early
incomplete resource sample.

The debug build and Android lint complete. Lint retains 15 warnings about the
deliberately pinned versions/target, JavaScript-enabled diagnostic WebViews,
backup/icon setup and untranslated diagnostic status text. Gradle reports
deprecations for Gradle 10. No clean-warning or release-readiness claim is made.
Root runtime/SPEC/dependency files remain at the published browser baseline;
normal repository lint and documentation/evidence checks cover the added files.
The final corpus contains 59 snapshots across seven runs from the same APK;
344 control assertions pass. The custom-scheme isolation failures remain visible.

## Primary references

- [WebViewAssetLoader](https://developer.android.com/reference/androidx/webkit/WebViewAssetLoader) and [builder](https://developer.android.com/reference/androidx/webkit/WebViewAssetLoader.Builder): documented HTTP(S) asset loading and host selection; actual custom-scheme behavior is independently recorded above.
- [WebViewClient](https://developer.android.com/reference/android/webkit/WebViewClient): request interception and navigation callbacks; returning null permits normal loading.
- [WebView evaluateJavascript](https://developer.android.com/reference/android/webkit/WebView#evaluateJavascript(java.lang.String,%20android.webkit.ValueCallback)): asynchronous page evaluation on the UI thread; not sender authentication.
- [AGP 9.3 compatibility](https://developer.android.com/build/releases/agp-9-3-0-release-notes): JDK/Gradle/SDK constraints for the selected build.
- [Emulator command line](https://developer.android.com/studio/run/emulator-commandline): installed app/state behavior and startup controls.

T23 completes the bounded research task with a documented incompatibility.
Dependent native SDK origin/loader implementation remains gated on the approved
T28 resolution. No production-scheme alternative is selected in this report.
