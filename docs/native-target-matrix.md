# T22 — Native targets, local toolchain and first-probe checklist

Date: 2026-10-27 (Asia/Seoul)
Status: Complete for T22 inventory/planning; native builds and probes have not run.
Baseline: 10d75d3, browser v0.1 complete; 1131 tests / 39 files previously verified.
Related plan: [T22–T65](native-implementation-plan.md).

## Confirmed requirements and open choices

Android (AOS) and iOS are both required. A host app/page may own multiple Portals
with different app origins; there is no application-wide single-origin limit.
The host framework and real integrating repositories remain undecided, as the
maintainer requested. Minimal probe apps do not choose the final public SDK.

The existing pure TypeScript protocol/client/host kernel remains the shared
authority. All capabilities stay asynchronous, grants/app identity are host
owned, and host credentials stay outside the guest bridge. Native-origin,
message-authentication and navigation work concerns SPEC §8 / §9; this task
records tests for those requirements without changing them.

| Choice | T22 position | Resolution point |
| --- | --- | --- |
| First Android experiment | Existing API 37.0 ARM64 Google APIs / 16KB AVD, provisionally | T23 must boot/build and record the actual OS, provider and page size |
| First iOS experiment | Existing iPhone 17 Pro simulator, iOS 26.4 runtime label / 26.4.1 runtime version, provisionally | T24 must boot/build and record the actual runtime |
| Product minimum Android/iOS versions | Undecided; installed SDK versions are not support commitments | T25–T28 feature/runtime decisions, then T59/T60 device verification |
| Android WebView support | Provider version and runtime feature support still unmeasured | T23 records provider; T25 checks candidate channels |
| iOS WebKit support | Record OS/runtime and API availability; no separate Android-style provider choice assumed | T24/T26 |
| Trusted TypeScript host execution context and framework binding | Undecided; never assume a native app supplies a JS runtime | T27 |
| Production origin | Current SPEC requires moonpool://<mini-app-id>/ | T23/T24 evidence, then approved T28 decision for any conflict |
| AGP / Gradle / AndroidX versions and probe project settings | Not pinned; no Android project exists yet | T23 checks a compatible minimal probe build, T25 records channel dependency |
| Actual app(s), physical devices and release support matrix | Not selected | T56–T61 |

These first experiment candidates reuse installed resources. Their availability
does not prove a successful boot, build, authenticated bridge or supported
production configuration. An additional baseline/lower-version Android image
and iOS runtime remain unselected; they are separate gaps before support claims.

## Local observations

Commands completed on the current Mac. This is an environment inventory, not a
native test result. Personal device names, serials and UDIDs are not retained.

| Area | Observed result | Practical meaning |
| --- | --- | --- |
| Host | macOS 26.6.2, build 25G83, arm64 | Use ARM64 emulator images for this first local experiment |
| Existing JS workspace | Node 22.19.0; pnpm 11.1.3 | Matches the repository's verified workspace toolchain |
| Android Studio | 2025.3; build AI-253.31033.145.2533.15113396 | IDE installed; no project build verified |
| JDKs | Default Zulu 17.0.18; Studio bundled OpenJDK 21.0.10 | Choose the JDK for the eventual pinned Gradle/AGP pair explicitly |
| Android SDK tools | Command-line Tools 20.0; Platform-Tools 37.0.0; Emulator 36.6.11.0 | Inventory commands work; no dependency/tool update performed |
| Installed Android platforms | API 31, 34, 35, 36, 36.1, 37.0 | Compile SDK packages, not evidence that those OS images can boot |
| Installed Android Build-Tools | 35.0.0, 36.0.0, 36.1.0, 37.0.0 | Build version still needs pairing with the probe project |
| Installed Android system images | API 37.0 Google APIs ARM64 / 16KB rev 5; Google Play ARM64 / 16KB rev 3 | No lower-version or non-16KB image observed; Play image description includes Pre-Release |
| Configured Android virtual device | One Pixel 7 Pro profile, API 37.0 Google APIs ARM64 / 16KB; Play Store disabled | Existing candidate uses the non-Play image; no boot performed |
| Android acceleration | emulator -accel-check exits 0; Hypervisor.Framework reported | Acceleration prerequisite detected; boot/rendering still unverified |
| Android attached transports | adb devices -l lists zero | No running emulator or attached Android device visible at inventory time |
| Xcode | 26.4.1, build 17E202; selected full Xcode; first-launch check exits 0 | CLI selection/setup checks pass; no native build verified |
| iOS SDKs | Device SDK 26.4 and Simulator SDK 26.4 installed | SDK presence is distinct from a bootable runtime |
| iOS simulator runtime | Label iOS 26.4; version 26.4.1, build 23E254a; available | One available iOS runtime observed |
| iOS simulator configurations | Six iPhone and five iPad profiles; all Shutdown and available | iPhone 17 Pro is the provisional first candidate, not an already-running app |
| Apple physical-device inventory | devicectl lists zero | No device listed by this tool; ownership/availability of physical test devices remains unknown |

