# Changelog

## Unreleased

### Changed

- Reject unknown top-level params fields for known methods with -32602
  (SPEC §4.2, ADR 0006), after scope enforcement and before provider access.
  Application-defined object keys inside storage.set's value remain allowed.
- Tighten the draft storage contract (SPEC §6.3, ADR 0004): storage.set must
  reject a missing or top-level null value with -32602. Nested null remains
  permitted, and storage.get returns `{ "value": null }` only for an absent
  key. Implementations allowing top-level null writes must reject them to
  conform to this revision.
