# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-09-04, storage.get/set typed by the maintainer and verified
> GREEN: 106 tests passed, typecheck and lint clean. Null policy is SPEC §6.3 /
> ADR 0004. Added missing rationale comments at the maintainer's request and
> recorded the comment standard below. Next: storage.delete. Study mode: junior.

## How we work (do not skip)

- **Tutor mode ("study coding mode"), level: junior — implementation-first
  (agreed 2026-08-19).** Division of labor: **The coding agent writes and maintains
  the tests; the maintainer TYPES the implementation code.** Explanations
  start from the running code ("what does this thing do"), then point at
  which tests cover it. Larger steps than before; the reward of each step is
  red tests turning green. The coding agent reads and verifies the maintainer's typed
  code after every step.
- Explanations at junior level: define every term in plain language with an
  analogy — but don't shrink the steps.
- **Refined 2026-09-02, after the maintainer asked "이거 스터디 모드 맞아?".**
  Every handover has, in this order: (1) the design and the why; (2) a
  glossary table for the step's NEW terms — plain definition plus an analogy;
  (3) the exact snippet to type, with a why per line (the maintainer asked
  for the code itself: "don't write the code for them" means don't Edit/Write
  it into the implementation files, not withhold it); (4) the concrete check
  with the expected test delta; (5) two to four named deep-dive offers. A
  handover missing (2) or (5) is the regression they noticed. Deep-dives are
  answered in prose unless they ask for HTML. `study/*.html` are gitignored
  personal notes and do NOT travel between machines.
- **Refined 2026-09-04 — keep the rationale in the code too.** The maintainer
  pointed out that the storage handovers had fewer useful comments than the
  existing code. Include English documentation comments with handover snippets
  for public contracts, wire types, guards, and invocation helpers where their
  purpose or constraints need explanation. Cite SPEC/ADRs and explain the
  security/portability rationale, input/output semantics, and important limits.
  Add inline comments where ordering or a subtle check matters (for example,
  identity selection, null versus falsy values, and awaiting write completion).
  Avoid merely translating syntax into prose. Chat explanations supplement
  these comments; they do not replace them. The agent can maintain requested
  comments without changing the maintainer's implementation logic.
- Dialogue in Korean, repository artifacts in English (see CLAUDE.md).

## Where we are (v0.1)

Done:

- pnpm workspaces skeleton per the CLAUDE.md repository layout
  (`packageManager` pinned to pnpm 11; internal deps use `workspace:*`;
  on a fresh machine run `corepack enable`, then `pnpm install`).
- TypeScript 7.0.2 (note: TS7 removed `baseUrl`; `paths` are `./`-relative
  now; `noUncheckedIndexedAccess` is ON — indexing gives `T | undefined`),
  Vitest 3. `npm run typecheck` passes.
- `packages/protocol`: real content — `Transport` interface (SPEC §3.1),
  `ERROR_CODES` (§4.4), `PROTOCOL_VERSION`, §5/§7 types.
- Biome 2.5.9 as the single formatter + linter (`npm run lint`,
  `npm run lint:fix`); `.vscode/` recommends the Biome extension with
  format-on-save. Chosen over Prettier+oxlint to keep one tool/one config.
- Test-writing roadmap: complete. All 10 §5 tests exist (7 host + 3 client);
  the in-memory linked Transport pair helper
  (`packages/host/test/helpers/memory-transport.ts`) delivers async
  (microtask), mirroring postMessage semantics.

### Phase: implementation to green

The maintainer types the implementation and watches reds turn green.

Implementation roadmap:

- **A. Host gate — DONE 2026-08-19.** Maintainer typed it; Claude verified.
  Replies -32005 to every request, ignores notifications (§4.1).
  `pnpm test` → 3 passed / 7 failed exactly as predicted (smoke, -32005
  gate, no-service-after--32004 green; the rest now fail as assertion
  diffs, not "Not implemented").
- **B. Host initialize — DONE 2026-08-19.** Maintainer typed it; Claude
  verified. All 7 original host tests green; lint and typecheck clean.
- **C. portal.ping + unknown-method reply — DONE 2026-08-20.** Two tests
  added by Claude (ping → `{ pong: true }` per §6.2; unknown method →
  -32601 — §4 forbids silence for id-bearing requests, and §4.4 coverage
  is in the v0.1 definition of done). Maintainer typed the two branches
  below the -32005 gate. Suite: 9 passed / 3 failed; lint + typecheck
  clean. Host suite fully green.
- **C2. Refactor under green — DONE 2026-08-20.** Typed `JsonRpcRequest` +
  `isJsonObject`/`isJsonRpcRequest` guards and `PORTAL_METHODS` constants in
  protocol; host reads through them. Tests stayed 9 passed / 3 failed as
  required. Committed as `refactor:`.
