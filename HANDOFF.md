# Session handoff

> Read this at the start of a session; update it whenever a step completes.
> Last updated: 2026-10-23. The maintainer switched to agent-led implementation
> and requested small tasks with an easy Korean explanation after each task.
> The agent now writes tests and implementation; manual typing and learning
> review are no longer prerequisites. Local study mode is off.
> T14 verified: 895 passed; typecheck, lint, and both example builds pass.
> portal.close submits acceptance before invoking a per-connect async UI hook.
> Read docs/implementation-plan.md for T01–T21, dependencies, and spec decisions.
> Next: T15, typed host notification sending. Milestone C is complete.
> T13 published as a7179db / cae510b; T14 is complete locally, not committed.
> T14 acceptance-before-dismissal policy is approved in SPEC §6.2 / ADR 0019.
> Do not ask again; implement the per-connect async onCloseRequested hook.
> T12 published as 1465d03 / f271a2f; remote confirmed in sync before T13.
> T13 local-error policy is approved in SPEC §4.6 / §4.7 and ADR 0018.
> Implement the approved fixed -32603 / {phase:"send"} mapping; do not ask again.
> T11 staged JSON validation is approved in SPEC / ADR 0016. Do not ask again.
> Policy questions: explain previous behavior → current problem → each option's consequences.
> The request-id policy is approved in SPEC / ADR 0015. Do not ask again.
> The method grammar and -32600 precedence are approved in SPEC / ADR 0014.
> The unencoded relative entry-path policy is approved in SPEC §7 / ADR 0011.
> Name length is approved: 1–40 Unicode code points. Do not ask again.
> The browser mini app now displays Moonpool Explorer after profile.get.
> Preserve prior lessons and explain each task in simple Korean with code.

## 2026-10-23 checkpoint — T14 commit and push

The maintainer requested committing and pushing T14, then T15 with an easy
code explanation. Publish the approved dismissal contract/kernel/tests,
browser example wiring/tests, and progress/learning materials as three small
commits. Verification remains 895 tests, typecheck, lint, and both example
builds passing. T15 covers typed host notification sending; client subscribers
remain T16. Preserve the existing transport and pending-request contracts.

## 2026-10-23 checkpoint — T14 complete

Published T13 as a7179db (terminal client lifecycle) and cae510b (progress/study)
to origin/master, confirming a clean tree and HEAD...origin/master 0/0 before
T14. The maintainer requested T14 with an easy code explanation. T14 remains
local; no T14 commit or push has been requested or performed.

Prepared ADR 0019 and explained previous behavior (-32601), the UI teardown
ordering problem, acceptance-first versus two-stage preparation, and the lack
of delivery acknowledgement. The maintainer explicitly approved the simpler
acceptance-first contract. Updated SPEC §6.2 and accepted ADR 0019 before
dependent tests/implementation. Eight existing request-gate regressions were
written and passed while awaiting approval. Do not ask for approval again.

Host.connect now accepts optional HostConnectionOptions, with per-connection
onCloseRequested(reason?: string): Promise<void>. After existing envelope/id/
initialization/JSON gates, portal.close rejects unknown fields and non-string
reason with -32602, preserving omission/empty/string contents. The portal
namespace needs no scope. Missing handler returns -32001. Submit result:{}
before invoking an async helper that awaits the handler. A submission throw
prevents invocation and propagates through the existing receive error path;
there is no second reply. A hook throw/rejection after acceptance is queued
for host-only rethrow, with no exception data or second response on the wire.
The kernel adds no automatic transport closure, new connection state, platform
API, dependency, or assertion. Success means acceptance, not receipt or
completed dismissal. Existing §11 peer-disconnect/document-epoch questions stay.
This task explicitly touches SPEC §9.4 / §9.5 / §9.6.

The mock host binds the hook to the captured transport and iframe. Check both
against current ownership, clear activeTransport, close that transport, remove
only that iframe, clear configuration button pressed states, and show reason
as textContent. Repeated/stale callbacks cannot dismiss a replacement frame.
The memory storage provider remains on the host page across Portal reopening.
The mini app's new close-demo.ts sends portal.close with reason "finished".
The button is disabled before handshake, while pending, and after acceptance;
errors display their code and allow deliberate retry. No automatic retries.
main.ts wires ready/unavailable alongside the existing storage UI.

Added 47 tests: 34 host, seven close-button, five mock-host, and one mini-app
entry wiring test; strengthened two existing handshake UI tests. Host RED:
20 failures/14 passes. UI RED: the close-demo module was absent and seven
behavior assertions failed, with 16 existing regressions passing. Corrected
TypeScript closure narrowing by using an arrow callback after DOM checks, and
used runtime validation of the happy-dom setting rather than a window type
assertion. All final checks pass; no existing test expectation was weakened.

Verified 895 tests across 32 files, typecheck, lint (87 files), both example
builds, and diff checks. Actual browser flow: initialize/profile in profile-only
mode, dismiss, open storage mode, store "dark", dismiss, reopen, read retained
"dark", dismiss. Captured /tmp/moonpool-t14-dismissed.png (not a repository
artifact). The browser verifies UI teardown/reopening; it does not establish
response receipt before document destruction. Temporary servers/tabs cleaned up.

Added study/18-portal-close.html, preserved T13 at #t13, updated the prior
lesson's wrap-up, and marked T14 complete / T15 next in the guide and roadmap.
All 282 local references across 19 study pages are valid, with no duplicate ids
and unchanged earlier interactive scripts. Browser QA confirmed lesson layout
and the updated current-task guide. Milestone C (T08–T14) is complete; v0.1 as
a whole is not yet complete. Next is T15 only, host notification sending;
T16 receives notifications, and T17–T18 still have the navigation decision gate.

## 2026-10-23 checkpoint — T14 policy approved

Published T13 as a7179db / cae510b to origin/master and confirmed a clean tree
and HEAD...origin/master 0/0. The maintainer approved ADR 0019's recommended
acceptance response before dismissal, including the receipt limitation and
host-only reporting after acceptance. Updated SPEC §6.2 before dependent work.
Eight existing request-gate regressions were written and passed while waiting.
Next: expand failing tests, add the bound async hook and example UI, verify,
and explain with code. This task touches SPEC §9.4 / §9.5 / §9.6.

## 2026-10-23 checkpoint — T13 commit and push

The maintainer requested committing and pushing T13, then T14 with an easy
code explanation. Publish the approved local failure policy, implementation,
tests, and ADR as one fix commit, then progress and learning materials as a
documentation commit. Verification remains 848 tests, typecheck, lint, and
both example builds passing. T14's dismissal contract requires a concrete
proposal and approval before dependent tests/implementation.

## 2026-10-23 checkpoint — T13 complete

The maintainer requested publishing T12 and implementing T13 with a simple
code explanation. T12 was pushed as 1465d03 / f271a2f to origin/master; the
clean tree and 0/0 remote comparison were confirmed before T13. T13 remains
local; no T13 commit or push has been requested or performed.

Prepared ADR 0018 with previous behavior, current problems, and the recommended
fixed-error mapping versus original thrown values. The maintainer explicitly
approved the recommendation. Updated SPEC §4.6 / §4.7 and accepted ADR 0018
before dependent tests and implementation. Do not ask for this approval again.

The client tracks closed per instance. request returns a rejected -32008
Promise before id allocation/timer creation/send when closed; initialize uses
the same path. Receive callbacks return before inspection after close. close
marks closed, snapshots/clears pending entries, clears timers and rejects all
calls before external cleanup. Repeated/reentrant close is a no-op. Attempt
unsubscribe and transport.close once each; after both attempts, rethrow the
first thrown cleanup value. A boolean records failure separately so undefined
is still a thrown value. Closure remains terminal after cleanup failures.

Wrap transport.send in try/catch. When the current id is still pending, delete
only that entry, clear its timer, and reject with MoonpoolError(-32603,
"failed to send the bridge request", {phase:"send"}). Do not inspect/coerce or
expose the original throw. Other calls keep their deadlines, the connection
remains usable, and the attempted id is consumed. Do not retry automatically:
delivery may have happened before the throw. If a response or close already
settled the entry during send, preserve that first outcome. Pending registration
remains before send. No platform API, runtime dependency, transport extension,
new type assertion, remote-health claim, or peer-disconnect signal was added.

Wrote 28 tests before runtime changes. Initial RED had 24 failures and four
passes. Corrected test-only typing (cleanup registry inference and mock-key
selection), and used a plain send function for the thrown Proxy case because
the test spy itself inspected its thrown value. Reran the corrected suite
against the committed T12 client, restoring the implementation in finally:
24 failures/four passes again. T13 passes all 28. No prior tests were weakened.
Tests cover post-close call/initialize, repeated/reentrant cleanup, adapter
exceptions including undefined, retained callbacks, multi-client isolation,
per-request send cleanup, raw throw noninspection, retained deadlines, no
retries/id reuse, late responses, recovery, and first-settlement ordering.

Verified 848 tests across 29 files, typecheck, lint (82 files), both example
builds, and diff checks. Actual browser localhost:5173 → localhost:5174/index.html
initialization/profile/storage set/get passed; the last get returned "dark".
The browser proof image is /tmp/moonpool-t13-browser.png, not a repository
artifact. Temporary dev/static servers and verification tabs were cleaned up.

Added study/17-client-local-failures.html, preserved T12 at #t12, updated its
wrap-up, and marked T13 complete / T14 next in the guide and implementation
plan. All 265 local references across 18 study pages are valid, no duplicate
ids were found, and prior interactive scripts remain unchanged. Browser QA
confirmed the new lesson layout and the current-task guide.

Next is T14 only. Its reason input, missing embedder-hook behavior, and
response/teardown order still require a concrete policy proposal. Explain
previous behavior → current problem → each option's consequences before
asking. T13's local client.close is distinct from portal.close's remote UI
dismissal request. Existing §11 peer-disconnect/document-epoch questions and
capability-specific response schemas remain separate.

## 2026-10-23 checkpoint — T13 policy approved

Published T12 as 1465d03 / f271a2f to origin/master and confirmed a clean tree
and HEAD...origin/master 0/0. Prepared ADR 0018 before asking the maintainer,
including previous behavior, the current problem, and both options' effects.
The maintainer explicitly approved the recommended fixed MoonpoolError mapping.
Updated SPEC §4.6 / §4.7 and accepted ADR 0018 before dependent tests/code.
Next: write failing tests, implement terminal local closure and per-request
send-failure cleanup, verify, and explain in Korean with code. T13 is local.

## 2026-10-23 checkpoint — T12 commit and push

The maintainer requested committing and pushing T12, then implementing T13
with an easy code explanation. Publish response validation and its tests/ADR
as one fix commit, then progress and learning materials as a documentation
commit. Verification remains 820 tests, typecheck, lint, and both example
builds passing. Prepare T13's local-failure proposal before dependent changes.

## 2026-10-23 checkpoint — T12 complete

Published T11 as 1695e9a (staged JSON validation) and 0585deb (progress/study)
to origin/master, then verified a clean tree and HEAD...origin/master 0/0.
The maintainer requested T12 implementation and an easy explanation with code.
T12 remains local; no T12 commit or push has been requested or performed.

Read SPEC and the existing JSON-RPC 2.0 §5 response/error contract. ADR 0017
records applying those requirements; no new policy or SPEC amendment was needed.
isJsonRpcResponse now accepts unknown and reuses isJsonValue on the entire
frame before field access. It requires own version/id/outcome/error members,
exactly one result/error, and an integer code with a string message. Nested
results, error data, and extra fields must be JSON. Valid extras, null-prototype
records, falsy values, shared acyclic data, and deep JSON remain usable. No
getter/toJSON evaluation, serialization, input mutation, new assertions,
platform APIs, dependencies, numeric bounds, or code whitelist were added.

Retain finite numeric diagnostic response ids because the host can echo an
invalid finite request id; actual pending Map membership decides correlation.
Null ids remain error-only. The client callback marks input unknown and uses
the strengthened guard before lookup, deletion, timer cleanup, or settlement.
Malformed replies receive no reply and cannot restart deadlines. Null/unknown/
expired/duplicate ids remain ignored. Valid errors preserve code/message/data
in MoonpoolError; host sanitization remains the credential boundary.

Added 116 tests across protocol and client. Corrected the test-only host import
and the existing host error-message expectation before the meaningful RED run:
39 failed and 77 existing-behavior regressions passed. All pass after the guard
change. Tests cover non-JSON values, both/neither outcomes, descriptors and
reflection errors, integer error codes, falsy results/data, out-of-order
completion, multiple pending calls, original deadlines, late/unknown/null ids,
and a real host/client provider failure with its sanitized wire error and
host-side rethrow. No existing test was weakened.

Verified 820 tests across 28 files, typecheck, lint (80 files), both example
builds, and diff checks. Actual browser localhost:5173 → localhost:5174/index.html
handshake, Moonpool Explorer, storage-enabled set, and get returning "dark" pass.
Browser proof image is /tmp/moonpool-t12-browser.png (not a repository artifact).
Temporary dev/static servers and verification tabs were cleaned up.

Added study/16-response-validation.html, preserved T11 at #t11 in the guide,
updated T11's wrap-up, and marked T12 complete / T13 next throughout progress
materials. All 248 local references across 17 study pages are valid, there are
no duplicate ids, and prior interactive scripts are unchanged. Browser checks
confirm the new lesson and updated current-task guide render correctly.

