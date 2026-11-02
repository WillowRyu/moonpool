# T25 Android message-channel probe

Standalone platform research, not a native SDK, replacement kernel or accepted
origin/codec/lifecycle contract. Baseline: published 6c5576e. Preserve the T23/T24
sources and retained evidence. No credentials, real providers, dispatcher,
JavascriptInterface, private WebView switch or certificate bypass is involved.

## Criteria recorded before implementation

Measure both native-origin/frame-aware WebMessageListener callbacks and the
WebMessagePort channel named in SPEC §3.1. The listener is an experimental
bootstrap/control, not a silent production transport substitution. HTTPS app
origins are fixed local .test controls, not approved production hostnames.

| Case | Required observation |
| --- | --- |
| M01 | Pin tools and actual WebView; feature-check listener, channel creation, posting, port callbacks/close before use. Unsupported features fail closed without a fallback. |
| M02 | Register before load; an inline first-script message arrives with actual WebView/sourceOrigin/isMainFrame metadata; record ordering versus page-finished. |
| M03 | A/B top frames and loaded same/foreign subframes send real messages; compare source metadata with deliberately forged payload identity. |
| M04 | Exact origin injection excludes a foreign origin; same-origin subframes still need a main-frame gate. A separate fixed-origin diagnostic observer records negatives without capabilities. |
| M05 | Route an actually observed second WebView's callback through the first's gate as a labeled host-routing negative; same origin must not imply same instance. |
| M06 | Same-origin reload/replacement, foreign navigation and return: record callback/reply-proxy identity and late replies. Navigation callbacks are observations, not authentication. |
| M07 | Transfer a native-created port to the exact main-frame origin; receive ordered text and round-trip replies. Record the absence of per-message origin/frame arguments. |
| M08 | Wrong targetOrigin must not deliver, paired with a working correct-target transfer. Origin-only delayed bootstrap after same-origin replacement must be measured. |
| M09 | Experimental document-scoped reply-proxy challenge plus port proof: current document succeeds; a replaced document cannot use the old proof. No challenge in a broadcast or port-transfer envelope. |
| M10 | Deliberately transfer an established port/proof to a loaded foreign subframe. Record whether the native port callback can distinguish delegation; do not hide a provenance gap behind a successful bootstrap. |
| M11 | Retire a native-owned binding; replay captured host callbacks as explicitly labeled host-replay negatives and check close/post behavior. This is not a complete peer-loss contract. |
| M12 | Custom-scheme hostname allow rule and native origin metadata, plus repeated HTTPS/custom runs from the same final APK. Record incompatibility, unsupported and negative results separately. |
| M13 | Guest-created MessageChannel port transfer in an origin/frame-attested listener callback. Verify the pinned 1.14.0 API's actual transferred port and ordered round trips without a targetOrigin bootstrap race. This does not add per-message origin metadata to subsequent port callbacks. |

All cases are initially Not run. Native-owned polling snapshots are diagnostic
only. Page doc labels and identity claims never select authority. Random proof
material is scoped to this public-data experiment and omitted from saved reports.
Frame/origin binding, transferable-port delegation, document identity and actual
native lifecycle remain explicit T28/T30/T31 decision inputs.

## Tooling and ownership

Reuse T23's pinned Gradle 9.6.1 wrapper via ../android-origin-probe/gradlew -p .;
AGP 9.3.1, Studio JDK 21.0.10, AndroidX WebKit 1.14.0, compile/target SDK 36,
Build-Tools 36.0.0, minSdk 31 (probe setting only). No new runtime dependency.
Build offline from the existing cache first. A separate application id keeps
T23's installed app and data intact.

Record already-running emulator ids/AVDs locally before booting the existing
Pixel_7_Pro_Dev AVD on a free explicit port. Do not mutate or stop a pre-existing
user emulator, clear data or use an implicit adb device. Shut down only the
emulator booted for this session. Local serials/paths remain in ignored files.

## Tests before the native harness

The small Admission classifier checks only experimental native sender metadata;
it is not a JSON-RPC dispatcher or permission gate. Its JVM contract tests cover
positive admission and independently isolate inactive/view/origin/frame rejection.
Run test_gate.py with the installed Studio JDK before implementation, then rerun
afterward. Native P/M cases still require actual emulator evidence.

## Reproduction

Use a shutdown AVD with the installed API 37 ARM64/16KB image, and a free explicit
emulator port pair. Record pre-existing devices before starting it. Keep the
local ownership file in local-results/ownership.json with owned (serial), avd
(exact AVD name), and protected (array of serial/avd objects). The runner checks
that the owned serial is not protected and still names that AVD. Never copy
another machine's device selection or use implicit adb targets.

From the workspace root, build/test using the pinned installed tools:

```sh
python3 experiments/android-message-probe/test_gate.py --java-home "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
python3 experiments/android-message-probe/build.py
# Replace placeholders with the verified owned AVD/serial and free even port.
emulator -avd <owned-avd> -port <free-even-port> -no-window -no-snapshot-save -no-boot-anim
adb -s <owned-serial> install -r experiments/android-message-probe/app/build/outputs/apk/debug/app-debug.apk
python3 experiments/android-message-probe/run_probe.py --profile https --run first --output experiments/android-message-probe/local-results/https-first.json
python3 experiments/android-message-probe/run_probe.py --profile https --run repeat --output experiments/android-message-probe/local-results/https-repeat.json
python3 experiments/android-message-probe/run_probe.py --profile custom --run first --output experiments/android-message-probe/local-results/custom-first.json
python3 experiments/android-message-probe/run_probe.py --profile custom --run repeat --output experiments/android-message-probe/local-results/custom-repeat.json
python3 experiments/android-message-probe/verify_results.py experiments/android-message-probe/local-results
adb -s <owned-serial> shell am force-stop org.moonpool.messageprobe
adb -s <owned-serial> emu kill
```

Wait for boot completion on that serial before installation. The build script
uses the installed Studio JDK path, not a global JDK selection. It generates
fingerprints only after build/lint succeeds. The runner checks current source
hashes and the installed APK hash before each launch. No loopback fixture or
adb reverse is needed. Keep new runs separate from historical results/.

## Measured outcome

Research complete on 2026-11-02 for WebView 145.0.7632.218 / API 37. Four final
runs retain 44 snapshots; the verifier passes 175 controls and the JVM gate
passes 11 cases. Build/lint succeed with 29 recorded warnings and Gradle 10
deprecation notes. See the [verification report](../../docs/android-message-probe-verification.md)
and [environment/fingerprints](results/environment.json).

Actual native listener metadata permits instance/origin/main-frame checks;
custom hostname rules fail and A/B custom source origins collapse. Correct-target
native port transfer and guest-created attested port handoff work, but port
callbacks lack ongoing origin/frame provenance. A delayed origin-only bootstrap
can reach a replacement document. Reply-proxy proof distinguishes that document
in the experiment, while deliberate port/proof forwarding still demonstrates
the provenance gap. No production protocol, origin or transport decision follows.

The initial port gate incorrectly compared Java wrapper references. The failing
round-trip verification led to binding by the native callback registration;
wrapper equality is now recorded only as a platform observation. Saved final
reports omit random proof values, local serials and user paths. T26/T27–T31
remain open; no Moonpool providers, dispatcher or credentials are installed.
