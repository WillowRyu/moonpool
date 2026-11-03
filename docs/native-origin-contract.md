# T28 — Native origin, local-loader and bootstrap contract proposal

Date: 2026-11-02
Status: Direction selected and supplementary research completed on 2026-11-03.
[Measured results and support limits](native-origin-contract-verification.md)
inform the origin decision. Cookie parity is now an additional required gate;
see the [common cookie/HTTP proposal](native-cookie-http-contract.md). No SPEC amendment, production SDK
implementation, broad support claim or T28 completion. [ADR 0026](adr/0026-bind-native-origins-loaders-and-bootstrap.md)
summarizes the decision. This draft concerns security requirements §9.1, §9.2,
§9.4 and §9.6; implementation remains gated.

## Evidence and the proposed change

| Existing rule / evidence | Consequence | Proposal |
| --- | --- | --- |
| SPEC §8 mandates the same custom origin shape on both OSes | [T23](android-origin-probe-verification.md) observes Android A/B custom origins collapse and DOM/storage mix | Android local HTTPS with a stable per-app host; retain iOS custom scheme |
| [T24](ios-origin-probe-verification.md) separates iOS DOM/localStorage/IndexedDB; custom cookies stay empty | Raw browser cookies differ; the maintainer requires equal product behavior | Proposed common async cookie/HTTP API and equal browser-cookie suppression, with new paired evidence |
| T23/T24 use shared website stores with public fixtures | Neither protects an integrating app's authenticated default store or separates cookies for a common remote API host | Require persistent per-app guest website stores, separate from host stores |
| [T25](android-message-probe-verification.md) authenticates initial handoff, then allows deliberate port/proof delegation | Port ownership does not establish current sender origin/frame | Native metadata on every inbound bridge message |
| [T26](ios-message-probe-verification.md) distinguishes direct replies from generic execution | Correct origin is insufficient for document lifetime | Retain ADR 0024; finalize bootstrap/generation details in T30 |

The original measurements justify changing the platform contract. The new
[supplementary evidence](native-origin-contract-verification.md) now measures the
Android .invalid namespace and both per-app store APIs. Its O01–O06 table separates
actual observations, modeled negatives and remaining limitations. The six iOS
startup controls expose an initialization-order requirement in the tested setup;
no broad platform-conformance claim follows.

## 1. Trusted registration and stable identity

Before creating a guest, the native manager validates its bundled manifest and
creates a trusted registration containing the exact app id, package root,
physical origin, website-store identity and host-selected grants. The manifest
permission declaration cannot grant itself access. Provider partitions remain
keyed by the full manifest id; origin hosts, hashes and guest messages never
replace that id. The host runtime remains private under ADR 0025.

For Android, define the candidate mapping exactly:

```text
key = lowercase RFC 4648 base32(SHA-256(ASCII(exact manifest.id))), no padding
origin = https://mp-<key>.invalid   (default HTTPS port, no alternate port)
profile name = moonpool-v1-<key>
entry URL = origin + / + individually URL-encoded accepted entry path segments
```

The full digest yields 52 base32 characters; mp- makes a 55-character DNS label.
Do not truncate the digest, hash a version/path, case-fold the id, add a shared
parent label, or select a random host per Portal. Verify URL parsing preserves
the expected scheme/host/port. The registry checks full-id-to-origin/profile
uniqueness; a collision is an admission error, never app merging. This is stable
within an integrating host's installation and across app version/Portal changes.
The key is public naming data, not a secret or authorization proof.

