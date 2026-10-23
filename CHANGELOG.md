# Changelog

## Unreleased

### Added

- Reject top-level request arrays with one -32600 response and id null before
  processing initialization or capability calls. Execute no array members,
  including notification-only batches, while preserving ordinary nested
  arrays in method input (SPEC §4.1, ADR 0013).
- Parse the browser example's actual moonpool.json as host-owned bundled text
  before Portal creation. Select the pinned origin by validated app id and
  resolve the declared entry from that origin's root; invalid configuration
  or an unmapped id stops startup (ADR 0012).
- Expose the pure host's `parseManifest` and local `ManifestError`, composing
  field validation with entry-path and recognized-scope admission. Recognize
  scopes from protocol capability namespaces, independently of host grants
  and installed providers; reject unknown declarations instead of dropping them.
- Add internal manifest field parsing and validation for JSON text, required
  members, id/name/version formats, and string permission arrays as the first
  stage of manifest admission.
- Add browser storage controls and host-selected profile-only/storage-enabled
  configurations. Recreate the Portal connection on each selection while
  retaining host-held storage, show permission errors and CRUD results, and
  validate read values before text rendering (ADR 0009).
- Install an asynchronous, per-mini-app in-memory storage provider in the
  browser mock host. Preserve falsy values and nested null, isolate identical
  keys across apps, and retain data across repeat handshakes. Default grants
  remain profile-only; browser storage controls follow separately.
- Connect the browser mock host's fixed profile provider and display
  profile.get results in the mini app after initialization. Render returned
  strings as text and show capability error codes separately from handshake
  failures. Add example tests for provider wiring and the display flow.

### Changed

- Represent uncorrelated errors with nullable response ids and explicitly
  ignore them in client correlation without settling requests or clearing
  their timers. Null ids remain invalid for Moonpool requests.
- Define manifest entries as unencoded, slash-separated relative file paths
  with literal parent traversal checked against the package root. Reject URL
  syntax, backslashes, percent encoding, controls, edge whitespace, and
  directory targets (SPEC §7, ADR 0011).
- Define manifest display-name length as 1–40 Unicode code points, including
  one per supplementary-plane character (SPEC §7, ADR 0010).
- Validate the browser mini app's profile displayName at runtime before
  rendering, replacing its result type assertion. Report invalid result
  shapes as local profile errors while preserving the successful handshake.
- Reject non-JSON storage.set values with -32602 before provider access
  (SPEC §6.3, ADR 0008). Invalid nested data must not be dropped or converted;
  nested null and application-defined object keys remain allowed.
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
