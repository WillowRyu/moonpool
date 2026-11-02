# T24 — iOS origin/local-content verification

Date: 2026-11-02 (Asia/Seoul)
Status: Research complete for the recorded simulator configuration. This is not
a production native SDK, physical-device result or approved origin/SPEC change.
Baseline: 4225453. The maintainer explicitly resumed the paused T24 experiment.

## Result and consequence

WKWebView on the tested iOS 26.4.1 simulator distinguishes
moonpool://com.example.probe.a from moonpool://com.example.probe.b. Page origins,
frame-message origins, navigation-action source-frame metadata and the loopback
server's observed Origin header retain the app hostname. Both app frames really
load; a self-frame permits DOM and localStorage reads, while a loaded foreign
frame rejects both with SecurityError. This differs from T23's Android result.

With one shared default persistent WKWebsiteDataStore, localStorage and IndexedDB
retain separate A/B markers across a second same-app view, reload, view recreation
and controlled native app-process restart. Custom-scheme document.cookie remains
empty after writes; this is an unavailable cookie facility, not successful cookie
isolation. The HTTP control writes separate A/B session cookies, but their values
are absent after native app restart and in the foreign-app navigation snapshot.
The fixture omits Expires/Max-Age; persistent-cookie lifetime is not tested. The result
supports further custom-scheme investigation on iOS, not full SPEC §8 conformance.

No guest-callable native message handler, Moonpool dispatcher/provider or privileged
kernel is installed. Navigation is intentionally permitted among the fixed test
apps and loopback controls to observe it. SPEC §9.1 message authentication and
§9.2 containment remain unimplemented here; navigation sourceFrame metadata is
not a substitute for per-message authentication. T25/T26 and the explicit T28
origin/loader contract decision remain necessary before native SDK loaders.

## Environment and ownership

| Item | Measured / selected value |
| --- | --- |
| Host | macOS 26.6.2, arm64; Node 22.19.0 / pnpm 11.1.3 |
| Build tools | Xcode 26.4.1 (17E202), Apple Swift 6.3.1; Swift language mode 5 |
| Simulator | Dedicated iPhone 17 Pro; runtime label iOS 26.4, actual 26.4.1 / 23E254a, arm64 |
| App | org.moonpool.iosoriginprobe; ad-hoc simulator-only research artifact |
| Binary | LC_BUILD_VERSION: IOSSIMULATOR, minimum 17.0, SDK 26.4 |
| WebKit | System WKWebView from that simulator runtime; no independently selected provider |
| Store | WKWebsiteDataStore.default(), isPersistent true, shared by A and B |
| Custom loader | Public WKURLSchemeHandler for moonpool; no private registration or preferences |
| HTTP controls | A: http://localhost:8878; B: http://127.0.0.1:8879; CORS/external: http://127.0.0.1:8877 |

17.0 is a probe build setting, not a product minimum-OS promise. A/B use different
HTTP hostnames so the control does not mistake port separation for cookie
isolation. No production hostname, per-app data-store policy or host framework
is selected. No runtime, SDK, package dependency or account was installed.

The retained owned simulator and all other available simulators were Shutdown
at resumption. Only the dedicated T24 id was booted/installed/launched and later
shut down; every other device's state was preserved. Device ids and raw local
build paths remain in ignored local-results, outside retained evidence.

## Evidence matrix

P01–P10 were recorded in [T22](native-target-matrix.md) before implementation.
Five final runs retain 55 snapshots and raw native events with identical build
fingerprints; 790 control assertions pass. Preliminary runs are excluded from
this final evidence set.

| Case | Custom scheme | HTTP control / interpretation |
| --- | --- | --- |
| P01 build/boot | App builds, signs, installs and launches on owned simulator | Same artifact; both profiles run |
| P02 app origins | Distinct moonpool://com.example.probe.a and b; native navigation source origins and server-observed Origin agree | Distinct localhost:8878 and 127.0.0.1:8879 origins |
| P03 resources | HTML, JS, CSS, SVG and same-app bundled JSON fetch load | Same public fixtures load over loopback HTTP |
| P04 isolation/sharing | A/B localStorage and IndexedDB retain their own markers; same-app second view reads A; cookies stay empty | Separate localStorage/IndexedDB; session-cookie writes succeed in initial A/B pages |
| P05 lifetime | Correct app markers survive reload, view recreation and native app-process terminate/launch | localStorage/IndexedDB persist; session-cookie values are absent after restart and in the foreign-navigation snapshot |
| P06 frame access | Self DOM/storage reads succeed; loaded foreign DOM/storage reads throw SecurityError | Equivalent positive and negative controls |
| P07 navigation | Same-app page/reload, A→B, loopback external and return observed | Same sequence; no containment claim for this permissive probe |
| P08 confinement/fallback | Missing resource and plain/encoded parent escape return local 404; unknown app has native 404 and cannot be fetched by guest | Missing/escape/unknown paths denied; same-origin unknown HTTP path is a readable 404, foreign-origin response is CORS-blocked |
| P09 CORS | Same-app fetch works; foreign-app fetch and missing-CORS endpoint fail; permitted endpoint sees the full custom Origin | Permitted endpoint sees exact HTTP origin; missing-CORS endpoint fails |
| P10 repetition | Seed/restart and offline runs repeat origin/DOM/storage observations | Independent seed/restart positive controls |

