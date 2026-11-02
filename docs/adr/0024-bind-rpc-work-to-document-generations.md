# 24. Bind RPC work to explicit document generations

Date: 2026-11-02
Status: Accepted design direction — selected by the maintainer on 2026-11-02.
Wire/bootstrap/lifecycle details and implementation remain gated below.

## Context

SPEC §11 records a known 0.1 limit: request ids restart in a new document, so a
late result can satisfy a different document's reused id. T25/T26 distinguish
origin, frame, document and reply-channel lifetimes. The comparative review
found randomized callback ids and navigation cleanup, not one universal epoch
contract. Random ids can solve response matching; explicit generations also
provide a shared owner for notifications, retained callbacks and retirement.

The maintainer selected document generations after discussing these tradeoffs.
This decides the design direction, not a claim that the current kernel already
implements it or approval of arbitrary field/version/error choices.

## Decision

1. Keep JSON-RPC 2.0 and the existing increasing positive request id. Correlate
   work by its document generation plus id, within the existing Portal binding.
   A page URL/name is not a generation: A→B→A must not reactivate the first A's
   retired connection. Reentry/restoration needs an explicit fresh-binding rule.
2. Establish generation ownership through validated initialization/bootstrap.
   Protect initialization replies as well as later results, errors and
   notifications. A sender-provided string alone is not document authentication
   and cannot select app identity, grants, provider partition or another Portal.
3. Capture the admitted generation when accepting work. After retirement, that
   work must not dispatch into or reply as a replacement generation. Never stamp
   an old result with whichever generation is current when the provider finishes.
4. Retire old document-bound callbacks/connections on the agreed transition;
   retain app storage, existing connection grants/consent and other origin/user
   state under §5.1. Retirement does not roll back already-dispatched provider
   effects or automatically cancel native operations.
5. Keep the pure kernel free of platform APIs and retain the three-method
   Transport boundary. Native origin/frame/instance checks and document-scoped
   reply primitives remain necessary; a generation label does not replace them.

## Consequences and implementation gate

The benefit is an explicit, cross-platform lifetime contract rather than relying
only on callback-id noncollision. The cost is bootstrap state, message metadata,
validation order, pending-call semantics and version migration. Add only the
required lifetime contract; no general task/stream/plugin framework is implied.

T27–T29 still determine trusted ownership, channel/bootstrap and codec context.
T30 must specify generation creation/nonreuse, authoritative binding, first
initialization correlation, retry/reentry, metadata shape/validation precedence,
stale-frame disposition and protocol compatibility. T31 must specify surviving
pending promises and close/renderer-loss behavior. Their unresolved details are
not silently chosen here. This records acceptance of the direction, not completion
of T30 or permission to skip those dependency gates.

T32 implements the approved contract with failing tests first; T33 handles the
approved terminal/pending-call behavior. The shipped 0.1 profile and public APIs
remain unchanged until that contract is written. This decision concerns SPEC
§5.1, §9 and §11; no new credential crosses the bridge.
Existing dismissal acceptance/Portal ownership rules are retained; any interaction
with document retirement must be resolved explicitly in T31, not inferred as
cancellation of an already-accepted dismissal.

The [isolated kernel regression probe](../../experiments/document-generation-contract/README.md)
uses the real current Host/Client to pin the response-id collision with controls.
Its three safety assertions are intentionally red under 0.1, outside the ordinary
passing suite. They are not replaced by a duplicate dispatcher or a fabricated
native conformance claim.
