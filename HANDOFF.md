# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-08-20.

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

### The kernel is complete. Next: STEP E.

`pnpm test` → 20 passed, `typecheck` and `lint` clean, working tree clean,
`origin/master` up to date at `19819ed`.

v0.1 definition of done, remaining:

- [ ] `packages/transport-iframe` — the first real platform adapter
      (`iframe` + `window.postMessage`)
- [ ] `examples/mock-host` + `examples/hello-miniapp` running in a browser
- [ ] Capabilities `profile.get` and `storage.*` (§6.3)
- [ ] Remaining §4.4 error-code coverage (notably `-32600` for an id-bearing
      frame that fails `isJsonRpcRequest`; see the C2 note below)

**Why E is a different kind of work.** Everything so far was verified over an
in-memory linked Transport pair. Real `postMessage` is the first time §8
(origin) and §9 (security requirements) actually bite: origin checking on
every inbound message, the `moonpool://<mini-app-id>/` origin rule, structured
clone vs JSON serialisation, and iframe sandbox attributes. Agree a roadmap
before typing — this is not a continuation of the client work, it is the
first platform adapter, and it is the piece the native ports will be measured
against.

**Known deferred item from C2:** an id-bearing frame with a bad `jsonrpc` or
non-string `method` is currently dropped silently instead of answered with
`-32600`. Spec-correct answer is `-32600`; it lands with the §4.4 coverage
work above.

### Picking this up on another machine

```bash
corepack enable          # once per machine
pnpm install
pnpm test                # expect 20 passed
```

The git remote uses a personal SSH host alias
(`git@github.com-personal:WillowRyu/moonpool.git`) — that alias must exist in
`~/.ssh/config` on the new machine or the clone/push will fail.

Tutor mode is machine-local and deliberately not committed (this repo is
meant to ship as MIT open source; nobody cloning it should inherit study
mode). Turn it on in the new session with `/study-coding-mode:toggle on`.
The "How we work" section above is the durable record of the agreement.

## Open decisions (maintainer's call, not made yet)

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
