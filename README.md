# Moonpool

An MIT runtime for isolated web mini apps behind an asynchronous, permissioned
bridge. Moonpool targets embedding inside native apps; its current implementation
proves the protocol in a browser reference host.

**Status:** the browser v0.1 milestone is complete (2026-10-26). See the
[completion and conformance record](docs/v0.1-conformance.md) for requirements,
evidence and scope. Protocol 0.1 remains draft/unstable. The deliverable is the
source workspace; its packages are private and export TypeScript source.

## What it does

A moonpool is a controlled opening in a ship's hull. Here, that opening is a
small bridge through which an isolated mini app can request host capabilities.

- Each mini app has a stable, distinct origin. One host page can contain Portals
  with different origins.
- JSON-RPC 2.0 carries every request/response. The host checks initialization,
  granted scope and input before invoking a capability.
- All capability calls return Promises. The kernel owns protocol logic; the
  embedder supplies asynchronous profile/storage implementations and UI lifetime.
- The reference browser host uses one trusted served wrapper per Portal, each
  with its own enforcing CSP and bound connection. Host-held app data survives
  Portal recreation while the memory provider remains alive.

## Run the browser example

Use the tested Node 22.19.0 / pnpm 11.1.3 environment and run from the workspace root:

```sh
pnpm install
pnpm run dev
```

Open [http://localhost:5173](http://localhost:5173). The command starts the host
and two fixed mini-app origins on ports 5174 and 5175. Occupied ports fail instead
of drifting. Host buttons select profile-only/storage-enabled grants and open
the second app concurrently. The sample reads a public profile and offers
storage set/get/delete and Portal dismissal. Host reload clears memory storage.

The separate [browser checks](http://localhost:5173/containment-check.html) drive
actual components through the same SDK and demonstrate failure/positive controls.
CSP response headers and the trusted wrapper are required parts of this setup.
Use the served example rather than opening HTML through `file://`.

## Client API

Inside an embedded reference mini app, the immediate parent is its trusted
host wrapper. The host origin is pinned by configuration:

```ts
import { createClient } from '@moonpool/client';
import { createIframeTransport } from '@moonpool/transport-iframe';

const client = createClient({
  transport: createIframeTransport({
    peerWindow: window.parent,
    peerOrigin: 'http://localhost:5173',
  }),
});

await client.initialize();
const profile = await client.call('profile.get');
```

These imports are workspace APIs. Generic call results are unknown; the example
checks the fields it renders. The host connection handle sends `portal.lifecycle`
(`resumed`/`paused`) through `notifyLifecycle`, and `portal.environmentChanged`
(`locale`/`colorScheme`) through `notifyEnvironmentChanged`. The embedder owns
timing. `client.onNotification` registers a subscriber and returns its unsubscribe
function.

## Architecture

The normative contract is [SPEC.md](SPEC.md). Protocol, client and host are pure
TypeScript packages with no third-party runtime dependencies. Their only shared
package dependency is `@moonpool/protocol`. Browser APIs live in the iframe adapter
and embedding example; the kernel typecheck omits the DOM library.

The complete transport boundary has three methods:

```ts
interface Transport {
  send(message: JsonValue): void;
  onMessage(handler: (message: JsonValue) => void): () => void;
  close(): void;
}
```

| Owner | Responsibility |
| --- | --- |
| Outer host | Trusted app/origin/grant registry, Portal lifetime, retained providers and app-partitioned storage |
| Per-Portal trusted wrapper | Narrow CSP, local host kernel/configuration/sender, provider facades and transport |
| Mini app | Client and application UI on its distinct origin |

The kernel supplies storage ownership from the manifest id. A caller selects a
key, never another app's partition. Different apps are separated; instances of
the same app share data and keep separate connections. Cross-realm host data
uses validated JSON snapshots, while guest requests retain staged validation.

## Browser v0.1 completion

- [x] Transport interface and iframe adapter
- [x] Client request encoding, correlation, timeouts and error mapping
- [x] Host dispatcher, manifest parsing and scope enforcement
- [x] Version negotiation and repeat handshake
- [x] `portal.*`, `profile.get` and `storage.*`
- [x] Runnable mock host and hello mini app
- [x] Meaningful client coverage for all 14 error codes and current producer tests

[Requirement-to-evidence map](docs/v0.1-conformance.md) ·
[error-code matrix](docs/error-code-matrix.md) ·
[final browser/security verification](docs/browser-integration-verification.md) ·
[implementation plan](docs/implementation-plan.md) ·
[Korean learning guide](study/index.html)

## Android and iOS follow-up — planned

The [native implementation plan](docs/native-implementation-plan.md) breaks the
next phase into T22–T65, with both Android and iOS required. The host framework
remains undecided. Early tasks measure platform constraints and establish the
trusted TypeScript execution context before native implementation.

The plan separates reference-app PoCs, actual-host/device verification and an
evidence-based deployment decision. These are planned milestones, not shipped
native support. T22's [target/toolchain inventory](docs/native-target-matrix.md)
is complete; T23/T24 are next. See the [Korean roadmap](study/27-native-roadmap.html).

## Verification

```sh
pnpm test
pnpm run typecheck
pnpm run lint
pnpm run build
```

T20 passed 1131 tests across 39 files, both typecheck targets plus the research
lab typecheck, Biome and both example builds. Native browser observations cover
the recorded Chrome 156 configuration, including final built-preview checks.
The conformance record links each requirement to source/tests/browser evidence.

## Scope and retained limits

Browser HTTP origins are a development exception under SPEC §8.1.1. Production
origins remain `moonpool://<mini-app-id>/`; native cores and production HTTPS
hosting have separate implementation/verification requirements. The current
milestone does not establish support for other browser configurations.

[SPEC §11](SPEC.md#11-open-questions) retains document epochs, peer disconnect,
consent, throttling and other open questions. Multiple-origin Portal composition
works; inter-Portal messaging/broadcast is still unspecified. Four error codes
have receiver coverage without current emitters, as the error matrix records.
The memory provider is development storage, and frame removal is not a GC or
performance guarantee. Distribution, signing and live updates remain out of scope.

## Contributing

Start with SPEC.md, [CLAUDE.md](CLAUDE.md) and the conformance record. Record
non-obvious decisions in docs/adr/, write tests before implementation, and
preserve the pure kernel/platform boundary. Protocol feedback should identify
an existing requirement, observation or explicitly unresolved question.

## License

MIT
