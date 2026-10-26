# Browser Portal ownership proposal

Date: 2026-10-26
Status: Accepted design companion to ADR 0022 — approved on 2026-10-26; T18 implementation follows.

Implementation checkpoint: T18 is implemented under SPEC §8.1.1. The original
proposal text below records its design requirements; see
[verification](browser-containment-verification.md) for the 1077-test baseline,
integrated Chrome 156 observations, final built-preview checks and limits.

## Previous behavior, problem, proposed result

The current iframe transport rejects foreign messages but leaves a connection
usable after an allowed-origin return. Closing on every load breaks ordinary
reloads. A single host-document CSP allowlist for A/B admits both destinations
without expressing which Portal owns which one. The first, unapproved ADR 0022
proposal avoided that problem by limiting a browser host document to one Portal.

The replacement gives each Portal a trusted served wrapper with its own CSP
and kernel, preserving multiple app origins in one development page. A's
violation revokes A; B keeps its connection, grants and data. Root-owned storage
also survives A's explicit recreation. That last guarantee and the host-only
realm adapters below are proposed integration requirements, not measured results.

## Execution contexts and authority

```text
Outer host document (host origin)
  registry: instance -> manifest / pinned origin / grants / bound Document
  retained profile and app-partitioned storage providers
  |
  +-- trusted wrapper A (host origin; own JavaScript realm)
  |     CSP frame-src: app A origin
  |     local HostConfig + host kernel + HostConnection + transport
  |     local async provider facades -> bound outer provider gateway
  |     +-- guest A (app A origin; client)
  |
  +-- trusted wrapper B (host origin; another JavaScript realm)
        CSP frame-src: app B origin
        local HostConfig + host kernel + HostConnection + transport
        local async provider facades -> bound outer provider gateway
        +-- guest B (app B origin; client)
```

Same origin permits trusted host code to cooperate; it does not merge their
Object.prototype values. The existing validator compares with its own realm's
prototype. The experiment rejected an outer-created environment object but
delivered an identical wrapper-created object. Keep that check intact.

Outer code receives a narrow async control facade, not the raw wrapper-owned
HostConnection. It validates caller data in the outer realm, produces a public
JSON snapshot, then passes text. The wrapper parses/validates locally and calls
its own sender with local objects. HostConfig metadata follows the same rule;
capability functions are installed locally, not serialized as configuration.
Provider values travel through the same explicit boundary in either direction.
No adapter signature here is a new public SDK API or guest JSON-RPC method.

The proposed codec contract is validate -> snapshot -> encode -> parse ->
validate, using the existing JSON value model. Snapshot through data descriptors;
do not invoke getters/toJSON, discard invalid members, coerce Date/non-finite
values, or weaken prototype rules. Reject invalid host input locally before
sending/invoking a provider. Snapshot tests must preserve nested JSON, null,
falsy values and keys such as __proto__, without sharing mutable references.
Malformed guest messages still reach the kernel's existing staged validation
unchanged; the codec is not an inbound-transport sanitizer.

Bootstrap/control/provider gateways are host-only and instance-bound, not a
generic top-window RPC listener. Root owns the actual iframe, expected URL,
generation and bound Document; it checks live binding before each operation.
A same-URL new wrapper Document is rejected. Retired handles cannot operate
on a replacement. Guest-supplied ids, grants, URL claims or forged bootstrap
messages cannot bind or redirect a gateway. Same-origin host code is trusted:
Document checks do not isolate a compromised wrapper from the host.

## Storage identity and lifetime

The retained outer provider uses the existing ADR 0003 contract. The wrapper
kernel supplies config.manifest.id separately from the validated key. Its
facade rejects an id inconsistent with its immutable binding; the outer
gateway independently chooses that binding's host-held app id. There is no
guest-selectable miniAppId field or unbound provider reference.

For illustration, the existing provider's partition is:

```ts
const apps = new Map<string, Map<string, StorageSetValue>>();
// Host-selected app id -> this app's keys and values.
```

