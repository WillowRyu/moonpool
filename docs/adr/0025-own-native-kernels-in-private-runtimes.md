# 25. Own native host kernels in private JavaScript runtimes

Date: 2026-11-02
Status: Accepted — framework-neutral native SDK/runtime model selected by the
maintainer; production integration and support limits remain later tasks.

## Context

The existing TypeScript kernel must stay authoritative and platform-independent.
Swift/Kotlin apps do not automatically supply a trusted JS runtime. T25/T26
measured guest sender/document behavior, and showed why origin, frame and runtime
lifetime differ. The host framework was deliberately undecided. T27 now needs
a specific host/runtime model before native implementation proceeds.

[Runtime probes](../trusted-runtime-verification.md) execute the unchanged real
kernel in JavaScriptCore and Android JavaScriptSandbox. They prove functional
language/scheduler compatibility and captured native owner fencing with public
provider fixtures. They are not production native-provider/transport integration.

## Decision

Choose framework-neutral native facades as the reference host model: Swift on
iOS and Kotlin-facing APIs on Android. Consumer app selection remains T56; this
does not require rewriting an integrating app or scaffolding an RN wrapper now.
Native, React Native and Flutter apps can build on this same native SDK model.
RN/Flutter require their own bindings to the Swift/Kotlin facade; no such binding
is implemented or verified by T27. This selects the SDK foundation, not all host
framework integrations or SDK packaging.

| Owner | Responsibility |
| --- | --- |
| Native host manager | Trusted app/config registry, retained app-partitioned providers, credentials and engine resources |
| Native Portal handle | One guest WebView, authenticated native transport, private host-runtime owner and bound controls |
| Private runtime | TypeScript Host/HostConnection/config and asynchronous provider facades; never guest scripts |
| Guest WebView | Mini-app code and TypeScript Client, with no private runtime/control references |

Use one JavaScriptCore VM/context and serial native queue per iOS Portal runtime.
Use one library-owned JavaScriptSandbox connection per Android application and
one JavaScriptIsolate per Portal runtime, with serialized owner-bound commands.
Android pins JavaScriptEngine and checks support before creating a host runtime.
Unsupported configurations fail closed; no implicit guest-realm/legacy fallback.

The native app packages the trusted host bundle produced from the shared kernel;
the guest package contains only guest/client code. Native transport checks actual
origin/frame/instance before forwarding data to the bound host owner. Public
control/provider snapshots cross as validated JSON text. Credentials stay in
native providers; guest ids/messages cannot select config, grants or partitions.
Do not expose raw JS contexts or HostConnection objects as guest handles.

Keep the host runtime across allowed guest document replacement, retaining
Portal/origin state. ADR 0024/T30 supplies the guest document-generation contract.
Portal retirement is terminal: invalidate owner-bound handles before cleanup,
drop queued old-owner work and release its realm/isolate/timers. Retained providers
outlive disposable Portal runtimes; retirement does not roll back accepted work.

## Consequences and alternatives

This supports ordinary Swift/Kotlin hosts with the same TypeScript kernel, without
duplicating dispatch in native languages or assuming React Native. Costs include
engine lifecycle/scheduler/provider adapters and Android provider availability.
Android sandbox loss can terminate multiple isolates; iOS JSC runs inside the app
process. Realm/VM separation is not a universal process-failure boundary.

An RN-only host could reuse its trusted app JS runtime and avoid a separate engine
owner, but would require RN as the host framework and a separate actual Hermes
trial. It was not measured here. A trusted host WebView is another possible native
backend, with view/rendering overhead; it is not the tested/default fallback.
An isolated world inside the guest WebView shares its DOM/document lifetime and
is not chosen as a long-lived host owner.

The maintainer selected the generic native option while confirming its intended
applicability beyond RN. T28–T31 still define loader/bootstrap, codec, document
identity and failure/close rules.
T35 must implement/test a production scheduler/host-bundle ABI; the probe's polling
adapter is not adopted. T42/T43 integrate real native providers. T53 measures
resource/pool defaults. No product minimum OS, memory limit, wire field or public
SDK implementation is decided here. JSON-RPC/Transport and pure package rules
remain unchanged; this decision concerns SPEC §3 / §9 ownership boundaries.