Next is T13 only; start with its existing local-failure decision gate. Explain
previous behavior, the current problem, and consequences of each option before
asking. Capability-specific result schemas (including initialize's existing
assertion), arbitrary Proxy effects/resource limits, and §11's document-epoch
race remain separate from this completed generic response task.

## 2026-10-23 checkpoint — T11 commit and push

The maintainer requested committing and pushing T11, then T12 with an easy
code explanation. Publish the approved staged JSON policy, implementation,
tests, and ADR as one feature commit, then progress and learning materials
as a documentation commit. Verification remains 704 tests, typecheck, lint,
and both example builds passing. T12 covers generic response validation and
promise correlation; method-specific result schemas remain outside this task.

## 2026-10-23 checkpoint — T11 complete

T10 was published as e4f7f89 (id ordering) and 45af7d1 (progress/study) to
origin/master before T11. The maintainer approved the ADR 0016 staged JSON
proposal after the previous-behavior/problem/consequences explanation. Updated
SPEC §4.1 / §4.2 / §5.1 and accepted ADR 0016 before dependent implementation.
Do not ask for that approval again. T11 remains local; no commit/push yet.

Added the private packages/host/src/incoming-request.ts inspector. It accepts
unknown, classifies arrays/unaddressable values, and recovers only own stored
numeric ids through property descriptors. It never evaluates routing getters.
Inspect all original descriptors, separating params only in an inspection view;
validate the envelope's original prototype/descriptors and extra data through
isJsonValue. Invalid params descriptors also invalidate the envelope. Keep
params unknown until deep validation at the approved stage, preserving original
references and data. No serialization, input mutation, coercion, public API,
Transport change, platform API, runtime dependency, or resource limit was added.

The host applies T10 sequence rules before ordinary errors. JSON-valid envelope
and object-or-omitted params shape establish initialize boundaries; malformed
envelope data cannot reset state. Deeply invalid initialize params do establish
the boundary, then initialization resets false before -32602. Own params with
undefined are present and fail the container gate. Ordinary calls retain the
initialization/scope gates before deep params validation, which now precedes
lookup even for unknown methods. All provider inputs pass this validation and
the existing method-specific checks. Ping moved below the shared scope/params
stage; the exact portal namespace remains exempt from grants.

Invalid envelope data gets -32600 with a fixed message. Echo finite numeric ids
and use null for NaN/infinities; update the old NaN test accordingly, as approved.
Batches and no safely recoverable own numeric id retain their response rules.
Reflection failures produce an invalid request when an id was recovered and
otherwise remain silent. Callable roots with stored numeric ids are rejected
without invoking them. Proxy trap side effects/concurrent mutation limitations
remain ADR 0008's known boundary, not a new security guarantee.

Initial preparation had four valid-input regressions. The first expanded run
had 58 tests, with 49 failures and nine passes. Added one callable-root case
when reviewing safe id recovery, observed its failure, and fixed it before
final verification. All 59 new tests pass, including getters/toJSON, non-JSON
leaves/objects/cycles, hidden/symbol/inherited members, frozen inputs, deep/shared
graphs, original value identity, error precedence, id consumption, and initialize
boundaries. Only the approved NaN expectation changed in existing runtime tests.
Verified 704 tests across 26 files, typecheck, lint (77 files), both example
builds, and diff checks. Actual browser localhost:5173 → localhost:5174/index.html
handshake, profile display, and storage-enabled set/get succeeded.

study/15-inbound-json.html explains descriptors, inspection views, original
params preservation, the two JSON gates, error/initialization ordering, and
verification using the requested previous/current/result structure. The guide
shows T11 complete and T12 next, preserves T10 at #t10 and all previous lessons,
and updates T10's wrap-up. All 232 local references across 16 study pages are
valid, with no duplicate ids and unchanged prior interactive scripts. Browser
checks confirm both the new lesson and updated current-task guide render.

Next is T12 only. Outbound response validation/correlation is separate from
this host request boundary. Existing §11 epoch, peer-close, and resource-policy
questions remain open. Keep policy questions in the maintainer's requested
previous-behavior → current-problem → each-choice-consequences format.

## 2026-10-23 checkpoint — T10 commit and push

The maintainer requested committing and pushing T10, then T11 with an easy
code explanation. Publish the approved id-order policy, implementation,
tests, and ADR as one feature commit, then progress and learning materials
as a documentation commit. Verification remains 645 tests, typecheck, lint,
and both example builds passing. Explain T11's policy proposal using previous
behavior, the current problem, and the consequences before asking approval.

## 2026-10-23 checkpoint — T10 complete

The maintainer requested committing/pushing T09, then T10 with an easy code
explanation. Published 1ebd7e4 (method syntax) and 41a2f47 (progress/study) to
origin/master and confirmed HEAD...origin/master 0/0. T10 remains local.

Prepared ADR 0015 as a proposal covering duplicate/backward-id correlation,
early consumption, and repeat initialization. The maintainer approved option 1.
They also requested a persistent communication change: every future policy
question must explain previous behavior, the current problem, and consequences
of the proposed options, so the decision is easy to understand. This is also
recorded in docs/implementation-plan.md. Do not merely present error codes or
a recommendation without that context.

Updated SPEC §4.1 / §4.2 / §5.1 and accepted ADR 0015 before implementation.
Each host connect closure now keeps lastRequestId, initially zero. After array
rejection and numeric-id detection, an exact general-request-shaped initialize
resets the floor before consuming its own id. Version/field failures still
establish that boundary; malformed envelopes, names, and params containers
cannot reset it. Positive integer ids must exceed the current floor, with
gaps allowed. Duplicate/backward ids receive one -32600/id:null response and
do not execute, lower the floor, change session state, or close the connection.

Consume a new positive integer id before later validation, state, scope, lookup,
params, or provider processing, even if these fail. This prevents malformed
duplicates from echoing a pending call's number through another error path.
Nonpositive/noninteger ids retain their existing behavior and do not consume
the floor; batches and notifications do not either. No numeric maximum, client
counter reset, wire field, platform API, or runtime dependency was introduced.
The existing null-error client handling preserves the original pending call
and timeout. Existing grants/storage and SPEC §9 checks remain in force.

Wrote 25 tests before implementation: 17 failed and eight passed. All now pass.
They cover increasing/gapped ids, completed and in-flight duplicates, backward
unused ids, consumption after rejection, invalid ids, malformed initialize
shapes, failed version/field negotiation and retries, separate connections on
one host, and storage/grant preservation. The real client/host in-flight test
also sends a malformed duplicate and checks one provider call, unchanged timer,
and eventual successful completion of the original call. Fixed only test typing
and formatting after the full run; no existing runtime tests needed weakening.

Verified 645 tests across 25 files, typecheck, lint (74 files), both example
builds, and diff checks. study/14-request-id-order.html starts with the requested
previous-behavior/problem/result explanation, then walks through the counter,
null errors, consumption, initialization boundaries, and the §11 epoch limit.
The guide shows T10 complete and T11 next, preserves T09 at #t09 and all earlier
lessons, and links T09's wrap-up to T10. All 215 local references across 15 study
pages are valid, with no duplicate ids and unchanged earlier interactive scripts.
Browser checks confirm the new lesson and updated task guide render correctly.

Next is T11 only. Its whole-JSON error and ordering decision remains open and
must account for the approved id-sequence/method-name gates. The §11 late
old-document response race remains open: resetting the id floor does not cancel
old providers or provide durable replay protection. No T10 commit or push yet.

## 2026-10-23 checkpoint — T09 commit and push

The maintainer requested committing and pushing T09, then starting T10 with
an easy code explanation. Publish the approved method grammar, validation,
tests, and ADR as one feature commit, then progress and learning materials
as a documentation commit. Verification remains 620 tests, typecheck, lint,
and both example builds passing. Resolve T10's request-id rejection and
correlation contract before implementing dependent behavior.

## 2026-10-23 checkpoint — T09 complete

The maintainer requested committing/pushing T08, then T09 with an easy code
explanation. Published 257fdd5 (batch/error-id handling) and 4f9dd4b (progress
and study notes) to origin/master. Confirmed HEAD...origin/master 0/0 before
T09 changes. T09 remains local; no T09 commit or push yet.

T09 had an explicit specification gate. Prepared ADR 0014 as a concrete
proposal and asked the maintainer to approve the grammar and error order.
While waiting, wrote 29 passing regressions for valid protocol names and
unknown-method permission behavior. The maintainer explicitly approved the
recommended rules: exactly one dot, two ASCII components starting lowercase
and continuing with letters/digits, and -32600 before params, initialization,
or permissions. Updated SPEC §4.2 / §6.1 and accepted ADR 0014 before writing
the dependent implementation. This decision is settled; do not ask again.

packages/protocol/src/index.ts now checks a private METHOD_NAME expression
inside isJsonRpcRequestEnvelope. Compare exec's full matched text with the
input to reject suffix line terminators despite JavaScript's $ behavior.
Keep the string check first, with no coercion, trimming, case conversion,
length limit, or registration lookup. isJsonRpcRequest reuses the same guard.
The host uses its existing envelope failure branch, with a fixed message
describing the expected version/id/name. It echoes the numeric id and does
not copy malformed method text into errors. No platform API or dependency
was added; all validation remains in the pure kernel.

Valid unknown names retain initialization, scope, and lookup behavior.
Syntax checking uses only public grammar, so early rejection does not reveal
whether an ungranted method exists. SPEC §9.3 / §9.6 ordering for ordinary
method params/providers is unchanged. Malformed initialize spellings do not
reset an active session, and valid handshakes remain usable afterward.
Standalone notifications remain silent, and T08 still rejects arrays as one
unit with id null. T10 id policy and T11 whole-JSON validation remain open.

The final T09 suite has 122 tests (58 protocol and 64 host). Before runtime
implementation, 83 failed and 39 passed. All now pass. Verified 620 tests
across 24 files, typecheck, lint (72 files), both example builds, and diff
checks. No browser application UI was added. The new behavior is checked
through shared guards and the real host over in-memory transports.

study/13-method-names.html explains the regex components, full-input check,
error precedence, grammar versus grants/method existence, and test evidence.
The guide shows T09 complete and T10 next, preserves T08 at #t08 with all
earlier lessons, and links T08's wrap-up to T09. All 198 local references
across 14 study pages are valid, with no duplicate ids and unchanged earlier
interactive scripts. Browser checks confirm the lesson and current-task
guide render correctly. Next is T10 only, starting with its existing
request-id rejection/correlation decision; do not infer approval from T09.

## 2026-10-23 checkpoint — T08 commit and push

The maintainer requested committing and pushing T08, then starting T09 with
an easy code explanation. Publish batch/error-id handling with its tests and
ADR as one feature commit, then its progress and learning materials as a
documentation commit. Verification remains 498 tests, typecheck, lint, and
both example builds passing. T09 still requires the documented method-format
error/ordering decision before tightening the normative request contract.

## 2026-10-23 checkpoint — T08 complete

The maintainer requested committing/pushing the completed work and then T08.
Published T06 as 1f93b47, T07 as 6346f8d, and their progress/study notes as
340e69a to origin/master. Confirmed a clean tree and HEAD...origin/master
0/0 before T08. The T08 changes remain local; no T08 commit or push yet.

The host now checks Array.isArray at receive entry, before numeric-id checks
and any session processing. Empty, nonempty, nested, malformed-member, and
notification-only arrays receive one object with id null and code -32600.
No member is inspected or dispatched, so provider calls and initialization
state are untouched. Standalone notifications and ordinary arrays inside
storage values retain their existing behavior. The fixed error message does
not echo array contents. SPEC §9.3 / §9.6 gates on ordinary requests remain.

JsonRpcResponse can represent a null id, and isJsonRpcResponse admits it only
for the existing error shape, never for success. Request guards still reject
null ids and require positive integers. The client ignores null ids before
pending lookup, preserving calls and their timers. It neither infers a batch
member's id nor sends an error reply. JSON-RPC 2.0 §5 already defines the
unknown-id error marker, so no spec amendment or approval gate was needed.
ADR 0013 records the decision and cites the official specification checked
during implementation. General response validation remains T12, and request
id reuse/backward-id behavior remains T10. No platform API, runtime dependency,
transport extension, resource limit, or batch execution feature was added.

Wrote 34 tests before implementation. The meaningful RED run had 20 assertion
failures and 14 passing regressions. Typecheck also first rejected null in
the existing response type. All new tests now pass: 20 host cases, ten shared
response/request-id cases, and four client cases. They verify initialization
before/after arrays, one reply, provider non-invocation, session preservation,
nullable-error guards, timer counts, timeout, subsequent calls, and a real
host/client connection with a pending provider response and a separate batch.

Verified 498 tests across 22 files, typecheck, lint (69 files), both example
builds, and git diff --check. Runtime batch behavior is exercised by controlled
transports and real in-memory host/client integration; no new browser UI was
added. study/12-batch-rejection.html explains the early return, null response
id, pending Map, timer preservation, and top-level versus nested arrays.
The guide shows T08 complete and T09 next, preserves T07 at #t07 and all earlier
lessons, and links T07's wrap-up to T08. All 180 local references across 13
study pages are valid, with no duplicate ids and unchanged earlier interactive
scripts. Browser checks confirm the new lesson and current-task guide render.

Next is T09 only. The method-format error code and rejection order are still
the existing spec decision gate in docs/implementation-plan.md. Do not treat
T08 as resolving that gate or the later request-id and JSON-boundary decisions.

## 2026-10-23 checkpoint — T06 and T07 commit and push

