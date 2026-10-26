# T18 browser containment implementation and verification

Date: 2026-10-26
Contract: SPEC §8.1.1 / §9.2, accepted ADR 0022.
Status: Implemented and verified for the recorded browser-development configuration.

## Implementation

The outer browser host owns the registry and one retained storage provider.
Each served, trusted wrapper owns its kernel/configuration/notification sender,
local provider facades, guest iframe and iframe transport. The wrapper has a
host-selected response CSP allowing only its pinned guest origin. A different
Portal may have a different origin in the same outer document.

The registry checks actual window, expected URL and bound Document for bootstrap
and subsequent operations. Guest claims and query parameters cannot select the
owning id or grants. Replacing a wrapper Document, including at the same URL,
revokes the old instance rather than silently rebinding it. Allowed guest
reloads retain the wrapper and use the existing repeat handshake.

The source-realm codec validates first, snapshots data descriptors into detached
records/arrays without inherited toJSON, encodes text, and validates after parsing
in the receiving realm. It is used only for host controls/provider data. Incoming
guest frames still pass unchanged through the kernel's staged validation. The
wrapper checks its provider id, and the outer gateway independently selects the
host-held manifest id. Closing a Portal leaves the app's retained storage intact.

Disposal invalidates handles before cleanup, attempts all cleanup steps, removes
both frames/listeners and owned references, and blocks late dispatch/transmission.
The iframe transport is now terminal and idempotent even if native cleanup fails.
Private wrapper provider facades settle obsolete work without forwarding its
result or turning ordinary revocation into an uncaught provider failure. This
does not cancel or undo already-dispatched writes/deletes.

Key sources: [registry](../examples/mock-host/src/browser-portal.ts),
[wrapper](../examples/mock-host/src/portal-wrapper.ts),
[codec](../examples/mock-host/src/json-boundary.ts),
[response policy](../examples/mock-host/src/browser-policy.ts),
[transport](../packages/transport-iframe/src/index.ts).

## Automated verification

1077 tests across 38 files pass, up from 995 (+82). Root typecheck, navigation-lab
typecheck, Biome and both multipage example builds pass. No dependency, pure
kernel API, Transport interface, production origin, or new guest RPC was added.

Assertions preceded the corresponding implementation. Five new transport tests
failed against the previous behavior; new module suites initially failed to load
their not-yet-created implementations. Additional insertion-failure and inherited
optional-getter regressions failed before their fixes. Existing example wiring
tests now start the actual wrapper/kernel with an in-memory transport; they
continue checking manifest admission, grants, storage and dismissal semantics.
They do not pretend that happy-dom enforces CSP or reproduces native frame realms.

Tests cover terminal send/receive/subscription guards, reentrant/throwing cleanup,
strict snapshots, invalid/getter/toJSON/cyclic data, dangerous-looking JSON keys,
bootstrap/Document/source binding, storage ownership/sharing/persistence, scope
denial, obsolete handles, delayed results, notifications, close acknowledgement,
startup failure, and trusted/enforcing frame-src event classification.

## Browser observations

In-app browser reporting Chrome/156.0.0.0, Node 22.19.0, pnpm 11.1.3, Vite 8.2.2.
Outer host/wrappers: localhost:5173; app A: :5174; app B: :5175; foreign target:
127.0.0.1:5174. Each origin is fixed; the two guest servers share reference app
source but have different host-owned manifests/identities. No changes were made
to source/server configuration inside the retained development sequence.

