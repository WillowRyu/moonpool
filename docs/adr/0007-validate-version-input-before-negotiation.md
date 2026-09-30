# 7. Validate version input before negotiation

Date: 2026-09-09
Status: Accepted

## Context

The host compared params.protocolVersion directly with PROTOCOL_VERSION.
Missing and non-string input therefore received the same -32004 response
as a well-typed but unsupported version. SPEC §5 showed a string version
without explicitly separating input validation from negotiation.

The maintainer approved clarifying this distinction. SPEC was updated before
tests or implementation.

## Decision

Require params.protocolVersion to be a string. Reject omitted params, a
missing field, and non-string values with -32602 before comparing versions.
Keep exact-match negotiation: unsupported strings receive -32004.

Add no version-format grammar, trimming, or coercion. An empty string and
whitespace-padded strings remain unsupported strings, not type errors.

The existing initialization reset stays before method-level validation.
Unknown fields are still rejected under ADR 0006. A rejected initialization
leaves the document uninitialized, and a valid retry remains possible.

## Consequences

- Callers can distinguish fixing an input's presence/type from choosing a
  protocol version supported by the host.
- A local typeof check narrows the value before comparison without adding
  a new public API or a separate version-format validator.
- Tests exercise the host bridge, including recovery after rejection and
  the reset of a previous document's successful initialization.
- Recursive JSON validation and malformed-container repeat handling remain
  separate work; this change addresses the method's required version field.

The maintainer typed the implementation on 2026-09-09 after the tests were
verified RED. Verification: 172 tests passed, typecheck and lint clean.
