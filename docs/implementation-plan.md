# Browser v0.1 implementation plan

Date: 2026-10-22
Last updated: 2026-10-26
Status: T01–T16 implemented; T17 research published; T18 published; T19 complete locally. T20–T21 remain. ADR 0022 is accepted. Milestone C is complete.
Normative source: `SPEC.md`. This plan does not amend the protocol.

## T19 complete — 2026-10-26

Committed/pushed T18 as 4aab691 / ab98b58 and confirmed the remote in sync before
starting T19. Added 54 tests covering all 14 SPEC §4.4 client mappings with and
without public data, null-id deadline preservation, actual host producers,
initialization/version recovery and private provider error sanitization.
Current implementation passes these contracts; no runtime or SPEC changes.

docs/error-code-matrix.md distinguishes ten current producing codes from four
defined codes without current emitters, and links each to meaningful evidence.
Controlled peer frames cover unimplemented producers without adding cancellation,
rate limiting, host-state policy, string decoding or peer-disconnect behavior.
Existing client timeout/local-close/send-failure suites remain producer coverage.
This verifies §4.4 / §9.4 privacy without changing the security contract.

1131 tests across 39 files, root typecheck and lint pass. T18's unchanged build/
browser baseline is retained; T20 will perform final integration verification.
study/24-error-code-matrix.html explains the code, producer distinction and
null-id timeline. T19 changes are local. Next: T20, then T21; v0.1 not complete.

## T18 complete — 2026-10-26

Published the accepted ADR revision as 0397b70. Recorded SPEC §8.1.1 / §9.2 and
implemented per-Portal served wrappers, terminal iframe transport closure,
host-held Window/URL/Document binding, strict host-only JSON realm adapters,
retained app-partitioned providers and complete exception-safe disposal.
Allowed inner navigation retains §5.1 semantics; same-URL wrapper replacement
does not rebind. No pure-kernel DOM imports, new guest RPCs or dependencies.

The normal example runs two fixed guest origins concurrently; root pnpm run dev
starts all three servers and both builds include their HTML entries. Existing
entry tests mount the real wrapper/kernel and preserve profile/storage/close
contracts. 1077 tests across 38 files, typechecks, lint and both builds pass.
Chrome 156 dev/final-preview observations confirm the recorded cases, including
A-only revocation while B remains pending, storage retained across recreation,
notifications across realms and persistent scope denial. See
docs/browser-containment-verification.md and study/23-browser-containment.html.

T18 was subsequently published as 4aab691 / ab98b58 before starting T19.
Existing §11 questions, cross-engine/full-scheme verification and production
origins are unchanged. The T19 checkpoint above records the next completed step;
full v0.1 completion has not been declared.

## Historical approval checkpoint — 2026-10-26

The maintainer explicitly approved the replacement and ownership companion,
requested committing/pushing it, then authorized tests-first T18 implementation.
Publish the prepared documentation first, record the contract in SPEC, and
implement the accepted realm/provider/lifetime requirements. Do not ask for
the same policy approval again. Earlier review-pending sections are historical.

## Historical replacement preparation — 2026-10-26

Published the completed multi-Portal research as 00c0c63 / 76bc212 and confirmed
origin/master in sync. Then revised ADR 0022 into one per-Portal containment
proposal and added docs/browser-portal-ownership-proposal.md. These proposal
edits are local and unapproved; the previous single-Portal draft was never
accepted. This requested documentation step does not implement T18.

Proposed ownership: each trusted served wrapper owns its kernel, configuration,
connection sender and transport; the outer host owns registry/provider lifetime
and app-partitioned data. Host-only async controls/provider facades exchange
validated JSON snapshots across realms. Keep the strict validator and existing
guest validation order. The host selects storage identity, and Portal disposal
does not erase the retained app partition. Same-app instances share data but
retain independent connections and scope checks. Memory data lasts only as
long as its provider. Remove both frames and invalidate stale handles on close.

The boundary codec/gateway, retained storage across wrapper recreation and
complete disposal are requirements awaiting tests and browser evidence, not
claims about the measured prototype. Approval must precede SPEC edits and
tests-first T18 integration. This proposal touches SPEC §9.2; production origin
requirements and §11 open questions remain. The companion lists acceptance checks.

