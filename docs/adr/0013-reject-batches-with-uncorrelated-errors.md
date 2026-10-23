# 13. Reject batches with one uncorrelated error

Date: 2026-10-23
Status: Accepted

## Context

SPEC §4.1 rejects all top-level request arrays in 0.x, but the host previously
dropped them at its numeric-id check. An array has no single request id; using
one member's id could incorrectly settle an unrelated client request.
The shared response type previously admitted only numeric ids.

## Decision

At host receive entry, before numeric-id checks or session processing, reject
every top-level array with one response object: id null, code -32600, and a
fixed message. Do not inspect or dispatch members. This includes empty,
nested, malformed, and notification-only arrays under Moonpool's explicit
no-batch profile. Standalone notifications remain unanswered.

Use the uncorrelated error id defined by
[JSON-RPC 2.0 §5](https://www.jsonrpc.org/specification#response_object).
The response type permits null; the response guard permits it only with an
error and retains the existing error-shape checks. Request guards still
require a positive integer id. No new request-id policy is introduced.

The client ignores a null-id response before looking up its numeric pending
Map. It does not settle calls, clear timers, infer a member id, or reply.
Existing correlated replies, timeouts, and closure rules continue to apply.

## Consequences

- Batch rejection changes no initialization, grants, or provider state. In
  particular, an initialize member cannot start or reset a document session.
- Arrays inside ordinary JSON params and storage values remain permitted
  where their existing method schema allows them; only the frame is tested.
- No transport API, platform dependency, spec amendment, payload limit, or
  batch execution feature is introduced. General response validation stays
  in T12; id reuse/backward-id policy stays in T10.
- Tests verify one reply, no provider calls, state preservation, nullable
  error recognition, and pending-request/timer isolation through a real
  client/host connection and controlled peer frames.
