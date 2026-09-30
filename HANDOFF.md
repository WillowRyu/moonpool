# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-09-30, maintainer's E4.4e implementation verified GREEN:
> 201 passed, typecheck, lint, and both example builds clean.
> Next: read the HTML walkthrough; maintainer updates the stale storage guard
> comments. Host error wording is aligned. Do not advance before learning review.
> The agent made no E4.4e production edits. The rejection policy is approved.
> Null policy is SPEC §6.3 / ADR 0004. Study mode: junior.

## 2026-09-08 checkpoint

The implementation and tests are split into four logical commits:

- `6e75358` — scoped storage deletion (E4.3).
- `7c0c630` — distinguish invalid params from malformed requests (E4.4a).
- `2b3aff7` — reject unknown method params, with SPEC §4.2 and ADR 0006 (E4.4b).
- `716b6c5` — reset initialization before repeat-handshake validation (E4.4c).

Verified the final implementation with `pnpm test --run` (162 passed),
`pnpm run typecheck`, `pnpm run lint`, and `pnpm run build` (both examples).
An independent read-only review found no blocking issues in this checkpoint.
This is incremental progress, not a declaration of full v0.1 conformance;
remaining validation work and known boundaries are listed below.

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
- **Refined 2026-09-30 — interrupted study sessions need a living HTML guide.**
  The maintainer requested an accessible architecture map, roadmap, current
  position, and sequential explanations of long code, including why each
  check exists. Maintain `study/index.html` as the stable entry point and
  `study/05-json-value-validation.html` as the current detailed lesson;
  `study/study.css` supplies their shared styles. Preserve the earlier notes.
  Read the guide alongside this handoff on resume. After each verified step,
  update its date, real check results, current status, next small action, and
  relevant explanation. Keep prior explanations available rather than
  replacing the guide with only the newest task. This is upkeep during study,
  not a scheduled automation or a live repository monitor.
  Teach long code in small conceptual blocks, with the current architecture
  and call path first, then each block's purpose, line roles, and failure it
  prevents. Avoid another large implementation handover while comprehension
  is pending. HTML teaching materials may be authored by the agent; meaningful
  Moonpool implementation remains typed by the maintainer. These Korean
  personal notes are gitignored; if missing on another machine, recreate them
  from SPEC, source, ADRs, and this handoff instead of assuming they travelled.

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
Baseline: **106 passed**, `typecheck` and `lint` clean after the maintainer
typed storage.set, reverified on 2026-09-07 before adding delete tests.
After storage.delete: **119 passed**, typecheck and lint clean.
After E4.4a: **134 passed**, reverified on 2026-09-08 before E4.4b.
After E4.4b: **160 passed**, typecheck and lint clean.
After E4.4c: **162 passed**, reverified on 2026-09-09.
After E4.4d: **172 passed**, typecheck and lint clean.
Current: **201 passed**, typecheck, lint, and both example builds pass after
the maintainer typed E4.4e's validator and storage.set integration. Verified
on 2026-09-30. Sequential explanation and the three requested deep-dives are
in the HTML guide. Stale storage guard comments remain for the maintainer to
update; host error wording is aligned. Conceptual review precedes the next task.
The browser example still has no capability providers.
The kernel, the first platform adapter, a real cross-origin bridge between the
two examples, and now the permission gate with the first scoped method are
done. **E4.3 (`storage.*`) is complete; E4.4 (remaining params guards) is in progress**, then
the example update and an ADR.

v0.1 definition of done, remaining:

- [x] `packages/transport-iframe` — the first real platform adapter
      (`iframe` + `window.postMessage`). Landed in E2/E2.1.
- [x] `examples/mock-host` + `examples/hello-miniapp` running in a browser.
      Landed in E3; a real §5 handshake crosses a real origin boundary and
      survives Portal reloads.
