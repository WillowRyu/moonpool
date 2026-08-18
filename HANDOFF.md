# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-08-18.

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

- npm workspaces skeleton per the CLAUDE.md repository layout.
- TypeScript 7.0.2 (note: TS7 removed `baseUrl`; `paths` are `./`-relative
  now), Vitest 3. `npm run typecheck` passes.
- `packages/protocol`: real content — `Transport` interface (SPEC §3.1),
  `ERROR_CODES` (§4.4), `PROTOCOL_VERSION`, §5/§7 types.
- `packages/client` / `packages/host`: typed stubs whose bodies throw
  "Not implemented" so tests fail for the right reason.
- `npm test` finds no test files yet — deliberate; tests are being written
  by the maintainer, one step at a time.

**In progress — STEP 1** of the test-writing roadmap: the maintainer is about
to type `packages/host/test/handshake.test.ts` (smoke test: `createHost({...})`
returns a host exposing `connect`). Expected check: `npm test` shows exactly
1 failing test, failing with "Not implemented: createHost".

## Test-writing roadmap (maintainer types, Claude tutors)

1. Smoke test for `createHost` (in progress)
2. Test helper: in-memory linked Transport pair — delivery must be async
   (microtask), mirroring postMessage semantics
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