| Observation | Recorded result | Evidence |
| --- | --- | --- |
| Concurrent real initialization | A/B initialize on different origins; two wrappers and two guests. | [01](../examples/mock-host/containment-results/01-initial.txt) |
| Different apps, same key | A/B retain different nested values, including null/false/0. | [02](../examples/mock-host/containment-results/02-different-app-partitions.txt) |
| Same app twice | Extra A reads A's existing partition; three wrappers/three guests before closing the extra instance. | [03](../examples/mock-host/containment-results/03-same-app-shared-data.txt) |
| Guest reload | Repeat initialize succeeds and A storage survives; B stays live. | [04](../examples/mock-host/containment-results/04-inner-reload-retains-data.txt) |
| Internal page/hash/notification/bootstrap | Internal navigation works, B receives outer-host environment changes through local wrapper objects, guest host-API access is blocked by SOP. | [05](../examples/mock-host/containment-results/05-navigation-notification-bootstrap.txt) |
| Wrong source and A-to-B navigation | Correct-origin/id forged outer reply does not finish B id 4; A's own policy revokes A, leaving B pending. | [06](../examples/mock-host/containment-results/06-b-request-held.txt), [07](../examples/mock-host/containment-results/07-a-blocked-b-still-pending.txt) |
| B completion after A revocation | B completes normally and reads its prior data; retired A control rejects; one wrapper/guest remains. | [08](../examples/mock-host/containment-results/08-b-completes-after-a-revocation.txt) |
| Storage beyond wrapper lifetime | Fresh A reads prior A data after CSP revocation and explicit host close/recreation. | [09](../examples/mock-host/containment-results/09-recreate-after-csp-retains-a-data.txt), [10](../examples/mock-host/containment-results/10-recreate-after-host-close-retains-data.txt) |
| Unauthorized wrapper replacement | Both same-URL reload and a different wrapper-policy URL revoke A and leave B live. | [11](../examples/mock-host/containment-results/11-same-url-wrapper-reload-rejected.txt), [12](../examples/mock-host/containment-results/12-wrapper-policy-replacement-rejected.txt) |
| Foreign direct/form/redirect/bounce | Each attempt triggers A's native enforced policy path and removes A; B remains. | [13](../examples/mock-host/containment-results/13-foreign-navigation.txt), [14](../examples/mock-host/containment-results/14-foreign-form.txt), [15](../examples/mock-host/containment-results/15-foreign-redirect.txt), [16](../examples/mock-host/containment-results/16-silent-bounce.txt) |
| Late provider completion | A's held provider finishes after revocation; A stays absent and B still completes a profile. Send suppression is additionally asserted directly in unit tests. | [17](../examples/mock-host/containment-results/17-a-provider-pending.txt), [18](../examples/mock-host/containment-results/18-late-a-completion-b-still-live.txt) |
| B's narrower grants | Storage remains -32000 before/after A revocation; profile still succeeds. | [19](../examples/mock-host/containment-results/19-b-profile-only-before-a-revocation.txt), [20](../examples/mock-host/containment-results/20-b-grants-preserved-after-a-revocation.txt) |
| Outer host reload | New memory provider starts empty for both apps. | [21](../examples/mock-host/containment-results/21-host-reload-resets-memory-provider.txt) |
| Normal example | The ordinary mock host initializes both app origins and serves their profiles. | [22](../examples/mock-host/containment-results/22-normal-example-two-origins.txt) |
| Final built preview | Final build repeats retained storage/notification and independent A revocation with B working. | [23](../examples/mock-host/containment-results/23-built-preview-storage-notification.txt), [24](../examples/mock-host/containment-results/24-built-preview-independent-revocation.txt) |

[Captured response headers](../examples/mock-host/containment-results/response-policies.txt)
verify host-only root policy, separate A/B policies, and frame-src 'none' for an
unknown wrapper app. The same selector middleware runs for development/preview.

The nested iframe input backend could read but not click the guest buttons.
The manual fixture therefore adds root controls that send origin/source-checked
diagnostic commands to its own probe. Those commands invoke the same real client
calls/navigation handlers; they are not SDK methods and do not relax the client's
immediate-parent peer check. The forged outer response was still rejected.
This instrumentation is confined to the separate containment check/probe pages.

Snapshots 01–20 are one development sequence, 21 is its explicit host reload,
22 the normal example, and 23–24 a fresh final built preview. A stale capture
helper initially pointed at a closed earlier tab during preview; it was rebound
and the already-completed storage/notification state was captured without
replaying those actions. Snapshot 09's footprint label is a previous inspection,
not a live count; use explicit counts in 01/03/07/08/10 onward. Rendered snapshot
label whitespace/final newlines were normalized without changing event values.

## Limits and diagnostics

This records selected cases in one engine, not all browsers, schemes, history,
BFCache, malicious host code or performance behavior. Frame removal and listener
bookkeeping are not heap/GC proof; in-flight callbacks can retain a retired realm
until settlement. The document-epoch and peer-disconnect questions remain §11.
Production HTTPS hosting and native cores are outside this development contract.

Retained [development](../examples/mock-host/containment-results/browser-errors.json)
and [preview](../examples/mock-host/containment-results/built-preview-errors.json)
tool logs contain a generic MutationObserver.observe error. Temporary error
listeners in the outer document, both wrappers and both guests captured no
corresponding page ErrorEvent ([diagnostic](../examples/mock-host/containment-results/observer-diagnostic.json)).
Its source was not identified; no clean-console or causal attribution claim is
made. The temporary listeners were removed. All functional observations above
remain separate from that diagnostic. Vite also emits an advisory about future
native config-loader support for extensionless imports; the pinned build passes.

The last local fixes after the main development sequence cover insertion-failure
cleanup and inherited optional-field reads; the final built-preview smoke check
uses those fixes. Test counts exclude manual observations. All created tabs and
development/preview servers were stopped after verification.
