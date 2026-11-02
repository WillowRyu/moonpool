# T27 — Trusted host runtime evidence and selection

Date: 2026-11-02 (Asia/Seoul)
Status: T27 complete; native facade/private-runtime model selected in ADR 0025.
Baseline: b4b7721, after requested four-commit publication and clean remote sync.

## Selected host model

[ADR 0025](adr/0025-own-native-kernels-in-private-runtimes.md) selects native,
framework-neutral Portal facades with a private TypeScript host runtime. It keeps
guest code/client in the guest WebView and the real host kernel outside that
realm. Native registry/providers retain identity, grants, data and credentials.
The choice is SDK/reference-host architecture, not selection of a real consumer
repository; that remains T56.
RN and Flutter can use the same native SDK foundation through their own bindings.
Those bindings are separate work, with no framework integration verified here.

| Candidate | Benefit | Cost / evidence |
| --- | --- | --- |
| Native facade + iOS JavaScriptCore / Android JavaScriptSandbox | Works without an RN host; executes one common TS kernel in private DOM-free runtimes | Actual compatibility measured here; adapters/support checks and engine lifecycle required |
| RN-host JS runtime | Reuses the existing trusted app JS environment when the host is RN | Requires RN selection and actual Hermes/runtime proof; not measured here |
| Private host WebView | Available browser primitives in a separate trusted realm | Extra view/rendering/lifecycle cost; comparison only, no adopted fallback |
| Named world in guest WebView | Separate globals, already measured in T26 | Shared DOM/document lifetime; does not independently retain host state across guest replacement |

## Tests and measured runtimes

The [probe](../experiments/trusted-runtime-probe/README.md) records R01–R12 before
native implementation. A Node VM contract test first failed for the missing
runtime entry, then both tests passed with the real kernel. The same 37 KB IIFE
bundle imports existing protocol/client/host sources and the host-only JSON
snapshot helper without modifying them. Native build hashes identify the exact
packaged bundle and sources; no source-map/user path is retained.

| Platform | Actual measured configuration |
| --- | --- |
| iOS | Xcode 26.4.1 / SDK 26.4; dedicated iPhone 17 Pro simulator, iOS 26.4.1 / 23E254a; arm64 JSC; Swift language mode 5 |
| Android | API 37 / Android 17 / CP21.260330.012, arm64/16KB; WebView 145.0.7632.218; JavaScriptEngine 1.1.1 support true |
| Android build | T23 Gradle 9.6.1 wrapper, AGP 9.3.1, Studio JDK 21.0.10, compile/target 36, Build-Tools 36.0.0, probe min 31 |

Google's JavaScriptEngine 1.1.1 was added only to the standalone experiment.
Official Maven resolution was needed once; the subsequent offline build/lint
passes. Pure package/root dependencies and APIs remain unchanged. The iOS target
minimum 17.0 and Android min 31 are probe settings, not a product support matrix.

Four native runs (iOS/Android first/repeat) each create three native-owned runtime
instances. In total, 12 owners execute 180 common-kernel checks; 120 evidence
assertions validate reports/source hashes. Two Node VM contract tests also pass.

Per owner, the real kernels exercise language/Reflect/descriptor/JSON behavior,
getter rejection, initialize, ping, profile projection, seeded storage fixture,
invalid JSON before provider invocation, permission denial, host notifications,
provider-error sanitization, client timeout, timer cancellation and microtask
ordering. No window/document global exists in the tested engine contexts.

Native observations confirm queue/executor use, terminal owner retirement and
dropping a scheduled native test control captured for the old owner. Controls
never redirect through a global current-runtime lookup. A separate diagnostic
realm lacks the private kernel control global. Native owner-created public
fixture snapshots seed recreated A while B starts separately.

## What the evidence does not establish

- The real Client and provider test doubles run inside the trusted fixture to exercise the
  real kernels. The production Client belongs in the guest. No actual native
  capability provider, app account, durable storage or authenticated guest
  transport is integrated by these tests; those remain T40–T43 and T48–T50.
- Snapshot seeding is orchestration evidence, not simultaneous provider sharing
  or durability. The separate diagnostic realm is not a full guest security test.
- The scheduler is a probe-only Native-driven polling shim. It demonstrates the
  required functional vectors and a private host-diagnostic sink; exact timer
  task/error semantics, event-driven production implementation, background
  throttling, performance and all queue interleavings remain to be specified
  and tested in T29/T31/T35. No production polling policy is selected.
- Android isolate support depends on the provider. One sandbox is shared, so a
  sandbox crash can affect all its isolates. JSC is in the iOS application
  process. Renderer/engine loss, resource caps and recovery are not tested here.
- Current protocol 0.1 remains unchanged, including its three intentionally red
  document-generation safety assertions. Runtime compatibility is not generation
  implementation, native conformance or approval of an origin change.

The initial Android lint found an API-33 readAllBytes call against probe min 31.
It was replaced with a compatible stream read; the final native build/lint passes
with 11 documented warnings (seven UI text, target SDK, dependency freshness,
backup configuration and icon). Gradle deprecation notes remain. Swift build,
ad-hoc signature, installed executable/APK and common asset hashes are verified.

Only the retained owned simulator and separately booted existing probe AVD were
installed/launched/stopped. Pre-existing user emulators and other simulator states
were excluded/preserved. No SDK/image install, credential, certificate bypass,
JavascriptInterface, native dispatcher or untrusted host-runtime script is used.

## Selection and next tasks

The maintainer selected the native facade/private-runtime model in ADR 0025
after reviewing the concrete options and confirming intended reuse by native,
RN and Flutter hosts. The [plan](native-implementation-plan.md)'s T27 SDK/runtime
selection gate is satisfied. This does not select a real app or implement its
framework binding. Real-app/framework selection is still T56; production SDK
work and support/resource limits remain later gates.

Next is T28's native origin/loader/bootstrap contract, followed
by codec/document/lifecycle decisions and shared implementation. No framework
binding, production scheduler, guest-origin mapping or wire metadata was added.

Primary references: [JavaScriptCore VM ownership/threading](https://developer.apple.com/documentation/javascriptcore/jsvirtualmachine),
[Android JavaScriptEngine lifecycle/support](https://developer.android.com/develop/ui/views/layout/webapps/jsengine),
[Google 1.1.1 artifact metadata](https://dl.google.com/dl/android/maven2/androidx/javascriptengine/javascriptengine/1.1.1/javascriptengine-1.1.1.pom),
[React Native runtime environments](https://reactnative.dev/docs/javascript-environment).
