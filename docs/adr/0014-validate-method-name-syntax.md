# 14. Validate method-name syntax at the request envelope

Date: 2026-10-23
Status: Accepted

## Context

SPEC §6.1 required namespace.action with lowerCamelCase on both sides, but
did not define its exact character grammar, the error code for a malformed
string, or its precedence relative to params, initialization, and permissions.
The envelope guard previously accepted any method string. T09 required this
specification decision before changing that contract.

## Decision

The maintainer approved the recommended grammar, error code, and validation
order on 2026-10-23. Amend SPEC before implementation.

Define the grammar as a full-string match of
`[a-z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*`: exactly one dot; each side starts
with an ASCII lowercase letter and continues with ASCII letters or digits.
Permit acronym runs after the first letter, such as profile.getURL, and
numeric suffixes such as storage2.get2. Reject underscores, hyphens, Unicode
letters, whitespace, empty components, and additional dots. Do not trim,
lowercase, or otherwise repair names. Do not introduce a length limit.

Make method syntax part of isJsonRpcRequestEnvelope, after establishing a
string method. For an addressable request, reject a malformed name with
-32600 Invalid Request and echo its numeric id, using the existing envelope
rejection path. This occurs before params-container validation, initialization
state, or scope enforcement. Do not invoke providers or alter session state.
The matcher must reject a suffix newline as well as interior whitespace.

Preserve the existing rules for arrays, no-id notifications, ids, valid
method names, permissions, and per-method params. This is name validation,
not capability registration or discovery. The exact portal namespace alone
remains exempt from scope requirements.

| Addressable request | Before initialization | After initialization |
| --- | --- | --- |
| profile..get with object params | -32600 | -32600 |
| profile..get with array params | -32600 | -32600 |
| profile.get with array params | -32602 | -32602 |
| profile.get with object params | -32005 | Existing scope/provider behavior |
| profile.unknown with object params | -32005 | -32000 if ungranted; -32601 if granted |

Standalone notifications still receive no reply even for malformed method
names. Top-level arrays still get the T08 single -32600/id:null response.
Malformed portal.initialize spellings are not repeat handshakes and must
not reset an existing session. A later valid initialization remains accepted.

## Consequences

- SPEC §6.1 defines the grammar and SPEC §4.2 defines rejection precedence,
  recorded before implementation. This resolves T09 only; the T11 whole-JSON
  boundary and T10 id policy remain separate decisions.
- Tests cover valid and malformed names, whitespace/newline boundaries,
  code precedence, provider non-invocation, unchanged session state, and the
  existing unknown-method permission behavior (SPEC §9.3 / §9.6).
- Keep all checks in the pure protocol/host kernel, with no platform API,
  dependency, scope registry, client-local failure contract, or new capability.
- Early syntax rejection depends only on public grammar, not a capability
  lookup, so it does not disclose whether an ungranted method is implemented.