## Multi-Portal follow-up result — 2026-10-26

The maintainer authorized the investigation. The served-wrapper candidate ran
two distinct app origins concurrently and revoked A without affecting B's
pending request, stored value, or grants. Bootstrap Window/Document binding,
wrong-source replies, same-URL wrapper replacement, and late sends were exercised.
A cross-realm API issue was found: an outer object is rejected by the current
wrapper-owned JSON validator, while a wrapper-created payload succeeds.

See docs/multi-portal-investigation.md and study/22-multi-portal-wrappers.html.
The prototype keeps the kernel/data in each wrapper and retains closed wrappers
for inspection; host API ownership, provider lifetime, complete disposal, and
memory costs need explicit integration design. SDK/SPEC remain unchanged.
Existing 995 tests and checks pass. This is manual evidence, not T18 completion
or approval of a replacement contract. Biome remains the formatter/linter.

## Historical investigation recommendation — 2026-10-26

Preserve multiple origin-bound Portals per app/screen and evaluate the equivalent
browser composition before adopting ADR 0022. Its original single-Portal profile
is under reconsideration. A host-controlled wrapper document with per-Portal CSP
has bounded observations; production integration remains unapproved. Verify independent
navigation enforcement, origin/source/bootstrap binding, continued B operation
when A is revoked, reload, and cleanup before writing the replacement contract.
T18 implementation and normative changes still require approval after evidence.
Production web hosting is not currently specified by the browser development
profile; the production custom-scheme invariant remains in force.

## Historical review clarification — 2026-10-26

One application/screen may contain multiple Portals with distinct origins.
ADR 0022's original single-origin condition is limited to a browser-development
host HTML document, not all Portals in an app. It does not replace per-app origin
isolation or require sharing a domain. Multiple mini-app origins in one browser
host document remain outside the original proposal and require a separate
verified design. Review is active, but no approval or T18 implementation exists.

## Historical checkpoint — 2026-10-23

The maintainer requested committing/pushing completed work and will review
ADR 0022 later. The proposal remains unapproved; no SPEC change or T18
implementation is authorized by this publication request.

| Tasks | Completed work |
| --- | --- |
| T01–T04 | Learning workflow, profile display, isolated memory storage, permission demos |
| T05–T07 | Manifest field/path/scope validation and real example manifest wiring |
| T08–T13 | Request/response validation, ordering, client closure, send-failure cleanup |
| T14–T16 | Portal dismissal, host notification sending, isolated client subscriptions |
| T17 | Manual navigation investigation, evidence, reproducible fixture, proposed ADR 0022 |

Current verification: 995 tests across 34 files, root typecheck, lab typecheck,
lint, and both example builds pass. Manual browser observations are separate.
Remaining: T18 navigation behavior after approval; T19 error-code matrix;
T20 final browser/security verification; T21 conformance and document reconciliation.
Full v0.1 completion has not been declared. The active review is recorded above.

## Working mode

The maintainer switched from typing implementation code to agent-led
implementation. The agent writes tests first, implements, verifies, and
explains each completed task in Korean before proceeding to the next task.
The local study-mode marker is off. Earlier tutor handovers are historical.

For policy questions, explain the previous behavior, the current problem,
and the expected consequences of each proposed option in plain Korean before
asking. The maintainer requested this structure on 2026-10-23 during T10.

Each explanation should cover:

1. What changed, using a concrete before/after example.
2. Why it is needed, defining new terms with a simple analogy.
3. How the request moves through the changed code, with a small useful snippet.
4. What the tests prove and any remaining limits.

Keep explanations accessible at junior level. The maintainer need not type
code or answer a comprehension check to continue. Answer questions when they
arise. After each verified task, update this plan's status and progress,
`HANDOFF.md`, and `study/`. Preserve task ids and earlier lessons so the
roadmap remains usable across sessions. Normal conversation and task explanations remain in Korean;
code, comments, ADRs, and other project documents remain in English.

## Verified baseline

On 2026-10-22, `master` matched `origin/master` at `c2d3e2e`.
Before planning edits, the working tree was clean.

