# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-08-19.

## How we work (do not skip)

- **Tutor mode ("study coding mode"), level: junior.** The maintainer is
  learning by building: they TYPE all meaningful code themselves. Claude
  explains the why first, hands over ONE small step to type, then reads and
  verifies the typed code before moving on. Claude fills only pure
  boilerplate/config, on request. Never write the meaningful code for them,
  even if a request sounds like "write it".
- Explanations at junior level: define every term in plain language with an
  analogy, one new term at a time.
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

### Current piece to type (STEP 7a — client side begins)

The host-side §5 suite is COMPLETE: 7 tests (smoke, happy path, scope
intersection, -32005 gate ×1, -32004 ×2 via it.each, no-service-after-32004),
all failing with "Not implemented: createHost". Roadmap items 1–6 done.

Now the client package. First: copy the transport helper (deliberate
duplication — test helpers stay package-local so packages remain
independent):

    mkdir -p packages/client/test/helpers
    cp packages/host/test/helpers/memory-transport.ts \
       packages/client/test/helpers/memory-transport.ts

Then type `packages/client/test/handshake.test.ts` with a local `RpcRequest`
interface and the first test: the test plays the HOST side this time
(collects what arrives at `hostEnd`), calls
`createClient({ transport: clientEnd }).initialize()` with a no-op `.catch`,
flushes, and asserts exactly one outgoing message: `toMatchObject` on
jsonrpc/method='portal.initialize'/params.protocolVersion='0.1', plus id is
a positive integer (§4.1). Full code is in the conversation.
Check: `pnpm test` → 8 tests failing — 7 with "Not implemented: createHost",
1 with "Not implemented: createClient".

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
