# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-08-19.

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
  now), Vitest 3. `npm run typecheck` passes.
- `packages/protocol`: real content — `Transport` interface (SPEC §3.1),
  `ERROR_CODES` (§4.4), `PROTOCOL_VERSION`, §5/§7 types.
- `packages/client` / `packages/host`: typed stubs whose bodies throw
  "Not implemented" so tests fail for the right reason.
- `npm test` finds no test files yet — deliberate; tests are being written
  by the maintainer, one step at a time.
- Biome 2.5.9 as the single formatter + linter (`npm run lint`,
  `npm run lint:fix`); `.vscode/` recommends the Biome extension with
  format-on-save. Chosen over Prettier+oxlint to keep one tool/one config.

**In progress — STEP 2** of the test-writing roadmap. STEP 1 is done: the
maintainer typed the `createHost` smoke test; it fails with
"Not implemented: createHost" as expected (correct red). Next the maintainer
types the in-memory Transport pair helper in
`packages/host/test/helpers/memory-transport.ts`, in two pieces:
(a) `TransportPair` interface + `flush()`, (b) `createLinkedTransports()`
with async (microtask) delivery mirroring postMessage semantics.

### Phase change: the red suite is COMPLETE — implementation begins

All 10 §5 tests exist and fail for the right reason: 7 host tests
("Not implemented: createHost") + 3 client tests ("Not implemented:
createClient"). Claude wrote the final client tests per the new division of
labor. From here the maintainer types the implementation and watches reds
turn green.

Implementation roadmap:

- **A. Host gate** — reply -32005 to every request; ignore notifications
  (§4.1). Expected: 3 tests green (smoke, -32005 gate, no-service-after
  -32004).
- **B. Host initialize** — validate protocolVersion (exact match → else
  -32004), compute the grantedScopes intersection, reply the full §5 result,
  flip the per-connection initialized flag. Expected: +3 green (happy path,
  intersection, -32004 ×2) — actually 4 more, total 7 host tests minus ping.
- **C. portal.ping** — after initialize, answer { pong: true }. Host suite
  fully green.
- **D. Client** — id issuance, pending map (promise correlation), initialize
  send + result/error mapping. All 10 green.
- **E. Payoff** — iframe transport + mock-host + hello-miniapp running in a
  real browser (v0.1 definition of done).

### Current piece to type (STEP A — host gate)

In `packages/host/src/index.ts`: widen the protocol import to include
`ERROR_CODES` and `JsonValue`, add an `isJsonObject` type guard, and replace
the throwing `createHost` body with a `connect` that subscribes to the
transport and answers every identified request with a -32005 error;
messages that are not objects or carry no numeric `id` are notifications —
ignored per §4.1. Full code is in the conversation.
Check: `pnpm test` → 3 passed, 7 failed (assertion failures now, not
"Not implemented").

## Test-writing roadmap (maintainer types, Claude tutors)

1. Smoke test for `createHost` (done)
2. Test helper: in-memory linked Transport pair — delivery must be async
   (microtask), mirroring postMessage semantics (in progress)
3. SPEC §5: every request before `portal.initialize` → `-32005`
4. SPEC §5 happy path: full `initialize` result shape
5. `grantedScopes` = intersection of `manifest.permissions` and host grants
6. SPEC §5: unsupported version → `-32004` (exact match in 0.x; further
   calls after the failure still rejected with `-32005`, never serviced)
7. Client side: `portal.initialize` is the first request / resolves with the
   result / rejects with code `-32004`

Then implementation to green, in this order: host not-initialized gate →
handshake handling → client promise correlation.

## Open decisions (maintainer's call, not made yet)

- **ADR candidate:** Moonpool targets BOTH full-screen mini apps and web
  components embedded inside native screens; the protocol stays
  embedding-agnostic (screen size/placement is a host-UI concern). Arbitrary
  remote URLs are explicitly out: no identity → conflicts with SPEC §8/§9.
- **Spec ambiguity found:** after a `-32004` response, may the mini app retry
  `portal.initialize` with a supported version? SPEC §5 says the host "MUST
  NOT service further calls" but does not address a corrected retry. Needs a
  spec decision (do not resolve by editing SPEC.md without approval).