Two A instances use the same app partition, even if their granted scopes differ;
a denied instance still cannot invoke storage. B uses a different partition.
Existing behavior defines no new transaction/atomicity guarantees for concurrent
writes. Bridge ids, initialization and disposal belong to individual connections.
Browser-native localStorage/IndexedDB retain their engine-managed origin rules;
this host provider handles storage.* and is not a substitute for those rules.

| Event | Connection/config | Host-managed app data |
| --- | --- | --- |
| Guest A same-origin reload | Same wrapper; repeat initialize per §5.1; preserve grants | Retained |
| Close or CSP-revoke A | Terminally disable that instance; B stays live | Retained; no delete-on-close |
| Host explicitly creates a new A | Fresh wrapper/kernel/binding; host selects grants | Reuse A's partition |
| Same URL wrapper reload without host restart | Reject replacement Document | Retained; no automatic bridge recovery |
| Another instance of the same app | Independent connection and scope checks | Shared app partition |
| Outer host/provider recreated | Fresh host session/provider | Memory provider starts empty; durable storage not promised |

Every provider facade remains async. Reject new calls through an inactive
binding before accessing the provider. Preserve existing sanitized guest error
mapping and host-local diagnostics while the connection is live. After an
await, recheck the instance before delivery. Disposing a Portal cannot undo
an already-dispatched write/delete; its completion cannot send to a new instance.

## Disposal and bounded support

Register CSP enforcement handling before creating the guest. Treat only a
browser-generated, enforcing frame-src violation in that wrapper as the
revocation trigger; a synthetic event or report-only policy is insufficient.
Also revoke on explicit close or unauthorized wrapper replacement. First mark
inactive and invalidate gateways; then close transport/listeners, remove guest
and outer wrapper, and release registry/control references. Perform all cleanup
attempts even if one throws. Dropped late responses cannot revive the instance;
calls to retired host controls reject locally without new wire error codes.
Other Portals remain active. Remote clients retain existing timeout behavior.
In-flight callbacks may retain their old realm until they settle; removing DOM
and registry references is not a guarantee of immediate garbage collection.

Normal fetched wrapper documents have response policy containers; srcdoc inherits
its parent's policy. Use served documents as measured, with server-selected
headers and fixed app-origin mapping. The basis is the
[HTML policy-container model](https://html.spec.whatwg.org/multipage/browsers.html#policy-containers)
and [CSP frame-src checks](https://www.w3.org/TR/CSP3/#directive-frame-src).
These standards support the mechanism, not an untested conformance claim.

The lab measured independent revocation, source/Document binding, repeat
handshake and late-send suppression in Chrome 156. It kept closed wrappers
for inspection and used wrapper-local Maps. It did not implement this retained
provider gateway, async control facade, strict codec or full outer-frame cleanup.
Do not treat that evidence as proof of those requirements, memory recovery,
other engines, all URL schemes/history/BFCache, or an outer-kernel relay.

## Acceptance checks after approval, before shipping T18

1. Derive failing tests from the approved SPEC edit. Cover source/origin checks,
   isolated A/B disposal, terminal send/receive guards, repeated close and
   cleanup failures without changing Transport or importing DOM into the kernel.
2. Test the source-realm codec and real wrapper control/provider boundary with
   nested valid values and invalid Date, undefined, non-finite numbers,
   accessors, toJSON and cycles. Rejected caller input runs neither accessors
   nor a provider; invalid provider results never become guest success payloads.
3. Test host-owned identity: same key in A/B differs; two A instances share
   data; scope denial wins; forged ids and retired handles cannot reach storage.
4. Measure A storage across inner reload, explicit close/recreate and CSP
   revoke/recreate with one retained outer provider. Reject unexpected wrapper
   reload; preserve B's pending request/grants/data and suppress late A replies.
5. Verify both frame removals, listener/control invalidation and exception-safe
   cleanup. Keep bookkeeping distinct from heap/GC/performance measurements.
6. Re-run location/form/redirect/silent-bounce and same-origin navigation with
   the integrated topology. Record exact engines and supported cases; keep
   unsupported behavior and SPEC §11 epoch/disconnect limits explicit.

The maintainer approved this browser-development contract and its tests-first
integration on 2026-10-26. This does not authorize native cores, production HTTPS hosting,
new guest RPCs, a different JSON validator, or resolution of SPEC §11.
