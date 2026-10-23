# 17. Validate responses before consuming pending calls

Date: 2026-10-23
Status: Accepted

## Context

The response guard checked only the top-level version, id, outcome presence,
and basic error fields. Non-JSON nested data, accessors, and fractional error
codes could pass or throw, and an explicit undefined outcome could hide a
second outcome. The client would then discard a pending entry and its timer.

SPEC §3.1 requires JSON data; §4 adopts
[JSON-RPC 2.0 §5](https://www.jsonrpc.org/specification#response_object),
including exactly one outcome and an integer error code. This task implements
those existing requirements without amending the protocol.

## Decision

Make isJsonRpcResponse accept unknown. First apply the existing isJsonValue
inspection to the complete frame, including result, error.data, and extra
members. Then require an object with own jsonrpc/id members, version 2.0,
and a numeric id or null. Require exactly one own result/error member.
An error must be an object with own integer code and string message members.
Null ids remain error-only under ADR 0013.

Retain finite numeric diagnostic ids: the host can echo a nonpositive or
fractional invalid request id. Response validation is not request-id admission;
the client's pending Map decides correlation. Do not whitelist error codes,
add numeric bounds, reject valid JSON extras, or interpret method-specific
result fields. Null, false, zero, and empty strings remain valid results/data.

Validate before touching pending entries or timers. Ignore malformed, null-id,
unknown-id, and late responses without replying or renewing deadlines. A valid
matching response discards its entry and clears its timer before settlement.
Preserve the wire error code/message/data in MoonpoolError. Credential removal
remains the host's responsibility; JSON shape validation cannot identify secrets.

## Consequences

- Reuse the portable JSON validator without assertions, coercion, serialization,
  getter/toJSON calls, input mutation, dependencies, or transport API changes.
- Inspection retains ADR 0008's limits: no payload/depth budget and no guarantee
  against arbitrary Proxy trap side effects or concurrent mutation. Shared
  acyclic data and deeply nested JSON remain supported.
- Existing §9 origin/source and host scope checks are unchanged. The complete
  response frame is checked before promise correlation; capability result
  schemas, client terminal closure, and the §11 document-epoch race are separate.
- Tests cover malformed frames, valid data, unchanged deadlines, out-of-order
  completion, duplicate/unknown/expired ids, and sanitized errors from a real
  host/client pair. No existing test contract is weakened.
