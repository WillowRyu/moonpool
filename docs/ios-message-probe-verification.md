# T26 — iOS message/reply/content-world research

Date: 2026-11-02 (Asia/Seoul)
Status: Bounded simulator research complete; no native SDK or protocol decision.
Baseline: committed 6c5576e plus preserved local T25 work.

Subsequent decision: the maintainer selected explicit document generations in
[ADR 0024](adr/0024-bind-rpc-work-to-document-generations.md). Detailed wire/
bootstrap and lifetime semantics remain T30/T31 work; this research record is
not a claim that generation support is implemented in the 0.1 kernel.

## Result

On the tested iOS 26.4.1 simulator, native WKScriptMessage metadata retains the
WebView, frame security origin, main-frame flag and content world. The probe
admits current main-frame messages from the configured app/world while rejecting
foreign origins, subframes, other-view host replays and retired bindings. Body
claims deliberately disagree with native metadata and never select authority.

Document replacement produces different outcomes depending on the reply path:

| Reply/execution path | Measured same-origin replacement and same-URL reload |
| --- | --- |
| Captured WKScriptMessageHandlerWithReply reply closure | Calling A's delayed closure does not resolve B's pending Promise, even when both payloads use diagnostic id 2. B's own closure succeeds. |
| Global evaluateJavaScript receiver | A's old id-2 marker reaches B and resolves B's controlled one-id receiver. |
| callAsyncJavaScript targeting captured old WKFrameInfo | Execution succeeds in B's new document; captured frame identity does not serve as a document-generation guarantee here. |

This reproduces a controlled stale-id collision at the JavaScript injection
boundary, not an actual Moonpool storage write, credential leak or vendor exploit.
As SPEC §11 states, same-origin replacement within one app/grant set is primarily
a correctness/lifetime concern. Receiving a new port/response is not inherently
wrong if connection ownership and pending work are deliberately transferred or
reinitialized. The research does not change those rules or add a wire epoch.

## Scope, setup and ownership

The separate [probe](../experiments/ios-message-probe/README.md) uses
org.moonpool.iosmessageprobe and fixed moonpool://com.example.probe.a/b assets.
T24/T25 source, binaries and retained results remain unchanged. No HTTP server,
file origin, network fallback, private WebKit switch, certificate exception,
credential, real capability/provider or duplicate Moonpool dispatcher is used.

| Item | Measured / selected value |
| --- | --- |
| Host | macOS 26.6.2 arm64; Node 22.19.0 / pnpm 11.1.3 |
| Tools | Xcode 26.4.1 / 17E202, Apple Swift 6.3.1; Swift language mode 5 |
| Binary | IOSSIMULATOR, arm64, SDK 26.4, minimum 17.0 (probe setting only) |
| Device | Retained dedicated iPhone 17 Pro research simulator |
| Runtime | Label iOS 26.4; actual 26.4.1 / 23E254a |
| Native APIs | Public WKScriptMessageHandlerWithReply, WKFrameInfo, WKContentWorld, WKUserScript and WKWebView execution APIs |
| Content worlds | Page and named MoonpoolT26; isolated globals, shared DOM |

Only the retained owned simulator id was booted, installed/launched and shut
down. Other simulator states were recorded before use and are unchanged at
cleanup. The owned device was rechecked/rebooted before installation after it
returned to Shutdown during preparation. No cause for that state transition is
inferred. No other device was booted or stopped; no SDK/runtime/package/global
Xcode change was needed. Installed executable/signature and source hashes were
verified; ids and machine-specific paths remain ignored locally.

## Controls recorded before implementation

The harness README records N01–N12. A standalone ten-case Swift Admission
contract failed before implementation and passes afterward. It tests actual
instance identity, origin tuple, main frame, registered world and active binding
without UIKit/WebKit or a running simulator. This does not select a native core.