- `pnpm test --run --reporter=dot`: 201 passed across 12 files.
- `pnpm run typecheck`: passed.
- `pnpm run lint`: passed; 47 files checked.
- `pnpm run build`: both browser examples passed.

Already implemented: the transport contract, iframe messaging and origin/source
checks, handshake and repeat initialization, client request correlation,
timeouts and draining pending requests on close, dispatch-time permissions,
profile/storage provider contracts, all three storage operations, and JSON
storage-value validation.

Still missing or incomplete: manifest parsing,
`portal.close`, host notification APIs, navigation containment, batch rejection,
some protocol validation, and full error-code coverage. Existing green tests
do not establish complete v0.1 conformance.

## Task sequence

Each task is sized for one logical change. Write failing behavioral tests
before implementation, run the checks appropriate to the change, and explain
the result before moving on. Documentation-only tasks need no artificial
runtime tests. Use a Conventional Commit if committing the task.

Progress on 2026-10-22: **T01 complete.** Aligned source comments, the study
entry point and lesson 05 wrap-up with the existing implementation and current
workflow. Reverified 201 tests, typecheck, lint, and both example builds.
Checked 35 local HTML references, preserved interactive scripts, and inspected
both updated pages in a real browser. Next at that checkpoint: T02.

**T02 complete (2026-10-22).** The mock host supplies an async fixed profile;
the mini app requests it after initialization and displays its name as text.
Bridge status and capability errors are separate. Seven example tests were
RED before implementation and GREEN afterward, bringing the suite to 208 tests
across 14 files. Typecheck, lint, and both example builds pass. Real-browser
verification confirms profile display across the pinned host/mini-app origins.
The explanation with code and a screenshot is `study/06-profile-demo.html`.
Next: T03.

**T02 follow-up complete (2026-10-22).** At the maintainer's request, the
profile display now checks the returned object's displayName at runtime
instead of asserting ProfileGetResult. Eleven additional tests cover invalid
result shapes and preserving an empty string. All 219 tests, typecheck, lint,
and both example builds pass. This is example-level field validation; T12's
generic response validation remains open. Next is still T03.

**T03 complete (2026-10-22).** Added and installed an async in-memory storage
provider with one Map per mini-app id. Eighteen new tests were RED before
implementation and GREEN afterward: 15 provider cases, two real host/client
integration cases over the memory transport, and one mock-host wiring/default
permission case. All 237 tests, typecheck, lint, and both example builds pass.
Repeat handshakes retain data; a fresh provider starts empty. Default grants
remain profile-only. The explanation is `study/07-memory-storage.html`.
Next: T04, show storage success and denial in the browser UI.

**T04 complete (2026-10-23).** Added host-selected profile-only and storage
configurations. Each selection closes the previous transport and replaces the
iframe; one host-held memory provider retains values across these connections.
The mini app exposes text-value CRUD, preserves bridge error codes, validates
read results without assertions, and prevents actions before initialization
or while another action is pending. Added 17 tests and strengthened four
existing cases; all 254 tests, typecheck, lint, and both example builds pass.
Actual browser checks confirm denial, successful set/get/delete, null after
deletion, and retained values after switching configurations. ADR 0009 records
the lifetime decision. The explanation is `study/08-storage-demo.html`.
Milestone A is complete. Next: T05, validate required manifest fields.

**T05 complete (2026-10-23).** Added internal parseManifestFields with local
ManifestError diagnostics. It validates JSON text, own required members,
manifestVersion, the exact id pattern, name length, SemVer syntax, and string
entry/protocolVersion/permissions fields without coercion. The maintainer
approved Unicode code-point counting for names; SPEC §7 was clarified first
and ADR 0010 records it. All 89 new tests, 343 tests total, typecheck, lint,
and both example builds pass. No platform API or runtime dependency was added.
The partial stage is not exported from the package or connected to the demo.
T06 must complete path containment and scope recognition before exposing the
full parser; T07 wires it into the example. The explanation is
`study/09-manifest-fields.html`. Next: T06.

