# Native scheme/origin discussion

Date: 2026-10-27
Status: Discussion note, not an accepted ADR or SPEC amendment.
Updated: 2026-11-02. T22–T26 are complete; shared native contracts remain open.

T24's [measured iOS result](ios-origin-probe-verification.md) now shows distinct
custom origins and DOM/storage isolation on iOS 26.4.1, with empty custom cookies
and HTTP session-cookie lifetime limitations. This adds evidence, not approval.

[T25 Android messaging](android-message-probe-verification.md) adds actual HTTPS
listener origin/frame/instance metadata and authenticated initial port handoff.
Origin-only transfer can reach a replacement document; transferable port/proof
delegation lacks ongoing sender provenance. Custom listener origins still
collapse and hostname rules fail. No production transport decision follows.

[T26 iOS messaging](ios-message-probe-verification.md) confirms actual
view/origin/frame/world metadata and document-scoped native Promise replies in
the tested simulator. Generic global and captured-frame execution can reach the
replacement document. These measured differences inform T27–T31; they do not
select the trusted runtime, wire epoch or production lifecycle policy.

## Problem and measured evidence

The maintainer deferred OTA and asked to focus on scheme/origin handling.
SPEC §8 currently mandates moonpool://<mini-app-id>/ on production platforms.
[T23](android-origin-probe-verification.md) measured a concrete incompatibility:
Android WebView 145 either rejects that URL through the official asset loader,
or loads intercepted bytes while collapsing A/B into moonpool:// and sharing
DOM/localStorage/IndexedDB access. This violates the intended per-app isolation.
The same harness's HTTPS positive/negative controls remain separated.

Chromium's WebView documentation describes the custom-scheme origin behavior;
it is not a reason to assume that every platform or URL API behaves identically.
An address, its parsed hostname and the document's effective security origin
must be measured separately. This note does not resume a simulator or add code.

## Candidate direction

| Area | Direction to evaluate | Evidence still required |
| --- | --- | --- |
| Android | Prefer supported local asset loading under fixed, distinct per-app HTTPS hosts | Resolve T25 document/delegation findings and native navigation behavior in the approved shared contracts |
| iOS | Continue evaluating public WKURLSchemeHandler; T24 origins/storage and T26 direct reply scoping are measured | Cookie requirements, approved world/document/lifecycle rules and broader runtime/device evidence |
| Shared contract | A stable host-selected app-id→effective-origin mapping, with the pure TypeScript kernel unchanged | T27 ownership/runtime model and explicit T28 ADR/SPEC approval |

The Android HTTPS row is a recommendation from the recorded evidence and
official loading API, not an adopted production hostname or a claim across all
WebView versions. Giving every app the same localhost origin does not meet the
isolation target. Do not assign a production domain suffix, numeric limits,
hostname encoding or migration behavior before the contract decision.

HTTPS-shaped URLs can map to bundled bytes without a network server/CDN.
Missing local requests must not silently fall through to the internet. iOS
cannot simply register WKURLSchemeHandler for an already-handled https scheme;
the platform loading strategy has to be evaluated independently.

## Checks before selecting physical origins

1. Fix app identity from trusted manifest/configuration; guest URLs, claims and
   messages cannot select app id, grants, provider partition or loader roots.
2. Keep each app's mapping stable across reloads and versions. Define hostname
   canonicalization, uniqueness and unsupported-input behavior explicitly.
3. Test self-access as a positive control and loaded cross-app frames as a
   negative control. Test localStorage, IndexedDB, cookies and CORS separately.
4. Check cookie Domain/parent-domain and port behavior. Distinct origins alone
   do not prove cookie isolation: cookies use domain/path rules and can cover
   subdomains; ports are not cookie isolation keys. Select the namespace and
   any data-store policy only after those cases are verified.
5. Bind actual native sender/frame/instance/document identity, including first
   message, redirect/reload, subframes and stale callbacks. Origin text alone
   cannot settle the §11 document identity or peer-disconnect contracts.
6. Confine real asset resolution to the selected package. Record missing files,
   encoded paths, cancellation and network fallback; never enable file access,
   wildcard bridge access or private engine behavior to make a probe pass.
7. Define compatibility for any scheme/origin change: whether previously stored
   WebView data exists, how it is handled, and how bridge-version compatibility
   is reported. storage.* provider identity remains host-owned and separate
   from the engine's browser-storage origin.

These are checks for existing SPEC §7–§9 requirements and open contracts, not new
accepted policies or error codes. They also explain why an unmeasured iOS scheme
or a hostname-only Android change cannot finish the native implementation gate.

## Relation to Ionic Portals and local content

The inspected Portals public sources use Capacitor 8; its documented defaults
are HTTPS/localhost on Android and capacitor/localhost on iOS. Per-Portal file
roots and bridge instances do not themselves prove per-app browser-storage
isolation. The code review is not an independent device test of that product.
The inspected source refs are e4c62bce1d6118b3b515542477a109718f3533ed (Android)
and 2dbeb34a68bbdde46f79232e75002e47269f0795 (iOS).

Bundled mini-app HTML/JS/CSS belongs to the installed host's local assets. Service
API requests are separate network activity; storage.* uses the host's provider
(the current example provider is memory-only). OTA remains excluded from the
current scope. No updater, CDN, signing or distribution work is introduced.

## Next decision gate

T24–T26 completed after explicit task requests. Use the paired native evidence
and T27 ownership outcome for T28's concrete proposal explaining previous behavior,
the problem and each option's consequences. Required approvals precede any
normative or native SDK loader change. This discussion completes no new task.

## Primary sources

- [Android in-app content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content): local HTTP(S) assets and default network fallback behavior.
- [Chromium WebView compatibility](https://chromium.googlesource.com/chromium/src/+/HEAD/android_webview/docs/web-platform-compatibility.md#url-and-origin-handling): scheme-only custom origins in Android WebView.
- [Capacitor configuration](https://capacitorjs.com/docs/config): per-platform scheme/hostname defaults.
- [Portals Android configuration](https://github.com/ionic-team/ionic-portals-android/blob/e4c62bce1d6118b3b515542477a109718f3533ed/IonicPortals/src/main/kotlin/io/ionic/portals/PortalFragment.kt) and [iOS configuration](https://github.com/ionic-team/ionic-portals-ios/blob/2dbeb34a68bbdde46f79232e75002e47269f0795/Sources/IonicPortals/PortalView/PortalUIView.swift): inspected loader/bridge setup.
- [Apple scheme handler registration](https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/seturlschemehandler(_:forurlscheme:)): custom schemes cannot replace an already-handled scheme.
- [HTTP cookie semantics](https://httpwg.org/specs/rfc6265.html): domain scope and absence of port isolation.