[RFC 6761 §6.4](https://www.rfc-editor.org/rfc/rfc6761#section-6.4) reserves .invalid
and its descendants. Choosing this namespace is a proposal based on that rule,
not an Android-documented production recipe. Android's loader documentation
recommends its reserved default domain or a domain the integrator owns; this
candidate avoids a registered-site collision by using a standards-reserved name.
No DNS server, TLS bypass, local HTTP server or CDN is involved. The local
interceptor still has to deny misses; DNS failure is not an enforcement mechanism.

For iOS, retain moonpool://<exact manifest.id>/ with no credentials or port.
Registration must round-trip the exact scheme/host through native URL parsing
and the supported security-origin representation without aliases. The manifest
grammar permits ids beyond ordinary DNS label/length limits. Such an id can be a
valid manifest yet unsupported by the native loader: report a host-local
registration failure, not -32602 over a nonexistent bridge. Do not silently trim,
rewrite or hash an unsupported iOS id. A supported-platform id matrix must pin
the actual admission boundary before the loader is claimed complete.

Both platforms pin the registration independently of the current URL. Parsed
sender origin must equal the registration's origin; null/opaque, wildcard or
prefix matches are insufficient. The origin root is an identity, not permission
to list files. The manifest's accepted entry text stays unchanged (§7); URL
encoding when constructing a load request does not relax manifest validation.

## 2. Website stores, cookies and retained data

Use one persistent guest website-data partition per registered app, shared by
same-app Portals. Different apps and every host-authenticated WebView use distinct
partitions, even when they access the same remote service hostname.

| Platform | Proposed ownership | Admission and lifetime |
| --- | --- | --- |
| Android | App-specific WebView Profile, named above | Require MULTI_PROFILE; setProfile before using/loading the WebView; use its own cookie/storage APIs |
| iOS | App-specific identified persistent WKWebsiteDataStore | Persist a nonzero UUID against the full id before creating/loading its WebView; reuse it across Portals and launches |

Do not use a default or nonpersistent store as a fallback. Native registration
metadata must be durable and collision checked; loss or mismatch of an existing
assignment is an explicit recovery error, not permission to allocate a fresh
empty store silently. Portal teardown releases owners, not the app's website
data or retained storage.* provider. App removal/data erasure is separate work.
The draft does not define general backup or provider durability policy (T48).

Host session cookies, tokens and credentials must never be copied into these
stores. Any later remote-service authentication must use separate app-scoped
credentials under SPEC §9.4; no token service is implemented here. This also
requires integrators to keep their own authenticated WebViews out of guest
partitions. A global cookie-disable switch would affect unrelated views and is
not a substitute for ownership.

Different origins are not enough for cookies: a Domain cookie can cover sibling
hosts, and ports do not separate it. The .invalid layout deliberately avoids a
shared registrable parent beneath the suffix. Parent-domain rejection is now measured on the retained Android target, alongside
the independent per-app-store boundary; each newly claimed configuration still
requires the same evidence. Test host-only, parent-domain and persistent cookies;
an empty cookie is not a passing isolation control unless cookie unavailability
is the expected case and a working HTTP(S) control is recorded.

Portable guest requirements include app-isolated DOM, localStorage and IndexedDB.
Browser storage is not a provider durability guarantee. T28's retained iOS
custom-scheme document.cookie remains unavailable in the measured configuration.
That observation is preserved; it no longer closes the product cookie contract.

The maintainer now requires equal Android/iOS cookie behavior. The
[common cookie/native-HTTP proposal](native-cookie-http-contract.md) makes engine
cookies unavailable on both platforms and supplies an app-owned asynchronous
session interface. Native HTTP automatically handles eligible server cookies;
raw document.cookie is not emulated through synchronous bridge calls. Independent
native-jar ownership remains unimplemented. Later
[C09/C10 suppression measurements](native-cookie-suppression-verification.md)
establish bounded policy locality but expose existing-cookie read/send on iOS.
The [admission baseline](native-cookie-store-admission.md), accepted as a direction
on 2026-11-03, requires refusing
cookie-bearing or unverified stores while preserving the same registration and
non-cookie data. This is not an approved migration or evidence of full containment.
Original tests remain unchanged; their passing controls are not new broker tests.

## 3. Loader confinement and network separation

Each Portal loader is bound to its registration's package root. A request URL
cannot select a different app/root even when that app is registered elsewhere.
Use Android WebViewAssetLoader behind this bound interceptor and iOS
WKURLSchemeHandler for moonpool. Install the complete policy before the first
guest script, including a valid initial load; a late page-finished hook is too late.

Proposed resource rules:

1. Admit only the exact registered local authority and GET/HEAD. Serve only
   regular packaged files, with correct MIME; HEAD has no body. No directory
   listing, automatic SPA index fallback, native file/content access or redirects
   from the local namespace to a network URL.
2. Treat manifest paths as unencoded paths (§7). For resource URLs, parse using
   the platform URL API and decode each escaped path segment exactly once using
   strict UTF-8. Reject malformed escapes, decoded separators/backslashes,
   controls and traversal above the selected root. A decoded percent sign is
   literal; never decode a second time. Query/fragment do not select filesystem
   paths. URL normalization cannot replace actual resolved-file confinement.
3. Resolve canonical filesystem paths, including symlinks where available, and
   verify containment in the trusted immutable root before reading. A shared
   text prefix is insufficient. Keep lookup/read protected from a mutable-root
   swap. APK entry lookup must likewise remain inside the selected app prefix.
4. Missing, unreadable, unsupported-method and denied local resources produce a
   local failure response. A WebViewAssetLoader null result must not become
   default network fallback. Reject other Moonpool app authorities locally;
   never serve their bytes through this Portal. No wildcard CORS response.
5. Under the proposed common-cookie profile, session/API traffic uses the
   explicitly granted native HTTP broker. Remote WebView connect/fetch/XHR and
   form paths are constrained before guest load; same-app local resources remain.
   Separately approved remote static-resource requests never receive native-jar
   cookies. Executable remote content still joins the app's trust and can invoke
   its granted SDK authority. This supersedes the draft's unrestricted browser
   remote-fetch allowance for this profile; it needs final approval and actual
   enforcement tests, not just a JS wrapper or a CSP assumption.

6. Interception/navigation gaps, including redirects, workers and unsupported
   URL schemes, must fail closed for local content. Disable unsupported paths
   before guest execution or reject the configuration; do not add an unverified
   service-worker/local-content path. Verify cache/restart behavior as well as
   online/offline misses. Do not claim that one callback sees every request.
7. iOS stopped WKURLSchemeTasks receive no further response/data/finish calls;
   all outstanding task owners are released on retirement.

These are proposed observable obligations. T38/T39 must derive failing loader
tests before code, including real filesystem cases and actual network observers.

## 4. Navigation and bootstrap authority

The native manager chooses the app, WebView, host-runtime owner, origin, store and
grants before loading. Inbound admission is ordered: active owner, actual bound
WebView, actual exact source origin, actual main-frame status, then approved
document binding (T30), then JSON/kernel validation (T29 and SPEC). An inbound
guest appId, origin, isMainFrame, generation or proof cannot replace those checks.
Recheck owner validity after queued asynchronous hops; captured callbacks cannot
select a replacement owner. Native registration/support errors stay host-local.

For Android, propose WebMessageListener as the per-message ingress, registered
with the exact origin rule before load. It supplies WebView/sourceOrigin/
isMainFrame on every callback. The receive boundary rejects transferred-port
authority; a port plus copied proof cannot bypass the metadata check. This is an
explicit change to SPEC §3.1's Android mechanism entry, not a new Transport method.
For iOS, use WKScriptMessageHandlerWithReply with actual WebView/frame origin/
main-frame checks. Guest-facing handlers remain in the guest-accessible world;
an isolated-world label alone cannot authenticate a page or make it a host realm.

Main-frame-only admission restricts direct bridge callers. An authorized top
frame can still proxy application data on someone else's behalf; neither this
contract nor a document generation proves the provenance of its arguments.
The declared scope/grant remains the authority to execute a capability.

Permit ordinary same-origin main-document navigation/reload and local subframes.
Reject direct native messages attributed to subframes. Same-origin child scripts
can access the top document's Client/objects/DOM and therefore share its app trust;
the main-frame gate does not isolate mutually untrusted same-origin documents.
Foreign frame navigation must be prevented and an enforced containment violation
must terminally retire the affected Portal. Disallow bridge-enabled about:, data:,
blob:, file: and content: main documents; the initial empty WebView has no authority.
Popups/new windows do not inherit a Portal or bridge. A user-activated external
link may be handed to the system browser by host policy only when its Portal
navigation is definitively cancelled before replacement. In that handled case,
the current document/Portal remains active. Other forbidden navigation or an
enforced containment violation retires it, even when the destination was blocked.
Opening the system browser cannot undo a retirement already triggered. No
automatic return/revival is allowed after retirement.

Navigation guards must cover redirects, form/POST submissions, frames, popups,
history restoration and programmatic replacement in the claimed configuration.
A top-level URL comparison after load cannot establish prevention. When required
coverage cannot be enforced, keep the bridge disabled and reject that support
claim. Retire before cleanup; already-dispatched effects are not rolled back.
Native T44/T45 must prove these obligations using real negative and positive cases.

Public bootstrap snapshots flow only to the bound admitted document and private
runtime owner. They contain no credentials and are not selected by guest URL
parameters. Direct native replies are preferred over generic global JS execution,
but neither an observed reply-proxy object identity nor navigation load callback
is a universal document identifier. T30 must specify generation issuance, initial
binding, duplicate/retry behavior, notifications and stale queued replies. T29
owns text/codec failures; T31 owns pending-call/renderer-loss/close semantics.
This draft deliberately adds none of those wire fields or error codes.

## 5. Compatibility and support failures

The proposal changes Android's physical origin and introduces explicit native
store ownership. The repository currently retains research fixtures, not a
conforming published native SDK. Preserve those fixtures/evidence as historical
data. Never import collapsed custom-origin storage as if it belonged to one app;
the original ownership may be ambiguous. Do not delete or silently migrate any
existing browser data. Future installed mappings require an explicit migration
decision; changing an origin or store re-keys browser data.

Keep browser-development §8.1.1 and the provider app id unchanged. No automatic
protocol version bump follows merely from a native URL change; T30 separately
owns the future wire migration. If approved, record native compatibility changes
in CHANGELOG and update CLAUDE.md itself, preserving its instruction symlinks.

Before loading, check the runtime/transport/store features as well as origin and
package registration. Also establish a verified safe WebKit startup sequence
before enumerating identified stores. The retained iOS26.4.1 configuration crashes
when enumeration is first; an empty nonpersistent view initializes the engine
without loading a guest and is released afterward. This measured workaround is
not a default/nonpersistent guest-store fallback or an Apple-wide guarantee. Unsupported configurations report a host-local failure
and expose no guest authority. No file://, shared-origin/default-store, wildcard
listener, guest-realm kernel or JavascriptInterface fallback. No product minimum
OS, broad provider range or numeric resource cap is established by API existence.
Per-app profile/storage overhead must feed the already planned T53 measurements.

## 6. Proposed SPEC edits and acceptance gates

After explicit approval and the supplementary evidence, apply a focused amendment:

| Location | Proposed amendment |
| --- | --- |
| SPEC §3.1 | Android native ingress uses origin/frame-aware WebMessageListener; Transport remains pure and unchanged |
| SPEC §7 | Clarify that syntactic manifest validity does not establish platform loader support; native admission never rewrites ids |
| SPEC §8 | Platform-specific stable physical-origin mapping and app-specific persistent guest stores; remove the blanket cookie guarantee |
| SPEC §9.1 / §9.2 | Native instance/main-frame checks, bootstrap ownership and containment obligations, alongside existing browser profile |
| SPEC §9.4 / §9.6 | Guest website stores cannot inherit host credentials; real resource confinement and local-miss behavior |
| CLAUDE.md | Replace the universal scheme invariant with the approved per-platform rule; preserve symlinks |

Acceptance cases to write before any supplementary probe/loader implementation:

| Cases | Required positive and negative observations | Gate |
| --- | --- | --- |
| O01 identity | Same exact id retains origin/store across two Portals, version and restart; different ids differ; collision/remap rejected | T28 supplementary + T38/T39 |
| O02 parsing | Long/boundary labels and numeric/hyphen ids; exact scheme/host/port; invalid iOS roundtrip rejects without rewriting | T28 supplementary + loader unit tests |
| O03 local storage | Real loaded A/B DOM, localStorage and IndexedDB controls in the newly selected stores, including restart | T28 supplementary |
| O04 cookies | Working HTTPS host-only/persistent control; Domain=invalid and sibling/parent negatives; iOS custom absence labeled unavailable | T28 supplementary |
| O05 shared service | Same remote HTTPS cookie host through A/B/host-auth partitions: distinct public sentinel cookies, same-app sharing and restart | T28 supplementary |
| O06 unsupported stores | Missing MULTI_PROFILE / identified-store support, early initialization, lost/duplicate assignments: no guest load or default fallback | T28 supplementary + T38/T39 |
| O07 loader | Actual files, symlinks, Unicode/space/percent paths, separators/traversal, misses, methods and wrong app; no network fallback online/offline | T38/T39 |
| O08 sender | Correct origin/wrong view, direct subframe, foreign/null origin, forged fields and retired owner rejected; main frame succeeds; same-origin child access via top is explicitly shared app trust | T40/T41 |
| O09 navigation | Same-app control plus foreign redirects/POST/frames/popups/history; violation retires only A while B works; definitively cancelled host-handled external link keeps its original document active | T44/T45 |
| O10 lifetime | Old initialize/result/error/notification excluded on reload and A→B→A; grants/provider data and accepted effects retained | T30/T31 contract, T32/T33 and native integration |

The maintainer selected this direction for the supplementary probes on 2026-11-03.
Those probes and independent verification are complete within the recorded
limits. Complete T28 and amend SPEC only after reviewing that evidence and
explicitly approving the final origin and cookie/HTTP contracts, including the
measured startup limit and the new C01–C12 parity gates.
T29–T31 and production loaders remain gated meanwhile.

## Primary sources

- [Android local content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content) and [WebViewAssetLoader](https://developer.android.com/reference/androidx/webkit/WebViewAssetLoader): HTTP(S) interception, domain guidance and nullable misses.
- [Android native message metadata](https://developer.android.com/reference/androidx/webkit/WebViewCompat.WebMessageListener): actual WebView/sourceOrigin/isMainFrame, separate from message payload.
- [Android setProfile](https://developer.android.com/reference/androidx/webkit/WebViewCompat#setProfile(android.webkit.WebView,java.lang.String)) and [Profile](https://developer.android.com/reference/androidx/webkit/Profile): runtime feature gate, early selection and partition-specific services.
- [Apple identified website data stores](https://developer.apple.com/documentation/webkit/wkwebsitedatastore/init(foridentifier:)) and [public WebKit header](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKWebsiteDataStore.h): persistent UUID-selected stores; API availability is not device evidence.
- [Apple scheme registration](https://developer.apple.com/documentation/webkit/wkwebviewconfiguration/seturlschemehandler(_:forurlscheme:)): cannot replace an already-handled scheme.
- [RFC 4648 base32](https://www.rfc-editor.org/rfc/rfc4648#section-6), [RFC 6761 .invalid](https://www.rfc-editor.org/rfc/rfc6761#section-6.4), [RFC 6265 cookie scope](https://httpwg.org/specs/rfc6265.html): naming and domain rules, not a native conformance claim.
