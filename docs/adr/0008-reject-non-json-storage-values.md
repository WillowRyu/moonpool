# 8. Reject non-JSON storage values without conversion

Date: 2026-09-09
Status: Accepted

## Context

The storage.set guard rejects a missing or top-level null value but does not
inspect nested data. The iframe transport's JsonValue assertion is not a
runtime check. A value containing undefined, NaN, a Date, or a cycle can
reach a provider even though it is outside the JSON data model.

Serializing to validate would change some inputs: an undefined object member
disappears, non-finite numbers become null, and Date values become strings.
That could store something different from what the caller supplied, with
different behavior across transports.

The maintainer approved explicit -32602 rejection without conversion.
SPEC §6.3 was updated before tests or implementation.

## Decision

Validate the storage.set value tree before provider availability or access,
after permission enforcement. Reject data outside the JSON model with
-32602. Do not normalize, remove, or replace invalid data.

Retain ADR 0004's top-level null rejection and nested null support. Retain
ADR 0006's freedom for application-defined keys inside the stored value.
A repeated reference to an acyclic object is not a cycle: it can represent
the same JSON content in two positions. A circular path cannot.

Use a pure validator in protocol with the storage.set guard as its first
consumer. Keep the Transport contract unchanged. This slice does not settle
invalid whole-envelope handling or a numeric size/depth limit.

## Consequences

- Rejected writes must leave existing storage and the supplied value intact.
- Host tests deliberately inject unknown values through the in-memory
  transport using a test-only cast. This preserves invalid data for the
  kernel to inspect; it is not proof of browser transport wiring.
- Cover invalid leaves, non-JSON objects, cycles, valid shared references,
  and nested values. Sparse array holes would be replaced by null during
  JSON serialization and must not be silently accepted as null elements.
- Avoid using the JavaScript call stack to traverse arbitrary input depth.
  A deep finite tree must not fail merely because validation recurses.
  Shared subtrees should not be repeatedly traversed exponentially.
- Resource limits and full boundary conformance remain follow-up work;
  these tests are not a claim that all of SPEC §9.6 is implemented.

## Implementation handover (2026-09-11)

Use an explicit stack of visit/complete tasks and a per-call object-state
map. Visiting an active ancestor rejects a cycle; visiting a completed
object reuses its validation result. Schedule completion below the object's
children so it runs only after they have passed.

Accept finite scalar JSON values, dense arrays, and ordinary records
(Object.prototype or null). Inspect own property descriptors rather than
evaluating getters, invoking toJSON, or serializing. Reject symbol keys,
non-enumerable record members, and named array members that serialization
would omit. Array length is bookkeeping, not a stored member. Reflection
failures yield false. This is inspection of received data, not a guarantee
against arbitrary Proxy trap side effects or concurrent mutation.

Tests additionally pin dropped-member cases, not executing getter/toJSON
code, and efficiently handling a small graph with many shared paths. Size
accounting for an expanded serialized representation remains separate work;
fast graph validation does not imply a small serialized payload.

## Verification (2026-09-30)

The maintainer typed the iterative validator in protocol and connected it to
isStorageSetParams. All 201 tests pass, including the 29 storage JSON boundary
cases. Typecheck, lint, and both browser example builds also pass. The agent
made no production implementation edits. This verifies the storage value
slice, not whole-envelope validation or a resource-limit policy. Host error
wording is aligned; guard documentation remained for the next study step at
that checkpoint.

## Documentation alignment (2026-10-22, T01)

The guard comments now describe nested JSON validation, top-level null
rejection, and the separate whole-frame validation boundary. The learning
guide records completion of this follow-up. Runtime logic and the decision
above are unchanged. Reverified all 201 tests, typecheck, lint, and both
browser example builds.