**T06 complete (2026-10-23).** The maintainer approved unencoded relative file
paths; SPEC §7 and ADR 0011 record the rules before implementation. Added path
syntax, final-file-segment, and left-to-right root-containment checks, plus
recognized scopes derived from protocol capability method namespaces. The
public host API now exports parseManifest and ManifestError. Accepted entry
text and permission order/duplicates are preserved; empty permissions work.
No platform API or runtime dependency was added. Lexical checks perform no
file I/O; actual file existence and filesystem containment belong to the
embedder. All 107 new tests, 450 tests total, typecheck, lint, and both example
builds pass, including three real host/client cases proving parsing neither
grants permissions nor installs providers. The explanation is
`study/10-manifest-entry-scopes.html`. Next: T07, integrate the actual manifest
file into the example. The example still uses its typed literal at this point.

**T07 complete (2026-10-23).** The mock host imports the actual hello-miniapp
moonpool.json as Vite raw text, runs the real parseManifest before creating
a Portal, and replaces the duplicated typed literal. It selects a pinned
origin by validated id from a host-owned Map, rejects unmapped ids, and
resolves entry from that origin's root. Iframe insertion and receiver setup
remain synchronous in the same task. ADR 0012 records this development-only
loading choice; the pure kernel and its dependencies are unchanged.
All 14 new tests, 464 tests total, typecheck, lint, and both example builds
pass. Thirteen new tests failed before implementation; the remaining case
protects the existing receiver ordering. Actual browser checks confirm
initialization, profile, storage set/get, invalid-entry startup rejection,
and normal startup after restoring the original file byte-for-byte.
The explanation is `study/11-manifest-example.html`. Milestone B is complete.
Next: T08, reject batch arrays with a single -32600 response.

**T08 complete (2026-10-23).** Before starting T08, committed and pushed
T06/T07 to origin/master as 1f93b47, 6346f8d, and 340e69a. The host now
rejects every top-level array with one -32600 response carrying id null,
before id checks or initialization, without inspecting or dispatching
members. The shared response type/guard recognizes uncorrelated errors;
null request ids and null-id success responses remain invalid. The client
ignores null ids before pending lookup, preserving calls and timers. Ordinary
storage-value arrays and standalone notifications retain their behavior.
ADR 0013 records the standard response-id rule and Moonpool's existing
no-batch profile; no spec amendment or platform dependency was added.
All 34 new tests, 498 tests total, typecheck, lint, and both example builds
pass. The meaningful RED run had 20 failures and 14 passing regressions.
The explanation is `study/12-batch-rejection.html`. Next: T09, with its
method-format rejection and ordering decision still required. General
response validation and request-id reuse policy remain T12 and T10.

**T09 complete (2026-10-23).** Committed and pushed T08 as 257fdd5 and
4f9dd4b before starting T09. The maintainer approved the exact ASCII
lowerCamelCase grammar and -32600 rejection before params, initialization,
and permissions. Recorded SPEC §4.2 / §6.1 and accepted ADR 0014 before
implementation. The shared envelope guard now validates the whole method
string, including rejecting suffix newlines, without trimming or coercion.
The host reuses its fixed envelope-error path. Valid unknown names retain
the existing scope-before-lookup behavior; malformed initialize spellings
do not reset a session. No platform API, dependency, length limit, registry,
or capability was added. All 122 new tests, 620 total across 24 files,
typecheck, lint, and both example builds pass. The final meaningful RED run
had 83 failures and 39 passing regressions. The explanation is
`study/13-method-names.html`. Next: T10, whose id-policy decision is still
required. The T11 JSON-boundary decision is also still open.

**T10 complete (2026-10-23).** Committed and pushed T09 as 1ebd7e4 and
41a2f47 before starting T10. The maintainer approved document-scoped id
ordering, early consumption, -32600/id:null sequence errors, and the general
initialize boundary. Recorded SPEC §4.1 / §4.2 / §5.1 and ADR 0015 first.
Each host connection remembers its current document's largest consumed id.
Duplicate/backward requests do not execute or settle earlier client calls;
new ids are consumed even if later checks fail. General initialize requests
reset the floor before consuming their own id, including failed negotiation.
Malformed initialize shapes cannot reset it. Existing grants/storage remain.
All 25 new tests, 645 total across 25 files, typecheck, lint, and both example
builds pass. The RED run had 17 failures and eight passing regressions.
The explanation is `study/14-request-id-order.html`. Next: T11, whose whole
JSON validation decision is still required. The §11 document-epoch race is
not resolved by this document-local counter.