The maintainer requested committing and pushing the completed T06/T07 work,
then continuing with T08. Publish entry/scope admission and actual manifest
example integration as separate feature commits, followed by their progress
and learning materials. Verification remains 464 tests, typecheck, lint,
and both example builds passing. Continue with T08 only after this checkpoint
has been pushed to origin/master.

## 2026-10-23 checkpoint — T07 complete

The maintainer requested T07. The T06 work was still uncommitted at the start;
preserve it alongside T07. No additional commit or push was requested.

examples/mock-host/src/main.ts now imports hello-miniapp/moonpool.json?raw as
host-owned text, calls the real parseManifest, selects a pinned origin from
a Map using the validated id, and resolves entry from that origin's root
with new URL. Removed the duplicated typed manifest literal. Invalid source
or an unmapped id throws before iframe creation. The default connection still
grants profile only, and the existing host buttons create fresh connections
with fixed grants. Iframe insertion and receiver attachment remain synchronous
in the same task, so the first handshake cannot precede listener setup.

Added examples/mock-host/src/vite-env.d.ts referencing vite/client so ?raw
imports have their existing Vite string type. The installed Vite raw loader
and its declaration were checked locally. ADR 0012 records the example's
file inclusion and URL resolution decisions; no spec amendment, runtime
dependency, or platform API in the pure kernel was introduced. SPEC §9.1's
pinned message origin and §9.3's dispatch-time scope enforcement remain in
place. URL resolution is not filesystem or redirect inspection; production
loader duties and T17–T18 navigation containment remain separate work.

Added 14 example tests. After fixing the test environment setup, the meaningful
RED run had 13 assertion failures and one passing receiver-ordering regression
case. All 14 now pass. Tests retain the real parser and dispatcher, varying
raw file text to verify version and manifest permissions in the handshake,
entry URL resolution (including ./, ../, Unicode, and spaces), invalid-source
startup rejection, and unknown-id rejection before Portal creation. The
ordering case checks receiver registration at the first microtask after
iframe insertion and then completes a real in-memory handshake.

Verified 464 tests across 19 files, typecheck, lint (65 files), and both example
builds. Actual browser checks at localhost:5173 show the Portal loading
localhost:5174/index.html, successful initialization, Moonpool Explorer, and
storage set/get in the host-selected storage configuration. Temporarily set
entry to ../index.html and reloaded: startup raised ManifestError and created
no Portal. Restored the original manifest byte-for-byte and confirmed normal
profile-only initialization again. There is no remaining manifest-file diff.

study/11-manifest-example.html explains raw text import, the origin Map,
URL resolution, validation/connection order, security boundaries, and actual
verification. The guide shows T07 complete and T08 next, preserves T06 at
#t06 and T05 at #t05 with all previous lessons, and updates T06's wrap-up.
All 163 local references across 12 study pages are valid, with no duplicate
ids and unchanged earlier interactive scripts. Browser checks confirm the
new lesson and updated current-task guide render correctly. Milestone B is
complete; full v0.1 conformance is still open. T06 and T07 remain local.

## 2026-10-23 checkpoint — T06 complete

T05 was committed and pushed to origin/master as fb834fb (approved name policy),
9206fc4 (parser and tests), and 6d870bc (progress and learning materials).
The maintainer then requested T06. No T06 commit or push was requested.

The initial T06 checkpoint paused only the underspecified entry syntax. After
the question was restated in plain Korean, the maintainer explicitly approved
the recommended rules. Updated SPEC §7 and ADR 0011 before implementing them.
This decision is settled; do not ask again. Entries are nonempty, unencoded
slash-separated relative file paths. Reject absolute paths, backslashes,
percent signs, colon/question/hash delimiters, Unicode controls, edge
whitespace, and directory targets. Allow literal Unicode, interior spaces,
./ and internal ../ that do not ascend above root. Reject a parent step at
depth zero immediately, even if later segments would descend again. Preserve
accepted entry text; do not trim, decode, or repair it.

packages/host/src/manifest.ts composes T05's internal field parser with this
lexical path check and scope recognition derived from PROFILE_METHODS and
STORAGE_METHODS, excluding the reserved portal namespace. Empty permissions
are allowed and original order/duplicates are preserved. The host package's
index now exports parseManifest and the local ManifestError. The partial
parseManifestFields remains internal, and its documentation points to the
full parser. No platform API or runtime dependency was added. The parser
performs no I/O and creates no bridge; file existence and actual containment,
including symlinks where applicable, remain the embedder loader's duty.

Before implementation, scope checks had 13 expected failures, direct
containment had four, and the approved additional entry rules had 40. All
107 T06 tests now pass, including composed field-regression cases and three
real client/host connections proving parsing neither grants permission nor
installs a provider. SPEC §9.3 and §9.7 boundaries remain enforced by the
existing dispatch gate. Protocol version negotiation remains in the handshake.

Verified 450 tests across 18 files, typecheck, lint (62 files), and both example
builds. Both example bundle hashes match T04/T05 after removing eager parser
module initialization. The example behavior and typed manifest literal are
unchanged; T07 will integrate the actual file and loader entry interpretation.

study/10-manifest-entry-scopes.html explains the approved syntax, path-depth
walk, namespace-derived Set, every, declared permissions versus grants and
providers, public API, local errors, and loader limits. The study entry point
shows T06 complete and T07 next, preserves T05 at #t05 and all earlier lessons,
and links the T05 wrap-up to T06. All 145 local references across 11 study
pages are valid, with no duplicate ids and unchanged earlier interactive
scripts. Browser checks confirm the new lesson's code/depth walkthrough and
the updated current-task guide render correctly. No T06 commit or push yet.

## 2026-10-23 checkpoint — T05 commit and push

The maintainer requested publishing T05, then continuing with T06. Split the
approved name-length specification and ADR, the internal parser and tests,
and the roadmap plus learning materials into separate logical commits.
Verification remains 343 tests, typecheck, lint, and both example builds
passing. T06 starts after this checkpoint has been pushed to origin/master.

## 2026-10-23 checkpoint — T05 complete

The maintainer requested the next task. SPEC §7's name length was genuinely
underspecified: they explicitly approved Unicode code points, counting a
supplementary-plane emoji as one. Updated SPEC first and recorded ADR 0010
before writing the length implementation. Combining marks and multi-code-point
emoji components count separately. This policy is settled; do not ask again.

Added packages/host/src/manifest-fields.ts as an internal first stage, with
ManifestFields and a local ManifestError carrying the failed field. It parses
actual text to unknown, requires a JSON object and own required members, then
checks manifestVersion 1, the exact SPEC id expression, 1–40 code-point names,
SemVer 2.0.0 syntax, string entry/protocolVersion, and arrays of scope strings.
It does not coerce, trim, deduplicate, or negotiate protocol versions. Errors
do not echo malformed source. Whole-string matching prevents the JavaScript
regex final-newline exception from admitting ids or versions with a suffix.

The SemVer expression comes from the official 2.0.0 specification. Numeric
components stay strings, avoiding JavaScript number precision restrictions.
Name counting uses the string iterator and stops after the 41st code point,
without allocating a character array for the whole input. Required members
cannot be supplied by Object.prototype. Implementation uses narrowing, with
no result type assertion or platform API.

This is intentionally not exported by packages/host/src/index.ts and is not
the full manifest parser. Entry containment and scope recognition are still
unchecked at this stage and must be completed in T06 before public admission;
T07 then replaces the demo's typed literal. No bridge is created by this
synchronous pure parsing helper; async capability contracts are unchanged.
No extra envelope-field policy or resource limit was introduced.

Wrote 89 failing tests before implementation; all now pass. Reverified the
full suite: 343 tests across 17 files, typecheck, lint, and both example builds.
The demo behavior is unchanged in this task. study/09-manifest-fields.html
explains parsing versus validation, required own members, name counting,
id/version formats, array members, errors, and staged admission. The guide
preserves earlier lessons and records T05 complete with T06 next.
All 126 local references across ten study pages are valid; earlier interactive
scripts are unchanged. Browser checks confirm the name-length walkthrough
and updated guide render correctly.

## 2026-10-23 checkpoint — T04 commit and push

The maintainer requested publishing the completed T04 work to origin/master.
Group the host configurations, mini-app controls, tests, and ADR 0009 as one
feature commit, with the task progress and learning materials in a separate
documentation commit. Verification remains 254 tests, typecheck, lint, and both
example builds passing, with actual browser CRUD and permission checks recorded
below. The versioned task list remains T01–T04 complete and T05 next.

## 2026-10-23 checkpoint — T04 complete

The maintainer reaffirmed TypeScript and requested T04 with an easy explanation
and source snippets. The host now offers two fixed configurations: profile-only
by default and profile plus storage. Each selection closes the old transport,
replaces the iframe, and attaches a fresh host connection in the same task as
frame creation. A single memory provider outside startPortal retains data.
ADR 0009 records the connection/document lifetime decision; no spec amendment,
runtime consent, transport extension, or dependency was introduced.

examples/hello-miniapp/src/storage-demo.ts owns text-value Set/Get/Delete
controls. main.ts enables it after initialization, independently of profile
success, and leaves it disabled on initialization failure. It sends denied
calls deliberately to demonstrate SPEC §9.3 host enforcement. Controls are
disabled while a request is pending and restored in finally. Read values are
checked with ordinary narrowing and isJsonValue before JSON text rendering;
there is no result type assertion. Empty keys and strings remain valid.

Added 17 tests and strengthened four existing initialization/profile cases.
Before implementation, the targeted suite had 21 failures and 15 passes; after
implementation all 36 pass. Full verification: 254 tests across 16 files,
typecheck, lint, and both example builds pass. Security checks (§9.3 / §9.6)
remain in the pure host; provider calls remain async (§9.5), and all returned
strings/error details are rendered as text. Pinned origins are unchanged.

Actual browser checks confirm allowed set/get, profile-only -32000 denial,
retained data after switching back to storage, successful delete, and null
after deletion. Iframe locator clicks were unavailable in computer use;
approved browser Tab/Enter actions completed the same controls successfully.
Screenshots are study/t04-storage-allowed.png and study/t04-storage-denied.png.
study/08-storage-demo.html explains host selection, fresh connections, UI
request ordering, finally, response guards, and the verification evidence.
The study entry point shows T04 and preserves T03/T02/T01 at stable anchors.
All 108 local references across nine study pages are valid; earlier interactive
scripts are unchanged. Browser checks confirm the new lesson and current guide.

Next is T05 only. General navigation containment and the same-iframe response
epoch issue remain separate T17–T18 / SPEC §11 work; do not treat this demo's
explicit frame replacement as solving either. The v0.1 roadmap is still open.

## 2026-10-22 checkpoint — T03 commit and push

The maintainer requested publishing T03 and asked whether the task list
persists. docs/implementation-plan.md is versioned with the repository and
retains T01–T21, completion criteria, dependencies, and decision gates.
Update its current status and progress after each verified task, alongside
this handoff and the study guide. Current progress is T01–T03 complete,
with T04 next. Publish T03 as a provider/test change and a separate roadmap
and learning-material update. Verification remains 237 tests, typecheck,
lint, and both example builds passing.

## 2026-10-22 checkpoint — T03 complete

Added examples/mock-host/src/memory-storage.ts and installed its provider in
the mock host. A nested Map partitions by the host-selected app id, then the
caller key. Async get/set/delete preserve false, zero, empty strings, and
nested null. Missing keys read as null; deleting a missing key is harmless.
The provider lives across handshakes but a fresh instance starts empty.
It is development-only memory storage, not persistence across host reloads.

Wrote 18 failing tests before implementation: 15 provider cases, two real
host/client integration cases using the memory transport, and one example
entry-point wiring/default-grant case. All now pass. Integration checks two
app identities using the same key, deletion isolation, repeated initialization,
and denied writes preserving existing data. The mock-host wiring test records
the real createHost config while still invoking the real kernel.

This implements ADR 0003; no new architecture decision or spec amendment is
needed. SPEC §9 is involved: the host still checks grants before provider
access (§9.3), all provider methods are async (§9.5), and the existing kernel
validates params (§9.6). Default grants remain ['profile'] even with storage
installed. No dependency, pure-kernel API, or browser origin changed.

Verified 237 tests across 15 files, typecheck, lint, and both example builds.
study/07-memory-storage.html explains Map nesting, factory/closure state,
get/set/delete, optional chaining, nullish fallback, lifetime, and the test
evidence with source snippets. The study entry point now shows T03, preserves
T02 under #t02 and T01 under #t01, and points to T04 next. All 89 local
references across eight study pages are valid; earlier interactive scripts
are unchanged. Browser checks confirm the new lesson and current-task guide.

Next is T04 only: show the default denial and a host-selected storage-enabled
configuration in the browser UI. Changing that configuration creates a fresh
connection; it is not runtime consent. Do not treat T03 tests as a claim that
the browser storage UI has already been exercised.

## 2026-10-22 checkpoint — commit and push

The maintainer requested committing and pushing the completed work to
origin/master. Group the checkpoint into aligned kernel comments, the browser
profile example with runtime displayName checks and tests, and the roadmap
plus Korean learning materials. This includes the screenshot and preserves
earlier lessons. Runtime verification remains 219 tests, typecheck, and both
example builds passing; lint and diff checks also pass. Next remains T03.

## 2026-10-22 checkpoint — T02 follow-up: inspect the displayed result

At the maintainer's request, replaced the profile result's `as ProfileGetResult`
with inline runtime checks and removed the unused type import. Before rendering,
the example requires a non-null, non-array object with a string displayName.
The checks narrow unknown without a type assertion. This validates the field
the view uses, not the complete optional profile schema or the generic client.

