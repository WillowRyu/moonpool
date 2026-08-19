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
- **C2. Refactor under green (maintainer-proposed 2026-08-20) —
  IN PROGRESS** (current piece, below). Typed `JsonRpcRequest` + checked
  guard and `PORTAL_METHODS` constants in protocol; host reads through
  them. Tests must stay 9 passed / 3 failed — that invariance is the
  success criterion.
- **D. Client** — id issuance, pending map (promise correlation),
  initialize send + result/error mapping. Expected: all 12 tests green.
  Claude hands the full typed-piece over once C2 lands.
- **E. Payoff** — iframe transport + mock-host + hello-miniapp running in a
  real browser (v0.1 definition of done).

### Commit checkpoint — DONE 2026-08-20

Steps A–C are committed (`04611f4` test, `d226d27` feat, `4b3bb85` docs);
the working tree is clean. The C2 refactor below goes on top as a pure
`refactor:` commit — the point of committing the green state first.

### Current piece to type (C2 — typed request guard + method constants)

Origin: the maintainer's own review of the handler (2026-08-20): can
`message` get a real type? predefine method names? switch over if-chains?
Decisions: adopt 1 and 2 in trust-boundary-compatible form (guard proves
the type at runtime; constants only for the reserved `portal` methods —
a closed enum of ALL methods would fight the "method name is the scope,
no registry" invariant). Defer 3: the chain is ordered security
checkpoints, not peer cases; a dispatch table arrives with real
capabilities.

**(1) `packages/protocol/src/index.ts`** — move `isJsonObject` here
(exported) and add:

```ts
/**
 * SPEC §4.2 — a request carrying an id. Deliberately a type alias, not an
 * interface: aliases get an implicit index signature, so the guard below
 * may narrow `JsonValue` to it.
 */
export type JsonRpcRequest = {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: { [key: string]: JsonValue };
};

/** Checked proof that a frame is a §4.2 request (notifications excluded). */
export function isJsonRpcRequest(value: JsonValue | undefined): value is JsonRpcRequest {
  return (
    isJsonObject(value) &&
    value.jsonrpc === '2.0' &&
    typeof value.id === 'number' &&
    typeof value.method === 'string' &&
    (value.params === undefined || isJsonObject(value.params))
  );
}

/** SPEC §6.2 — reserved core methods; the `portal` namespace needs no scope. */
export const PORTAL_METHODS = {
  INITIALIZE: 'portal.initialize',
  PING: 'portal.ping',
  CLOSE: 'portal.close',
} as const;
```

**(2) `packages/host/src/index.ts`** — delete the local guard; import
`isJsonRpcRequest` and `PORTAL_METHODS` from '@moonpool/protocol' (drop
`type JsonValue`, now unused). Handler head becomes:

```ts
      transport.onMessage((message) => {
        if (!isJsonRpcRequest(message)) {
          // SPEC §4.1: notifications (and malformed frames) are never answered.
          return;
        }
        const { id, method } = message;

        if (!initialized && method === PORTAL_METHODS.INITIALIZE) {
          const requested = message.params?.protocolVersion;
```

…and the two string literals below become `PORTAL_METHODS.PING` and
`${method}`. Known, accepted behavior shift for untested input: an
id-bearing frame with a bad `jsonrpc`/`method` field is now dropped
instead of getting -32005; the spec-correct answer is -32600, which lands
with the §4.4 coverage work.

**Check:** `pnpm test` still **9 passed / 3 failed**; lint + typecheck
clean. Commit as
`refactor: typed JSON-RPC request guard and portal method constants`.

### Next piece (STEP D — the client), after C2

The client is a receptionist with a numbered-ticket machine: `request()`
takes a ticket (`nextId++`), files the promise's resolve/reject in a
`pending` map under that number, sends the JSON-RPC frame; the single
`onMessage` return-desk looks the id up, deletes the entry, resolves with
`result` or rejects with `error`; unknown/late ids are ignored (§4.5).
Claude hands the full typed-piece when C2 is green.

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
