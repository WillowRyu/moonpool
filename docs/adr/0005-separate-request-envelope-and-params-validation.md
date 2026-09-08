# 5. Separate request envelope and params validation

Date: 2026-09-07
Status: Accepted

## Context

SPEC §4.2 requires params to be an object or omitted, and assigns invalid
params their own error code, -32602. Before E4.4a, the host used one complete
request guard and answered -32600 for any failure. This conflated an invalid
JSON-RPC envelope with invalid arguments, even when jsonrpc, id, and method
are otherwise correct.

Simply changing that error code would misclassify malformed envelopes.
Removing the params check from the existing guard while retaining its
JsonRpcRequest predicate would falsely claim that params is an object.

## Decision

Introduce an intermediate JsonRpcRequestEnvelope type and an
isJsonRpcRequestEnvelope guard. The guard proves the object shape, JSON-RPC
version, positive integer id, and string method. Its params field remains
JsonValue until the complete request guard verifies object-or-omitted shape.

Keep JsonRpcRequest's existing object-or-omitted params contract. Its guard
uses the envelope guard and then checks params, so it remains usable as a
standalone complete request-shape validator.

The host keeps its no-id rule first. It then rejects invalid envelopes with
-32600 and invalid params containers with -32602, before session or method
processing. This splits the existing wire-shape gate in place. Per-method
field validation remains after the permission gate and before provider
availability or invocation (§9.3 / §9.6).

## Consequences

- Type narrowing reflects what has actually been validated at each stage.
  An envelope alone cannot justify reading params.key or protocolVersion.
- The complete guard repeats the cheap envelope check when the host calls
  it after the envelope guard. Keeping its independent contract is simpler
  than adding another validator that assumes an earlier check was performed.
- All validation remains in the pure kernel. The transport contract and
  wire format are unchanged.
- This does not decide unknown-field handling, recursive JSON validation,
  size limits, batch responses, or reused request ids. Those remain separate
  work. Required method fields are not proven by either general guard.

The maintainer typed the E4.4a implementation on 2026-09-07 after the tests
were verified RED. Verification: 134 tests passed, typecheck and lint clean.
