# 16. Validate inbound JSON in stages

Date: 2026-10-23
Status: Accepted

## Context

storage.set already deeply validated its value, but arbitrary non-JSON data
elsewhere in a structured-clone request could pass routing checks. Validating
everything before permission checks would change the approved -32000 versus
-32602 precedence. Reading routing getters before checking their descriptors
would execute caller code. Whole-message error classification is the T11 gate.

## Decision

The maintainer approved this staged contract on 2026-10-23. Amend SPEC before
implementing the new rejection behavior.

Inspect received values as unknown without serialization, coercion, mutation,
getter evaluation, or toJSON calls. Reuse isJsonValue's existing value contract.
The host may inspect a shallow envelope view excluding params and then validate
the original params separately. This is inspection only: no invalid input may
be dropped or repaired to admit it; provider values keep their original data.

Require own enumerable data members on an ordinary record (Object.prototype
or null) for the envelope, including its optional params member descriptor.
Get routing fields only from own data descriptors. Accessor, hidden, symbol,
non-ordinary, or recursively non-JSON envelope data is an invalid request.
Arbitrary extra envelope members remain allowed when valid JSON. No size or
depth limit is introduced; preserve shared acyclic values and nested nulls.

Maintain these stages:

1. Reject top-level arrays as in T08. Ignore frames without a recoverable own
   numeric data id, including notifications. Do not execute getters to find it.
2. Classify initialization using a JSON-valid envelope outside params plus
   existing request syntax and object-or-omitted params shape. A valid boundary
   resets the id floor as in T10. Deeply invalid params still establish this
   boundary and later fail with -32602; invalid envelope data cannot reset it.
3. Apply T10 sequence rejection/consumption before ordinary errors. Duplicates
   still get -32600/id:null even if other input is invalid.
4. Reject bad envelope syntax or non-JSON envelope data with -32600. Echo a
   finite numeric id; use null for NaN/infinities so the response itself is
   JSON. This explicitly replaces the old NaN echo test expectation.
5. Reject malformed params containers with -32602. An own params:undefined
   is present and invalid, unlike omission. Then apply initialization and scope
   gates before deep params validation for ordinary calls.
6. Reject non-JSON params trees with -32602 before method lookup, field checks,
   provider availability, or invocation. An initialize resets initialization
   before this check; ping and other portal methods require no scope. Valid
   JSON unknown methods retain scope-before-lookup behavior. Unknown methods
   with non-JSON params now get -32602 after grants rather than -32601.

All error text is fixed and does not echo invalid data. Reflection failures
fail closed; if a numeric id was safely recovered, use the same sequence/error
rules, otherwise stay silent. As in ADR 0008, this does not guarantee freedom
from arbitrary Proxy trap side effects or concurrent mutation.

## Consequences

- SPEC §4.1, §4.2, and §5.1 were amended before implementation. The new envelope
  admission refines T10's boundary, while preserving id consumption, method
  syntax, scope-before-deep-params, and existing storage error behavior.
- Invalid input never reaches providers; valid extra JSON envelope members,
  shared graphs, arbitrary storage keys, and original values remain usable.
- Root/header getters are not a supported wire representation. Unknown-data
  test injection must exercise the actual host boundary without serializing.
- Keep Transport unchanged. No new public API, platform dependency, string
  parsing transport, payload limit, or outbound response policy is included.