- [ ] Capabilities `profile.get` and `storage.*` (§6.3) — kernel operations
      landed in E4.2/E4.3. Remaining input validation (E4.4) and example
      providers (E4.5) are still open.
- [ ] Remaining §4.4 error-code coverage (`-32600` for malformed id-bearing
      frames landed in E0; `-32602` for non-object `params` landed in E4.4a;
      still open:
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
- **Original §5.1 coverage was incomplete.** Rate-limit counters and consent
  records name state this host does not keep yet. However, initialization
  reset is observable when a repeat handshake fails: E4.4c (2026-09-08)
  adds tests exposing the stale initialized=true value. The previous claim
  that no message could observe the reset boundary overlooked rejection.

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

### E4.3 — `storage.*` (get/set/delete DONE)

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

**2026-09-07 — storage.delete tests, verified RED before implementation.**
Added 13 tests to storage.test.ts (46 storage tests total): identity/key
forwarding and the empty result, deletion from the second of two apps sharing
one partitioned provider (preserving the first app's same key and the second
app's unrelated key), waiting for deletion to finish, two permission cases,
the initialization gate, missing provider, three invalid-key cases,
validation-before-availability, and both provider failure shapes with
host-only error reporting. The setup helper now supplies a throwing delete
stub for tests that exercise only get/set.

Verified **109 passed / 10 failed** overall. The three newly green cases pin
the existing permission/initialization gates. The remaining cases reach
`-32601 unknown method: storage.delete`; the completion-order test fails on
that early reply's presence. Typecheck reports six missing-delete member
errors in the test fixtures; lint passes. No production code was changed.

Handover: protocol `STORAGE_METHODS.DELETE`, `StorageDeleteParams`, and
`isStorageDeleteParams`; host import of the guard, async
`StorageProvider.delete(miniAppId, key): Promise<void>`,
`invokeStorageDelete`, and a guarded branch after storage.set and before the
unknown-method fallback. Reuse the agreed scope → params → availability →
invocation order and get/set's sanitized error / queueMicrotask reporting.
The helper must await deletion before sending `{}`. This handover was typed
and verified as recorded below.

**2026-09-07 — storage.delete implementation DONE.** The maintainer typed
the protocol and host additions above. The agent read both implementation
diffs and verified **119 passed**, typecheck and lint clean. The delete branch
is below the permission gate and before the unknown-method fallback; it
validates before checking provider availability, passes config.manifest.id
and the key separately, awaits completion before sending {}, and follows
get/set's sanitized error and host-side rethrow policy. The agent did not
edit the implementation.

The maintainer asked what the offered deep-dive about combining get/delete
input guards meant. Both currently check the same object/string-key shape.
Explain extraction as sharing that rule in one helper while preserving each
operation's intent. This is an optional refactor, not a missing feature or
an agreed next task. With a one-line duplication and E4.4 policies still
open, the current recommendation is to keep the guards separate for now.
Any later extraction should preserve behavior with all tests staying green.

### E4.4a — distinguish non-object params from invalid requests (DONE)

**2026-09-07 — tests verified RED before implementation.** Added 15 tests
in `packages/host/test/invalid-params.test.ts`: six non-object JSON params
shapes on ping, array params on all four scoped methods without invoking a
provider, invalid initialize params with a valid retry, two valid ping
forms, a malformed envelope that also carries array params, and an id-less
array-params frame that must stay silent. Updated the introductory comment
in invalid-request.test.ts to point to this suite.

Verified **123 passed / 11 failed** overall. All 11 failures receive -32600
where SPEC §4.2 requires -32602; the four newly green cases preserve the
surrounding rules. Typecheck and lint pass. Production files were not edited
by the agent. The root cause is the host mapping every failure of the
complete isJsonRpcRequest guard to INVALID_REQUEST, although that guard also
checks the params container.

The implementation handover introduces JsonRpcRequestEnvelope with
`params?: JsonValue` and isJsonRpcRequestEnvelope for the basic jsonrpc/id/
method checks. JsonRpcRequest keeps its existing object-or-omitted params
contract; its guard calls the envelope guard and checks params. The host
keeps hasRequestId first, then rejects a bad envelope with -32600 and a bad
params container with -32602. These are the existing general wire-shape
checks, split in place before the handshake. Per-method field guards remain
after permission checks. ADR 0005 records why both intermediate and complete
request shapes are needed and why the complete guard stays independently
usable.

**2026-09-07 — implementation DONE.** The maintainer typed the intermediate
type and envelope guard, composed isJsonRpcRequest from envelope + params
checks, and split the host's rejection into -32600 / -32602 in the existing
wire-shape gate. The agent read the implementation diff and verified
**134 passed**, typecheck and lint clean. Added only omitted explanatory
comments from the handover (including the delete branch's ordering comment);
the maintainer's implementation logic was not changed. ADR 0005 now records
implementation verification.

The maintainer requested all four related explanations: why the intermediate
type says params?: JsonValue; claiming only what was checked; the positions
of general and per-method validation; and why the complete guard repeats
the envelope check. Explain with one request progressing through stages:
params may be an array/null after an envelope-only check, becomes
object-or-omitted after the complete shape guard, and gets a string key only
after its method guard. Type predicates are trusted declarations, not
compiler-verified proofs. The standalone complete guard intentionally checks
its own premises; the host's first call exists to classify -32600 vs -32602.
General shape checks are before session state; scoped method-field checks
remain after permission and method lookup. These explanations were delivered
in chat before the maintainer paused the session; do not automatically repeat
them on resume.

Keep the qualification explicit: the envelope guard does not prove that
arbitrary browser data is JSON. JsonValue is the current Transport input
contract, and recursive validation remains open. Unknown extra fields,
recursive JSON checks, size limits, and missing/wrong method-specific fields
are subsequent steps; no unapproved policy is settled by E4.4a.

### E4.4b — unknown params fields (DONE)

**2026-09-08 — resumed.** Re-read SPEC, ADRs 0003/0005, and the current
guards. Reverified **134 passed**, typecheck and lint clean. Study mode is
still junior. The preceding deep-dives are complete.

SPEC originally listed each method's params without specifying whether
additional members were ignored or rejected. The maintainer approved
explicit rejection on 2026-09-08: unsupported params should be clearly
reported, not silently carried along. SPEC §4.2 was updated before tests;
ADR 0006 and CHANGELOG.md record the contract tightening. Do not ask again.

Known methods reject unknown top-level params members with -32602. This
does not restrict application-defined keys inside storage.set's value,
including a nested miniAppId. Permission precedes method-specific checks;
validation precedes provider availability and invocation. The host still
selects storage identity from its manifest (ADR 0003). Extra JSON-RPC
envelope members and unknown method handling are unaffected. A new optional
param will not be silently tolerated by an older host; that compatibility
cost was part of the approved proposal.

**2026-09-08 — tests verified RED.** Added 26 tests in
`packages/host/test/unknown-params.test.ts`: extra fields on all six handled
methods; forged miniAppId on all storage operations; constructor/toString
as unsupported names; validation-before-availability and permission-first
behavior for every scoped method; initialization, unknown method, and
notification ordering; a write/read round trip preserving arbitrary nested
value keys; both empty/omitted profile params; and an extra envelope member.
Updated the related test-file comments and ADR 0003's old open-policy note.

Verified **145 passed / 15 failed**, typecheck and lint clean. The 15 failures
are ordinary assertion mismatches: unsupported params still succeed, or the
host answers -32001 before it rejects them. The 11 newly green cases preserve
existing ordering and accepted data. Production logic has not been changed
by the agent for E4.4b.

Implementation handover:

- protocol: `hasOnlyParamKeys(params: JsonValue | undefined,
  allowedKeys: readonly string[]): boolean`, checking omission or an object
  whose own enumerable names all occur in allowedKeys. No recursion or
  mutation. Empty/omitted params have no unknown keys; required-field checks
  remain separate. This boolean does not claim a complete method schema.
- host: import the helper. Add a local `rejectUnknownParams(id, params,
  allowedKeys): boolean` inside connect after grantedScopes. Return false
  when the names pass; otherwise send one -32602 reply with a fixed message
  and return true. The caller returns immediately when rejection occurred.
- At the beginning of each existing method branch call that rejection
  helper: initialize allows ['protocolVersion']; ping/profile.get allow [];
  storage.get/delete allow ['key']; storage.set allows ['key', 'value'].
  All scoped branches already follow the permission gate. Keep existing
  required-field and provider checks after the new call. Do not implement
  portal.close as part of this step.

**2026-09-08 — implementation DONE.** The maintainer typed
hasOnlyParamKeys, the local rejection helper, and its calls at the start of
all six handled method branches. The agent read the implementation diff and
verified **160 passed**, typecheck and lint clean. Scoped calls follow the
permission gate and precede provider access. The helper examines top-level
names only; nested storage values stay intact. Corrected one copied
storage.set comment that incorrectly said only the key came from the caller;
the maintainer's implementation logic was not changed.

The maintainer requested all three offered explanations: why every returns
true on an empty array, how allowed-key checks differ from required-field
checks, and why the rejection helper's return does not stop its caller.
Explain every as finding no counterexample: no keys means no forbidden key,
not that required keys exist. Use a storage.get table for {}, { key: 'theme' },
{ key: 42 }, and { key: 'theme', extra: true } to separate names, presence,
and value types. Explain that return exits the function currently executing:
the helper returns a rejection flag, and the onMessage callback must return
separately to stop that request before provider access. This ends one
callback invocation, not the connection or its future message handling.
These deep-dives are delivered in this turn; do not repeat them by default.

### E4.4c — reset initialization before rejecting a repeat (DONE)

**2026-09-08 — found while reviewing remaining input validation.** The
initialize branch sets initialized=true on success but never resets it on
entry. After an earlier success, an unsupported version or an unknown params
field returns an error while leaving the previous document's success active.
The next portal.ping incorrectly succeeds. SPEC §5.1 already requires resetting
initialization state on a repeat handshake; no new policy or SPEC edit is
needed for this fix.

Added two cases in `packages/host/test/handshake.test.ts`: initialize
successfully, then send a replacement document's initialize with either
protocolVersion '9.9' or an unsupported extra params field. Assert its
existing -32004/-32602 response, then require -32005 for a subsequent ping.
Each case also requires a valid retry to restore service with the original
granted scopes. Corrected the test file's old claim that initialization
reset could not be observed.

Verified **160 passed / 2 failed**, typecheck and lint clean. Both tests
expect -32005 but receive { pong: true }; the earlier rejection codes are
already correct. The failure is stale state, not error-code mapping.

Handover: at the beginning of the host's PORTAL_METHODS.INITIALIZE branch,
before rejectUnknownParams and version comparison, add the commented
`initialized = false;`. Keep the existing success assignment to true.
Only document initialization state resets; transport, grantedScopes, and
stored values are preserved. The agent has not changed production logic.
**2026-09-08 — implementation DONE.** The maintainer added the commented
initialized=false assignment at the start of the initialize branch, before
unknown-field rejection and version comparison. The success assignment to
true remains in place. The agent read the exact block and verified
**162 passed**, typecheck and lint clean. No implementation or comment edits
were needed during verification.

The maintainer requested all three offered deep-dives. Explain why resetting
on entry covers every method-level rejection path, whereas resetting in
each failure branch is easy to omit as validation grows. Resetting first
establishes an uninitialized default; only successful negotiation restores
true. Explain document-scoped initialization versus app/origin-scoped grants
and stored values: a reload replaces the page's running context but does not
revoke the user's grant or erase the app's data. Finally, distinguish tests
that start with false from a sequence that first establishes true: the old
first-handshake failure tests could not expose stale success. The new tests
also require a valid retry to restore service. These explanations were
completed on 2026-09-08; do not repeat them by default on resume.

These cases reach the initialize branch with a valid general request shape.
They do not establish handling of malformed-envelope or malformed-container
repeat messages rejected earlier in the pipeline. Required-field validation,
recursive JSON validation, and size limits remain separate work.

### E4.4d — required protocolVersion input (DONE)

**2026-09-09 — resumed.** The working tree was clean at aaa5adc on master.
Reverified 162 tests passed, typecheck and lint clean; study mode remains
junior. E4.4c and the earlier deep-dives are complete.

The initialize branch currently compares message.params?.protocolVersion
directly with PROTOCOL_VERSION. Missing input and non-string values therefore
receive -32004, just like a well-typed but unsupported version. SPEC §5 shows
a string version and defines unsupported-version handling, but does not
explicitly distinguish missing/wrongly typed input from version negotiation.

The maintainer approved the following clarification on 2026-09-09. SPEC §5
was updated before tests; ADR 0007 and CHANGELOG.md record the distinction:

> portal.initialize requires params.protocolVersion to be a string. Missing
> params, a missing protocolVersion, or a non-string protocolVersion MUST
> be rejected with -32602 before version negotiation. A string that does not
> exactly match a protocol version supported by the host MUST be rejected
> with -32004.

This policy adds no version-format grammar or coercion. Under the approved
rule, an empty string is still an unsupported string (-32004), matching
the existing exact-match behavior. Unknown fields remain rejected under
ADR 0006. The E4.4c reset stays before these checks so failed initialization
cannot inherit prior success, and valid retry remains possible.

**2026-09-09 — tests verified RED.** Added seven input cases in handshake.test.ts
for omitted params, missing protocolVersion, null, number, boolean, array,
and object values. Each requires -32602, subsequent -32005 for ping, and a
valid initialization retry restoring service. Added a repeat-initialization
case with a missing version to pin the existing reset ahead of this new
rejection. Extended unsupported-string cases with '' and ' 0.1 ' to preserve
exact-match behavior without a non-empty rule or trimming.

Verified **164 passed / 8 failed** (172 total). All eight failures receive
-32004 instead of -32602; the two new unsupported-string cases are already
green. Typecheck and lint pass. Production code has not been edited by the
agent. The tests use the real host bridge; the omitted-params frame is built
directly because the existing request helper defaults params to {}.

Handover: inside PORTAL_METHODS.INITIALIZE, immediately after
`const requested = message.params?.protocolVersion;` and before the existing
version comparison, check `typeof requested !== 'string'`. On failure,
send -32602 with a fixed message and return. Keep the existing early reset,
unknown-field check, exact version comparison, and success assignment.
A local check is sufficient; no new public type/guard is needed.
**2026-09-09 — implementation DONE.** The maintainer inserted the local
typeof check immediately after reading requested, before version comparison,
and below the existing initialization reset and unknown-field check. The
agent read the block and verified **172 passed**, typecheck and lint clean.
No implementation edits were needed. ADR 0007 records verification. The
maintainer requested proceeding, not the optional deep-dives; do not deliver
them automatically on resume. Do not ask for this policy again.

### Current piece — E4.4e, non-JSON storage values (implementation GREEN; learning review)

The next boundary is storage.set's arbitrary value tree. Its current guard
rejects top-level undefined/null but does not inspect nested values.
Nested undefined and NaN can therefore reach the provider. Native
JSON.stringify demonstrates the portability problem: { nickname: undefined }
becomes {}, and { score: NaN } becomes { score: null }.

The maintainer approved the clarification on 2026-09-09 and explicitly
requested updating the spec and starting with tests. SPEC §6.3, ADR 0008,
and CHANGELOG.md were updated before tests. The rule: storage.set MUST
reject a value containing data outside the JSON value model with -32602,
before invoking its provider. It MUST NOT remove, coerce, or replace invalid
data to make the value JSON-compatible. This includes nested undefined,
non-finite numbers, non-JSON objects such as Date/Map, and circular references.
Nested null and application-defined object keys remain allowed, under the
existing ADR 0004/0006 rules. The existing scope and availability ordering
remains unchanged.

This first slice concerns the storage value tree. A pure validator belongs
in protocol and can be used by the existing storage.set guard; it does not
change Transport's interface or normalize payloads. Whole-envelope handling
and size/depth limits remain separate decisions. This policy is settled;
do not ask again.

**2026-09-09 — tests prepared and verified RED.** Added 23 tests in
`packages/host/test/storage-json.test.ts`. Sixteen invalid-value cases cover
undefined in objects/arrays, non-finite numbers, Date/Map/Set/typed-array
values, nested bigint, direct/indirect/array cycles, and sparse array holes.
Also require validation before availability and preservation of both the
existing stored value and the original invalid input. Five already-green
cases preserve permission/initialization gates, ordinary nested JSON,
shared acyclic content, and a deep finite tree.

Verified **177 passed / 18 failed** (195 total), typecheck and lint clean.
Failures are ordinary response mismatches: invalid writes still succeed,
or availability responds -32001 instead of input rejection -32602. The
test-only cast deliberately injects unknown values without serialization;
no production Transport signature was changed. The 20,000-level tree is a
stress sample to catch recursive call-stack failure, not a chosen limit.
The assertions for that case also traverse iteratively.

**2026-09-11 — implementation handover.** Added six boundary/stress tests
before handing over implementation: symbol-keyed members, non-enumerable
members, named array members, no toJSON execution, no getter evaluation,
and a 31-object shared graph whose expanded paths would exceed a billion
leaf visits. Verified **178 passed / 23 failed** (201 total), typecheck and
lint clean. New rejection cases still succeed; the shared-graph case is
already green before validation. This does not impose a protocol size limit.

The maintainer is handed isJsonValue(value: unknown): value is JsonValue in
protocol. It uses visit/complete tasks in an array stack and a local
Map<object, 'visiting' | 'valid'>. An active ancestor means a cycle; completed
subtrees can be reused. Validate scalar leaves, dense array indices and
ordinary record prototypes, then inspect own string-keyed enumerable data
descriptors without evaluating getters. Array length is excluded from data
members. Reject reflective failures. ADR 0008 records this implementation
rationale and its boundaries, including Proxy traps and serialized expansion.

Integrate by retaining the existing required-key/top-level-null checks in
isStorageSetParams and adding isJsonValue(params.value). Update its stale
comment and the host's invalid-params message to mention a non-null JSON
value. No E4.4e implementation code has been written by the agent. On resume,
inspect the maintainer's files before repeating the handover. Expected after
typing: **201 passed**, typecheck and lint clean; not yet verified.

**2026-09-30 — resumed in Codex, study mode still junior.** Inspected the
current implementation: isJsonValue is absent and isStorageSetParams still
checks only the required key and top-level undefined/null. Reverified
`pnpm test --run --reporter=dot`: **178 passed / 23 failed** (201 total).
All failures remain in storage-json.test.ts; typecheck and lint pass.
The next handover covers the validator and its storage.set integration as
one learning step. No production code or test changes were made on resume.
Wait for the maintainer's typing, then inspect their files and verify the
expected **201 passed** result before advancing.

**2026-09-30 — maintainer's implementation verified GREEN; explanation requested.**
The maintainer typed the complete iterative isJsonValue validator and added
isJsonValue(params.value) to isStorageSetParams. Read the implementation and
verified **201 passed**, typecheck, lint, and both example builds clean.
The agent did not modify production logic. The old guard documentation still
says nested data is unchecked, and its inline comment describes only the
outer inspection. The host error still says "non-null value" rather than
"non-null JSON value". These are the next small handover, not another feature.

The maintainer asked for a detailed sequential explanation and persistent,
readable HTML materials because study sessions are intermittent. Created
study/index.html (architecture, request flow, roadmap, current state, next
action, glossary, links to existing notes) and
study/05-json-value-validation.html (15 annotated source blocks, cycle versus
sharing, visit/complete stack replay, getter/descriptor experiment, test
mapping, and the remaining comment/message handover). Shared styles are in
study/study.css. All are personal, ignored materials. The supplied explanation
must not be treated as proof the maintainer has reviewed or understood it;
continue questions and conceptual review before advancing. Update these
materials alongside HANDOFF after subsequent verified study steps.

Verified the new HTML guide in the browser: architecture and lesson render,
all three stack replay examples reach their expected outcomes, descriptor
inspection leaves the getter call count unchanged, and direct reading calls
it once. Block navigation works. Both pages fit a 390px viewport without
page-level horizontal overflow; the temporary viewport override was reset.
Local links and anchors were checked. The source snapshot is dated, not a
live view of the implementation.

**2026-09-30 — commit/push checkpoint requested.** The maintainer updated the
host's storage.set error to require a "non-null JSON value". The guard's old
documentation and inline comment remain for the next study step. Reverified
**201 passed**, typecheck, lint, and both example builds clean; git diff check
also passes. Split the checkpoint into required version input, JSON storage
validation, and session documentation. Personal study HTML remains ignored;
the tracked handoff preserves its maintenance instructions and recreation
sources. This checkpoint does not declare complete v0.1 conformance.

Feature commits in this checkpoint:

- `b5d66f9` — validate required version input before negotiation (E4.4d).
- `8f0ac35` — reject non-JSON storage values without conversion (E4.4e).

The remaining session documentation is a separate docs commit. The maintainer
requested pushing this checkpoint to origin/master.

Resume checklist:

1. Decision 4 is approved; do not ask again.
2. storage.get/set/delete are verified GREEN and the provider discussion is finished.
   Both identity and null policies are approved; do not repeat either decision.
3. E4.3, E4.4a, E4.4b, E4.4c, and the requested deep-dives are complete.
   E4.4d is also verified GREEN. E4.4e's rejection policy is approved and
   the maintainer's implementation is verified GREEN (201 passed). Read the
   HTML guide and answer questions before advancing; hand over only the stale
   guard comments next. Version-input, unknown-field, and non-JSON
   storage rejection policies are settled; do not ask again.
   Guard extraction and a shared
   `invoke(id, run)` helper remain optional refactor candidates under green;
   neither is required before starting E4.4.
4. The read slice includes `isJsonObject` + `typeof key === 'string'`, with
   negative tests for omitted params, a missing key, and a non-string key.
   Remaining E4.4 work covers method-field cases and value size limits.
   Non-object params now receive -32602 through E4.4a's general wire-shape
   check; unknown fields (including a forged miniAppId) are rejected by E4.4b.
   Also validate the actual JSON value tree at the browser ingress boundary:
   a JsonValue annotation/cast does not prove that a structured-clone payload
   is JSON. Current method guards check required fields and the null policy;
   storage.set now rejects nested undefined, non-finite numbers, non-JSON
   objects, and cycles. This does not validate the entire inbound envelope or
   establish size/depth limits. Address remaining boundaries before claiming
   full §9.6 conformance.
5. E4.5: mock-host gets a `Map`-backed `StorageProvider` and a constant
   `ProfileProvider`; hello-miniapp calls `profile.get` and renders it, and
   calls `storage.set` so a `-32000` is visible on screen (mock-host grants
   only `profile` on purpose). E4.6: ADR for decisions 1–3 (decision 4 is
   already ADR 0003), HANDOFF, commit.

### Picking this up on another machine

```bash
corepack enable          # once per machine
pnpm install
pnpm test --run          # E4.4e implementation: expect 201 passed
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
