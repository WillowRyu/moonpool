# 19. Acknowledge Portal dismissal before invoking UI teardown

Date: 2026-10-23
Status: Accepted — maintainer approved the acceptance contract on 2026-10-23

## Context

SPEC §6.2 lists portal.close with optional reason and an empty result, but the
dispatcher currently returns -32601 after initialization. It does not define
reason's type, a missing embedder handler, or the meaning/order of success.
An embedder can destroy the caller's document when dismissing its UI, so
waiting until after dismissal to send a reply can leave no recipient.
Transport.send returns void: successful submission does not confirm receipt.

## Decision

- After existing envelope/id/initialization/JSON checks, accept omitted params,
  an empty object, or an optional string reason. Preserve strings, including
  empty strings, without trimming or coercion. Reject unknown params names and
  non-string reason with -32602 before handler lookup. No scope is required.
- Supply an optional asynchronous onCloseRequested(reason?: string):
  Promise<void> hook in per-connect options, not shared capability grants or
  caller-selected identity. The embedder binds it to that specific Portal.
  A missing hook returns -32001 and does not close anything.
- For a valid request with a hook, submit exactly one result:{} response
  through transport.send before invoking the hook. Success means acceptance
  of the dismissal request, not completed UI teardown or confirmed delivery.
  If response submission throws, do not invoke the hook or send a second reply;
  preserve the existing receive-side exception reporting path.
- Invoke the hook once per accepted request and await its Promise internally.
  A synchronous throw/rejection after acknowledgement is reported only on the
  host through the existing queued-rethrow mechanism. Do not send a second
  response, forward host exception details, retry, or roll back the success.
- The embedder owns transport/UI teardown and must make it idempotent for the
  bound Portal. A delayed hook must not dismiss a replacement Portal. Fresh
  valid ids remain separate requests; existing duplicate-id rules still apply.
  The pure kernel adds no DOM calls, automatic transport close, new wire event,
  client acknowledgement, or new connection-state machine.

## Consequences and alternative

This provides a small one-stage integration: send acceptance, then request UI
dismissal. It establishes submission-before-teardown ordering, not a guarantee
that the caller processes success before its document is destroyed. Other
pending calls retain existing timeout/local-close semantics if their context
survives; peer-disconnect signalling remains SPEC §11's open question.

An alternative is a two-stage embedder API: prepare/approve dismissal first,
then submit success, then invoke a separately returned teardown action. It
can report preparation failure before acceptance, at the cost of two host
responsibilities; it still cannot confirm response delivery with this transport.
The recommendation is the simpler acceptance contract above.

The maintainer approved the recommendation after reviewing prior behavior,
the problem, both options, and the delivery limitation. Updated SPEC §6.2
before dependent implementation/tests. Eight existing-gate regressions were
written and passed while awaiting approval.
T14 includes a mini-app close button and a bound browser host handler, with
tests for input/availability precedence, no-scope access, exception privacy,
submission/teardown ordering, and stale Portal identity. This touches SPEC §9.4,
§9.5, and §9.6: keep host details local, use async hooks, and validate before
calling embedder code. No navigation/disconnect solution or native core is added.
