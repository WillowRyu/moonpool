# 20. Bind typed notification senders to host connections

Date: 2026-10-23
Status: Accepted

## Context

SPEC §6.4 defines two host-to-mini-app notifications with no id, but the host
currently exposes only request reception. T15 adds typed sending; subscriber
delivery belongs to T16. A host can attach several transports, so selecting a
recipient through shared mutable state risks notifying the wrong Portal.

## Decision

Return a HostConnection handle from Host.connect, bound to that transport.
Existing callers may continue ignoring the return value. Expose asynchronous
notifyLifecycle(state) and notifyEnvironmentChanged(changes) methods for exactly
the two §6.4 events. Keep their state/params and discriminated wire types in
protocol. Do not introduce a generic arbitrary-method sending API.

Validate local sender arguments at runtime as well as in TypeScript. Lifecycle
is resumed or paused. Environment changes are an ordinary JSON object with
only optional colorScheme (light/dark) and locale (string). Both fields may be
absent; preserve an empty string and do not invent locale syntax/length rules.
Reject invalid local input with a fixed TypeError before transport access,
without getters, conversion, or echoing the input. This is local API validation,
not a new wire error or a decision about unknown inbound notification methods.

Construct fresh frames and params from the declared fields only, omitting id
entirely. Send once using the existing transport, without registering correlation,
a timer, or a reply listener. The Promise resolves after send returns, not after
peer receipt or processing. A synchronous send exception rejects that Promise
with the original local error; do not retry or send an error frame.

This is a send-only API: the embedder owns when to notify and its current
environment/lifecycle state. Sending does not change handshake state, id floors,
grants, config/environment objects, or storage. It does not queue until handshake,
infer OS state, broadcast, or track whether a separately owned transport closed.
The embedder owns connection lifetime and must stop using its sender on teardown.

## Consequences

- Implements existing §3.1 / §4.1 / §6.4 requirements without a SPEC amendment,
  new wire field, transport extension, platform API, or runtime dependency.
- Fresh params prevent caller mutation from changing an already submitted
  notification. Two handles remain isolated even when one host is reused.
- Tests verify exact frames, local validation, asynchronous failures, no timers,
  unchanged request state, connection isolation, and real-client pending-call
  safety. Current clients ignore notifications; subscriber behavior remains T16.
- SPEC §11 document epochs and peer-disconnect signalling remain open. No
  delivery acknowledgement, automatic state synchronization, replay, or
  additional lifecycle state is claimed.
