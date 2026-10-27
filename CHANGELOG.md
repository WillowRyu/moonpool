# Changelog

## Unreleased

Browser v0.1 milestone complete on 2026-10-26. The source workspace implements
the seven completion requirements in its tested browser-development configuration.
Protocol 0.1 remains draft/unstable; this status does not publish a release.
See [completion evidence and retained limits](docs/v0.1-conformance.md).

### Added

- Complete T22's native target/toolchain inventory and pre-code Android/iOS
  origin-probe criteria. Record installed virtual-device candidates, build/boot
  gaps, SDK-tool warnings and unresolved host/support choices; no native runtime
  code, tool installation or protocol change is included.
- Document the Android/iOS follow-up as 44 planned tasks (T22–T65), with paired
  platform evidence, acceptance criteria and dependencies. Keep the host
  framework undecided and distinguish reference PoCs, real-app verification
  and deployment decisions. Add the Korean roadmap; no native implementation
  or protocol change is included in this planning checkpoint.
- Reconcile the browser v0.1 checklist, public roadmap, working agreement and
  learning guide with verified behavior. Add a requirement/security evidence map,
  explicit deployment/provider responsibilities and retained §11 limits (T21).
- Record final browser integration/security verification with actual storage
  and close components, both notifications, permission/input/privacy checks,
  native origin/source and targetOrigin controls, and built-preview evidence.
  Extend only the separate manual fixtures and retain an HTML-only diagnostic
  control; 1131 tests and all required checks pass (T20).
- Complete the SPEC §4.4 error-code verification matrix: test all 14 client
  mappings with/without data, null-id deadline preservation, specified actual
  host producers and provider-error sanitization. Document unimplemented
  producers separately; no reserved policy or runtime behavior changes (T19).
- Implement accepted ADR 0022 / SPEC §8.1.1 browser containment: independently
  CSP-bound served wrappers, wrapper-local kernels, strict host-only JSON realm
  adapters, trusted Document/instance binding and retained app-partitioned
  providers. Terminally revoke only the affected Portal, invalidate stale
  controls, remove both frames, and attempt cleanup despite failures. Preserve
  same-origin repeat handshakes and storage across explicit recreation (T18).
- Run the browser example with two fixed app origins and add separate manual
  integration checks with recorded development/built-preview evidence.
- Accept replacement ADR 0022 for per-Portal browser containment with
  explicit wrapper/host realm ownership, retained app-partitioned providers,
  host-only data boundaries and complete disposal acceptance checks. This is
  an approved design, implemented and verified in T18.

- Extend the manual navigation lab with independently policy-bound Portal
  wrappers, recorded multi-origin isolation/lifetime observations, and a
  documented cross-realm integration constraint. This remains research and
  does not change the normative or shipped containment contract.
- Add a manual three-origin navigation research fixture, recorded browser
  observations, and a proposed constrained CSP development profile for T18.
  This records gaps in iframe navigation observability; it does not change
  the normative contract or ship navigation containment (T17, ADR 0022).
- Add client.onNotification with independent, idempotently removable local
  subscriptions to the two SPEC §6.4 events. Validate inbound data, project
  known fields, and give each listener a separate copy. Isolate synchronous
  throws and asynchronous rejections while preserving response correlation;
  clear subscriptions on close and ignore unknown/malformed notifications
  without replying (ADR 0021).
- Return a connection-bound notification sender from Host.connect, with async
  notifyLifecycle and notifyEnvironmentChanged methods for SPEC §6.4. Add
  shared notification types, validate local arguments at runtime, and create
  fresh id-free frames without request correlation or timers. Completion
  confirms local submission only; subscriber delivery follows separately
  (ADR 0020).
- Implement portal.close with optional string reason and a per-connection
  asynchronous onCloseRequested embedder hook. Validate input before returning
  -32001 for a missing hook; no scope is required. Submit acceptance before
  invoking dismissal, keep later hook failures host-local, and document that
  response delivery/completed teardown is not guaranteed (SPEC §6.2, ADR 0019).
- Add a mini-app dismissal button and a browser host handler that closes only
  its captured Portal, displays reason as text, and preserves host storage
  when starting a fresh Portal. Repeated/stale handlers cannot dismiss a
  replacement frame.
- Validate inbound request envelopes and params as JSON in separate stages.
  Inspect own data descriptors without running getters or converting input;
  preserve valid extra envelope fields and original provider values. Reject
  non-JSON envelopes with -32600 and non-JSON params with -32602 after grants
  (SPEC §4.1 / §4.2 / §5.1, ADR 0016).
- Enforce strictly increasing request ids per document on each host connection.
  Reject duplicate/backward ids with -32600 and id null without dispatching
  or disturbing pending calls; consume new positive ids before validation.
  General initialize requests begin a fresh sequence while preserving grants
  and storage, including when version negotiation fails (ADR 0015).
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

### Fixed

- Make iframe transport closure terminal and idempotent: ignore late sends,
  subscriptions and retained callbacks, stop receive fan-out after closure,
  and preserve closure through reentrant or failing platform cleanup (§8.1.1).

### Changed

- Make local client closure terminal and idempotent. Reject later calls with
  -32008 without sending or allocating timers; drain pending calls before
  once-only adapter cleanup, even when cleanup throws. Map synchronous send
  failures to fixed -32603 / {phase:"send"} errors after per-request cleanup,
  preserving other calls, consumed ids, and the first settled outcome without
  automatic retries (SPEC §4.6 / §4.7, ADR 0018).
- Validate complete response JSON before client correlation, including nested
  results, error data, and extra members. Require exactly one own outcome and
  an integer error code. Ignore malformed replies without consuming pending
  calls or renewing deadlines; preserve valid falsy values and wire errors
  (SPEC §4.3 / §4.5, ADR 0017).
- Return id null for NaN/infinite request ids so errors remain JSON. Treat
  explicit params:undefined as invalid, and reject non-JSON params before
  lookup even for unknown methods after their scope is granted.
- Require method names to contain exactly two ASCII lowerCamelCase components
  separated by one dot, allowing letters/digits after each initial lowercase
  letter. Reject malformed names with -32600 before params, initialization,
  or scope checks; preserve valid unknown-method permission behavior
  (SPEC §4.2 / §6.1, ADR 0014).
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
