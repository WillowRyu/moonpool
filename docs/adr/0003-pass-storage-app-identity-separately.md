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
  Storage null semantics were subsequently resolved in ADR 0004, and unknown
  params fields are rejected under ADR 0006. Any value size limit remains an
  open decision. An extra miniAppId field must never select another app.

## Example implementation verification (2026-10-22, T03)

The mock host now installs createMemoryStorageProvider with a separate Map
per app id. Provider and bridge integration tests verify app isolation,
deletion boundaries, preserved falsy values, repeat-handshake persistence,
and permission denial with the production provider installed. A fresh provider
starts empty; state is development-only and does not survive host restarts.
This implements the existing decision without changing the protocol.
