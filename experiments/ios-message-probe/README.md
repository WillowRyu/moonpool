# T26 iOS message/reply probe

Standalone native API research, not a Moonpool SDK, provider dispatcher or
approved document-identity/transport contract. Preserve T23–T25 sources/evidence.
No credentials, private WebKit switch, file origin, network service or dependency.

## Criteria recorded before native implementation

| Case | Required observation |
| --- | --- |
| N01 | Actual Xcode/SDK/runtime, simulator target and installed executable fingerprint. Use only the retained owned simulator and a separate app package. |
| N02 | First inline message before navigation finish, with native webView/frameInfo/securityOrigin/world metadata separate from forged body claims. |
| N03 | A/B top frames, loaded same/foreign iframes, exact instance/origin/main-frame/world admission; successful current replies and explicit rejected promises. |
| N04 | Named content-world globals/handler isolation from page globals, shared DOM, and forMainFrameOnly user-script behavior. Handler visibility itself is not a main-frame permission gate. |
| N05 | Actual second same-origin WebView metadata routed through A's gate as an explicitly labeled host-replay negative; frame-targeted positive execution in the current frame/world. |
| N06 | Same-origin replacement and actual same-URL reload with old/new native reply closures. Reuse public payload id 2; old replies must be observed independently from current positive replies. |
| N07 | Delayed WKScriptMessageHandlerWithReply completion: record actual delivery or loss after replacement, not an assumed cancellation of native work. |
| N08 | Controlled legacy global receiver: a delayed evaluateJavaScript reply with reused diagnostic id reaches the current document or fails. Public markers only; no real storage overwrite. |
| N09 | Evaluate/callAsyncJavaScript using a previously captured WKFrameInfo after replacement/reload, paired with a current-frame positive. Record whether frame identity is document identity. |
| N10 | Foreign navigation and return with native-origin denial and fresh successful positive. No containment conformance is claimed for the permissive observer. |
| N11 | Explicit binding retirement rejects real later calls. Remove handlers and invoke a retained page reference; record promise/delivery behavior with an active positive control first. |
| N12 | Repeat all-frames/main-only script profiles from one final app, retaining native events, page snapshots, fixed-origin public assets and unavailable/error notes separately. |

All cases start Not run. Document labels and random page-instance labels are
diagnostics, not authentication or proposed JSON-RPC envelope fields. A minimal
legacy one-id receiver demonstrates a transport failure mode; it is not a second
Moonpool client/dispatcher or a new capability. Tests concern SPEC §9 and §11;
protocol/kernel and production lifetime policies remain unchanged.

## Ownership and build

Reuse the dedicated Moonpool T24 Origin Probe simulator only after checking its
retained id/name/state and all other simulator states. Keep ids in ignored
local-results/ownership.json. Never mutate booted/all or a user simulator.
Use org.moonpool.iosmessageprobe, preserving the installed T24 app/data.
Xcode 26.4.1, Simulator SDK 26.4, arm64 simulator target, Swift language mode 5
and probe minimum 17.0 are reused without an installation or global tool change.

The Admission predicate has a standalone Swift contract test before the native
harness. It checks metadata only, not capabilities or JSON-RPC. Native examples
and SDK semantics still require actual simulator observations.

## Reproduction

Before booting, derive local-results/ownership.json from the retained T24 owned
simulator id/name and a fresh inventory of all other available device ids/states.
The fields are owned, name and others (array of id/state objects). Keep this file
local; do not copy device selections across machines. Mutating simctl commands
must name the verified owned id, never booted/all or a user device.

```sh
python3 experiments/ios-message-probe/test_gate.py
python3 experiments/ios-message-probe/build.py
# Replace <owned-id> with the verified local id.
xcrun simctl boot <owned-id>
xcrun simctl bootstatus <owned-id> -b
xcrun simctl install <owned-id> experiments/ios-message-probe/build/MessageProbe.app
python3 experiments/ios-message-probe/run_probe.py --profile all-frames --run first --output experiments/ios-message-probe/local-results/all-frames-first.json
python3 experiments/ios-message-probe/run_probe.py --profile all-frames --run repeat --output experiments/ios-message-probe/local-results/all-frames-repeat.json
python3 experiments/ios-message-probe/run_probe.py --profile main-only --run first --output experiments/ios-message-probe/local-results/main-only-first.json
python3 experiments/ios-message-probe/run_probe.py --profile main-only --run repeat --output experiments/ios-message-probe/local-results/main-only-repeat.json
python3 experiments/ios-message-probe/verify_results.py experiments/ios-message-probe/local-results
xcrun simctl terminate <owned-id> org.moonpool.iosmessageprobe
xcrun simctl shutdown <owned-id>
```

The runner checks ownership/state, source fingerprints and the installed
executable hash before each launch. Exported reports include public observations
and build hashes; source/vendor caches and machine-local details stay ignored.
Retain new runs separately from historical results/. No fixture server or
additional simulator runtime is required.

## Measured result

Completed 2026-11-02: four final runs / 80 snapshots, 187 native controls and ten
Swift admission checks pass on iOS 26.4.1 / 23E254a. Captured native reply closures
do not resolve a replacement document's Promise; current replies succeed. Global
evaluation demonstrates a controlled reused-id collision. Captured old frame
execution also targets the replacement document in the measured runs. Named
world globals/handlers are isolated from the page while DOM is shared.

The removal visibility reader initially threw when the handler namespace was
removed. Failing observation verification led to a guarded diagnostic read;
the retained-reference rejection and namespace disappearance are now both
recorded. No platform protection was weakened to make a test pass.

Read the [verification record](../../docs/ios-message-probe-verification.md)
and the separate [public-source comparison](../../docs/native-document-lifetime-comparison.md).
The latter pins Portals/Capacitor, Tauri and React Native WebView source without
installing or executing those vendor runtimes. Neither report adopts a wire
field, protocol version, host runtime or production cancellation policy.
