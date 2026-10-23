# Browser v0.1 implementation plan

Date: 2026-10-22
Last updated: 2026-10-23
Status: In progress. T01–T10 complete; next is T11.
Normative source: `SPEC.md`. This plan does not amend the protocol.

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
| T18 | Implement the approved browser containment behavior. | Off-origin navigation tears down the Portal bridge; returning to the allowed origin does not silently revive the old connection; same-origin reload still follows §5.1. Listeners are removed. No DOM access enters the pure kernel. | T17; containment decision |

T17 is an early investigation and may run before Milestone A is complete.
Pinned targetOrigin and dropping foreign-origin messages already help protect
messages, but neither alone proves that the bridge is torn down after
navigation. Do not weaken §9.2 to fit an iframe limitation.

### Milestone E: verify and document completion

| ID | Task | Completion evidence | Depends on |
| --- | --- | --- | --- |
| T19 | Complete the SPEC §4.4 error-code matrix. | All 14 codes have meaningful tests for client error mapping, with host/transport behavior tested where a producer is specified. Reserved codes are tested using controlled peer frames; no rate limiter, consent UI, or string transport is added just to manufacture them. | T08–T16 |
| T20 | Verify browser integration and security scenarios. | Record actual browser results for handshake, profile, storage success/denial, reload, close, notifications, foreign-origin/source rejection, and navigation containment. Run all tests, typecheck, lint, and both example builds. | T04, T07, T14, T16, T18, T19 |
| T21 | Reconcile the public roadmap and final conformance record. | README, CHANGELOG, HANDOFF, study status, and necessary ADRs match the verified behavior. Map each v0.1 requirement to evidence and record remaining approved limitations. Declare completion only when the required checks and specification decisions are resolved. | T20 |

Real-browser verification does not by itself require adopting a new automated
browser runner. If one is introduced later, revisit HANDOFF's existing
`queueMicrotask` to `reportError` transition requirement and record its ADR.

## Decisions needed before affected implementation

These are planning gates, not approved specification changes. Continue
independent tasks while a dependent task awaits the maintainer's decision.

T09's method-format decision and T10's id policy are resolved in SPEC and
ADRs 0014–0015. Do not ask for those approvals again; the remaining gates
below are separate.

- **JSON boundary validation (T11).** Specify rejection codes and ordering for
  non-JSON envelope content before tightening the whole-frame guard. Preserve
  the approved id-sequence and method-syntax precedence,
  scope-before-method-param validation,
  and the existing permission behavior for unknown methods.
- **Client local failures (T13).** Confirm the post-close -32008 behavior and
  define synchronous transport-send failure mapping without inventing a
  claim about remote host health.
- **Portal dismissal (T14).** §6.2 lists `{ reason? }` but does not define its
  type, missing-hook behavior, or completion/teardown order. Proposed starting
  point: an optional string and a success reply before destroying the frame;
  approve a precise contract before implementing it.
- **Browser navigation (T17–T18).** Establish a feasible observation and
  teardown mechanism. If strict §9.2 behavior cannot be achieved, propose a
  spec change and wait for approval rather than claiming conformance.

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
