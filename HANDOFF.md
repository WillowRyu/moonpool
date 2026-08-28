# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-08-28.

## How we work (do not skip)

- **Tutor mode ("study coding mode"), level: junior — implementation-first
  (agreed 2026-08-19).** Division of labor: **Claude writes and maintains
  the tests; the maintainer TYPES the implementation code.** Explanations
  start from the running code ("what does this thing do"), then point at
  which tests cover it. Larger steps than before; the reward of each step is
  red tests turning green. Claude reads and verifies the maintainer's typed
  code after every step.
- Explanations at junior level: define every term in plain language with an
  analogy — but don't shrink the steps.
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

`pnpm test` → **54 passed**, `typecheck` and `lint` clean, working tree clean.
The kernel and the first platform adapter are both done; E3 is next.

v0.1 definition of done, remaining:

- [x] `packages/transport-iframe` — the first real platform adapter
      (`iframe` + `window.postMessage`). Landed in E2/E2.1.
- [ ] `examples/mock-host` + `examples/hello-miniapp` running in a browser
      — **E3, the current piece.** The two examples exist and render, but no
      bridge crosses between them yet.
- [ ] Capabilities `profile.get` and `storage.*` (§6.3)
- [ ] Remaining §4.4 error-code coverage (`-32600` for malformed id-bearing
      frames landed in E0; still open: `-32602` for non-object `params`,
      batch arrays via `id: null`, id uniqueness per connection)

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
(`unhandledrejection` vs `error`), and error collectors commonly hook only
the latter.

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

### Current piece (E3 — connect the examples, maintainer types)

Wire the transport into `examples/mock-host` and `examples/hello-miniapp` so
a real handshake crosses a real origin boundary in a browser. mock-host
already pins `MINI_APP_ORIGINS` (§8.1) and renders the iframe; hello-miniapp
already renders its own origin.

**Known problem to solve, not yet solved: the load race.** The host holds
`iframe.contentWindow` as soon as the element exists, but the mini app's
listener does not exist until its document has run. Anything the host posts
before that is delivered to a window with no listener and is simply lost —
`postMessage` has no delivery receipt. The Portal side does not have the
mirror problem: its parent is already loaded. Options to weigh in the next
session: host waits for the iframe's `load` event before connecting; or the
Portal announces readiness and the host connects on that; or the client
retries `portal.initialize` under the §4.5 timeout. The third is the only one
that also survives a Portal reload — which HMR triggers on every save, so the
next session will hit this repeatedly and can use it as the test case.

### Picking this up on another machine

```bash
corepack enable          # once per machine
pnpm install
pnpm test                # expect 54 passed
```

The git remote uses a personal SSH host alias
(`git@github.com-personal:WillowRyu/moonpool.git`) — that alias must exist in
`~/.ssh/config` on the new machine or the clone/push will fail.

Tutor mode is machine-local and deliberately not committed (this repo is
meant to ship as MIT open source; nobody cloning it should inherit study
mode). Turn it on in the new session with `/study-coding-mode:toggle on`.
The "How we work" section above is the durable record of the agreement.

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
- **Spec ambiguity found:** after a `-32004` response, may the mini app retry
  `portal.initialize` with a supported version? SPEC §5 says the host "MUST
  NOT service further calls" but does not address a corrected retry. Related:
  what should a SECOND `portal.initialize` after a successful one return?
  Needs a spec decision (do not resolve by editing SPEC.md without approval).
- **Language question (asked 2026-08-19):** could the kernel be Rust or Go?
  Discussed in session: the client must be JS — it runs inside the mini
  app's web view (Rust→WASM still needs a JS shim for postMessage and the
  bridge is I/O-bound, not compute-bound, so it buys nothing). Rust becomes
  a real option for a SHARED native core after the protocol stabilizes
  (post-v0, per the CLAUDE.md ordering); Go does not fit mobile embedding.
  Possible ADR when native cores start.