Added 11 tests first: ten malformed-result cases failed before implementation,
while the empty-string case already passed. All now pass. Malformed values
produce an ordinary local Error handled by the existing profile catch, keeping
the successful bridge status. No new wire error code, permission policy, or
kernel API was introduced. The host-side SPEC §9 checks remain unchanged.

Reverified 219 tests across 14 files, typecheck, lint, and both example builds.
All 72 local references across seven study pages are valid. Updated the T02
code walkthrough and study entry point with the actual checks, evaluation
order, type narrowing, and the distinction from the earlier assertion. The
initial T02 browser screenshot still illustrates the unchanged valid result.
Next remains T03; this follow-up does not complete the general response
validation work planned in T12.

## 2026-10-22 checkpoint — T02 complete

The maintainer requested T02 and asked for code alongside the easy explanation.
Added seven failing example tests before implementation. The initial meaningful
RED run had seven assertion failures: no profile provider was installed and
the mini app had no profile request or display. The same seven tests now pass.

The mock host supplies an async profile provider returning the fixed public
displayName Moonpool Explorer. The mini app waits for initialization, calls
profile.get, and renders the name with textContent. The handshake's returned
strings also use textContent. Profile failures preserve the successful bridge
status and display their error code; failed initialization sends no profile
request. At this initial checkpoint the generic client result was asserted as
ProfileGetResult; the subsequent runtime-check follow-up above replaces that
assertion in the example.

The change touches the existing SPEC §9 boundaries: dispatch-time scope checks
remain in the host (§9.3), the fixture contains no host credentials (§9.4),
and the provider remains asynchronous (§9.5). Grants still contain only profile.
No kernel API, protocol rule, or runtime dependency changed; no new ADR is needed.

