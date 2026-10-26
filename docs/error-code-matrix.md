# SPEC §4.4 error-code verification matrix

Date: 2026-10-26
Status: T19 complete — 14 receiver mappings covered; specified current producers covered.
Normative source: SPEC §4.3–§4.7, §5, §6 and §9. No contract or runtime change.

## What the matrix proves

Receiving an error and producing that error are separate responsibilities.
The [client matrix](../packages/client/test/error-code-matrix.test.ts) supplies
controlled peer frames for all 14 codes and verifies the actual MoonpoolError,
exact code/message/data, timer cleanup, single settlement and unrelated-request
isolation. Each code is tested with nested public JSON data and with data omitted.
The literal table is copied from SPEC, and an assertion detects missing, extra
or renumbered SDK constants. It is a test inventory, not a new runtime whitelist;
unknown integer error codes remain supported by the existing response validator.
An omitted wire data member becomes undefined on the local error object; an
explicit wire data:undefined remains invalid JSON under the existing validation.

Every row also receives an id:null error while a call is pending. The call and
its original deadline remain intact; it expires with local -32003 at 1000 ms,
even though the uncorrelated frame arrived at 600 ms. Uncorrelated errors cannot
identify a request. In particular, a parse-error frame does not itself let the
client guess which call failed.

## All 14 codes

All rows have both correlated and uncorrelated client coverage in the common
matrix above. Producer references below distinguish real current behavior from
defined codes whose emitting feature is not implemented.

| Code | Constant / meaning | Current producer | Producer evidence |
| --- | --- | --- | --- |
| -32700 | PARSE_ERROR | No decoder in the current object-valued Transport. Receiver tests use controlled frames. | SPEC §3.1; common matrix only; no string transport added. |
| -32600 | INVALID_REQUEST | Host envelope/method/sequence/batch validation. | New real-host matrix; [invalid requests](../packages/host/test/invalid-request.test.ts), [batches](../packages/host/test/batch.test.ts), [request ids](../packages/host/test/request-id.test.ts). |
| -32601 | METHOD_NOT_FOUND | Host lookup after initialization/scope/input gates. | New real-host matrix; [handshake/unknown method](../packages/host/test/handshake.test.ts), [scope ordering](../packages/host/test/permission-gate.test.ts). |
| -32602 | INVALID_PARAMS | Host parameter container/data/schema checks. | New real-host matrix; [params](../packages/host/test/invalid-params.test.ts), [JSON stages](../packages/host/test/inbound-json.test.ts), [unknown fields](../packages/host/test/unknown-params.test.ts). |
| -32603 | INTERNAL_ERROR | Sanitized host provider failure; local client send failure. | New real-host matrix; [provider errors](../packages/host/test/permission-gate.test.ts), [storage providers](../packages/host/test/storage.test.ts), [local send failures](../packages/client/test/local-failures.test.ts). |
| -32000 | PERMISSION_DENIED | Host scope gate. | New real-host matrix; [permission gate](../packages/host/test/permission-gate.test.ts). |
| -32001 | CAPABILITY_UNAVAILABLE | Host has no implementation/close handler for a known method. | New real-host matrix; [permission gate](../packages/host/test/permission-gate.test.ts), [portal.close](../packages/host/test/portal-close.test.ts). |
| -32002 | USER_CANCELLED | No consent/picker cancellation producer is defined. | Controlled receiver coverage; new provider-throw sanitization test. portal.close returns acceptance, not cancellation. |
| -32003 | TIMEOUT | Client request deadline. | New uncorrelated matrix; [timeout/default/late response](../packages/client/test/timeout.test.ts). |
| -32004 | PROTOCOL_VERSION_UNSUPPORTED | Host exact-match handshake refusal. | New actual host/client refusal and corrected retry; [host handshake](../packages/host/test/handshake.test.ts), [client handshake](../packages/client/test/handshake.test.ts). |
| -32005 | NOT_INITIALIZED | Host gates calls before successful initialization. | New actual host/client gate and recovery; [host handshake](../packages/host/test/handshake.test.ts). |
| -32006 | RATE_LIMITED | Reserved; §11 defines no rate-limit policy. | Controlled receiver coverage; new provider-throw sanitization test. No limiter/backoff added. |
| -32007 | HOST_UNAVAILABLE | No generic host-state/availability policy is implemented. | Controlled receiver coverage; new provider-throw sanitization test. |
| -32008 | CONNECTION_CLOSED | Local client close drains calls and rejects later calls. Peer disconnect remains §11. | [Close](../packages/client/test/close.test.ts), [terminal local failures](../packages/client/test/local-failures.test.ts); controlled receiver coverage adds no disconnect policy. |

Eight unique codes have actual host producers. The client locally produces
-32603, -32003 and -32008; because -32603 overlaps, ten unique codes have current
producers. The remaining four have receiver coverage without invented producers.
Manifest JSON failures are local ManifestError values, not a bridge -32700 decoder.

## Real producer and privacy checks

Six parameterized cases run the actual host and client together for malformed
method, unknown granted method, invalid params, failing provider, denied scope,
and unavailable capability. Tests verify that gates do not invoke the provider,
except the deliberately failing provider. Two more cases verify -32004 with a
valid explicit retry and -32005 followed by successful initialization.

Three cases make a provider throw MoonpoolError carrying -32002, -32006 or
-32007 plus private diagnostic data. The actual host still produces sanitized
-32603, without exposing the original message/data on the wire; the original
exception remains observable through the host's queued diagnostic. An exception
containing a code does not implement a cancellation, throttling or availability
policy. These tests cover existing SPEC §4.4 / §9.4 protections, not a new policy.

The existing local-failure tests independently exercise actual send exceptions,
draining multiple calls/timers on close, post-close rejection, reentrancy,
cleanup exceptions and no automatic retransmission. New generic wire mapping
tests deliberately make no second call for a synthetic -32008 response and do
not define how peer-initiated disconnect should affect connection state.

## Verification and limits

Added 54 tests: 1 complete-constant-table check, 28 correlated error mappings,
14 null-id/deadline cases, 6 real host error producers, 2 handshake/gate recovery
cases and 3 provider-exception sanitization cases. They pass against the existing
implementation, so no production implementation or SPEC edit was needed.

Total: 1131 tests across 39 files pass (1077 + 54). Root typecheck and Biome
checks pass. No dependencies, browser behavior, public APIs, or reserved producer
policies changed. The latest relevant build/browser baseline is T18; T20 will
perform final browser/security verification. T21 conformance reconciliation remains.

This is error-contract coverage, not a code-coverage percentage or a claim that
every code has a production emitter. Rate limiting, consent UI, host availability,
string decoding and peer disconnect retain their existing scope/status.
