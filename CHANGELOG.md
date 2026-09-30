# Changelog

## Unreleased

### Changed

- Require a string protocolVersion for portal.initialize (SPEC §5, ADR 0007).
  Missing or non-string input now receives -32602; unsupported strings
  continue to receive -32004 under exact-match negotiation.
- Reject unknown top-level params fields for known methods with -32602
  (SPEC §4.2, ADR 0006), after scope enforcement and before provider access.
  Application-defined object keys inside storage.set's value remain allowed.
- Tighten the draft storage contract (SPEC §6.3, ADR 0004): storage.set must
  reject a missing or top-level null value with -32602. Nested null remains
  permitted, and storage.get returns `{ "value": null }` only for an absent
  key. Implementations allowing top-level null writes must reject them to
  conform to this revision.