ANDROID_HOME points to the installed SDK; JAVA_HOME and DEVELOPER_DIR are unset.
The default java command successfully reports JDK 17, and xcode-select resolves
the full Xcode installation. No global gradle executable was found; no project
wrapper exists yet. Probe build-tool compatibility/download needs are checked
when T23 starts, not inferred from IDE presence.

### Inventory warning to carry into T23

SDK package listing returned exit 0 but reported both an integer-expression
warning in sdkmanager and an SDK XML v3/v4 reader mismatch. The package list was
cross-checked against local platform/image source.properties and the AVD config.
The API 37.0 platform metadata reports Android 17 and PreviewSdkInt=0, while the
separate Play image's package-list description says Pre-Release. Do not label
every installed image stable or every API 37 image preview from either signal.
This inventory does not establish their current public release-channel status.

The listing was run with Studio's bundled JDK 21 for that invocation only.
The cause of either warning is undiagnosed; no tools, Java configuration or SDK
metadata were changed to suppress it. Before relying on build/dependency
resolution, T23 must verify the selected toolchain and record any blocking error.

## Reproducing the inventory

These are the relevant checks, not commands to install or launch a device:

```sh
node --version
pnpm --version
java -version
/usr/libexec/java_home -V
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
  "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --list_installed
adb version
emulator -version
emulator -list-avds
emulator -accel-check
adb devices -l
xcode-select -p
xcodebuild -version
xcodebuild -checkFirstLaunchStatus
xcodebuild -showsdks
xcrun simctl list runtimes --json
xcrun simctl list devices available --json
xcrun devicectl list devices
```

T22 used devicectl JSON output in a temporary directory, recorded only counts
and removed the temporary output. Recheck volatile device state before running
T23/T24. Do not commit raw device listings or machine-specific absolute paths.

## T23 / T24 experiment criteria — recorded before probe code

Use two fixed app ids, com.example.probe.a and com.example.probe.b, with separate
host-selected package roots and identical small HTML/JS/CSS fixtures. Use public
marker strings only. Every case below is Not run as of T22.

The required custom scheme is the subject of the experiment. An official
HTTP(S) loader may be a labeled positive control, not a silent production-origin
replacement. A supported API's inability to load the required scheme is a valid
research finding. Never use private engine switches or file:// as a conforming
fallback. Leave credential-bearing native capabilities out of the probe.

| Case | Observation to record | Required outcome / how to interpret it |
| --- | --- | --- |
| P01 — build and boot | Exact build-tool pins, image/runtime, OS build, architecture, build/install/launch result | A real launched probe and reproducible commands, or an explicit setup failure; inventory alone does not pass |
| P02 — app A/B origins | Requested/committed URL, page location.origin, browser security behavior and available native origin metadata | Distinct stable app identities under SPEC §8; record opaque/null origins or missing metadata as gaps, never authority |
| P03 — local resources | Entry, relative JS/CSS/image paths and fetch of a bundled JSON marker | Resources resolve inside the intended package; record API errors, MIME/encoding and unsupported fetch behavior |
| P04 — storage isolation | localStorage, IndexedDB and cookie attempts in A/B; same-app second view | Record each facility independently: A's marker cannot be read by B; distinguish unavailable storage from isolation success |
| P05 — storage lifetime | Reload, view recreation and controlled app-process restart using unchanged app ids and data-store settings | Verify the claimed retained origin data separately at each boundary; do not infer native storage.* durability from browser storage |
| P06 — cross-app access | A attempts to read B's DOM and storage through a nested frame/window; normal A self-access is the positive control | Browser isolation must prevent cross-app reads; failure to load B is not sufficient evidence of an access gate |
| P07 — navigation | Same-app URL change, same-app reload, A→B and controlled external navigation/return | Log actual navigation callbacks and document/origin changes; identify containment needs for T28/T44/T45 without claiming a completed policy |
| P08 — confinement and fallback | Missing assets, wrong app id, paths that attempt package escape, external resource request and offline retry | No read outside the selected package; record any unexpected network fallback, URL normalization and failed local request |
| P09 — origin/CORS behavior | Controlled fetch/self and cross-app/local-test endpoint requests, observable Origin headers and response/error | Record actual origin/CORS semantics; a load callback or guest-reported URL alone cannot establish native sender identity |
| P10 — repeatability | Run A/B positive controls again; retain commands, versions and pass/fail/unavailable notes | Attribute findings to the tested configuration; one platform's observation does not pass the other |