- **D. Client — DONE 2026-08-20.** Maintainer typed it; Claude verified.
  `MoonpoolError` (client-local), `Pending` map keyed by id, `nextId` from 1,
  one `onMessage` return desk registered at construction, §4.5 unknown-id
  replies ignored. `isJsonRpcResponse` + `JsonRpcResponse` added to protocol.
  `call()` params narrowed from `Record<string, unknown>` to
  `Record<string, JsonValue>` — the bridge carries JSON only. **All 12 tests
  green.**
  - Regression caught during this step: `isJsonRpcRequest`'s body was
    overwritten with the response-checking logic (paste accident), which
    silently broke 8 host tests while `typecheck` stayed clean. Lesson worth
    keeping: a type predicate is an *unchecked assertion* — `return true`
    compiles — so guard bodies must be covered by tests.
- **D2. Client timeouts (§4.5) — DONE 2026-08-20.** Tests by Claude
  (`packages/client/test/timeout.test.ts`); maintainer typed the
  implementation. `setTimeout`/`clearTimeout` are declared as module-local
  ambient globals in the client rather than pulling in `"DOM"` or
  `@types/node`, which would also make `window`/`process` compile inside the
  pure packages. 16 passed / 0 failed.
- **D3. Connection teardown (§4.6) — DONE 2026-08-20.** Spec gap resolved
  with maintainer approval and SPEC.md updated first (`b7ebde9`): new
  `-32008 CONNECTION_CLOSED` in §4.4, new §4.6, new §11 entry. Tests by
  Claude (`packages/client/test/close.test.ts`); maintainer typed
  `ERROR_CODES.CONNECTION_CLOSED` and the `close()` drain. **20 passed /
  0 failed.**

- **E0. -32600 for malformed id-bearing frames — DONE 2026-08-24**
  (`a41bd89`). New `hasRequestId` envelope guard in protocol; the host now
  answers `-32600` (echoing the id) instead of silently dropping id-bearing
  malformed frames. Notifications and non-objects stay silent (§4.1).
  28 passed. See "Why two id checks" below.
- **E0.5. §4.1 id profile: positive integers — DONE 2026-08-24**
  (`1fbe68e`). Maintainer typed the guard tightening (`typeof` +
  `Number.isInteger` + `> 0` in `isJsonRpcRequest`; `hasRequestId`
  untouched). id 0 / -5 / 3.7 / NaN now answered with -32600, echoing the
  id. **32 passed.** Uniqueness/monotonicity deferred twice over: needs
  per-connection state (host-level, cannot live in the pure guard), and §4.1
  binds only the SENDER — the receiver's response code for a reused id is a
  genuine spec gap needing a maintainer decision first (tracked in Open
  decisions).

### Current status

Before E4.3: **73 passed**, `typecheck` and `lint` clean.
After storage.get: **85 passed**, `typecheck` and `lint` clean. The maintainer
typed the complete read slice and the agent verified it on 2026-09-04.
Current: `pnpm test` → **106 passed**, `typecheck` and `lint` clean after the
maintainer typed storage.set. Both get and set are implemented; delete is next.
The browser example still has no capability providers.
The kernel, the first platform adapter, a real cross-origin bridge between the
two examples, and now the permission gate with the first scoped method are
done. **E4.3 (`storage.*`) is in progress**, then E4.4 (remaining params guards), then
the example update and an ADR.

v0.1 definition of done, remaining:

- [x] `packages/transport-iframe` — the first real platform adapter
      (`iframe` + `window.postMessage`). Landed in E2/E2.1.
- [x] `examples/mock-host` + `examples/hello-miniapp` running in a browser.
      Landed in E3; a real §5 handshake crosses a real origin boundary and
      survives Portal reloads.
- [ ] Capabilities `profile.get` and `storage.*` (§6.3) — `profile.get`
      landed in E4.2 with the gate; **`storage.*` is E4.3, the current
      piece.**
- [ ] Remaining §4.4 error-code coverage (`-32600` for malformed id-bearing
      frames landed in E0; still open: `-32602` for non-object `params`,
      batch arrays via `id: null`, id uniqueness per connection)

**The permission gate exists and runs as of E4.2 (2026-09-02).** The
paragraph that stood here recorded that scope enforcement had never run and
that `-32000` appeared nowhere in the codebase. Both are fixed;
`packages/host/test/permission-gate.test.ts` is the proof. The framing it
gave is still the right one for the rest of E4: SPEC §6.3 calls the v0.1
capability set "deliberately minimal … the goal is to exercise the permission
model", so the capabilities are the vehicle and the gate is the cargo.

**Why E was a different kind of work** (kept as the rationale for how E1–E2
were sequenced). Everything before it was verified over an in-memory linked
Transport pair. Real `postMessage` is the first time §8 (origin) and §9
(security requirements) actually bite: origin checking on every inbound
message, the `moonpool://<mini-app-id>/` origin rule, structured clone vs
JSON serialisation, and iframe sandbox attributes. E is not a continuation
of the client work — it is the first platform adapter, and it is the piece
the native ports will be measured against.

