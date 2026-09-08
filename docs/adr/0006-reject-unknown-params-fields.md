# 6. Reject unknown params fields

Date: 2026-09-08
Status: Accepted

## Context

SPEC lists each method's inputs but originally left unknown-field handling
unspecified. Required-field guards allowed additional fields, and host
dispatch ignored them. A caller could therefore believe an unsupported
option had taken effect even though the host never used it.

The maintainer chose explicit rejection over silently ignoring unsupported
params. SPEC §4.2 was updated before writing the tests or implementation.

## Decision

For a known method, reject a top-level params member not defined for that
method with -32602. Scoped methods check permission first, then validate
params before checking provider availability or invoking it (§9.3 / §9.6).
Core methods apply their own allowed names in their existing branches.

Apply this restriction only to params itself. Application-defined object
keys inside storage.set's value remain data, including keys named
miniAppId, constructor, or anything else representable in the value contract.
This does not add a restriction on JSON-RPC envelope members or change the
handling of unknown methods and notifications.

The kernel continues to select storage identity from its manifest (ADR 0003).
Rejecting a forged params.miniAppId supplements that rule; it does not replace
it or mean that ignoring an unused field would itself breach isolation.

## Consequences

- Unsupported options and misspelled extra fields become visible failures.
  A rejected write/delete must not reach its provider or mutate storage.
- A new optional param will not be silently tolerated by an older host;
  protocol evolution must account for that compatibility cost.
- Use a pure helper to check only allowed top-level names. Required fields
  and their value types remain separate checks: having no unknown fields
  does not imply that a request contains all required inputs.
- Each existing method branch supplies its own allowed names, keeping the
  schema next to dispatch without introducing a method registry or plugin
  mechanism. A small host helper can send the common -32602 rejection.
- Recursive JSON validation and size limits remain later E4.4 work. This
  change does not claim full §9.6 conformance or implement unhandled methods.

The maintainer typed the implementation on 2026-09-08 after the tests were
verified RED. Verification: 160 tests passed, typecheck and lint clean.
