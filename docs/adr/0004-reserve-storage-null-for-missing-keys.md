# 4. Reserve a null storage result for missing keys

Date: 2026-09-04
Status: Accepted

## Context

SPEC §6.3 uses `{ "value": null }` for an absent key. Without a restriction on
storage.set, deliberately storing null would produce the same read result.
Accepting that ambiguity is possible, but makes absence indistinguishable
from an intentionally stored value.

## Decision

Reserve a top-level null value for the missing-key result. A storage.set
request with no value, or with value equal to null, receives -32602 before
the provider is called. Rejecting it must not change an existing value.

Null nested inside an object or array remains valid JSON data. False, zero,
and the empty string are also valid stored values. The restriction applies
only to the entire value supplied to storage.set.

The maintainer approved the exact SPEC §6.3 wording before the tests and
implementation. Removing a key is expressed through storage.delete.

## Consequences

- A successful read containing `{ "value": null }` unambiguously means that
  the key is absent. No additional response field is needed.
- A caller deliberately submitting null gets an explicit error, rather than
  a successful write whose result looks like absence. Applications that need
  a nullable field can store an object containing that field.
- The kernel validates the rule before invoking a provider (SPEC §9.6).
  Provider implementations must preserve the same distinction when encoding
  and reading stored data.
- The provider contract can exclude null at the top level while continuing
  to accept ordinary JSON objects and arrays containing null.
- This tightens the draft storage contract and is recorded in CHANGELOG.md.
