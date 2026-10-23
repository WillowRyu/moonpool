# 15. Enforce request-id order within each document

Date: 2026-10-23
Status: Accepted

## Context

SPEC §4.1 required unique increasing positive integer ids, while §5.1 resets
request correlation at repeat initialization. The receiver's rejection code,
correlation, consumption point, and precedence were not specified. Echoing
a reused id can reject an earlier call whose provider is still running.
T10 needed this contract approved before implementation.

## Decision

The maintainer approved option 1 on 2026-10-23. Record SPEC §4.1 / §4.2 / §5.1
before implementation.

Keep the largest consumed positive integer id in each host connection's
current document, initially zero. Gaps are allowed. After top-level batch
rejection and numeric-id detection, classify a document boundary: an exact
portal.initialize with a valid general request envelope and object-or-omitted
params. Such an initialization resets the id floor before consuming its own
id, regardless of subsequent field/version validation. Its id need not be 1;
the existing retry with a continuing client sequence remains valid.

For other numeric-id frames, check positive integer sequence order before
envelope/method-name and params validation. An id less than or equal to the
floor receives one -32600 error with id null and a fixed message, never the
reused number. The frame is not dispatched and the floor/state do not change.
Null marks an id that cannot be uniquely correlated under Moonpool's profile;
the existing client ignores it, preserving any original pending call/timer.
This response rule is an explicit Moonpool contract, not a claim that base
JSON-RPC prescribes this particular duplicate-id policy.

Consume a new positive integer id immediately, even if later validation,
initialization, permission, lookup, params, or provider processing rejects
the frame. Thus a malformed request cannot claim the same id again. Other
validation codes retain their precedence once the sequence gate passes.
SPEC §4.2's numeric-id echo rule gets an explicit sequence-rejection exception.

Malformed initialization envelopes/params containers do not establish a new
document boundary. If they carry a new positive integer id, consume it and
apply the existing -32600/-32602 validation. If reused/backward, reject with
the sequence error without resetting initialization. Valid general initialize
requests still reset initialization before method-specific validation, as today.

Keep existing handling for nonpositive/noninteger/nonnumeric ids, batches,
and no-id notifications; they do not consume the positive-integer floor.
Do not add a numeric maximum or require consecutive ids. Do not reset grants,
storage, consent, or rate-limit state. Rejection does not close the connection.

| Sequence in one connection | Result |
| --- | --- |
| initialize 1, ping 3, ping 5 | All accepted |
| initialize 1, write 2, write 2 | Second write not executed; -32600/id:null |
| initialize 1, ping 5, ping 3, ping 6 | 3 rejected; 6 still accepted |
| malformed name 5, corrected request 5 | First gets -32600/id:5; second -32600/id:null |
| initialize 1, ping 9, initialize 1, ping 2 | New document accepts 1 then 2 |
| initialize 1, initialize 1 with unsupported version | New document uninitialized; version error |

## Consequences

- SPEC §4.1, §4.2, and §5.1 were amended before implementation. Tests cover
  in-flight duplicates, ordering, failed requests, boundary/retry behavior,
  connection independence, and preserved storage/grants.
- The sender's normal increasing counter already works. No client id reset,
  new wire field, transport API, platform dependency, or capability is needed.
- This is document-scoped ordering, not durable replay protection. Re-handshake
  intentionally begins a new sequence; it must not erase origin-scoped state.
- The existing §11 response-epoch race across document replacement remains
  open. Do not claim that resetting this floor cancels old provider work or
  prevents old-document replies from matching new-document calls.