**T11 complete (2026-10-23).** T10 was committed and pushed as e4f7f89 and
45af7d1. The maintainer approved ADR 0016; SPEC §4.1 / §4.2 / §5.1 was updated
before implementation. The private host inspector reads own data descriptors,
validates the envelope outside params, and preserves original params for deep
validation after initialization/scope. Reject invalid envelopes with -32600,
non-JSON params with -32602 before lookup, and echo non-finite ids as null.
No getters/toJSON, coercion, input mutation, platform API, or dependency was
introduced. Valid JSON extras, shared/deep data, original values, and existing
sequence/permission behavior remain covered. All 59 new tests, 704 total across
26 files, typecheck, lint, and both example builds pass. The initial 58-case
RED run had 49 failures; an additional callable-root regression was verified
RED before its fix. Updated the old NaN response expectation to the approved
null-id rule. Actual browser initialization/profile/storage set/get pass.
The explanation is `study/15-inbound-json.html`. Next: T12, response validation
and correlation. Resource limits and arbitrary Proxy side effects remain outside
this contract, as documented in ADR 0008.

**T12 complete (2026-10-23).** Committed and pushed T11 as 1695e9a and
0585deb before starting T12. The shared response guard now accepts unknown,
validates the entire frame with isJsonValue, requires own response/outcome/error
members, and checks integer error codes. Client correlation still runs only
after validation; malformed replies cannot consume entries, clear timers, or
renew deadlines. Preserve falsy JSON results/data, valid extras, numeric
host diagnostic ids, null-id errors, unknown error codes, and wire error fields.
ADR 0017 records the implementation of existing JSON-RPC rules; SPEC is unchanged.
Wrote 116 new tests; the meaningful RED run had 39 failures and 77 passing
regressions. All 820 tests across 28 files, typecheck, lint, and both example
builds pass. Actual browser initialization, profile, and storage set/get pass.
The explanation is `study/16-response-validation.html`. Next: T13, with its
client-local failure policy decision still required. Method-specific result
schemas and the §11 document-epoch race remain separate.

**T13 complete (2026-10-23).** Committed and pushed T12 as 1465d03 and
f271a2f before T13. The maintainer approved ADR 0018's fixed local failure
mapping after the previous-behavior/problem/consequences explanation. Updated
SPEC §4.6 / §4.7 first. Client close now marks terminal state and drains calls
before once-only adapter cleanup, rejects later call/initialize with -32008,
and ignores retained callbacks. Both cleanup operations are attempted; the
first thrown value is rethrown after cleanup. Synchronous send failures clear
only that request's entry/timer and reject with fixed -32603 / {phase:"send"}.
Keep other requests usable, consume failed ids, never retry automatically,
and preserve earlier response/close outcomes. No transport API, dependency,
platform API, or new assertion was added. All 28 new tests and 848 total across
29 files, typecheck, lint, and both example builds pass. After correcting the
test harness, the committed T12 client had 24 failures and four passing
regressions; the implementation passes all 28. Actual browser initialization,
profile, and storage set/get pass. The explanation is
`study/17-client-local-failures.html`. Next: T14, whose dismissal contract
still requires approval. Peer-disconnect signaling remains a §11 question.

**T14 complete (2026-10-23).** Committed and pushed T13 as a7179db and
cae510b. The maintainer approved the ADR 0019 acceptance contract; SPEC §6.2
was updated before dependent implementation. portal.close validates optional
string reason and rejects unknown fields before handler lookup. The optional
per-connect onCloseRequested hook needs no scope; absence returns -32001.
Submit one result:{} response before invoking/awaiting the hook internally;
subsequent failure is reported only on the host. Acceptance does not guarantee
receipt or completed UI teardown. The example adds a handshake-gated close
button and an idempotent, captured-frame handler that cannot dismiss a
replacement Portal. Reason is rendered as text and storage survives reopening.
Added 47 tests and strengthened two existing handshake/UI checks. Host RED:
20 failures / 14 passes; UI RED included a missing module and seven failing
behavior checks. All 895 tests across 32 files, typecheck, lint, and both
example builds pass. Actual browser close, restart, store, close, restart,
read retained data, and close pass. The explanation is
`study/18-portal-close.html`. Milestone C is complete. Next: T15, typed host
notification sending. SPEC §9.4 / §9.5 / §9.6 are covered; §11 peer-disconnect
and document-epoch questions remain separate.