Example tests live under examples/*/test and are included by Vitest and the
browser TypeScript project. The host-entry-point test uses the actual host
kernel and an in-memory transport; UI tests control the client to verify
ordering, text rendering, profile error codes -32000/-32001, and handshake
failure. Browser validation separately confirms the actual cross-origin
bridge from localhost:5173 to localhost:5174 displays Moonpool Explorer.

Verified: 208 tests across 14 files, typecheck, lint, and both example builds
pass. study/06-profile-demo.html explains the implementation with source
snippets, a glossary, request flow, errors, and test evidence. Its screenshot
is study/t02-profile.png. The entry point now shows T02 and T03; T01's preserved
explanation has the stable anchor study/index.html#t01. Lesson 05 links follow
that anchor. All 72 local references across seven study pages are valid, with
earlier interactive scripts unchanged. Browser checks confirm the new lesson
and current-task guide render correctly. Next: T03 only; storage UI
success/denial modes remain T04.

## 2026-10-22 checkpoint — T01 complete

The maintainer authorized starting the task plan and reiterated the request
for an easy explanation after each task. Completed T01:

- The client header now describes request correlation, timeouts, and draining
  in-flight requests on local close instead of calling it a skeleton.
- isStorageSetParams documentation now describes recursive JSON validation,
  top-level null rejection, valid falsy values, and the separate whole-frame
  validation boundary. This documents SPEC §6.3 / §9.6 and ADRs 0004/0008;
  no validation logic or security policy changed.
- study/index.html records the current implementation workflow, T01's easy
  explanation, the T01–T21 roadmap, and T02 as next. The earlier architecture
  and JSON-validation material remain available.
- The lesson 05 wrap-up marks the stale comments as resolved, preserves its
  dated source snapshots and exercises, and links to the current task guide.

Verified after edits: 201 tests across 12 files, typecheck, lint (47 files),
and both example builds pass. Both updated HTML pages have valid local links
and anchors (35 references), no duplicate ids, and unchanged interactive
scripts. Actual browser checks confirm the updated task guide and lesson
wrap-up render correctly. No new tests were added for this documentation-only
task. No new ADR is needed because no design decision changed.

Next is T02: add the mock host's constant profile provider, then display the
profile result as text in the mini app, including bridge errors. Follow the
test-first workflow for the new behavior and explain it when verified.

## 2026-10-22 checkpoint — implementation plan and workflow change

The maintainer asked to proceed with building the project instead of typing
implementation code as a study exercise. They then requested an accessible
explanation after every task: what changed, why, how the code works, and what
the tests prove, using simple examples and definitions for new terms.
The agent performs the work and explains the result before the next task;
there is no implicit requirement to wait for a comprehension answer.

`docs/implementation-plan.md` records 21 tasks toward browser v0.1: useful
example calls, manifest validation, protocol/connection behavior, host events,
navigation containment, and final verification. Specification gaps are
explicit gates for the affected tasks, not permission to silently amend SPEC.
That checkpoint covered planning; feature implementation had not begun.

Fetched origin: local master matches origin/master at c2d3e2e. Reverified on
2026-10-22: 201 tests across 12 files, typecheck, lint (47 files), and both
example builds pass. The working tree was clean before these planning edits.
The study-coding-mode controller confirmed enabled junior mode, then disabled
it at the maintainer's request. The marker is local and is not committed.

Earlier tutor instructions and resume checklists below describe past sessions.
For this work, the agreement above supersedes the manual-typing and mandatory
learning-review requirements. Existing protocol and architecture decisions,
test-first development, language rules, and security boundaries still apply.

## 2026-09-08 checkpoint

The implementation and tests are split into four logical commits:

- `6e75358` — scoped storage deletion (E4.3).
- `7c0c630` — distinguish invalid params from malformed requests (E4.4a).
- `2b3aff7` — reject unknown method params, with SPEC §4.2 and ADR 0006 (E4.4b).
- `716b6c5` — reset initialization before repeat-handshake validation (E4.4c).

Verified the final implementation with `pnpm test --run` (162 passed),
`pnpm run typecheck`, `pnpm run lint`, and `pnpm run build` (both examples).
An independent read-only review found no blocking issues in this checkpoint.
This is incremental progress, not a declaration of full v0.1 conformance;
remaining validation work and known boundaries are listed below.

## How we work (do not skip)

Historical tutor workflow: the 2026-10-22 agreement above is current.
Preserve these notes for the existing learning material and earlier work.

- **Tutor mode ("study coding mode"), level: junior — implementation-first
  (agreed 2026-08-19).** Division of labor: **The coding agent writes and maintains
  the tests; the maintainer TYPES the implementation code.** Explanations
  start from the running code ("what does this thing do"), then point at
  which tests cover it. Larger steps than before; the reward of each step is
  red tests turning green. The coding agent reads and verifies the maintainer's typed
  code after every step.
- Explanations at junior level: define every term in plain language with an
  analogy — but don't shrink the steps.
- **Refined 2026-09-02, after the maintainer asked "이거 스터디 모드 맞아?".**
  Every handover has, in this order: (1) the design and the why; (2) a
  glossary table for the step's NEW terms — plain definition plus an analogy;
  (3) the exact snippet to type, with a why per line (the maintainer asked
  for the code itself: "don't write the code for them" means don't Edit/Write
  it into the implementation files, not withhold it); (4) the concrete check
  with the expected test delta; (5) two to four named deep-dive offers. A
  handover missing (2) or (5) is the regression they noticed. Deep-dives are
  answered in prose unless they ask for HTML. The HTML notes were initially
  local; since the maintainer's 2026-09-30 request, study/ is versioned.
- **Refined 2026-09-04 — keep the rationale in the code too.** The maintainer
  pointed out that the storage handovers had fewer useful comments than the
  existing code. Include English documentation comments with handover snippets
  for public contracts, wire types, guards, and invocation helpers where their
  purpose or constraints need explanation. Cite SPEC/ADRs and explain the
  security/portability rationale, input/output semantics, and important limits.
  Add inline comments where ordering or a subtle check matters (for example,
  identity selection, null versus falsy values, and awaiting write completion).
  Avoid merely translating syntax into prose. Chat explanations supplement
  these comments; they do not replace them. The agent can maintain requested
  comments without changing the maintainer's implementation logic.
- Dialogue in Korean, project artifacts in English, with the approved Korean
  learning-material exception for study/ (see CLAUDE.md).
- **Refined 2026-09-30 — interrupted study sessions need a living HTML guide.**
  The maintainer requested an accessible architecture map, roadmap, current
  position, and sequential explanations of long code, including why each
  check exists. Maintain `study/index.html` as the stable entry point and
  `study/05-json-value-validation.html` as the current detailed lesson;
  `study/study.css` supplies their shared styles. Preserve the earlier notes.
  Read the guide alongside this handoff on resume. After each verified step,
  update its date, real check results, current status, next small action, and
  relevant explanation. Keep prior explanations available rather than
  replacing the guide with only the newest task. This is upkeep during study,
  not a scheduled automation or a live repository monitor.
  Teach long code in small conceptual blocks, with the current architecture
  and call path first, then each block's purpose, line roles, and failure it
  prevents. Avoid another large implementation handover while comprehension
  is pending. HTML teaching materials may be authored by the agent; meaningful
  Moonpool implementation remains typed by the maintainer. These Korean
  learning materials are now versioned at the maintainer's explicit request.
  They travel with a clone or pull; if absent, restore them from Git. Keep
  the local study-mode marker and editor/session settings untracked.

## Where we are (v0.1)

Done:

- pnpm workspaces skeleton per the CLAUDE.md repository layout
  (`packageManager` pinned to pnpm 11; internal deps use `workspace:*`;
  on a fresh machine run `corepack enable`, then `pnpm install`).
- TypeScript 7.0.2 (note: TS7 removed `baseUrl`; `paths` are `./`-relative
  now; `noUncheckedIndexedAccess` is ON — indexing gives `T | undefined`),
  Vitest 3. `npm run typecheck` passes.
- `packages/protocol`: real content — `Transport` interface (SPEC §3.1),
  `ERROR_CODES` (§4.4), `PROTOCOL_VERSION`, §5/§7 types.
- Biome 2.5.9 as the single formatter + linter (`npm run lint`,
  `npm run lint:fix`); `.vscode/` recommends the Biome extension with
  format-on-save. Chosen over Prettier+oxlint to keep one tool/one config.
- Test-writing roadmap: complete. All 10 §5 tests exist (7 host + 3 client);
  the in-memory linked Transport pair helper
  (`packages/host/test/helpers/memory-transport.ts`) delivers async
  (microtask), mirroring postMessage semantics.

### Phase: implementation to green

The maintainer types the implementation and watches reds turn green.

Implementation roadmap:

- **A. Host gate — DONE 2026-08-19.** Maintainer typed it; Claude verified.
  Replies -32005 to every request, ignores notifications (§4.1).
  `pnpm test` → 3 passed / 7 failed exactly as predicted (smoke, -32005
  gate, no-service-after--32004 green; the rest now fail as assertion
  diffs, not "Not implemented").
- **B. Host initialize — DONE 2026-08-19.** Maintainer typed it; Claude
  verified. All 7 original host tests green; lint and typecheck clean.
- **C. portal.ping + unknown-method reply — DONE 2026-08-20.** Two tests
  added by Claude (ping → `{ pong: true }` per §6.2; unknown method →
  -32601 — §4 forbids silence for id-bearing requests, and §4.4 coverage
  is in the v0.1 definition of done). Maintainer typed the two branches
  below the -32005 gate. Suite: 9 passed / 3 failed; lint + typecheck
  clean. Host suite fully green.
- **C2. Refactor under green — DONE 2026-08-20.** Typed `JsonRpcRequest` +
  `isJsonObject`/`isJsonRpcRequest` guards and `PORTAL_METHODS` constants in
  protocol; host reads through them. Tests stayed 9 passed / 3 failed as
  required. Committed as `refactor:`.
- **D. Client — DONE 2026-08-20.** Maintainer typed it; Claude verified.
  `MoonpoolError` (client-local), `Pending` map keyed by id, `nextId` from 1,
  one `onMessage` return desk registered at construction, §4.5 unknown-id
  replies ignored. `isJsonRpcResponse` + `JsonRpcResponse` added to protocol.
  `call()` params narrowed from `Record<string, unknown>` to
  `Record<string, JsonValue>` — the bridge carries JSON only. **All 12 tests
  green.**
  - Regression caught during this step: `isJsonRpcRequest`'s body was
    overwritten with the response-checking logic (paste accident), which
    silently broke 8 host tests while `typecheck` stayed clean. Lesson worth
    keeping: a type predicate is an *unchecked assertion* — `return true`
    compiles — so guard bodies must be covered by tests.
- **D2. Client timeouts (§4.5) — DONE 2026-08-20.** Tests by Claude
  (`packages/client/test/timeout.test.ts`); maintainer typed the
  implementation. `setTimeout`/`clearTimeout` are declared as module-local
  ambient globals in the client rather than pulling in `"DOM"` or
  `@types/node`, which would also make `window`/`process` compile inside the
  pure packages. 16 passed / 0 failed.
- **D3. Connection teardown (§4.6) — DONE 2026-08-20.** Spec gap resolved
  with maintainer approval and SPEC.md updated first (`b7ebde9`): new
  `-32008 CONNECTION_CLOSED` in §4.4, new §4.6, new §11 entry. Tests by
  Claude (`packages/client/test/close.test.ts`); maintainer typed
  `ERROR_CODES.CONNECTION_CLOSED` and the `close()` drain. **20 passed /
  0 failed.**

- **E0. -32600 for malformed id-bearing frames — DONE 2026-08-24**
  (`a41bd89`). New `hasRequestId` envelope guard in protocol; the host now
  answers `-32600` (echoing the id) instead of silently dropping id-bearing
  malformed frames. Notifications and non-objects stay silent (§4.1).
  28 passed. See "Why two id checks" below.
- **E0.5. §4.1 id profile: positive integers — DONE 2026-08-24**
  (`1fbe68e`). Maintainer typed the guard tightening (`typeof` +
  `Number.isInteger` + `> 0` in `isJsonRpcRequest`; `hasRequestId`
  untouched). id 0 / -5 / 3.7 / NaN now answered with -32600, echoing the
  id. **32 passed.** Uniqueness/monotonicity deferred twice over: needs
  per-connection state (host-level, cannot live in the pure guard), and §4.1
  binds only the SENDER — the receiver's response code for a reused id is a
  genuine spec gap needing a maintainer decision first (tracked in Open
  decisions).

### Current status

Before E4.3: **73 passed**, `typecheck` and `lint` clean.
After storage.get: **85 passed**, `typecheck` and `lint` clean. The maintainer
typed the complete read slice and the agent verified it on 2026-09-04.
Baseline: **106 passed**, `typecheck` and `lint` clean after the maintainer
typed storage.set, reverified on 2026-09-07 before adding delete tests.
After storage.delete: **119 passed**, typecheck and lint clean.
After E4.4a: **134 passed**, reverified on 2026-09-08 before E4.4b.
After E4.4b: **160 passed**, typecheck and lint clean.
After E4.4c: **162 passed**, reverified on 2026-09-09.
After E4.4d: **172 passed**, typecheck and lint clean.
Current: **201 passed**, typecheck, lint, and both example builds pass after
the maintainer typed E4.4e's validator and storage.set integration. Verified
on 2026-09-30. Sequential explanation and the three requested deep-dives are
in the HTML guide. Stale storage guard comments remain for the maintainer to
update; host error wording is aligned. Conceptual review precedes the next task.
The browser example still has no capability providers.
The kernel, the first platform adapter, a real cross-origin bridge between the
two examples, and now the permission gate with the first scoped method are
done. **E4.3 (`storage.*`) is complete; E4.4 (remaining params guards) is in progress**, then
the example update and an ADR.

v0.1 definition of done, remaining:

- [x] `packages/transport-iframe` — the first real platform adapter
      (`iframe` + `window.postMessage`). Landed in E2/E2.1.
- [x] `examples/mock-host` + `examples/hello-miniapp` running in a browser.
      Landed in E3; a real §5 handshake crosses a real origin boundary and
      survives Portal reloads.
- [ ] Capabilities `profile.get` and `storage.*` (§6.3) — kernel operations
      landed in E4.2/E4.3. Remaining input validation (E4.4) and example
      providers (E4.5) are still open.
- [ ] Remaining §4.4 error-code coverage (`-32600` for malformed id-bearing
      frames landed in E0; `-32602` for non-object `params` landed in E4.4a;
      still open:
      batch arrays via `id: null`, id uniqueness per connection)

**The permission gate exists and runs as of E4.2 (2026-09-02).** The
paragraph that stood here recorded that scope enforcement had never run and
that `-32000` appeared nowhere in the codebase. Both are fixed;
`packages/host/test/permission-gate.test.ts` is the proof. The framing it
gave is still the right one for the rest of E4: SPEC §6.3 calls the v0.1
capability set "deliberately minimal … the goal is to exercise the permission
model", so the capabilities are the vehicle and the gate is the cargo.

**Why E was a different kind of work** (kept as the rationale for how E1–E2
were sequenced). Everything before it was verified over an in-memory linked
Transport pair. Real `postMessage` is the first time §8 (origin) and §9
(security requirements) actually bite: origin checking on every inbound
message, the `moonpool://<mini-app-id>/` origin rule, structured clone vs
JSON serialisation, and iframe sandbox attributes. E is not a continuation
of the client work — it is the first platform adapter, and it is the piece
the native ports will be measured against.

### Why two id checks (decided 2026-08-24)

`hasRequestId` answers the postal question — "is there a numeric id we can
echo a reply to?" (it exists so `-32600` replies can be built at all).
`isJsonRpcRequest` answers the conformance question — "did the sender follow
the §4.1/§4.2 profile?". Profile tightenings (positive integer now; anything
later) go ONLY on the conformance side: if the envelope check shared them, a
frame with a non-conformant id would be silently dropped as if it were a
notification — violating "every id-bearing frame gets exactly one reply".
They overlap textually today for different reasons; do not merge them.

### §8.1 decision — dev-transport origins (approved 2026-08-24)

Browsers cannot register custom scheme handlers, so the dev transport cannot
serve `moonpool://`. §8's real invariant is per-app uniqueness + stability,
not the scheme itself. SPEC now has §8.1: dev transports MAY substitute
per-mini-app http origins (fixed localhost port per app), the id→origin
mapping MUST be pinned (drifting ports silently re-key storage), and host
and Portal MUST be cross-origin even in dev — a same-origin Portal would
make the §9.1 origin check pass vacuously. Alternatives rejected:
`*.localhost` subdomains (Safari friction), sandboxed opaque origins
(isolation without identity — kills the mini app's own storage, which §8
exists to protect).

- **E1. Dev plumbing — DONE 2026-08-25.** Claude filled it (pure config, per
  the tutor-mode division of labor); maintainer chose the stack.
  - **Vite 8.2.2** in both examples with PINNED ports (`strictPort: true`):
    mock-host 5173, hello-miniapp 5174 — SPEC §8.1. Verified: a second
    server on a taken port now fails loudly instead of hopping to 5175.
  - **vitest upgraded 3.2.7 → 4.1.11** so the workspace holds ONE Vite (8).
    vitest 3 pinned vite 7 transitively; leaving it would have meant the dev
    server and the test transform pipeline running different Vite versions.
    32 tests stayed green across the major bump. biome 2.5.9 → 2.5.10
    (`biome migrate` applied to biome.json).
  - **tsconfig split**, and this is load-bearing: root `tsconfig.json` now
    lists protocol/client/host explicitly and still has no DOM lib, so
    `window`/`document` do not typecheck there. `tsconfig.browser.json` adds
    `DOM` + `DOM.Iterable` for transport-iframe and the examples only.
    `pnpm run typecheck` runs both projects.
  - Examples are vanilla TS (maintainer's call): a framework would make the
    reader separate bridge code from framework code, and would signal to
    mini app authors that one is required.
  - Verified in a browser: mock-host embeds the hello Portal cross-origin,
    both render `PROTOCOL_VERSION` from the workspace package, no console
    errors. Root `pnpm run dev` starts both in parallel.

- **E2. iframe transport — DONE 2026-08-26.** Tests by Claude
  (`peer.test.ts` pure, `iframe-transport.test.ts` under happy-dom);
  maintainer typed `src/peer.ts` and `src/index.ts`. **52 passed.**
  `happy-dom` 20.11.6 added at the root for this step.

### E2 design rationale — reread this before answering questions on it

**One factory, not two.** The plan said the host side and the Portal side
would be separate, asymmetric Transport implementations. Writing the tests
showed the difference collapses to a single argument: both post to a peer
window, both listen on their own window, both pin one origin. So there is one
`createIframeTransport({ peerWindow, peerOrigin, localWindow? })`. The
asymmetry is real but lives at the CALL SITE — the host passes
`iframe.contentWindow`, the Portal passes `window.parent` — which is where
"who is my peer" is actually known. Two near-duplicate factories would have
duplicated mechanism to express a difference in knowledge.

**`PeerWindow` is a one-method structural type**, not `Window`. Depending on
the narrowest interface makes the package's real platform surface visible in
the type, and lets test stubs satisfy it without a cast.

**Why `isFromPeer` is a separate pure module.** It is the entire answer to
"did this come from the other end?", and `window`'s `message` event is a
public mailbox — any frame, popup, or embedder on the page can post to it.
Keeping the decision DOM-free means it is not verified through happy-dom's
approximation of postMessage. The wiring test then supplies `event.origin`
and `event.source` synthetically, so a test can pose as a hostile frame —
something an emulator's own postMessage will never do for you.

**The three checks, and what each one alone would miss:**

| Check | Missing it admits |
| --- | --- |
| `event.origin === peer.origin`, exact | `startsWith` accepts `http://localhost:51740` and `http://localhost:5174.evil.com` |
| `event.source === peer.window` | a second frame on the peer's own origin — origin says which house, never which room |
| both origins `!== "null"` | every sandboxed iframe on the web reports `"null"`; accepting it admits anonymous senders. Refused on the CONFIG side too, so a misconfiguration cannot opt in |

A peer origin written with a trailing slash matches nothing, by design:
exact comparison makes a misconfigured origin check fail closed. Normalising
it would be the kind of helpfulness that grows bypasses.

**`targetOrigin` is pinned, never `'*'`.** The second argument to
`postMessage` is a browser-enforced delivery condition, and it is the last
line of defence behind §9.2 navigation containment: if the Portal navigated
away, the frame is not delivered at all. `'*'` would hand every frame —
handshake results included — to whoever is there instead.

**`event.data as JsonValue` is a cast, not validation, and that is correct.**
§3.1 forbids a transport from modifying payloads, and the kernel already
proves frame shape at its own boundary (`isJsonRpcRequest` /
`isJsonRpcResponse`). Validating here would duplicate the trust boundary
instead of respecting "check once, at the door".

**Handler set, one window listener.** Same shape as the client's `pending`
map: one listener for the connection rather than one per handler (per-handler
listeners are O(n²) on every inbound message and leak if not detached), and
the handler set is snapshotted before iteration because a handler may
unsubscribe mid-iteration — the same discard-before-settle discipline used in
`client.close()`.

### E2.1 — handler isolation on throw — DONE 2026-08-28

**The defect.** `createIframeTransport` fans out to `handlers` with a plain
`for` loop inside ONE window listener. If a handler throws, the loop aborts
and every handler after it is skipped. That is a WEAKER guarantee than the
platform's own: the browser isolates each registered listener from the
others.

**Measured, not assumed** (Chrome, 2026-08-26):

| Setup | Ran | Exception escaped `dispatchEvent`? |
| --- | --- | --- |
| Three separate `addEventListener` listeners, 2nd throws | L1, L2-throws, **L3** | no — browser reports it as an uncaught error and continues |
| One listener iterating three handlers, 2nd throws (our shape) | H1, H2-throws — **H3 skipped** | no — caught at the listener boundary |

Note happy-dom let the exception escape `dispatchEvent` where Chrome did not;
another reason the origin decision lives in a DOM-free module.

**Impact today: none** — exactly one handler is ever registered (the kernel's,
via `client`/`host`). It bites the moment a second one exists, which is the
very use case the handler Set is for (attaching a bridge logger without
touching the kernel). Then correctness starts depending on registration
order: kernel-then-logger loses the log exactly when a kernel throw makes it
most needed; logger-then-kernel lets a bad logger silently stop the bridge.

**Decision: fix it, per-handler `try`/`catch` that re-throws asynchronously**
so the error still surfaces as an uncaught error / `window.onerror`. Isolate
without swallowing — swallowing would be the silent-callback antipattern, and
the browser's own semantics (table above) are the target to match.

Rejected: leaving it (the trap outlives the memory of it, and this is the
cheapest moment to fix); a bare `try`/`catch` that swallows (hides bugs).

**Shipped.** Tests by Claude (two, appended to `iframe-transport.test.ts`);
maintainer typed the per-handler `try`/`catch`. **54 passed.**

**Why `queueMicrotask`, decided while writing the tests.** Three candidates
for "re-throw asynchronously", measured rather than assumed:

| Candidate | Verdict |
| --- | --- |
| `reportError(e)` | The exact primitive — WHATWG's "report an exception" as a public API. **Undefined in happy-dom AND in Node 22**, so it cannot be tested here. `lib.dom.d.ts` declares it, so it typechecks and then throws at runtime |
| `setTimeout(() => { throw e })` | Works, testable via `vi.runAllTimers()`. Rejected: background tabs clamp timers to 1000ms+, so a bridge error could be reported a second late; and `setTimeout` already means *real elapsed time* in the client's §4.5 timeout — reusing it here makes one name carry two intents |
| `queueMicrotask(() => { throw e })` | **Chosen.** No clamping, reported in the same event loop turn as the frame that caused it, and the name says "get off this stack" and nothing else. Testable via `vi.useFakeTimers({ toFake: ['queueMicrotask'] })` + `vi.runAllTicks()` |

Not `Promise.resolve().then(() => { throw e })`: that produces an
**unhandled rejection**, not an uncaught error. Different event
(`unhandledrejection` vs `error`). Correction 2026-09-02: modern collectors
(Sentry's `GlobalHandlers`, Datadog RUM) hook BOTH by default, so the
argument is not "it would be missed" but "it would be reported worse" — a
rejection is grouped separately and, when its reason is not an `Error`,
arrives with no stack ("Non-Error promise rejection captured"); a re-thrown
uncaught error carries the original stack. And Promise jobs cannot be faked
by `vi.useFakeTimers`, so the `then` form is untestable here.

No `reportError ?? queueMicrotask` fallback: the branch would be untestable
in one direction here, so production would run a path the tests never touch,
with different timing (synchronous vs microtask) from the one they prove.
**Transition trigger:** the day a real-browser test runner (Playwright or
equivalent) lands, switch to `reportError` with no fallback branch and assert
via `window.onerror`. That switch is an ADR.

**A third test was written and deliberately dropped:** "two throwing handlers
are both reported". Under sinon fake timers a second `vi.runAllTicks()`
re-throws the FIRST error, which is a fake-timer artifact, not browser
behavior. The property is real (the spec continues the microtask checkpoint
past a throw) but this harness cannot honestly assert it. Same lesson as the
happy-dom `dispatchEvent` divergence above: **a fact measured through a fake
is a fact about the fake.**

### E3 — connect the examples — DONE 2026-08-28

Maintainer typed both sides; verified in a real browser, not only in tests.
`3e556ea` (examples), `225fd21` (SPEC §5.1), `71e1262` (host fix).

**The load race described in the previous handoff does not exist.** SPEC §5
says "the mini app initiates", so the host never sends first, and the host
attaches its listener in the same synchronous task that creates the iframe —
a parent script runs to completion before any script inside the iframe can
run. The ordering is a guarantee, not luck. It holds only while the host
attaches synchronously: an `await` before `createIframeTransport` would give
it away.

The race is real for §6.4 host-initiated notifications (`portal.lifecycle`,
`portal.environmentChanged`) — no id, no reply, so a lost one is undetectable.
Not reachable today: `Host` exposes only `connect()`. Revisit when §6.4 lands.

**Measured, correcting a claim made twice in session.** It was asserted that
an iframe's `load` fires after the new document's first `postMessage`, so a
`load`-based reload detector would always be too late. Wrong: measured 6/6 in
Chrome, `load` fires *first*. Calling `postMessage` and delivering the message
are different events, and delivery is a separate task. The argument against a
`load`-based detector is not ordering — it is that `load` (DOM manipulation
task source) and posted messages (posting-message task source) are different
task sources, and HTML lets the UA choose between them, so the order is
unspecified either way. See §5.1 for the wording that survived.

**E3.3 — the repeat handshake.** Reproduced in the browser: reloading the
Portal produced `-32601 unknown method: portal.initialize`, and the bridge
stayed dead for that document's life. Root cause was a wrong assumption in
SPEC §5, not in the code — `connection == document`, which `iframe`'s
WindowProxy makes false. SPEC §5.1 written and approved first, then tests,
then a one-condition fix (`!initialized &&` deleted). Full rationale lives in
SPEC §5.1 and the commit messages; the decisions the maintainer made were:
accept repeat handshakes (over rejecting them, which would break multi-page
mini apps outright), make the reset list **closed** so a wrong judgement fails
safe, and forbid re-prompting for consent.

Two things worth carrying forward:

- **A weak test was written and labelled as weak rather than deleted.** "Leaves
  the connection usable after a repeat handshake" passes both before and after
  the fix, because the pre-fix host kept serving `portal.ping` — only the
  handshake broke. Its comment says so. The test that actually catches the
  defect is the one above it.
- **Original §5.1 coverage was incomplete.** Rate-limit counters and consent
  records name state this host does not keep yet. However, initialization
  reset is observable when a repeat handshake fails: E4.4c (2026-09-08)
  adds tests exposing the stale initialized=true value. The previous claim
  that no message could observe the reset boundary overlooked rejection.

### Current piece (E4 — capabilities and the permission gate)

`profile.get` and `storage.*` (§6.3), and with them the first real use of
`grantedScopes`. Points to settle before typing:

- **Where does the gate live?** `namespace.action` where the namespace *is*
  the scope (CLAUDE.md invariant — there is no separate scope registry), so
  the check is `grantedScopes.includes(method.split('.')[0])`. It belongs
  above per-method dispatch, below the `-32005` gate. `portal.*` is exempt
  (§6.2, "no scope required").
- **`-32000 PERMISSION_DENIED` vs `-32601 METHOD_NOT_FOUND`.** A host that
  answers `-32601` for a scoped method the caller lacks leaks less (the mini
  app cannot enumerate what exists), but `-32000` is far kinder to debug and
  is what §4.4 reserves the code for. Needs a decision, and it is a §9
  question — flag it as such.
- **Where does `storage.*` actually store?** §6.3 says namespaced per mini app
  id by the host, and §8 binds data to the origin. For mock-host, an
  in-memory `Map` keyed by `${miniAppId}:${key}` is enough and avoids
  implying persistence the spec has not specified.
- The example should call something and render the result, and should show a
  denied call too — `storage.*` is ungranted in mock-host on purpose, so the
  permission model stays visible on screen.

**Decided 2026-09-02** (maintainer's call, after the `study/04` deep-dives
on fail-closed ordering, error-code leakage, dependency injection, and
hand-written params guards):

- **Decision 1 — `-32000`, and the scope check runs BEFORE method lookup.**
  A caller without the scope gets `-32000` for every method in that
  namespace, existing or not, so an ungranted namespace cannot be
  enumerated. Within a granted namespace an unknown method is `-32601`.
  Answering `-32601` for everything ungranted was rejected: the mini app
  already knows its `grantedScopes` from the handshake, so nothing is hidden
  and debuggability wins. This is a §9 decision.
- **Decision 2 — typed capability slots on `HostConfig`**, one per §6.3
  namespace (`profile`, `storage`), each an interface of async methods the
  embedding host implements (mock-host: a constant profile and an in-memory
  `Map`). The kernel validates `params` (`-32602`), answers `-32001` when a
  slot is absent and `-32603` when a handler throws. A generic
  method→handler map was rejected: it moves §9.6 validation out of the
  kernel and is the seed of a plugin system (out of scope for v0).
- Check order after the `-32005` gate: `portal.*` (exact namespace match,
  never `startsWith`) → scope (`-32000`) → known method (`-32601`) → params
  (`-32602`) → handler present (`-32001`) → invoke.
- Storage identity was settled on 2026-09-04: pass app id and key separately
  (decision 4 below, ADR 0003). Unknown extra params fields and value size
  limits remain open for step 4.
- **Refactor candidate, under green, after E4:** `InitializeResult`,
  `HostInfo`, `PortalEnvironment` are `interface`s that cross the wire. They
  compile only because the host builds the handshake result as an object
  literal and the client casts (`result as InitializeResult`); an interface
  has no implicit index signature, so assigning one to `JsonValue` fails
  (verified 2026-09-02 with tsc 7.0.2). Wire shapes should be `type`
  aliases, like `JsonRpcRequest` / `JsonRpcResponse` / `ProfileGetResult`.
  Rule of thumb recorded for contributors: union or alias → `type`; crosses
  the bridge → `type`; a contract for code (methods, config) → `interface`.
- **Open decision, raise at the end of E4:** enable `exactOptionalPropertyTypes`.
  Without it a provider may return `{ avatarUrl: undefined }`, which
  typechecks against `avatarUrl?: string` and then crosses a structured-clone
  transport as a non-JSON `undefined`. Tried on the root project
  2026-09-02: exactly one existing line fails (`packages/client/src/index.ts:39`).

### E4.2 — permission gate + `profile.get` — DONE 2026-09-02

Tests by Claude (`packages/host/test/permission-gate.test.ts`, 16 tests);
maintainer typed protocol and host. **73 passed.**

What landed:

- protocol: `PORTAL_NAMESPACE`, `PROFILE_METHODS`, `ProfileGetResult` (a
  `type` alias — see the interface-vs-type note above).
- host: `HostConfig.capabilities?.profile?: ProfileProvider`, decision 2's
  typed slot. `grantedScopes` (manifest ∩ host grant) is computed once per
  connection, OUTSIDE the message handler, and shared by the handshake reply
  (copied with `[...]`) and the gate — it is origin-scoped consent, so §5.1's
  reset cannot reach it by construction.
- The gate: `method.split('.')[0] ?? ''`, exempt only when
  `=== PORTAL_NAMESPACE`, placed below `portal.ping` and above the `-32601`
  fallthrough. Replies `-32000` with `data: { scope }`.
- `profile.get`: `-32001` when the slot is empty; otherwise `invokeProfileGet`
  awaits the provider inside `try` (catches a sync throw AND a rejection),
  builds the result from the two §6.3 fields only — allowlist on the way out,
  because a provider returning `session.user` satisfies `ProfileProvider`
  structurally and must not leak, and `avatarUrl: undefined` must not cross a
  structured-clone transport — replies `-32603` with a fixed message on
  failure, then re-throws the provider's error via `queueMicrotask`
  (decision 3, same shape and rationale as E2.1). `queueMicrotask` is a
  module-local ambient declaration in host, like the client's `setTimeout`.

Worth carrying forward:

- **The gate was first typed inside the `portal.ping` branch.** Dead code:
  typecheck and lint green, tests unchanged at 9 red. The tests caught what
  the compiler cannot — the same lesson as the D-step guard-body accident.
- Four gate tests pass before the gate exists and say so in their comments.
  They pin the gate's PLACE: below `-32005`, below `portal.*`, before the
  provider call.
- Provider-failure tests live under
  `vi.useFakeTimers({ toFake: ['queueMicrotask'] })`; without it the real
  re-throw fails the run as an unhandled error. `useRealTimers()` discards
  the parked throw.

### E4.3 — `storage.*` (get/set/delete DONE)

`storage.get` / `storage.set` / `storage.delete` (§6.3), a `StorageProvider`
slot next to `profile`, mock-host backed by an in-memory `Map`. The gate
already covers the `storage` namespace; nothing new there. Glossary given on
2026-09-02: key-value store = 사물함, namespacing = "302호의 3번 사물함",
isolation = 남의 호수 사물함은 열쇠가 안 맞음, composite key = 호수와 번호를
한 줄로 쓴 것.

**Decision 4 — approved 2026-09-04: app id and key are separate arguments.** §6.3:
"namespaced per mini app id by the host. A mini app MUST NOT be able to read
another mini app's keys." Recorded in
`docs/adr/0003-pass-storage-app-identity-separately.md`.

The kernel selects the identity from host-held configuration; the provider
must actually partition its data by that identity. An argument alone does
not guarantee isolation. Options considered:

| | Shape | For | Against |
| --- | --- | --- | --- |
| **A (accepted)** | provider takes the id separately — `get(miniAppId, key)`, `set(miniAppId, key, value)`, `delete(miniAppId, key)`; the kernel always passes `config.manifest.id` | identity selection can be tested at the kernel boundary; providers choose their own storage layout | one more argument; providers still must enforce separation |
| A' | kernel composes `${id}:${key}` | provider takes one key | couples the contract to an encoding convention; contrary to the earlier note, a colon in the key alone cannot collide when valid app ids contain no colon |
| B | host injects a per-mini-app provider | kernel stays id-agnostic | correct binding must be verified separately in each embedding host |

Tests under A: the provider receives the manifest id and the unmodified key
separately; two connections using one partitioned provider read their own
values for the same key. A missing key answers `{ value: null }`. Failure and
re-throw semantics match `profile.get`. A smuggled `params.miniAppId` must
never choose another app; its dedicated test is deferred until E4.4 decides
whether unknown fields are ignored or rejected, so the test does not silently
settle that open policy.

**2026-09-04 — storage.get test handover.** Added 12 tests in
`packages/host/test/storage.test.ts`: id/key forwarding and JSON result,
missing key, two-app reads, async settlement, denied scope, missing provider,
three invalid-key cases, validation-before-availability, and two provider
failure shapes. Verified **74 passed / 11 failed** overall; the existing
scope gate accounts for the one new green test. Failures are caused by
`-32601 unknown method: storage.get`, not a test-loading error. Typecheck has
exactly two expected errors: missing `StorageProvider` export and missing
`HostCapabilities.storage`. Lint passes.

**2026-09-04 — storage.get implementation DONE.** The maintainer typed the
complete read slice: protocol
`STORAGE_METHODS.GET`, `StorageGetParams`, `StorageGetResult`,
`isStorageGetParams`; host `StorageProvider.get(miniAppId, key):
Promise<JsonValue>`, optional storage slot, `invokeStorageGet`, and the branch
below the permission gate. The provider interface has only get for this step;
set/delete are added with their tests later. Read the diff and ran all checks:
**85 passed**, both missing-contract type errors resolved, lint clean. The
implementation matches the handover, including gate placement and error
handling. No implementation code has been edited by the agent.

The maintainer asked for two deep-dives before moving on: identity forwarding
versus storage isolation, and whether a provider checks feature availability.
Explain from their code: the embedding host supplies the executable provider;
the kernel checks its presence and separately enforces grantedScopes. The
provider performs the operation and must respect the app id. The first test
observes the kernel's call arguments; the two-app test uses a deliberately
partitioned test provider. Neither certifies an arbitrary future provider's
storage layout. The real example provider needs its own isolation checks when
it is implemented. Also discussed dependency injection, ports and adapters,
when a boundary is useful, and passing a concrete notifier object to a caller.
The maintainer requested proceeding after those examples; do not repeat the
provider lesson before moving on.

**Null policy — approved 2026-09-04 (ADR 0004).** The maintainer approved the
proposal to reject a missing or top-level null storage.set value with -32602,
while permitting null inside objects and arrays. SPEC §6.3 now reserves
`{ "value": null }` for an absent key. The assistant explicitly restated that
even an intentional top-level null write gets an error. Allowing null with an
ambiguous read result was an alternative; it was not the chosen policy.
SPEC was updated before the tests. CHANGELOG.md records the draft-contract
tightening, and ADR 0004 records the decision. Do not ask again.

**2026-09-04 — storage.set tests, verified RED before implementation.** Added 21
tests to storage.test.ts: id/key/value forwarding and an empty result, two-app
write/read round trips, false/zero/empty-string/nested-null values, waiting for
write completion, permission and initialization gates, missing provider,
invalid params, validation-before-availability, preserving an existing value
on null rejection, and both provider failure shapes. The setup helper accepts
partial providers and fills unused operations with throwing stubs; this keeps
the existing read tests focused as the provider contract grows.

Before implementation, verified **88 passed / 18 failed** overall (33 storage
tests, of which 15 pass). The three newly green cases cover the existing permission and
initialization gates. All 18 failures are caused by -32601 for storage.set.
Typecheck reports eight occurrences of the missing set member in test fixtures;
lint passes. Existing production code has not been changed by the agent.

**2026-09-04 — storage.set implementation DONE.** The maintainer typed
STORAGE_METHODS.SET; protocol StorageSetValue = Exclude<JsonValue, null>,
StorageSetParams, and isStorageSetParams (object, string key, value neither
undefined nor null); StorageProvider.set with Promise<void>; invokeStorageSet
awaiting the provider before sending an empty result; and the guarded set
branch after the permission gate. The agent read the diff and verified
**106 passed**, typecheck and lint clean. No separate type is needed for the
literal empty success result.

The maintainer then requested richer comments matching the earlier code.
Added English documentation and inline rationale to the storage contracts,
guards, invocation helpers, and dispatch branches. Corrected the stale
"storage read method", "Skeleton only", and single-invocation-location
comments. These are documentation edits; the implementation remains the
maintainer's. Carry this comment style into the delete handover.

**2026-09-07 — storage.delete tests, verified RED before implementation.**
Added 13 tests to storage.test.ts (46 storage tests total): identity/key
forwarding and the empty result, deletion from the second of two apps sharing
one partitioned provider (preserving the first app's same key and the second
app's unrelated key), waiting for deletion to finish, two permission cases,
the initialization gate, missing provider, three invalid-key cases,
validation-before-availability, and both provider failure shapes with
host-only error reporting. The setup helper now supplies a throwing delete
stub for tests that exercise only get/set.

Verified **109 passed / 10 failed** overall. The three newly green cases pin
the existing permission/initialization gates. The remaining cases reach
`-32601 unknown method: storage.delete`; the completion-order test fails on
that early reply's presence. Typecheck reports six missing-delete member
errors in the test fixtures; lint passes. No production code was changed.

Handover: protocol `STORAGE_METHODS.DELETE`, `StorageDeleteParams`, and
`isStorageDeleteParams`; host import of the guard, async
`StorageProvider.delete(miniAppId, key): Promise<void>`,
`invokeStorageDelete`, and a guarded branch after storage.set and before the
unknown-method fallback. Reuse the agreed scope → params → availability →
invocation order and get/set's sanitized error / queueMicrotask reporting.
The helper must await deletion before sending `{}`. This handover was typed
and verified as recorded below.

**2026-09-07 — storage.delete implementation DONE.** The maintainer typed
the protocol and host additions above. The agent read both implementation
diffs and verified **119 passed**, typecheck and lint clean. The delete branch
is below the permission gate and before the unknown-method fallback; it
validates before checking provider availability, passes config.manifest.id
and the key separately, awaits completion before sending {}, and follows
get/set's sanitized error and host-side rethrow policy. The agent did not
edit the implementation.

The maintainer asked what the offered deep-dive about combining get/delete
input guards meant. Both currently check the same object/string-key shape.
Explain extraction as sharing that rule in one helper while preserving each
operation's intent. This is an optional refactor, not a missing feature or
an agreed next task. With a one-line duplication and E4.4 policies still
open, the current recommendation is to keep the guards separate for now.
Any later extraction should preserve behavior with all tests staying green.

### E4.4a — distinguish non-object params from invalid requests (DONE)

**2026-09-07 — tests verified RED before implementation.** Added 15 tests
in `packages/host/test/invalid-params.test.ts`: six non-object JSON params
shapes on ping, array params on all four scoped methods without invoking a
provider, invalid initialize params with a valid retry, two valid ping
forms, a malformed envelope that also carries array params, and an id-less
array-params frame that must stay silent. Updated the introductory comment
in invalid-request.test.ts to point to this suite.

Verified **123 passed / 11 failed** overall. All 11 failures receive -32600
where SPEC §4.2 requires -32602; the four newly green cases preserve the
surrounding rules. Typecheck and lint pass. Production files were not edited
by the agent. The root cause is the host mapping every failure of the
complete isJsonRpcRequest guard to INVALID_REQUEST, although that guard also
checks the params container.

The implementation handover introduces JsonRpcRequestEnvelope with
`params?: JsonValue` and isJsonRpcRequestEnvelope for the basic jsonrpc/id/
method checks. JsonRpcRequest keeps its existing object-or-omitted params
contract; its guard calls the envelope guard and checks params. The host
keeps hasRequestId first, then rejects a bad envelope with -32600 and a bad
params container with -32602. These are the existing general wire-shape
checks, split in place before the handshake. Per-method field guards remain
after permission checks. ADR 0005 records why both intermediate and complete
request shapes are needed and why the complete guard stays independently
usable.

**2026-09-07 — implementation DONE.** The maintainer typed the intermediate
type and envelope guard, composed isJsonRpcRequest from envelope + params
checks, and split the host's rejection into -32600 / -32602 in the existing
wire-shape gate. The agent read the implementation diff and verified
**134 passed**, typecheck and lint clean. Added only omitted explanatory
comments from the handover (including the delete branch's ordering comment);
the maintainer's implementation logic was not changed. ADR 0005 now records
implementation verification.

The maintainer requested all four related explanations: why the intermediate
type says params?: JsonValue; claiming only what was checked; the positions
of general and per-method validation; and why the complete guard repeats
the envelope check. Explain with one request progressing through stages:
params may be an array/null after an envelope-only check, becomes
object-or-omitted after the complete shape guard, and gets a string key only
after its method guard. Type predicates are trusted declarations, not
compiler-verified proofs. The standalone complete guard intentionally checks
its own premises; the host's first call exists to classify -32600 vs -32602.
General shape checks are before session state; scoped method-field checks
remain after permission and method lookup. These explanations were delivered
in chat before the maintainer paused the session; do not automatically repeat
them on resume.

Keep the qualification explicit: the envelope guard does not prove that
arbitrary browser data is JSON. JsonValue is the current Transport input
contract, and recursive validation remains open. Unknown extra fields,
recursive JSON checks, size limits, and missing/wrong method-specific fields
are subsequent steps; no unapproved policy is settled by E4.4a.

### E4.4b — unknown params fields (DONE)

**2026-09-08 — resumed.** Re-read SPEC, ADRs 0003/0005, and the current
guards. Reverified **134 passed**, typecheck and lint clean. Study mode is
still junior. The preceding deep-dives are complete.

SPEC originally listed each method's params without specifying whether
additional members were ignored or rejected. The maintainer approved
explicit rejection on 2026-09-08: unsupported params should be clearly
reported, not silently carried along. SPEC §4.2 was updated before tests;
ADR 0006 and CHANGELOG.md record the contract tightening. Do not ask again.

Known methods reject unknown top-level params members with -32602. This
does not restrict application-defined keys inside storage.set's value,
including a nested miniAppId. Permission precedes method-specific checks;
validation precedes provider availability and invocation. The host still
selects storage identity from its manifest (ADR 0003). Extra JSON-RPC
envelope members and unknown method handling are unaffected. A new optional
param will not be silently tolerated by an older host; that compatibility
cost was part of the approved proposal.

**2026-09-08 — tests verified RED.** Added 26 tests in
`packages/host/test/unknown-params.test.ts`: extra fields on all six handled
methods; forged miniAppId on all storage operations; constructor/toString
as unsupported names; validation-before-availability and permission-first
behavior for every scoped method; initialization, unknown method, and
notification ordering; a write/read round trip preserving arbitrary nested
value keys; both empty/omitted profile params; and an extra envelope member.
Updated the related test-file comments and ADR 0003's old open-policy note.

Verified **145 passed / 15 failed**, typecheck and lint clean. The 15 failures
are ordinary assertion mismatches: unsupported params still succeed, or the
host answers -32001 before it rejects them. The 11 newly green cases preserve
existing ordering and accepted data. Production logic has not been changed
by the agent for E4.4b.

Implementation handover:

- protocol: `hasOnlyParamKeys(params: JsonValue | undefined,
  allowedKeys: readonly string[]): boolean`, checking omission or an object
  whose own enumerable names all occur in allowedKeys. No recursion or
  mutation. Empty/omitted params have no unknown keys; required-field checks
  remain separate. This boolean does not claim a complete method schema.
- host: import the helper. Add a local `rejectUnknownParams(id, params,
  allowedKeys): boolean` inside connect after grantedScopes. Return false
  when the names pass; otherwise send one -32602 reply with a fixed message
  and return true. The caller returns immediately when rejection occurred.
- At the beginning of each existing method branch call that rejection
  helper: initialize allows ['protocolVersion']; ping/profile.get allow [];
  storage.get/delete allow ['key']; storage.set allows ['key', 'value'].
  All scoped branches already follow the permission gate. Keep existing
  required-field and provider checks after the new call. Do not implement
  portal.close as part of this step.

**2026-09-08 — implementation DONE.** The maintainer typed
hasOnlyParamKeys, the local rejection helper, and its calls at the start of
all six handled method branches. The agent read the implementation diff and
verified **160 passed**, typecheck and lint clean. Scoped calls follow the
permission gate and precede provider access. The helper examines top-level
names only; nested storage values stay intact. Corrected one copied
storage.set comment that incorrectly said only the key came from the caller;
the maintainer's implementation logic was not changed.

The maintainer requested all three offered explanations: why every returns
true on an empty array, how allowed-key checks differ from required-field
checks, and why the rejection helper's return does not stop its caller.
Explain every as finding no counterexample: no keys means no forbidden key,
not that required keys exist. Use a storage.get table for {}, { key: 'theme' },
{ key: 42 }, and { key: 'theme', extra: true } to separate names, presence,
and value types. Explain that return exits the function currently executing:
the helper returns a rejection flag, and the onMessage callback must return
separately to stop that request before provider access. This ends one
callback invocation, not the connection or its future message handling.
These deep-dives are delivered in this turn; do not repeat them by default.

### E4.4c — reset initialization before rejecting a repeat (DONE)

**2026-09-08 — found while reviewing remaining input validation.** The
initialize branch sets initialized=true on success but never resets it on
entry. After an earlier success, an unsupported version or an unknown params
field returns an error while leaving the previous document's success active.
The next portal.ping incorrectly succeeds. SPEC §5.1 already requires resetting
initialization state on a repeat handshake; no new policy or SPEC edit is
needed for this fix.

Added two cases in `packages/host/test/handshake.test.ts`: initialize
successfully, then send a replacement document's initialize with either
protocolVersion '9.9' or an unsupported extra params field. Assert its
existing -32004/-32602 response, then require -32005 for a subsequent ping.
Each case also requires a valid retry to restore service with the original
granted scopes. Corrected the test file's old claim that initialization
reset could not be observed.

Verified **160 passed / 2 failed**, typecheck and lint clean. Both tests
expect -32005 but receive { pong: true }; the earlier rejection codes are
already correct. The failure is stale state, not error-code mapping.

Handover: at the beginning of the host's PORTAL_METHODS.INITIALIZE branch,
before rejectUnknownParams and version comparison, add the commented
`initialized = false;`. Keep the existing success assignment to true.
Only document initialization state resets; transport, grantedScopes, and
stored values are preserved. The agent has not changed production logic.
**2026-09-08 — implementation DONE.** The maintainer added the commented
initialized=false assignment at the start of the initialize branch, before
unknown-field rejection and version comparison. The success assignment to
true remains in place. The agent read the exact block and verified
**162 passed**, typecheck and lint clean. No implementation or comment edits
were needed during verification.

The maintainer requested all three offered deep-dives. Explain why resetting
on entry covers every method-level rejection path, whereas resetting in
each failure branch is easy to omit as validation grows. Resetting first
establishes an uninitialized default; only successful negotiation restores
true. Explain document-scoped initialization versus app/origin-scoped grants
and stored values: a reload replaces the page's running context but does not
revoke the user's grant or erase the app's data. Finally, distinguish tests
that start with false from a sequence that first establishes true: the old
first-handshake failure tests could not expose stale success. The new tests
also require a valid retry to restore service. These explanations were
completed on 2026-09-08; do not repeat them by default on resume.

These cases reach the initialize branch with a valid general request shape.
They do not establish handling of malformed-envelope or malformed-container
repeat messages rejected earlier in the pipeline. Required-field validation,
recursive JSON validation, and size limits remain separate work.

### E4.4d — required protocolVersion input (DONE)

**2026-09-09 — resumed.** The working tree was clean at aaa5adc on master.
Reverified 162 tests passed, typecheck and lint clean; study mode remains
junior. E4.4c and the earlier deep-dives are complete.

The initialize branch currently compares message.params?.protocolVersion
directly with PROTOCOL_VERSION. Missing input and non-string values therefore
receive -32004, just like a well-typed but unsupported version. SPEC §5 shows
a string version and defines unsupported-version handling, but does not
explicitly distinguish missing/wrongly typed input from version negotiation.

The maintainer approved the following clarification on 2026-09-09. SPEC §5
was updated before tests; ADR 0007 and CHANGELOG.md record the distinction:

> portal.initialize requires params.protocolVersion to be a string. Missing
> params, a missing protocolVersion, or a non-string protocolVersion MUST
> be rejected with -32602 before version negotiation. A string that does not
> exactly match a protocol version supported by the host MUST be rejected
> with -32004.

This policy adds no version-format grammar or coercion. Under the approved
rule, an empty string is still an unsupported string (-32004), matching
the existing exact-match behavior. Unknown fields remain rejected under
ADR 0006. The E4.4c reset stays before these checks so failed initialization
cannot inherit prior success, and valid retry remains possible.

**2026-09-09 — tests verified RED.** Added seven input cases in handshake.test.ts
for omitted params, missing protocolVersion, null, number, boolean, array,
and object values. Each requires -32602, subsequent -32005 for ping, and a
valid initialization retry restoring service. Added a repeat-initialization
case with a missing version to pin the existing reset ahead of this new
rejection. Extended unsupported-string cases with '' and ' 0.1 ' to preserve
exact-match behavior without a non-empty rule or trimming.

Verified **164 passed / 8 failed** (172 total). All eight failures receive
-32004 instead of -32602; the two new unsupported-string cases are already
green. Typecheck and lint pass. Production code has not been edited by the
agent. The tests use the real host bridge; the omitted-params frame is built
directly because the existing request helper defaults params to {}.

Handover: inside PORTAL_METHODS.INITIALIZE, immediately after
`const requested = message.params?.protocolVersion;` and before the existing
version comparison, check `typeof requested !== 'string'`. On failure,
send -32602 with a fixed message and return. Keep the existing early reset,
unknown-field check, exact version comparison, and success assignment.
A local check is sufficient; no new public type/guard is needed.
**2026-09-09 — implementation DONE.** The maintainer inserted the local
typeof check immediately after reading requested, before version comparison,
and below the existing initialization reset and unknown-field check. The
agent read the block and verified **172 passed**, typecheck and lint clean.
No implementation edits were needed. ADR 0007 records verification. The
maintainer requested proceeding, not the optional deep-dives; do not deliver
them automatically on resume. Do not ask for this policy again.

### Current piece — E4.4e, non-JSON storage values (implementation GREEN; learning review)

The next boundary is storage.set's arbitrary value tree. Its current guard
rejects top-level undefined/null but does not inspect nested values.
Nested undefined and NaN can therefore reach the provider. Native
JSON.stringify demonstrates the portability problem: { nickname: undefined }
becomes {}, and { score: NaN } becomes { score: null }.

The maintainer approved the clarification on 2026-09-09 and explicitly
requested updating the spec and starting with tests. SPEC §6.3, ADR 0008,
and CHANGELOG.md were updated before tests. The rule: storage.set MUST
reject a value containing data outside the JSON value model with -32602,
before invoking its provider. It MUST NOT remove, coerce, or replace invalid
data to make the value JSON-compatible. This includes nested undefined,
non-finite numbers, non-JSON objects such as Date/Map, and circular references.
Nested null and application-defined object keys remain allowed, under the
existing ADR 0004/0006 rules. The existing scope and availability ordering
remains unchanged.

This first slice concerns the storage value tree. A pure validator belongs
in protocol and can be used by the existing storage.set guard; it does not
change Transport's interface or normalize payloads. Whole-envelope handling
and size/depth limits remain separate decisions. This policy is settled;
do not ask again.

**2026-09-09 — tests prepared and verified RED.** Added 23 tests in
`packages/host/test/storage-json.test.ts`. Sixteen invalid-value cases cover
undefined in objects/arrays, non-finite numbers, Date/Map/Set/typed-array
values, nested bigint, direct/indirect/array cycles, and sparse array holes.
Also require validation before availability and preservation of both the
existing stored value and the original invalid input. Five already-green
cases preserve permission/initialization gates, ordinary nested JSON,
shared acyclic content, and a deep finite tree.

Verified **177 passed / 18 failed** (195 total), typecheck and lint clean.
Failures are ordinary response mismatches: invalid writes still succeed,
or availability responds -32001 instead of input rejection -32602. The
test-only cast deliberately injects unknown values without serialization;
no production Transport signature was changed. The 20,000-level tree is a
stress sample to catch recursive call-stack failure, not a chosen limit.
The assertions for that case also traverse iteratively.

**2026-09-11 — implementation handover.** Added six boundary/stress tests
before handing over implementation: symbol-keyed members, non-enumerable
members, named array members, no toJSON execution, no getter evaluation,
and a 31-object shared graph whose expanded paths would exceed a billion
leaf visits. Verified **178 passed / 23 failed** (201 total), typecheck and
lint clean. New rejection cases still succeed; the shared-graph case is
already green before validation. This does not impose a protocol size limit.

The maintainer is handed isJsonValue(value: unknown): value is JsonValue in
protocol. It uses visit/complete tasks in an array stack and a local
Map<object, 'visiting' | 'valid'>. An active ancestor means a cycle; completed
subtrees can be reused. Validate scalar leaves, dense array indices and
ordinary record prototypes, then inspect own string-keyed enumerable data
descriptors without evaluating getters. Array length is excluded from data
members. Reject reflective failures. ADR 0008 records this implementation
rationale and its boundaries, including Proxy traps and serialized expansion.

Integrate by retaining the existing required-key/top-level-null checks in
isStorageSetParams and adding isJsonValue(params.value). Update its stale
comment and the host's invalid-params message to mention a non-null JSON
value. No E4.4e implementation code has been written by the agent. On resume,
inspect the maintainer's files before repeating the handover. Expected after
typing: **201 passed**, typecheck and lint clean; not yet verified.

**2026-09-30 — resumed in Codex, study mode still junior.** Inspected the
current implementation: isJsonValue is absent and isStorageSetParams still
checks only the required key and top-level undefined/null. Reverified
`pnpm test --run --reporter=dot`: **178 passed / 23 failed** (201 total).
All failures remain in storage-json.test.ts; typecheck and lint pass.
The next handover covers the validator and its storage.set integration as
one learning step. No production code or test changes were made on resume.
Wait for the maintainer's typing, then inspect their files and verify the
expected **201 passed** result before advancing.

**2026-09-30 — maintainer's implementation verified GREEN; explanation requested.**
The maintainer typed the complete iterative isJsonValue validator and added
isJsonValue(params.value) to isStorageSetParams. Read the implementation and
verified **201 passed**, typecheck, lint, and both example builds clean.
The agent did not modify production logic. The old guard documentation still
says nested data is unchecked, and its inline comment describes only the
outer inspection. The host error still says "non-null value" rather than
"non-null JSON value". These are the next small handover, not another feature.

The maintainer asked for a detailed sequential explanation and persistent,
readable HTML materials because study sessions are intermittent. Created
study/index.html (architecture, request flow, roadmap, current state, next
action, glossary, links to existing notes) and
study/05-json-value-validation.html (15 annotated source blocks, cycle versus
sharing, visit/complete stack replay, getter/descriptor experiment, test
mapping, and the remaining comment/message handover). Shared styles are in
study/study.css. These were initially personal, ignored materials and are now
versioned under the explicit request recorded below. The supplied explanation
must not be treated as proof the maintainer has reviewed or understood it;
continue questions and conceptual review before advancing. Update these
materials alongside HANDOFF after subsequent verified study steps.

Verified the new HTML guide in the browser: architecture and lesson render,
all three stack replay examples reach their expected outcomes, descriptor
inspection leaves the getter call count unchanged, and direct reading calls
it once. Block navigation works. Both pages fit a 390px viewport without
page-level horizontal overflow; the temporary viewport override was reset.
Local links and anchors were checked. The source snapshot is dated, not a
live view of the implementation.

**2026-09-30 — commit/push checkpoint requested.** The maintainer updated the
host's storage.set error to require a "non-null JSON value". The guard's old
documentation and inline comment remain for the next study step. Reverified
**201 passed**, typecheck, lint, and both example builds clean; git diff check
also passes. Split the checkpoint into required version input, JSON storage
validation, and session documentation. Personal study HTML remains ignored;
the tracked handoff preserves its maintenance instructions and recreation
sources. This checkpoint does not declare complete v0.1 conformance.

Feature commits in this checkpoint:

- `b5d66f9` — validate required version input before negotiation (E4.4d).
- `8f0ac35` — reject non-JSON storage values without conversion (E4.4e).

The remaining session documentation is a separate docs commit. The maintainer
requested pushing this checkpoint to origin/master.

**2026-09-30 — maintainer requested publishing the study materials too.**
Remove study/ from .gitignore and version the stable index, lessons 01–05,
shared stylesheet, and architecture preview image. CLAUDE.md records the
narrow Korean-language exception for study/; other project artifacts remain
English. Update the guide's old local-only wording. Keep all study materials
updated with subsequent verified steps. Session-mode markers remain ignored;
cloning the notes does not enable tutor mode for another contributor.
Verified all study-page relative links and anchors, the preview image, and
root lint (47 files, clean). Added explicit button types and aligned teaching
page scripts/styles with existing lint rules. Browser checks confirm the
getter/descriptor and cycle demonstrations and the older event-loop replay
still work. No Moonpool runtime implementation changed.

Resume checklist:

1. Decision 4 is approved; do not ask again.
2. storage.get/set/delete are verified GREEN and the provider discussion is finished.
   Both identity and null policies are approved; do not repeat either decision.
3. E4.3, E4.4a, E4.4b, E4.4c, and the requested deep-dives are complete.
   E4.4d is also verified GREEN. E4.4e's rejection policy is approved and
   the maintainer's implementation is verified GREEN (201 passed). Read the
   HTML guide and answer questions before advancing; hand over only the stale
   guard comments next. Version-input, unknown-field, and non-JSON
   storage rejection policies are settled; do not ask again.
   Guard extraction and a shared
   `invoke(id, run)` helper remain optional refactor candidates under green;
   neither is required before starting E4.4.
4. The read slice includes `isJsonObject` + `typeof key === 'string'`, with
   negative tests for omitted params, a missing key, and a non-string key.
   Remaining E4.4 work covers method-field cases and value size limits.
   Non-object params now receive -32602 through E4.4a's general wire-shape
   check; unknown fields (including a forged miniAppId) are rejected by E4.4b.
   Also validate the actual JSON value tree at the browser ingress boundary:
   a JsonValue annotation/cast does not prove that a structured-clone payload
   is JSON. Current method guards check required fields and the null policy;
   storage.set now rejects nested undefined, non-finite numbers, non-JSON
   objects, and cycles. This does not validate the entire inbound envelope or
   establish size/depth limits. Address remaining boundaries before claiming
   full §9.6 conformance.
5. E4.5: mock-host gets a `Map`-backed `StorageProvider` and a constant
   `ProfileProvider`; hello-miniapp calls `profile.get` and renders it, and
   calls `storage.set` so a `-32000` is visible on screen (mock-host grants
   only `profile` on purpose). E4.6: ADR for decisions 1–3 (decision 4 is
   already ADR 0003), HANDOFF, commit.

### Picking this up on another machine

```bash
corepack enable          # once per machine
pnpm install
pnpm test --run          # E4.4e implementation: expect 201 passed
```

The git remote uses a personal SSH host alias
(`git@github.com-personal:WillowRyu/moonpool.git`) — that alias must exist in
`~/.ssh/config` on the new machine or the clone/push will fail.

Tutor mode is local to the session working directory and deliberately not
committed (this repo is meant to ship as MIT open source; nobody cloning it
should inherit study mode). In Claude Code, resume with
`/study-coding-mode:toggle on`. With the Codex plugin installed, use
`$study-coding-mode:study-coding-mode on`; use `status` to inspect without
changing state. Both hosts share the gitignored `.claude/study-coding-mode`
marker in the session working directory. An explicit `on` preserves the saved
level; a bare invocation toggles and could turn an active mode off.

Verified in Codex on 2026-09-04: plugin `study-coding-mode@willow` 0.3.0 is
enabled and its skill is available; the bundled mode controller returns
`{"enabled":true,"level":"junior"}` for this workspace. Automatic hook delivery
was not verified; use the explicit resume command when restoring context.
If the plugin is unavailable in another agent, ask it to follow the "How we
work" section of HANDOFF.md. Codex reads `AGENTS.md`, a symlink to `CLAUDE.md`.
The "How we work" section above is the durable record of the agreement.
Claude's memory files remain local. The Korean study/ materials, including
lessons 01–05 and the stable index, are now versioned with the repository.

## Open decisions (maintainer's call, not made yet)

- **Receiver behavior on id reuse (§4.1):** the spec says senders MUST NOT
  reuse ids (positive, monotonically increasing) but never says what a
  receiver replies when they do. Needs a spec decision (likely `-32600`, but
  do not resolve by editing SPEC.md without approval). Enforcement would be
  host-side per-connection state, not the pure guard.

- **ADR candidate:** Moonpool targets BOTH full-screen mini apps and web
  components embedded inside native screens; the protocol stays
  embedding-agnostic (screen size/placement is a host-UI concern). Arbitrary
  remote URLs are explicitly out: no identity → conflicts with SPEC §8/§9.
- ~~Retry after `-32004`, and a second `portal.initialize`~~ — **resolved
  2026-08-28** in SPEC §5 and the new §5.1 (`225fd21`). Both are allowed.
- **Language question (asked 2026-08-19):** could the kernel be Rust or Go?
  Discussed in session: the client must be JS — it runs inside the mini
  app's web view (Rust→WASM still needs a JS shim for postMessage and the
  bridge is I/O-bound, not compute-bound, so it buys nothing). Rust becomes
  a real option for a SHARED native core after the protocol stabilizes
  (post-v0, per the CLAUDE.md ordering); Go does not fit mobile embedding.
  Possible ADR when native cores start.
