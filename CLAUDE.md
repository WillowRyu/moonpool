# Moonpool

An open-source runtime for embedding sandboxed web mini apps inside native
applications. A web view plus a permissioned bridge — the isolation model of
Ionic Portals, rebuilt as open source under MIT.

Read `SPEC.md` before writing any code. It is the normative document for this
project; this file is the working agreement.

---

## Architecture invariants

These are settled decisions. Do not propose alternatives without being asked,
and do not change them without explicit maintainer approval.

- **Protocol is JSON-RPC 2.0.** No custom message format. Profile restrictions
  are in `SPEC.md` §4.
- **Kernel is pure, transport is swappable.** Encoding, promise correlation,
  dispatch, and permission checks MUST NOT import any platform API. The
  `Transport` interface (`SPEC.md` §3.1) is the entire platform boundary.
- **Everything is async.** Every capability returns a Promise. Never add a
  synchronous bridge call, even for trivially cheap data — one synchronous API
  makes the iOS and Android transports unimplementable.
- **Method name is the permission scope.** `namespace.action`, where
  `namespace` is the scope. There is no separate scope registry.
- **`protocolVersion` is negotiated in the handshake.** Present from the first
  release; not retrofittable.
- **Never expose host credentials to a mini app.** No session tokens, cookies,
  or API keys cross the bridge.
- **Origin is `moonpool://<mini-app-id>/`.** Never `file://`. Changing this
  breaks stored data for every deployed mini app.

## Out of scope for v0

Do not implement, scaffold, or suggest these. They are the difference between
a project one person can maintain and one that dies:

live updates · CDN distribution · bundle signing · developer portal ·
plugin system · Flutter wrapper · native iOS/Android cores · analytics ·
capability discovery API

Native cores and additional transports come after the protocol is stable and
proven in the browser. That ordering is deliberate.

## v0.1 definition of done

- [ ] `Transport` interface, with an iframe implementation for the browser
- [ ] Client: JSON-RPC encoding, promise correlation, timeout, error mapping
- [ ] Host: dispatcher, manifest parsing, scope enforcement
- [ ] Handshake with version negotiation
- [ ] Capabilities: `portal.*`, `profile.get`, `storage.*`
- [ ] Mock host + hello-world mini app runnable in a browser
- [ ] Test coverage for every error code in `SPEC.md` §4.4

---

## Working agreement

**`SPEC.md` wins.** If the implementation and the spec disagree, the
implementation is wrong. If the spec is genuinely wrong or underspecified, stop
and say so — propose a spec change and wait for approval. Do not resolve the
conflict by editing the spec to match the code.

**Tests before implementation.** Derive failing tests from the spec first, then
implement. Tests are the contract the maintainer reviews; keep them readable as
specification rather than as coverage.

**Record decisions.** When a non-obvious design choice is made, write a short
ADR in `docs/adr/NNNN-title.md`: context, decision, consequences. One page.
These double as onboarding docs for contributors.

**Explain, don't just produce.** This project is also a learning exercise for
the maintainer, and it is a security-sensitive component. When you make a
choice with a security or portability rationale, say why in one or two
sentences. If a change touches §9 of the spec, flag it explicitly.

**Small commits.** One logical change each. Conventional Commits
(`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).

**Ask before scope growth.** Generation is cheap; maintenance is not. If a task
implies work beyond what was requested, surface it rather than building it.

---

## Repository layout

```
SPEC.md                     protocol specification (normative)
CLAUDE.md                   this file
packages/
  protocol/                 shared types, error codes, message validation (pure)
  client/                   runs inside the mini app
  host/                     dispatcher, permission gate, manifest parsing
  transport-iframe/         browser development transport
examples/
  mock-host/                dev host, runs in a browser
  hello-miniapp/            minimal mini app
docs/adr/                   architecture decision records
```

Nothing in `packages/protocol`, `packages/client`, or `packages/host` may
import a platform API. That rule is what keeps the native ports cheap later.

## Stack

TypeScript (strict), npm workspaces, Vitest, Node 20+.
Prefer zero runtime dependencies in `protocol`, `client`, and `host`.

## Commands

```bash
npm install
npm test              # vitest
npm run typecheck     # tsc --noEmit
npm run build
npm run dev           # serves examples/mock-host
```

## Language policy

- All artifacts that live in the repository are in **English**: code,
  comments, commit messages, SPEC.md, ADRs, READMEs, issues, and PR
  descriptions. This keeps the project contributable for a global audience.
- All **conversation with the maintainer is in Korean**: session dialogue,
  plans, explanations, and questions. When quoting spec text or code, keep
  the original English inline.