**T15 complete (2026-10-23).** Committed and pushed T14 as 6166a4e,
d1d13b0, and 5cd4d93. Host.connect now returns a HostConnection bound to its
transport, exposing async notifyLifecycle and notifyEnvironmentChanged.
Shared protocol types describe the two event payloads and discriminated wire
frames. The sender validates local arguments without assertions/conversion,
snapshots declared fields, and sends id-free frames without timers, request
correlation, or a reply listener. Invalid local arguments reject with fixed
TypeError; send exceptions reject locally without retry. Configuration,
initialization, grants, id floors, and other pending calls remain unchanged.
ADR 0020 records this send-only API; SPEC is unchanged. All 45 new tests failed
before implementation and now pass. All 940 tests across 33 files, typecheck,
lint, and both example builds pass. Real host/client memory-transport tests
prove notifications cannot settle or extend an existing request. No example
UI/subscriber or platform integration was added. The explanation is
`study/19-host-notifications.html`. Next: T16, subscriber delivery; embedder
state/timing/lifetime ownership and §11 limitations remain explicit.

**T16 complete (2026-10-23).** Committed and pushed T15 as 5aebae6 and
de26d0e. Added client.onNotification with independent local registrations and
idempotent unsubscribe. Preserve the response path first; validate known,
id-free notifications and project declared fields into fresh per-listener
copies. Ignore unknown/malformed messages without replies. Snapshot registration
order, skip removed listeners, defer additions to the next event, and clear
subscribers before adapter cleanup on close. Synchronous throws and Promise
rejections are reported locally through the existing queued-rethrow pattern
without blocking other callbacks or request correlation. ADR 0021 records
local API semantics; SPEC is unchanged. All 55 new tests failed before
implementation and now pass. All 995 tests across 34 files, typecheck, lint,
and both example builds pass. Updated one typed example mock for the new API;
no example runtime UI or OS-event wiring was added. The explanation is
`study/20-client-notifications.html`. Next: T17, browser navigation investigation.
Notifications have no replay; registration before initialize helps with early
events, but receipt before receiver/subscriber installation is not guaranteed.

**T17 complete (2026-10-23).** Committed and pushed T16 as dadbd28 and
bcd9920. Added a separate manual three-origin fixture using the real kernel
and transport, with HMR/watch/dependency discovery disabled during measurement.
Recorded Chrome 155 observations for internal navigation/reload/hash, foreign
calls/return, silent pre-load excursions, a load-close candidate, and CSP
location/form/redirect/bounce prevention. The current bridge rejects foreign
calls but remains usable after return; load-close both breaks internal navigation
and misses pre-load calls. CSP prevented the tested foreign loads while keeping
allowed reloads usable. docs/navigation-investigation.md links the raw evidence.
ADR 0022 initially proposed a single-Portal CSP development profile; that draft
was never approved. The 2026-10-26 replacement was subsequently approved and
implemented in T18 with explicit kernel/provider ownership. The investigation
itself changed neither SPEC nor production code; see the T18 checkpoint above.
Existing 995 tests, typecheck, lint, both builds, and the lab's separate typecheck
pass. Manual observations are not counted as automated tests or cross-engine
certification. The explanation is `study/21-navigation-investigation.html`.
Next: decide the T18 contract, then implement it. This task touches SPEC §9.2.

