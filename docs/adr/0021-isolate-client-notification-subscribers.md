# 21. Deliver validated notifications to isolated client subscribers

Date: 2026-10-23
Status: Accepted

## Context

T15 can send SPEC §6.4 notifications, but the client currently ignores them.
T16 needs local subscriptions without changing response correlation, timeouts,
or terminal client closure. Application callbacks can throw, reject, mutate
their input, unsubscribe, or close the client while a message is dispatched.

## Decision

Expose onNotification(listener): () => void on MoonpoolClient. The listener
receives the existing HostNotification discriminated union and may return void
or Promise<void>. Registration is local and sends no frame. Each registration
is independent, including repeated registration of one function. Unsubscribe
is idempotent. After close, registration returns a no-op without retaining it.

Preserve the response path first, including T12's permitted JSON response extras.
For other frames, recognize only ordinary JSON objects with own version 2.0,
one of the two known method names, and no own id of any kind. Validate params
and declared values without getters, coercion, or serialization. Unknown
methods and malformed notifications are ignored with no reply. Lifecycle
requires own state resumed/paused; environment fields are optional light/dark
colorScheme and string locale. Omitted environment params means an empty
change under §4.2's object-or-omitted rule; omitted lifecycle state is invalid.

Unlike T15's restricted local sender arguments, valid JSON extension members
in received envelopes/params need not be exposed or rejected by this client.
Project only the known fields into a fresh HostNotification. Give each listener
its own frame/params copy, so callback mutation cannot alter another delivery
or the transport input. This defines the local API view, not a new wire format.

Take a registration-order snapshot for each dispatch. Additions start with the
next notification; skip registrations removed before their turn. Never await
one listener before invoking the next. Catch synchronous failures and observe
Promise rejections, reporting each on the mini-app side via the existing queued
rethrow pattern. Do not swallow, reply, cancel other listeners, or affect
pending calls. No browser test runner or reportError migration is introduced.

On close, clear subscribers before invoking adapter cleanup; T13's closed
receive guard handles retained callbacks. Closing/unsubscribing inside a
listener prevents later removed listeners from running. Already-started async
application work is not cancelled. There is no replay, state mutation, or
implicit initialization: only notifications arriving while registered are
delivered. Register before initialize when early host events matter.

## Consequences

Implement existing SPEC §4 / §6.4 and local subscription semantics without a
SPEC amendment, wire error/ack, timer, transport extension, or platform import.
Unknown notification tolerance is distinct from local sender input validation.
The §6.4 startup race recorded in HANDOFF still exists before a receiver or
subscriber is installed; this task adds no buffering or receipt guarantee.
Tests cover both events, validation, mutation, subscription changes, close,
synchronous/asynchronous listener failures, and real-host request correlation.
Example event controls and OS observers are not added to this library task.
