# 3. Pass storage app identity separately from the key

Date: 2026-09-04
Status: Accepted

## Context

SPEC §6.3 requires storage to be namespaced per mini app id. Two mini apps
may use the same key without sharing data. The host kernel already derives
permissions from host-held configuration; storage ownership must likewise
come from that configuration, never from a request field.

## Decision

The embedding host supplies a StorageProvider with asynchronous methods:
`get(miniAppId, key)`, `set(miniAppId, key, value)`, and
`delete(miniAppId, key)`. The kernel supplies `config.manifest.id` and passes
the validated key separately. No request field can override the app identity.

The provider must partition storage by the supplied id. Passing an id does
not itself enforce isolation: the kernel owns selecting the correct identity,
and the provider owns respecting it when accessing data. The browser example
can implement this with a separate in-memory map for each app id.

Permission checks stay before method dispatch (§9.3), and params are validated
before invoking the provider (§9.6). The provider methods remain asynchronous
(§9.5), so the kernel does not depend on any platform storage API (§3).

## Consequences

- A kernel test can observe the id and key separately and verify that two
  connections use their own ids through one shared provider. Each embedding
  host must also verify that its provider actually partitions data.
- A provider bound to one mini app would shorten calls to `get(key)`, but
  would leave correct binding entirely to each embedding host.
- A kernel-composed string key would couple the provider contract to an
  encoding convention. Keeping the arguments separate leaves that choice
  inside each provider. With the current manifest id grammar (no colon), a
  colon in the caller's key alone does not cause a collision in `id:key`;
  this decision does not introduce a ban on colon-containing keys.
- This identity decision changes no wire message or SPEC requirement.
  Storage null semantics were subsequently resolved in ADR 0004. Unknown
  params fields and any value size limit remain open decisions. An extra
  miniAppId field must never select another app, whether unknown fields are
  eventually ignored or rejected.