| Case | Outcome |
| --- | --- |
| N01 | Installed simulator target and executable fingerprint verified; all final runs use the same build. |
| N02 | Inline head messages precede navigation finish; native origin/frame/world metadata is separate from forged payload claims. |
| N03 | A/B and same-origin second views work. Loaded same/foreign frames report page-handler visibility; native frame/origin gate rejects their requests with Promise errors. |
| N04 | Page cannot see named-world globals or handler. Native named-world evaluation sees them; a DOM marker is shared. The main-only profile limits isolated user-script execution, while the page handler remains available to subframes. |
| N05 | Explicit host replay of an actual second WebView's metadata is rejected. Current captured frame execution succeeds as a positive control. |
| N06/N07 | Held old reply closures are called after replacement/reload without resolving the new document's held Promise. The new document's same-payload-id reply succeeds; native work was not automatically cancelled. |
| N08 | Controlled global id-2 receiver resolves with an old document's marker after both replacement and reload. No application storage is written. |
| N09 | Previously captured WKFrameInfo executes in the replacement document in all final runs, including the same-URL reload; request URL snapshot alone is insufficient. |
| N10 | Foreign main-frame navigation receives wrong-origin errors; a fresh return has valid responses. This permissive observation is not production containment. |
| N11 | Explicit retirement rejects real later calls. Removing handlers makes the retained JavaScript reference reject; no accepted native message follows removal. |
| N12 | All-frames/main-only profiles each repeat, with all 20 snapshots available per run. |

Four final runs retain 80 snapshots; 187 native control assertions and ten Swift
contract checks pass. Reports retain raw native events and public page values
with identical source/build metadata. See the [environment](../experiments/ios-message-probe/results/environment.json).
The same-URL case verifies equal href with a different page-instance label;
these page labels are diagnostic, not authentication identifiers.
Final pnpm run check passes 1134 TypeScript tests / 40 files, nine Python tests,
both typechecks, Biome (250 files) and both browser builds, with the existing
nonblocking Vite warning. Native build/signature and Swift checks are separate
from those browser/kernel checks.

The initial removal snapshot failed because removing the last page-world handler
also removed its messageHandlers namespace. The diagnostic getter itself threw.
The verifier caught the unavailable observation; guarded visibility reads now
record that error separately from the retained reference's rejected Promise.
The completed final reports replace neither earlier native evidence nor that
locally retained preliminary run.

## Interpretation and retained limits

Captured native reply closures provide useful document-scoped delivery in this
configuration. Generic execution against a WebView or captured frame can target
the current document. Their different semantics must not be hidden behind a
single assumption that a matching origin/frame means the same document.

A named content world separates JavaScript globals/handler names, while sharing
the DOM. Its existence does not select the trusted TypeScript execution model,
eliminate origin checks or prove a complete host/guest security boundary.
The callback metadata identifies WebKit's message/frame/world context, not every
possible delegation or application-level intent.

All held completion blocks are invoked at most once. This records reply
bookkeeping; it does not show cancellation, rollback, renderer loss, all queued
native work or persistent provider behavior. Swift/Foundation JSON bridging is
not a lossless Moonpool codec proof; T29 remains open. No physical-device, lower
OS or different-runtime claim follows from this simulator configuration.

The [comparative review](native-document-lifetime-comparison.md) separately
describes public-source behavior in Portals/Capacitor, Tauri and React Native
WebView. Those vendor runtimes were not installed or executed in T26.

## Reproduction and next gate

Use the README's explicit owner/device setup. Build, verify the installed hash,
run both profiles twice and export only the research app's report:

```sh
python3 experiments/ios-message-probe/test_gate.py
python3 experiments/ios-message-probe/build.py
python3 experiments/ios-message-probe/verify_results.py experiments/ios-message-probe/results
pnpm run check
```

T22–T26 research is complete. T27 now has paired platform evidence for trusted
runtime/ownership choices. T28–T31 must define origin/channel/bootstrap, codec,
document identity and retirement semantics with explicit approval. This research
does not choose a document-id field, generator, protocol version or cancellation
policy, and does not amend SPEC or accepted ADRs.

Primary API references: [WKScriptMessageHandlerWithReply](https://developer.apple.com/documentation/webkit/wkscriptmessagehandlerwithreply),
[WKScriptMessage](https://developer.apple.com/documentation/webkit/wkscriptmessage),
[WKContentWorld](https://developer.apple.com/documentation/webkit/wkcontentworld),
[WKWebView JavaScript execution APIs](https://developer.apple.com/documentation/webkit/wkwebview).
Installed SDK headers were inspected alongside actual simulator measurements.