### Milestone A: demonstrate useful calls

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T01 | Align stale comments and the study entry point with the existing implementation and current workflow. | Storage guard comments describe recursive JSON validation; the client no longer claims to be a skeleton; study status identifies the new plan and preserves earlier lessons. | Baseline |
| T02 | Supply a constant profile provider and display `profile.get` in the mini app. | A successful handshake leads to a visible display name; provider content is rendered as text; failures show their bridge code. | T01 |
| T03 | Add the mock host's in-memory storage provider. | A nested Map partitions values by app id; get/set/delete and absent-key behavior work; tests prove two app ids cannot share the same key's value. | T01 |
| T04 | Expose storage success and permission denial in the example. | The default profile-only connection visibly rejects storage with -32000; a host-selected storage-enabled configuration demonstrates set/get/delete. A configuration change creates a fresh connection rather than changing grants through mini-app input. | T02, T03 |

The Map is a development provider, not durable storage across host reloads.
The two configurations are a host-controlled demonstration, not runtime
consent or a new permission protocol.

### Milestone B: validate mini-app configuration

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T05 | Parse and validate required manifest fields in the pure host package. | Valid manifests succeed; malformed JSON, missing fields, wrong types, unsupported manifestVersion, invalid id/name/version, and malformed permissions fail before a bridge is created. No platform APIs or runtime dependencies are introduced. | T01 |
| T06 | Validate manifest entry paths and known scopes. | Absolute paths and package-root escapes are rejected; unknown scopes fail explicitly; empty permissions remain valid. Scope names follow protocol capability namespaces, with no independent permission registry. | T05 |
| T07 | Wire the example's actual `moonpool.json` through the parser. | The host uses host-owned manifest input instead of a duplicated typed literal; invalid configuration prevents Portal startup; the receiver is still attached before the mini app can handshake. | T06 |

Entry validation must agree with the example loader's interpretation. Resolve
any genuinely ambiguous path or version policy through the decision process
below, rather than inventing a restrictive private manifest format.

### Milestone C: finish request and connection behavior

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T08 | Reject top-level batch arrays with -32600. | Empty and nonempty arrays receive the required single invalid-request reply and execute no methods. Null response ids can be represented without allowing a valid client request to use null. Clients ignore uncorrelated error responses. | T01 |
| T09 | Validate the `namespace.action` method format. | Valid lowerCamelCase names reach existing dispatch; malformed names follow the approved rejection contract. Unknown valid names retain existing permission and method-lookup behavior. | T01; method-format decision approved in ADR 0014 |
| T10 | Enforce the approved request-id policy. | Tests cover reuse and backward ids, initialization retries, and the fresh sequence after repeat handshake. Document-scoped correlation resets without clearing grants or storage. | T08; id decision |
| T11 | Validate JSON at the inbound request boundary. | Structured-clone values outside JSON cannot reach providers; tests preserve existing rejection precedence and allowed extra JSON envelope members. No input is coerced to make it valid. | T09; JSON-boundary decision |
| T12 | Tighten response validation and correlation tests. | Malformed result/error shapes cannot settle a request; valid falsy results, sanitized errors, unknown ids, and late responses retain their specified behavior. | T08 |
| T13 | Make client closure terminal and clean up failed sends. | Requests after close cannot send or create pending timers; repeated close is harmless; a synchronous send failure cannot leave a pending entry or timer. Error semantics follow an approved contract where the current spec is silent. | T01; applicable decisions |
| T14 | Implement `portal.close` through an asynchronous embedder hook. | Params are validated, no scope is required, the dismissal request reaches the host UI, and response/teardown ordering is verified under the approved contract. Provider failures do not expose host details. | T09, T13; close decision |

### Milestone D: support host events and browser containment

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T15 | Add typed host notification sending for the two specified events. | `portal.lifecycle` and `portal.environmentChanged` produce id-free frames with the specified params; sending does not register a request or timeout. | T01 |
| T16 | Deliver host notifications through the client. | Subscribers receive known events, can unsubscribe, and are detached on close; unknown methods are tolerated; notifications never settle a pending request. A subscriber failure cannot disable request correlation. | T13, T15 |
| T17 | Investigate iframe navigation containment in a real browser. | Record what the host can observe for same-origin reload, navigation to another origin, and returning to the original origin. Identify whether SPEC §9.2 can be satisfied with the current platform boundary. Produce an ADR proposal if a design decision or spec change is necessary. | Baseline |
| T18 | Completed 2026-10-26: approved browser containment. | Per-Portal CSP wrappers, host-bound realm/provider adapters and terminal cleanup preserve independent Portals and retained app storage. Same-origin reload follows §5.1; revoked instances cannot revive. No DOM enters the pure kernel. Verification: 1077 tests and recorded Chrome 156 dev/preview cases. | T17; accepted ADR 0022 |