### Why two id checks (decided 2026-08-24)

`hasRequestId` answers the postal question — "is there a numeric id we can
echo a reply to?" (it exists so `-32600` replies can be built at all).
`isJsonRpcRequest` answers the conformance question — "did the sender follow
the §4.1/§4.2 profile?". Profile tightenings (positive integer now; anything
later) go ONLY on the conformance side: if the envelope check shared them, a
frame with a non-conformant id would be silently dropped as if it were a
notification — violating "every id-bearing frame gets exactly one reply".
They overlap textually today for different reasons; do not merge them.

### §8.1 decision — dev-transport origins (approved 2026-08-24)

Browsers cannot register custom scheme handlers, so the dev transport cannot
serve `moonpool://`. §8's real invariant is per-app uniqueness + stability,
not the scheme itself. SPEC now has §8.1: dev transports MAY substitute
per-mini-app http origins (fixed localhost port per app), the id→origin
mapping MUST be pinned (drifting ports silently re-key storage), and host
and Portal MUST be cross-origin even in dev — a same-origin Portal would
make the §9.1 origin check pass vacuously. Alternatives rejected:
`*.localhost` subdomains (Safari friction), sandboxed opaque origins
(isolation without identity — kills the mini app's own storage, which §8
exists to protect).

- **E1. Dev plumbing — DONE 2026-08-25.** Claude filled it (pure config, per
  the tutor-mode division of labor); maintainer chose the stack.
  - **Vite 8.2.2** in both examples with PINNED ports (`strictPort: true`):
    mock-host 5173, hello-miniapp 5174 — SPEC §8.1. Verified: a second
    server on a taken port now fails loudly instead of hopping to 5175.
  - **vitest upgraded 3.2.7 → 4.1.11** so the workspace holds ONE Vite (8).
    vitest 3 pinned vite 7 transitively; leaving it would have meant the dev
    server and the test transform pipeline running different Vite versions.
    32 tests stayed green across the major bump. biome 2.5.9 → 2.5.10
    (`biome migrate` applied to biome.json).
  - **tsconfig split**, and this is load-bearing: root `tsconfig.json` now
    lists protocol/client/host explicitly and still has no DOM lib, so
    `window`/`document` do not typecheck there. `tsconfig.browser.json` adds
    `DOM` + `DOM.Iterable` for transport-iframe and the examples only.
    `pnpm run typecheck` runs both projects.
  - Examples are vanilla TS (maintainer's call): a framework would make the
    reader separate bridge code from framework code, and would signal to
    mini app authors that one is required.
  - Verified in a browser: mock-host embeds the hello Portal cross-origin,
    both render `PROTOCOL_VERSION` from the workspace package, no console
    errors. Root `pnpm run dev` starts both in parallel.

- **E2. iframe transport — DONE 2026-08-26.** Tests by Claude
  (`peer.test.ts` pure, `iframe-transport.test.ts` under happy-dom);
  maintainer typed `src/peer.ts` and `src/index.ts`. **52 passed.**
  `happy-dom` 20.11.6 added at the root for this step.

### E2 design rationale — reread this before answering questions on it

**One factory, not two.** The plan said the host side and the Portal side
would be separate, asymmetric Transport implementations. Writing the tests
showed the difference collapses to a single argument: both post to a peer
window, both listen on their own window, both pin one origin. So there is one
`createIframeTransport({ peerWindow, peerOrigin, localWindow? })`. The
asymmetry is real but lives at the CALL SITE — the host passes
`iframe.contentWindow`, the Portal passes `window.parent` — which is where
"who is my peer" is actually known. Two near-duplicate factories would have
duplicated mechanism to express a difference in knowledge.

**`PeerWindow` is a one-method structural type**, not `Window`. Depending on
the narrowest interface makes the package's real platform surface visible in
the type, and lets test stubs satisfy it without a cast.

**Why `isFromPeer` is a separate pure module.** It is the entire answer to
"did this come from the other end?", and `window`'s `message` event is a
public mailbox — any frame, popup, or embedder on the page can post to it.
Keeping the decision DOM-free means it is not verified through happy-dom's
approximation of postMessage. The wiring test then supplies `event.origin`
and `event.source` synthetically, so a test can pose as a hostile frame —
something an emulator's own postMessage will never do for you.

**The three checks, and what each one alone would miss:**

| Check | Missing it admits |
| --- | --- |
| `event.origin === peer.origin`, exact | `startsWith` accepts `http://localhost:51740` and `http://localhost:5174.evil.com` |
| `event.source === peer.window` | a second frame on the peer's own origin — origin says which house, never which room |
| both origins `!== "null"` | every sandboxed iframe on the web reports `"null"`; accepting it admits anonymous senders. Refused on the CONFIG side too, so a misconfiguration cannot opt in |

A peer origin written with a trailing slash matches nothing, by design:
exact comparison makes a misconfigured origin check fail closed. Normalising
it would be the kind of helpfulness that grows bypasses.

**`targetOrigin` is pinned, never `'*'`.** The second argument to
`postMessage` is a browser-enforced delivery condition, and it is the last
line of defence behind §9.2 navigation containment: if the Portal navigated
away, the frame is not delivered at all. `'*'` would hand every frame —
handshake results included — to whoever is there instead.

**`event.data as JsonValue` is a cast, not validation, and that is correct.**
§3.1 forbids a transport from modifying payloads, and the kernel already
proves frame shape at its own boundary (`isJsonRpcRequest` /
`isJsonRpcResponse`). Validating here would duplicate the trust boundary
instead of respecting "check once, at the door".

**Handler set, one window listener.** Same shape as the client's `pending`
map: one listener for the connection rather than one per handler (per-handler
listeners are O(n²) on every inbound message and leak if not detached), and
the handler set is snapshotted before iteration because a handler may
unsubscribe mid-iteration — the same discard-before-settle discipline used in
`client.close()`.

### E2.1 — handler isolation on throw — DONE 2026-08-28

**The defect.** `createIframeTransport` fans out to `handlers` with a plain
`for` loop inside ONE window listener. If a handler throws, the loop aborts
and every handler after it is skipped. That is a WEAKER guarantee than the
platform's own: the browser isolates each registered listener from the
others.

**Measured, not assumed** (Chrome, 2026-08-26):

| Setup | Ran | Exception escaped `dispatchEvent`? |
| --- | --- | --- |
| Three separate `addEventListener` listeners, 2nd throws | L1, L2-throws, **L3** | no — browser reports it as an uncaught error and continues |
| One listener iterating three handlers, 2nd throws (our shape) | H1, H2-throws — **H3 skipped** | no — caught at the listener boundary |

Note happy-dom let the exception escape `dispatchEvent` where Chrome did not;
another reason the origin decision lives in a DOM-free module.

**Impact today: none** — exactly one handler is ever registered (the kernel's,
via `client`/`host`). It bites the moment a second one exists, which is the
very use case the handler Set is for (attaching a bridge logger without
touching the kernel). Then correctness starts depending on registration
order: kernel-then-logger loses the log exactly when a kernel throw makes it
most needed; logger-then-kernel lets a bad logger silently stop the bridge.

**Decision: fix it, per-handler `try`/`catch` that re-throws asynchronously**
so the error still surfaces as an uncaught error / `window.onerror`. Isolate
without swallowing — swallowing would be the silent-callback antipattern, and
the browser's own semantics (table above) are the target to match.

Rejected: leaving it (the trap outlives the memory of it, and this is the
cheapest moment to fix); a bare `try`/`catch` that swallows (hides bugs).

**Shipped.** Tests by Claude (two, appended to `iframe-transport.test.ts`);
maintainer typed the per-handler `try`/`catch`. **54 passed.**

**Why `queueMicrotask`, decided while writing the tests.** Three candidates
for "re-throw asynchronously", measured rather than assumed:

| Candidate | Verdict |
| --- | --- |
| `reportError(e)` | The exact primitive — WHATWG's "report an exception" as a public API. **Undefined in happy-dom AND in Node 22**, so it cannot be tested here. `lib.dom.d.ts` declares it, so it typechecks and then throws at runtime |
| `setTimeout(() => { throw e })` | Works, testable via `vi.runAllTimers()`. Rejected: background tabs clamp timers to 1000ms+, so a bridge error could be reported a second late; and `setTimeout` already means *real elapsed time* in the client's §4.5 timeout — reusing it here makes one name carry two intents |
| `queueMicrotask(() => { throw e })` | **Chosen.** No clamping, reported in the same event loop turn as the frame that caused it, and the name says "get off this stack" and nothing else. Testable via `vi.useFakeTimers({ toFake: ['queueMicrotask'] })` + `vi.runAllTicks()` |

Not `Promise.resolve().then(() => { throw e })`: that produces an
**unhandled rejection**, not an uncaught error. Different event
(`unhandledrejection` vs `error`). Correction 2026-09-02: modern collectors
(Sentry's `GlobalHandlers`, Datadog RUM) hook BOTH by default, so the
argument is not "it would be missed" but "it would be reported worse" — a
rejection is grouped separately and, when its reason is not an `Error`,
arrives with no stack ("Non-Error promise rejection captured"); a re-thrown
uncaught error carries the original stack. And Promise jobs cannot be faked
by `vi.useFakeTimers`, so the `then` form is untestable here.

No `reportError ?? queueMicrotask` fallback: the branch would be untestable
in one direction here, so production would run a path the tests never touch,
with different timing (synchronous vs microtask) from the one they prove.
**Transition trigger:** the day a real-browser test runner (Playwright or
equivalent) lands, switch to `reportError` with no fallback branch and assert
via `window.onerror`. That switch is an ADR.

**A third test was written and deliberately dropped:** "two throwing handlers
are both reported". Under sinon fake timers a second `vi.runAllTicks()`
re-throws the FIRST error, which is a fake-timer artifact, not browser
behavior. The property is real (the spec continues the microtask checkpoint
past a throw) but this harness cannot honestly assert it. Same lesson as the
happy-dom `dispatchEvent` divergence above: **a fact measured through a fake
is a fact about the fake.**

### E3 — connect the examples — DONE 2026-08-28

Maintainer typed both sides; verified in a real browser, not only in tests.
`3e556ea` (examples), `225fd21` (SPEC §5.1), `71e1262` (host fix).

**The load race described in the previous handoff does not exist.** SPEC §5
says "the mini app initiates", so the host never sends first, and the host
attaches its listener in the same synchronous task that creates the iframe —
a parent script runs to completion before any script inside the iframe can
run. The ordering is a guarantee, not luck. It holds only while the host
attaches synchronously: an `await` before `createIframeTransport` would give
it away.

The race is real for §6.4 host-initiated notifications (`portal.lifecycle`,
`portal.environmentChanged`) — no id, no reply, so a lost one is undetectable.
Not reachable today: `Host` exposes only `connect()`. Revisit when §6.4 lands.

**Measured, correcting a claim made twice in session.** It was asserted that
an iframe's `load` fires after the new document's first `postMessage`, so a
`load`-based reload detector would always be too late. Wrong: measured 6/6 in
Chrome, `load` fires *first*. Calling `postMessage` and delivering the message
are different events, and delivery is a separate task. The argument against a
`load`-based detector is not ordering — it is that `load` (DOM manipulation
task source) and posted messages (posting-message task source) are different
task sources, and HTML lets the UA choose between them, so the order is
unspecified either way. See §5.1 for the wording that survived.

**E3.3 — the repeat handshake.** Reproduced in the browser: reloading the
Portal produced `-32601 unknown method: portal.initialize`, and the bridge
stayed dead for that document's life. Root cause was a wrong assumption in
SPEC §5, not in the code — `connection == document`, which `iframe`'s
WindowProxy makes false. SPEC §5.1 written and approved first, then tests,
then a one-condition fix (`!initialized &&` deleted). Full rationale lives in
SPEC §5.1 and the commit messages; the decisions the maintainer made were:
accept repeat handshakes (over rejecting them, which would break multi-page
mini apps outright), make the reset list **closed** so a wrong judgement fails
safe, and forbid re-prompting for consent.

Two things worth carrying forward:

- **A weak test was written and labelled as weak rather than deleted.** "Leaves
  the connection usable after a repeat handshake" passes both before and after
  the fix, because the pre-fix host kept serving `portal.ping` — only the
  handshake broke. Its comment says so. The test that actually catches the
  defect is the one above it.
- **§5.1's reset boundary is normative but untested**, and the test file says
  that in as many words. Rate-limit counters and consent records name state
  this host does not keep yet. Deliberate: a test that only looks like
  coverage is worse than an honest note.

### Current piece (E4 — capabilities and the permission gate)

`profile.get` and `storage.*` (§6.3), and with them the first real use of
`grantedScopes`. Points to settle before typing:

- **Where does the gate live?** `namespace.action` where the namespace *is*
  the scope (CLAUDE.md invariant — there is no separate scope registry), so
  the check is `grantedScopes.includes(method.split('.')[0])`. It belongs
  above per-method dispatch, below the `-32005` gate. `portal.*` is exempt
  (§6.2, "no scope required").
- **`-32000 PERMISSION_DENIED` vs `-32601 METHOD_NOT_FOUND`.** A host that
  answers `-32601` for a scoped method the caller lacks leaks less (the mini
  app cannot enumerate what exists), but `-32000` is far kinder to debug and
  is what §4.4 reserves the code for. Needs a decision, and it is a §9
  question — flag it as such.
- **Where does `storage.*` actually store?** §6.3 says namespaced per mini app
  id by the host, and §8 binds data to the origin. For mock-host, an
  in-memory `Map` keyed by `${miniAppId}:${key}` is enough and avoids
  implying persistence the spec has not specified.
- The example should call something and render the result, and should show a
  denied call too — `storage.*` is ungranted in mock-host on purpose, so the
  permission model stays visible on screen.

**Decided 2026-09-02** (maintainer's call, after the `study/04` deep-dives
on fail-closed ordering, error-code leakage, dependency injection, and
hand-written params guards):

- **Decision 1 — `-32000`, and the scope check runs BEFORE method lookup.**
  A caller without the scope gets `-32000` for every method in that
  namespace, existing or not, so an ungranted namespace cannot be
  enumerated. Within a granted namespace an unknown method is `-32601`.
  Answering `-32601` for everything ungranted was rejected: the mini app
  already knows its `grantedScopes` from the handshake, so nothing is hidden
  and debuggability wins. This is a §9 decision.
- **Decision 2 — typed capability slots on `HostConfig`**, one per §6.3
  namespace (`profile`, `storage`), each an interface of async methods the
  embedding host implements (mock-host: a constant profile and an in-memory
  `Map`). The kernel validates `params` (`-32602`), answers `-32001` when a
  slot is absent and `-32603` when a handler throws. A generic
  method→handler map was rejected: it moves §9.6 validation out of the
  kernel and is the seed of a plugin system (out of scope for v0).
- Check order after the `-32005` gate: `portal.*` (exact namespace match,
  never `startsWith`) → scope (`-32000`) → known method (`-32601`) → params
  (`-32602`) → handler present (`-32001`) → invoke.
- Storage identity was settled on 2026-09-04: pass app id and key separately
  (decision 4 below, ADR 0003). Unknown extra params fields and value size
  limits remain open for step 4.
- **Refactor candidate, under green, after E4:** `InitializeResult`,
  `HostInfo`, `PortalEnvironment` are `interface`s that cross the wire. They
  compile only because the host builds the handshake result as an object
  literal and the client casts (`result as InitializeResult`); an interface
  has no implicit index signature, so assigning one to `JsonValue` fails
  (verified 2026-09-02 with tsc 7.0.2). Wire shapes should be `type`
  aliases, like `JsonRpcRequest` / `JsonRpcResponse` / `ProfileGetResult`.
  Rule of thumb recorded for contributors: union or alias → `type`; crosses
  the bridge → `type`; a contract for code (methods, config) → `interface`.
- **Open decision, raise at the end of E4:** enable `exactOptionalPropertyTypes`.
  Without it a provider may return `{ avatarUrl: undefined }`, which
  typechecks against `avatarUrl?: string` and then crosses a structured-clone
  transport as a non-JSON `undefined`. Tried on the root project
  2026-09-02: exactly one existing line fails (`packages/client/src/index.ts:39`).

### E4.2 — permission gate + `profile.get` — DONE 2026-09-02

Tests by Claude (`packages/host/test/permission-gate.test.ts`, 16 tests);
maintainer typed protocol and host. **73 passed.**

What landed:

- protocol: `PORTAL_NAMESPACE`, `PROFILE_METHODS`, `ProfileGetResult` (a
  `type` alias — see the interface-vs-type note above).
- host: `HostConfig.capabilities?.profile?: ProfileProvider`, decision 2's
  typed slot. `grantedScopes` (manifest ∩ host grant) is computed once per
  connection, OUTSIDE the message handler, and shared by the handshake reply
  (copied with `[...]`) and the gate — it is origin-scoped consent, so §5.1's
  reset cannot reach it by construction.
- The gate: `method.split('.')[0] ?? ''`, exempt only when
  `=== PORTAL_NAMESPACE`, placed below `portal.ping` and above the `-32601`
  fallthrough. Replies `-32000` with `data: { scope }`.
- `profile.get`: `-32001` when the slot is empty; otherwise `invokeProfileGet`
  awaits the provider inside `try` (catches a sync throw AND a rejection),
  builds the result from the two §6.3 fields only — allowlist on the way out,
  because a provider returning `session.user` satisfies `ProfileProvider`
  structurally and must not leak, and `avatarUrl: undefined` must not cross a
  structured-clone transport — replies `-32603` with a fixed message on
  failure, then re-throws the provider's error via `queueMicrotask`
  (decision 3, same shape and rationale as E2.1). `queueMicrotask` is a
  module-local ambient declaration in host, like the client's `setTimeout`.

Worth carrying forward:

- **The gate was first typed inside the `portal.ping` branch.** Dead code:
  typecheck and lint green, tests unchanged at 9 red. The tests caught what
  the compiler cannot — the same lesson as the D-step guard-body accident.
- Four gate tests pass before the gate exists and say so in their comments.
  They pin the gate's PLACE: below `-32005`, below `portal.*`, before the
  provider call.
- Provider-failure tests live under
  `vi.useFakeTimers({ toFake: ['queueMicrotask'] })`; without it the real
  re-throw fails the run as an unhandled error. `useRealTimers()` discards
  the parked throw.

### Current piece — E4.3, `storage.*` (get/set DONE; delete NEXT)

`storage.get` / `storage.set` / `storage.delete` (§6.3), a `StorageProvider`
slot next to `profile`, mock-host backed by an in-memory `Map`. The gate
already covers the `storage` namespace; nothing new there. Glossary given on
2026-09-02: key-value store = 사물함, namespacing = "302호의 3번 사물함",
isolation = 남의 호수 사물함은 열쇠가 안 맞음, composite key = 호수와 번호를
한 줄로 쓴 것.

**Decision 4 — approved 2026-09-04: app id and key are separate arguments.** §6.3:
"namespaced per mini app id by the host. A mini app MUST NOT be able to read
another mini app's keys." Recorded in
`docs/adr/0003-pass-storage-app-identity-separately.md`.

The kernel selects the identity from host-held configuration; the provider
must actually partition its data by that identity. An argument alone does
not guarantee isolation. Options considered:

| | Shape | For | Against |
| --- | --- | --- | --- |
| **A (accepted)** | provider takes the id separately — `get(miniAppId, key)`, `set(miniAppId, key, value)`, `delete(miniAppId, key)`; the kernel always passes `config.manifest.id` | identity selection can be tested at the kernel boundary; providers choose their own storage layout | one more argument; providers still must enforce separation |
| A' | kernel composes `${id}:${key}` | provider takes one key | couples the contract to an encoding convention; contrary to the earlier note, a colon in the key alone cannot collide when valid app ids contain no colon |
| B | host injects a per-mini-app provider | kernel stays id-agnostic | correct binding must be verified separately in each embedding host |

Tests under A: the provider receives the manifest id and the unmodified key
separately; two connections using one partitioned provider read their own
values for the same key. A missing key answers `{ value: null }`. Failure and
re-throw semantics match `profile.get`. A smuggled `params.miniAppId` must
never choose another app; its dedicated test is deferred until E4.4 decides
whether unknown fields are ignored or rejected, so the test does not silently
settle that open policy.

**2026-09-04 — storage.get test handover.** Added 12 tests in
`packages/host/test/storage.test.ts`: id/key forwarding and JSON result,
missing key, two-app reads, async settlement, denied scope, missing provider,
three invalid-key cases, validation-before-availability, and two provider
failure shapes. Verified **74 passed / 11 failed** overall; the existing
scope gate accounts for the one new green test. Failures are caused by
`-32601 unknown method: storage.get`, not a test-loading error. Typecheck has
exactly two expected errors: missing `StorageProvider` export and missing
`HostCapabilities.storage`. Lint passes.

**2026-09-04 — storage.get implementation DONE.** The maintainer typed the
complete read slice: protocol
`STORAGE_METHODS.GET`, `StorageGetParams`, `StorageGetResult`,
`isStorageGetParams`; host `StorageProvider.get(miniAppId, key):
Promise<JsonValue>`, optional storage slot, `invokeStorageGet`, and the branch
below the permission gate. The provider interface has only get for this step;
set/delete are added with their tests later. Read the diff and ran all checks:
**85 passed**, both missing-contract type errors resolved, lint clean. The
implementation matches the handover, including gate placement and error
handling. No implementation code has been edited by the agent.

The maintainer asked for two deep-dives before moving on: identity forwarding
versus storage isolation, and whether a provider checks feature availability.
Explain from their code: the embedding host supplies the executable provider;
the kernel checks its presence and separately enforces grantedScopes. The
provider performs the operation and must respect the app id. The first test
observes the kernel's call arguments; the two-app test uses a deliberately
partitioned test provider. Neither certifies an arbitrary future provider's
storage layout. The real example provider needs its own isolation checks when
it is implemented. Also discussed dependency injection, ports and adapters,
when a boundary is useful, and passing a concrete notifier object to a caller.
The maintainer requested proceeding after those examples; do not repeat the
provider lesson before moving on.

**Null policy — approved 2026-09-04 (ADR 0004).** The maintainer approved the
proposal to reject a missing or top-level null storage.set value with -32602,
while permitting null inside objects and arrays. SPEC §6.3 now reserves
`{ "value": null }` for an absent key. The assistant explicitly restated that
even an intentional top-level null write gets an error. Allowing null with an
ambiguous read result was an alternative; it was not the chosen policy.
SPEC was updated before the tests. CHANGELOG.md records the draft-contract
tightening, and ADR 0004 records the decision. Do not ask again.

**2026-09-04 — storage.set tests, verified RED before implementation.** Added 21
tests to storage.test.ts: id/key/value forwarding and an empty result, two-app
write/read round trips, false/zero/empty-string/nested-null values, waiting for
write completion, permission and initialization gates, missing provider,
invalid params, validation-before-availability, preserving an existing value
on null rejection, and both provider failure shapes. The setup helper accepts
partial providers and fills unused operations with throwing stubs; this keeps
the existing read tests focused as the provider contract grows.

Before implementation, verified **88 passed / 18 failed** overall (33 storage
tests, of which 15 pass). The three newly green cases cover the existing permission and
initialization gates. All 18 failures are caused by -32601 for storage.set.
Typecheck reports eight occurrences of the missing set member in test fixtures;
lint passes. Existing production code has not been changed by the agent.

**2026-09-04 — storage.set implementation DONE.** The maintainer typed
STORAGE_METHODS.SET; protocol StorageSetValue = Exclude<JsonValue, null>,
StorageSetParams, and isStorageSetParams (object, string key, value neither
undefined nor null); StorageProvider.set with Promise<void>; invokeStorageSet
awaiting the provider before sending an empty result; and the guarded set
branch after the permission gate. The agent read the diff and verified
**106 passed**, typecheck and lint clean. No separate type is needed for the
literal empty success result.

The maintainer then requested richer comments matching the earlier code.
Added English documentation and inline rationale to the storage contracts,
guards, invocation helpers, and dispatch branches. Corrected the stale
"storage read method", "Skeleton only", and single-invocation-location
comments. These are documentation edits; the implementation remains the
maintainer's. Carry this comment style into the delete handover.

Resume checklist:

1. Decision 4 is approved; do not ask again.
2. storage.get/set are verified GREEN and the provider discussion is finished.
   Both identity and null policies are approved; do not repeat either decision.
3. Continue with delete tests and a commented handover. Maintainer types
   protocol `STORAGE_METHODS` additions and the result types (type
   aliases — they cross the wire); host `StorageProvider` (every method
   async, §9.5) and `HostCapabilities.storage?`; the three dispatch branches,
   each through an async invoke helper with the same try/catch, `-32603`,
   `queueMicrotask` re-throw shape as `invokeProfileGet`. A shared
   `invoke(id, run)` helper is the obvious refactor — do it UNDER GREEN,
   after the three branches work, not before.
4. The read slice includes `isJsonObject` + `typeof key === 'string'`, with
   negative tests for omitted params, a missing key, and a non-string key.
   E4.4 covers the remaining params cases, unknown fields (including a forged
   miniAppId), and value size limits. Non-object params still hit the existing
   request-envelope guard; that known error-code issue is deferred to E4.4.
   Also validate the actual JSON value tree at the browser ingress boundary:
   a JsonValue annotation/cast does not prove that a structured-clone payload
   is JSON. Current method guards check required fields and the null policy;
   nested undefined, non-finite numbers, non-JSON objects, and cycles are not
   covered yet. Address this before claiming full §9.6 conformance.
5. E4.5: mock-host gets a `Map`-backed `StorageProvider` and a constant
   `ProfileProvider`; hello-miniapp calls `profile.get` and renders it, and
   calls `storage.set` so a `-32000` is visible on screen (mock-host grants
   only `profile` on purpose). E4.6: ADR for decisions 1–3 (decision 4 is
   already ADR 0003), HANDOFF, commit.

### Picking this up on another machine

```bash
corepack enable          # once per machine
pnpm install
pnpm test                # expect 106 passed
```

The git remote uses a personal SSH host alias
(`git@github.com-personal:WillowRyu/moonpool.git`) — that alias must exist in
`~/.ssh/config` on the new machine or the clone/push will fail.

Tutor mode is local to the session working directory and deliberately not
committed (this repo is meant to ship as MIT open source; nobody cloning it
should inherit study mode). In Claude Code, resume with
`/study-coding-mode:toggle on`. With the Codex plugin installed, use
`$study-coding-mode:study-coding-mode on`; use `status` to inspect without
changing state. Both hosts share the gitignored `.claude/study-coding-mode`
marker in the session working directory. An explicit `on` preserves the saved
level; a bare invocation toggles and could turn an active mode off.

Verified in Codex on 2026-09-04: plugin `study-coding-mode@willow` 0.3.0 is
enabled and its skill is available; the bundled mode controller returns
`{"enabled":true,"level":"junior"}` for this workspace. Automatic hook delivery
was not verified; use the explicit resume command when restoring context.
If the plugin is unavailable in another agent, ask it to follow the "How we
work" section of HANDOFF.md. Codex reads `AGENTS.md`, a symlink to `CLAUDE.md`.
The "How we work" section above is the durable record of the agreement —
Claude's memory files and the `study/` notes (01–04, Korean HTML) exist only
on the original machine.

## Open decisions (maintainer's call, not made yet)

- **Receiver behavior on id reuse (§4.1):** the spec says senders MUST NOT
  reuse ids (positive, monotonically increasing) but never says what a
  receiver replies when they do. Needs a spec decision (likely `-32600`, but
  do not resolve by editing SPEC.md without approval). Enforcement would be
  host-side per-connection state, not the pure guard.

- **ADR candidate:** Moonpool targets BOTH full-screen mini apps and web
  components embedded inside native screens; the protocol stays
  embedding-agnostic (screen size/placement is a host-UI concern). Arbitrary
  remote URLs are explicitly out: no identity → conflicts with SPEC §8/§9.
- ~~Retry after `-32004`, and a second `portal.initialize`~~ — **resolved
  2026-08-28** in SPEC §5 and the new §5.1 (`225fd21`). Both are allowed.
- **Language question (asked 2026-08-19):** could the kernel be Rust or Go?
  Discussed in session: the client must be JS — it runs inside the mini
  app's web view (Rust→WASM still needs a JS shim for postMessage and the
  bridge is I/O-bound, not compute-bound, so it buys nothing). Rust becomes
  a real option for a SHARED native core after the protocol stabilizes
  (post-v0, per the CLAUDE.md ordering); Go does not fit mobile embedding.
  Possible ADR when native cores start.