### Android-specific T23 handover

1. Recheck the existing AVD/image and tool warnings; pin the minimal probe build's
   JDK/Gradle/AGP and compile settings before executing it. No pinned pair exists
   yet. If dependencies or another image are needed, identify them concretely.
2. Boot the existing candidate without wiping its data. Record the selected OS
   build/API, actual page size and current WebView package/version, not just
   the configured image path or a Chrome version.
3. Compare the required custom-scheme attempt with the documented asset-loader
   HTTP(S) control. Keep A/B identity fixed and log resource interception/fallback.
4. Run P01–P10 and report the security/loader gaps. Leave actual authenticated
   message-channel behavior and runtime feature checks to T25.

### iOS-specific T24 handover

1. Recheck the selected full Xcode and available iOS runtime; build a minimal
   probe for the existing simulator. Record build destination/runtime precisely.
2. Use public WKWebView / WKURLSchemeHandler APIs for the required scheme;
   record scheme-task completion/cancellation and the chosen WKWebsiteDataStore.
3. Run P01–P10 with the same app ids and public markers. Report each storage
   facility separately and record native frame-origin metadata where available.
4. Leave authenticated message/reply/content-world decisions to T26. A scheme
   handler accepting a URL does not itself prove origin/storage isolation.

## Remaining host decisions and readiness

T27 needs concrete candidates for the trusted TypeScript execution environment,
required JS primitives/timers, native↔JS calls, thread/actor ownership, bundle
loading, provider lifetime and framework-specific packaging. Evaluate those
against both platforms' evidence before asking for a host choice. No guest
request may choose its app partition, grants or credentials. The user already
answered that the host framework is undecided; do not repeat that broad question.

T22 is complete because requirements, installed prerequisites, unknowns and
observation criteria are recorded. T23 and T24 are ready to begin setup/probe
work, subject to their explicit build/boot checks. No native build, app launch,
bridge authentication or device conformance has been verified. Physical test
devices and the lower/current product support matrix remain open for later
gates. No SDK, simulator runtime or dependency was installed in T22.

## Primary documentation checked

- [Android emulator acceleration](https://developer.android.com/studio/run/emulator-acceleration): architecture/acceleration requirements and the acceleration check.
- [Android Java selection](https://developer.android.com/build/jdks): IDE, shell and project JDK choices can differ; verify compatibility for the selected build tools.
- [Android SDK manager](https://developer.android.com/tools/sdkmanager): package inventory versus installation; this report records the installed tool, not a tool-upgrade recommendation.
- [Android in-app content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content): the official asset loader uses HTTP(S), which needs reconciliation with the current custom-scheme requirement.
- [Android WebViewCompat](https://developer.android.com/reference/androidx/webkit/WebViewCompat): current provider metadata and per-feature runtime checks are distinct from the Android API level; custom-scheme origin allow rules have different host matching.
- [Apple simulated/physical devices](https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices): a selected run destination and platform support are needed; simulator evidence does not establish physical-device behavior.
- [Apple simulator runtimes/configurations](https://developer.apple.com/documentation/safari-developer-tools/adding-additional-simulators): a runtime and a device configuration are separate prerequisites.

Official documentation informs the checklist; the local commands above supply
the inventory. Neither substitutes for the measurements in T23–T26.