T17 is an early investigation and may run before Milestone A is complete.
Pinned targetOrigin and dropping foreign-origin messages already help protect
messages, but neither alone proves that the bridge is torn down after
navigation. Do not weaken §9.2 to fit an iframe limitation.

### Milestone E: verify and document completion

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T19 | Completed 2026-10-26: SPEC §4.4 error-code matrix. | All 14 client mappings and current producer paths have meaningful tests. Added 54 cases and docs/error-code-matrix.md; 1131 total tests pass. Defined codes without producers use controlled peer frames; runtime/SPEC/policies unchanged. | T08–T16 |
| T20 | Verify browser integration and security scenarios. | Record actual browser results for handshake, profile, storage success/denial, reload, close, notifications, foreign-origin/source rejection, and navigation containment. Run all tests, typecheck, lint, and both example builds. | T04, T07, T14, T16, T18, T19 |
| T21 | Reconcile the public roadmap and final conformance record. | README, CHANGELOG, HANDOFF, study status, and necessary ADRs match the verified behavior. Map each v0.1 requirement to evidence and record remaining approved limitations. Declare completion only when the required checks and specification decisions are resolved. | T20 |

Real-browser verification does not by itself require adopting a new automated
browser runner. If one is introduced later, revisit HANDOFF's existing
`queueMicrotask` to `reportError` transition requirement and record its ADR.

## Decisions needed before affected implementation

These are planning gates, not approved specification changes. Continue
independent tasks while a dependent task awaits the maintainer's decision.

T09's method-format decision, T10's id policy, and T11's inbound JSON policy
are resolved in SPEC and ADRs 0014–0016; T13 and T14 are resolved in
ADRs 0018–0019.
Do not ask for those approvals again. The remaining gates below are separate.

- **Client local failures (T13): resolved on 2026-10-23.** The maintainer
  approved terminal local closure, post-close -32008 Promise rejection,
  once-only cleanup, and per-request send failure cleanup with fixed -32603 /
  {phase:"send"}. SPEC §4.6 / §4.7 and ADR 0018 record ordering and diagnostics.
  No automatic retry or claim about remote host health. Do not ask again.
- **Portal dismissal (T14): resolved on 2026-10-23.** The maintainer approved
  optional string reason, -32001 without a per-connect async handler, and
  success as acceptance submitted before invoking dismissal. Subsequent hook
  failures are reported only on the host; no delivery/completion guarantee.
  SPEC §6.2 and ADR 0019 record the contract. Do not ask again.
- **Browser navigation (T17–T18): accepted and implemented.** ADR 0022 was
  explicitly approved on 2026-10-26 and published as 0397b70. SPEC §8.1.1 and
  T18 implement independent served wrappers, local kernels/APIs, retained
  outer providers and terminal disposal. Verification records 1077 tests and
  selected Chrome 156 dev/preview cases. Do not ask approval again or claim
  unrestricted iframe conformance from origin filtering/load events.

Do not choose numeric payload/depth limits during this work: the spec defines
none. Any such policy needs a separate proposal. The document-epoch race,
peer-disconnect signaling, runtime consent, and rate-limit policy remain the
existing §11 open questions.

## Security and completion rules

T03, T04, T06, T09, T11, T14, and T17–T20 touch SPEC §9 and must be flagged when explained.
Every other task must still preserve the existing permission, identity, and
credential boundaries. Render provider data as text in the example.

Maintain the pure kernel and swappable Transport contract, async capability
calls, exact version negotiation, namespace-based scopes, host-selected app
identity, pinned distinct development origins, and zero new kernel runtime
dependencies. Keep native transports/cores and distribution outside v0.1.

The first implementation slice is T01 → T02 → T03 → T04. Full v0.1 completion
requires the remaining milestones and resolved mandatory conformance gates;
Milestone A alone is a useful demonstration, not a release claim.