The custom-scheme offline run stops all three loopback listeners first. Bundled
HTML/JS/CSS/SVG/JSON and local rejection responses remain available, while explicit
HTTP fetches fail and external navigation records NSURLErrorDomain -1004 with no
fixture report. This separates local scheme delivery from the network controls;
the simulator's entire network was not disabled.

The research resolver admits only two fixed hosts and the known bundled roots;
it does not forward misses to a network loader. Its path guards and shipped
regular fixture files are bounded harness controls, not a production loader or
proof of every symlink/path/canonicalization policy. The separate Python HTTP
regression tests cover the previously fixed absolute-path/symlink cases.

The native app terminates and launches without reinstalling/clearing data between
phases. This tests native app-process restart, not forced WebKit process loss,
simulator reboot, OS upgrade, power loss or storage.* provider durability.
The fetchDataRecords enumeration does not list custom-scheme hosts despite
successful guest storage rereads; it lists HTTP records retained from earlier
control runs. Do not infer custom storage unavailability or complete storage-
management support from that enumeration.

Cookie writes use SameSite=Lax; Path=/ with no expiry. The verifier requires
initial HTTP writes to succeed and rejects foreign marker values, while retaining
empty later observations explicitly. It does not call absent cookies successful
isolation or assert persistence for session cookies. Domain/parent-domain/port
policies and persistent cookies still need separate cases before T28 decisions.

## Cancellation and build corrections

The first cancellation attempt removed a view 100 ms after load; the delayed
scheme request had not started, so it provided no cancellation evidence. The
recorded failing verification requires an actual delayed scheme-start. The
final harness waits for that callback before stopping/removing the view.
Each custom run records one start → stop → suppressed-after-stop sequence,
no response/data/finish callbacks for the stopped task and zero pending tasks.
Normal requests finish independently. This exercises the existing public API
rule without inventing a Moonpool lifecycle/teardown contract.

The earlier compiler warning was reproduced: xcrun's implicit macOS SDK conflicted
with the explicit iOS target during linking. Selecting --sdk iphonesimulator at
xcrun as well as swiftc removes the warning. vtool confirms the simulator target;
codesign verification and actual installation/launch supply additional checks.
The global Xcode selection remains unchanged.

## Reproduction and retained evidence

See [the harness instructions](../experiments/ios-origin-probe/README.md) for
explicit simulator ownership and the seed/restart/offline sequence. Never target
booted/all, erase existing data or mutate an unrelated simulator.

Retained [environment](../experiments/ios-origin-probe/results/environment.json)
and the five JSON reports include the executable, native/runner/build sources,
adapted/base JS and complete fixture-file hashes. The Android source/evidence is
unchanged. JSON reports retain public markers, resource statuses, navigation
callbacks, source-frame origins and scheme-task bookkeeping, without credentials
or device ids. A WebKit-owned https scheme is not registered by this probe.

```sh
python3 experiments/ios-origin-probe/verify_results.py experiments/ios-origin-probe/results
pnpm run check
```

The verifier checks controls and claimed storage results, including a self-access
positive before foreign denial. Custom-scheme cookies remain an explicit gap.
Root checks cover the existing TypeScript/Python suites, typechecks, Biome and
browser builds; they are separate from the simulator observations. pnpm run check
passes 1134 TS tests / 40 files, 9 Python tests, both typecheck targets, lint and
both example builds. The known nonblocking Vite config-loader warning remains.

## Next task boundary

T24 completes bounded iOS research. T25 (Android channel/authentication) and T26
(iOS messages/replies/content worlds) are the next paired evidence tasks; neither
ran in this session. T27 selects trusted kernel ownership/runtime and T28 must
resolve Android incompatibility, iOS cookie limitations and origin/loader rules
with explicit approval. SPEC and accepted ADRs remain unchanged.

Primary API references: [WKURLSchemeHandler](https://developer.apple.com/documentation/webkit/wkurlschemehandler),
[scheme-task cancellation](https://developer.apple.com/documentation/webkit/wkurlschemehandler/webview(_:stop:)),
[frame securityOrigin](https://developer.apple.com/documentation/webkit/wkframeinfo/securityorigin),
[persistent website data store](https://developer.apple.com/documentation/webkit/wkwebsitedatastore/default()).
These describe API contracts; measured results above come from the retained probe.
