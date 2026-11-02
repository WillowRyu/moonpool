# Native bridge document-lifetime comparison

Date: 2026-11-02 (Asia/Seoul)
Status: Requested research, not an accepted ADR or production transport choice.
Question: how do similar runtimes handle reload, late responses and callback ids?

## Evidence and scope

T26 supplies [Moonpool's own simulator observations](ios-message-probe-verification.md).
The comparisons below inspect pinned public source and official API documentation;
no vendor application was built or device-tested. A dependency range is not a
consumer lockfile, and source evidence is not a universal security guarantee.
Neither a vulnerability nor cancellation of all native work is inferred merely
from the presence/absence of an epoch field in these paths.

The [source manifest](../experiments/ios-message-probe/results/vendor-source-manifest.json)
records five repositories, 18 inspected files, revision-specific URLs and hashes.
Tags inspected: Portals iOS 0.14.1, Portals Android 0.14.0, Capacitor 8.6.0,
Tauri tauri-v2.12.5 and React Native WebView v16.0.0. These are the observed
version-tag snapshots, not a claim about every installed consumer.

| Implementation | Confirmed mechanism in inspected path | What this does not establish |
| --- | --- | --- |
| Portals / Capacitor JavaScript | Document-local callback Map; randomized starting counter, then incremented callbackId; unknown callback has no Promise to resolve | Deterministic document-generation validation or cancellation of running plugin work |
| Capacitor iOS | Navigation reset clears stored calls/listeners; result delivery evaluates global fromNative(callbackId, ...) | Per-request WK reply-closure binding on that result path |
| Capacitor Android | Navigation reset; origin-aware listener/main-frame check on modern path; response uses a retained reply-proxy field | A request captures its own immutable document reply proxy |
| Tauri JS callback/eval path | Random Uint32 callback identifiers and a current-document Map; unknown ids warn and are not executed | An explicit document-generation contract, or all platform/channel paths behaving identically |
| React Native WebView | String message events and host JavaScript injection | A built-in correlated RPC/epoch protocol; applications own that higher layer |
| T26's direct WK reply path | Captured reply block resolves its original Promise; old completion does not reach new document in measured runs | All generic WebView/frame JavaScript execution being document-bound |

## Ionic Portals delegates to Capacitor

Portals iOS declares the Capacitor Swift package range from 8.0.0 up to the next
major; its PortalUIView creates a CapacitorBridge. Android declares
com.capacitorjs:core [8.0.0,9.0.0) and builds a Bridge per Portal fragment.
This supports reviewing Capacitor's relevant bridge code. It does not prove a
particular application's resolved version or extra wrapper/plugin behavior.
[iOS dependency](https://github.com/ionic-team/ionic-portals-ios/blob/2dbeb34a68bbdde46f79232e75002e47269f0795/Package.swift#L15-L19),
[iOS bridge owner](https://github.com/ionic-team/ionic-portals-ios/blob/2dbeb34a68bbdde46f79232e75002e47269f0795/Sources/IonicPortals/PortalView/PortalUIView.swift#L20-L28),
[Android dependency](https://github.com/ionic-team/ionic-portals-android/blob/e4c62bce1d6118b3b515542477a109718f3533ed/IonicPortals/build.gradle.kts),
[Android bridge creation](https://github.com/ionic-team/ionic-portals-android/blob/e4c62bce1d6118b3b515542477a109718f3533ed/IonicPortals/src/main/kotlin/io/ionic/portals/PortalFragment.kt#L293-L387).

Capacitor's JS bridge allocates a callback Map on initialization. Its counter
starts at Math.floor(Math.random() * 134217728), with an explicit source comment
about reload/old-session collision avoidance; registered calls increment that
counter. Responses look up callbackId; a missing entry does not resolve another
Promise. This reduces accidental overlap without proving that an old result
belongs to the active document. Randomized ids are not origin authentication.
[ID initialization](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/core/native-bridge.ts#L914-L927),
[registration](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/core/native-bridge.ts#L999-L1024),
[response lookup](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/core/native-bridge.ts#L1048-L1096).

On iOS, didStartProvisionalNavigation calls bridge.reset(), which removes stored
calls and plugin listeners. Successful/error result paths still evaluate
window.Capacitor.fromNative in the WebView. In the inspected one-shot plugin
success closure, toJs can be called directly; clearing saved listener calls is
not evidence that arbitrary plugin work has been aborted. These mechanisms
combine lifecycle cleanup with callback-id routing, rather than the direct
WKScriptMessageHandlerWithReply path tested by T26.
[navigation reset](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/ios/Capacitor/Capacitor/WebViewDelegationHandler.swift#L43-L48),
[reset body](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/ios/Capacitor/Capacitor/CapacitorBridge.swift#L310-L319),
[one-shot completion](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/ios/Capacitor/Capacitor/CapacitorBridge.swift#L527-L551),
[global response delivery](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/ios/Capacitor/Capacitor/CapacitorBridge.swift#L598-L630).

Android's modern listener checks isMainFrame and updates a MessageHandler-level
javaScriptReplyProxy field. sendResponseMessage later uses that field; it is not
captured per PluginCall in the inspected code. Thus a document-scoped proxy API
does not automatically make a wrapper's response routing document-scoped.
Navigation also resets saved calls/listeners. Legacy bridge paths exist in this
source, including JavascriptInterface; Moonpool's prohibition remains unchanged.
This is source-path analysis, not a reproduced Capacitor misdelivery.
[listener and field](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/android/capacitor/src/main/java/com/getcapacitor/MessageHandler.java#L17-L45),
[response path](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/android/capacitor/src/main/java/com/getcapacitor/MessageHandler.java#L101-L145),
[navigation reset](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/android/capacitor/src/main/java/com/getcapacitor/BridgeWebViewClient.java#L62-L70),
[reset body](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/android/capacitor/src/main/java/com/getcapacitor/Bridge.java#L576-L582).

## Tauri callback ids

The inspected Tauri core script obtains each callback identifier with
crypto.getRandomValues(new Uint32Array(1))[0], stores it in a callback Map and
deletes one-shot entries. runCallback invokes an existing entry; otherwise it
warns about the app having reloaded while asynchronous Rust work was running.
This explicitly accommodates late completion with no callback in the current
document. Random identifiers reduce accidental reuse but are not a document
epoch or proof of cancellation.
[callback registry](https://github.com/tauri-apps/tauri/blob/993038c49185307dfc895ab7657d77ca0d5ed7c7/crates/tauri/scripts/core.js#L5-L48).

The inspected Rust response path has platform/data-dependent branches. Some
format a call to window.__TAURI_INTERNALS__.runCallback and evaluate it; others
use a channel response. The conclusion above is scoped to the callback/eval
path and does not claim that every Tauri IPC/channel implementation has the same
document-delivery semantics.
[callback formatter](https://github.com/tauri-apps/tauri/blob/993038c49185307dfc895ab7657d77ca0d5ed7c7/crates/tauri/src/ipc/format_callback.rs#L100-L104),
[platform response branches](https://github.com/tauri-apps/tauri/blob/993038c49185307dfc895ab7657d77ca0d5ed7c7/crates/tauri/src/ipc/protocol.rs#L316-L420).

## React Native WebView exposes a lower-level transport

Its documented postMessage API sends a string to onMessage. The inspected iOS
handler forwards data plus the frame request URL; host postMessage injects a
MessageEvent into the WebView via JavaScript. This is messaging infrastructure,
not a correlated RPC implementation. No shared request-id/document-epoch policy
is supplied by these inspected methods; an app or its RPC wrapper must define
that behavior. A URL in an event is not itself a verified document generation.
[message API](https://github.com/react-native-webview/react-native-webview/blob/f3fbb205cb176c1073e247babcbbf62df9b5132f/docs/Reference.md#onmessage),
[iOS receive](https://github.com/react-native-webview/react-native-webview/blob/f3fbb205cb176c1073e247babcbbf62df9b5132f/apple/RNCWebViewImpl.m#L743-L760),
[iOS send](https://github.com/react-native-webview/react-native-webview/blob/f3fbb205cb176c1073e247babcbbf62df9b5132f/apple/RNCWebViewImpl.m#L1081-L1091).

## Implications for Moonpool and subsequent selection

The evidence supports a document-lifetime contract covering retained callbacks,
results/errors/initialization/notifications and reused request ids. It does not
justify treating origin, a frame handle, random callback ids or initial channel
bootstrap as interchangeable with an active-document check.

For iOS, the captured native reply closure is a useful delivery primitive. After
reviewing the comparison, the maintainer selected explicit document generations
in [ADR 0024](adr/0024-bind-rpc-work-to-document-generations.md). Generation
creation/verification, captured request ownership, replacement timing, pending
Promise outcomes, compatibility and old-notification handling still require the
detailed T30/T31 contracts.
Old results must not be relabeled with whatever document is current when native
work finishes. Invalidation also does not roll back an already-performed write.

Do not copy another runtime's callback-id scheme into Moonpool's approved
request-id profile, expose host credentials, add a native core or modify SPEC as
part of this comparison. T27–T31 remain the existing explicit decision gates.

The selected direction is recorded; its detailed wire/lifecycle contract and
implementation are separate. The current 0.1 profile remains unchanged. The
[real-kernel probe](../experiments/document-generation-contract/README.md) now
pins old initialization and reused-id collisions as intentionally failing safety
assertions, with unknown-id and retained-write/grant positive controls.
