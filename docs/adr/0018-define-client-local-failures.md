# 18. Define terminal client closure and local send failures

Date: 2026-10-23
Status: Accepted — maintainer approved the recommended mapping on 2026-10-23

## Context

SPEC §4.6 drains in-flight calls on local close, but does not explicitly define
later calls, repeated close, or exceptions from send. Currently later calls
still send and arm timers; a synchronous send exception rejects the Promise
with the transport's raw thrown value while leaving its pending entry/timer.
Calling close again repeats adapter cleanup. These are client-local failures;
they do not establish that the remote host is unhealthy or a request undelivered.

## Decision

- Make local close terminal. Mark closed and discard/reject all pending calls
  with -32008, clearing their timers before invoking adapter cleanup. Later
  call/initialize return rejected Promises with -32008, without sending,
  allocating ids, arming timers, or reopening. Repeated/reentrant close is a no-op.
  Ignore callbacks that an adapter retained after close.
- Attempt unsubscribe and transport.close once each. Even if cleanup throws,
  the client remains closed and its pending calls/timers are already drained.
  Attempt both cleanup operations, then synchronously rethrow the first thrown
  value from close (even undefined). This is a local lifecycle API failure,
  separate from capability Promises; it is not mapped to a remote wire error.
- If transport.send throws synchronously while that request is still pending,
  delete only its entry, clear its timer, and reject its Promise with
  MoonpoolError(-32603, "failed to send the bridge request", { phase: "send" }).
  Do not forward the raw thrown value/message/stack or inspect/coerce it.
  Do not classify it as -32007 (remote host health) or -32008 (terminal closure).
- Leave the connection and other pending calls usable after a send failure.
  Consume the attempted id; never reuse it. Do not retry automatically: a
  transport may throw after delivery, so duplicate side effects are possible.
  A later reply for the discarded id is ignored.
- First settlement wins. A synchronous response or local close during send
  may already consume the entry. A subsequent send exception must not replace
  that outcome or affect other requests. Register pending before calling send.
  Synchronous adapter callbacks do not make capability APIs synchronous.

## Consequences and alternative

The recommended mapping gives callers a stable code and a fixed phase marker
for a local send failure, without claiming remote execution did or did not
occur. Unknown transport exception details are not exposed in the rejection.
The alternative is to keep rejecting with the original thrown value after the
same cleanup. That preserves transport diagnostics but leaves callers handling
arbitrary values and platform-specific shapes instead of MoonpoolError.

The maintainer approved this decision after the previous behavior, problem,
and consequences were explained. SPEC §4.6 / §4.7 is updated before dependent
implementation/tests. No new error code, transport API, automatic
retry, remote disconnect detection, result schema, or platform dependency was
added. Peer disconnect and document epochs remain §11 questions. Tests
exercise cleanup, future calls, independent pending requests, failure recovery,
late responses, reentrancy, and first-settlement ordering using fake timers.
