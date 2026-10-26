# T20 browser integration and security verification

Date: 2026-10-26
Status: Complete for the recorded browser-development configuration.
Normative source: SPEC §3–§6, §8.1.1 and §9; accepted ADR 0022.

## Configuration and method

Measured in the in-app browser reporting Chrome/156.0.0.0 on macOS, with
Node 22.19.0, pnpm 11.1.3 and Vite 8.2.2. The contained development/preview
composition uses localhost:5173 for host/trusted wrappers, :5174 for app A,
and :5175 for B. The separate native transport lab uses 127.0.0.1 ports
5273/5274/5275. Ports are fixed and fail if occupied.

Expected checks were written before measurement. No new browser runner,
dependency, protocol policy or kernel implementation was introduced. The
existing manual probe now instantiates the actual createStorageDemo and
createCloseDemo components, using the real client, host, registry, wrappers,
realm codec and memory provider. Root controls invoke those component buttons
through origin/source-checked fixture commands. They are not guest SDK RPCs
and do not relax the bridge's immediate-parent peer binding.

Records are scoped rendered DOM text/attributes obtained through the browser
tool, not hidden application state. Each JSON record retains host labels/logs,
guest status/component output and client event text. Frame counts come from an
explicit inspection before capture. Initial and normal-example accessibility
snapshots are retained as text. Manual observations do not increase Vitest counts.

## Contained integration results

Evidence lives in [integration-results](../examples/mock-host/integration-results/).

| Check | Observed result | Evidence |
| --- | --- | --- |
| Handshake/profile | Both distinct app identities initialize with host-selected grants; only displayName reaches the client despite a dummy private provider field. | [01](../examples/mock-host/integration-results/01-initial-handshake-public-profile.json) |
| Actual storage UI | Both components set/get their own settings value; deleting A returns null for A and preserves B. | [02](../examples/mock-host/integration-results/02-component-set.json), [03](../examples/mock-host/integration-results/03-component-get-partitions.json), [04](../examples/mock-host/integration-results/04-component-delete.json), [05](../examples/mock-host/integration-results/05-delete-isolation-and-missing-null.json) |
| Markup-looking data | The actual storage view displays the literal string; no image element or injected DOM marker appears. | [06](../examples/mock-host/integration-results/06-markup-is-inert-text.json) |
| Native non-JSON input | A Date is sent through native structured clone without normalization; -32602 follows, write count stays four, prior JSON value remains. | [07](../examples/mock-host/integration-results/07-json-value-write.json), [08](../examples/mock-host/integration-results/08-date-rejected-before-provider.json), [09](../examples/mock-host/integration-results/09-json-value-preserved.json) |
| Permissions/identity claims | B profile-only rejects set/get/delete with -32000 after a forged grant packet and blocked SOP host-API access. Recreating B with permission reveals its unchanged prior value. | [10](../examples/mock-host/integration-results/10-ungranted-set-and-forged-grants.json), [11](../examples/mock-host/integration-results/11-ungranted-get.json), [12](../examples/mock-host/integration-results/12-ungranted-delete.json), [13](../examples/mock-host/integration-results/13-denied-actions-preserved-b-data.json) |
| Version negotiation | Unsupported 9.9 returns -32004; profile is gated with -32005; an explicit 0.1 retry restores normal profile calls. | [14](../examples/mock-host/integration-results/14-unsupported-version.json), [15](../examples/mock-host/integration-results/15-call-gated-after-version-refusal.json), [16](../examples/mock-host/integration-results/16-explicit-version-recovery.json) |
| Notifications and correlation | B id 3 stays pending through an outer-host forged reply, paused/resumed/environment notifications and A revocation; real completion then succeeds. | [17](../examples/mock-host/integration-results/17-b-profile-held.json), [18](../examples/mock-host/integration-results/18-notifications-and-wrong-source-do-not-settle-b.json), [19](../examples/mock-host/integration-results/19-b-completes-after-a-revocation.json) |
| Unsubscribe | After unsubscribe, further sends add no portal notification callbacks; the three prior deliveries remain. The subscription-removal log is not a fourth notification. | [20](../examples/mock-host/integration-results/20-unsubscribe-stops-notifications.json) |
| Local client close | Pending B id 4 rejects -32008; a later call is locally rejected without another provider invocation. Releasing the old provider does not overwrite it; A still works. | [21](../examples/mock-host/integration-results/21-pending-before-local-close.json), [22](../examples/mock-host/integration-results/22-local-close-rejects-pending.json), [23](../examples/mock-host/integration-results/23-late-response-and-post-close-call.json) |
| Actual close UI | The shared close component requests portal.close; A is dismissed with reason finished and both frames removed; a freshly live B still serves profile. | [24](../examples/mock-host/integration-results/24-actual-close-component-dismisses-only-a.json) |
| Lifetime/reload | Host recreation, same-origin reload and internal page navigation preserve A data; repeat handshake keeps grants. | [25](../examples/mock-host/integration-results/25-data-retained-after-guest-dismissal.json), [26](../examples/mock-host/integration-results/26-repeat-handshake-retains-grants-data.json), [27](../examples/mock-host/integration-results/27-internal-navigation-retains-data.json) |
| Wrapper authority | Same-URL wrapper reload and replacement by a B-policy URL revoke only A. | [28](../examples/mock-host/integration-results/28-wrapper-document-reload-rejected.json), [29](../examples/mock-host/integration-results/29-wrapper-policy-replacement-rejected.json) |
| Navigation containment | Direct foreign navigation, form, redirect and silent bounce each revoke A through its enforcing policy; B and its data survive. | [30](../examples/mock-host/integration-results/30-foreign-navigation.json), [31](../examples/mock-host/integration-results/31-foreign-form.json), [32](../examples/mock-host/integration-results/32-foreign-redirect.json), [33](../examples/mock-host/integration-results/33-silent-bounce.json), [34](../examples/mock-host/integration-results/34-b-data-after-navigation-revocations.json) |

The close observation establishes dismissal, not guaranteed delivery of its
acceptance before document destruction. Existing unit tests establish response
submission before the hook; ADR 0019 explicitly does not guarantee receipt.
Local client.close leaves its page present; peer-close signaling remains §11.

## Native origin/source and targetOrigin controls

The deliberately uncontained lab isolates transport checks. It is not a
conforming Portal and its allowed-origin return is not production containment.

| Native origin | Native source WindowProxy | Provider count | Evidence |
| --- | --- | --- | --- |
| Expected | Bound peer | 1 after initial handshake/profile | [35](../examples/mock-host/integration-results/35-transport-bound-peer-initial.json) |
| Expected | Another iframe | Stays 1 for valid profile id 900 | [36](../examples/mock-host/integration-results/36-correct-origin-wrong-native-source.json) |
| Expected | Bound peer | Increases to 2 for the positive control | [37](../examples/mock-host/integration-results/37-bound-source-positive-control.json) |
| Foreign | Same bound WindowProxy | Stays 2 for valid profile id 50 | [38](../examples/mock-host/integration-results/38-same-native-source-wrong-origin.json) |
| Expected after return | Same bound WindowProxy | Increases to 3 for id 100 | [41](../examples/mock-host/integration-results/41-allowed-origin-positive-control.json) |

The observer records native MessageEvent.origin/source and isFromPeer, while
actual provider counts verify that rejected packets were not dispatched.
The positive controls exclude a dead receiver as the reason for rejection.
The full initialize response in 35 records negotiated protocolVersion 0.1.

The actual SDK transport's pinned marker does not arrive while the peer is at
the foreign origin ([39](../examples/mock-host/integration-results/39-sdk-target-origin-blocks-foreign-delivery.json)).
A separately labeled direct foreign-target fixture marker confirms that the
foreign listener is alive ([40](../examples/mock-host/integration-results/40-foreign-listener-positive-control.json)).
After return, the SDK marker is acknowledged at the allowed origin
([42](../examples/mock-host/integration-results/42-sdk-target-origin-allowed-control.json)).
The foreign control does not modify SDK configuration or authorize credential
delivery. Only public fixture marker data is used.

## Final built-preview controls and checks

The final build adds read/delete invocation logs alongside write logs in the
fixture. Profile-only B rejects all three storage methods with zero provider
storage calls in [43](../examples/mock-host/integration-results/43-built-ungranted-set.json),
[44](../examples/mock-host/integration-results/44-built-ungranted-get.json) and
[45](../examples/mock-host/integration-results/45-built-ungranted-delete.json).
Allowed A set/get/delete positive controls then log actual provider invocations
and return null after deletion ([46](../examples/mock-host/integration-results/46-built-provider-set-get-positive-controls.json),
[47](../examples/mock-host/integration-results/47-built-provider-delete-positive-control.json)).

The same build verifies public profile/both event types
([48](../examples/mock-host/integration-results/48-built-profile-and-both-notifications.json)),
actual close and retained data across recreation
([49](../examples/mock-host/integration-results/49-built-save-before-dismissal.json),
[50](../examples/mock-host/integration-results/50-built-close-component.json),
[51](../examples/mock-host/integration-results/51-built-recreate-retains-data.json)),
and A-only navigation revocation with B continuing
([52](../examples/mock-host/integration-results/52-built-navigation-isolated.json)).
The ordinary built mock-host page initializes both app origins and profiles
([53](../examples/mock-host/integration-results/53-normal-built-example.txt)).

[HTTP policies](../examples/mock-host/integration-results/response-policies.txt)
confirm exact host/A/B origins, frame-src 'none' for an unknown app, and no
effect from a guest-origin query claim. All 1131 tests in 39 files, root
typecheck, lab typecheck, lint and both multipage builds pass. No SDK kernel,
transport implementation, normal UI component, public API or SPEC changes
were needed. Added controls and counters are manual verification instrumentation.

## Evidence boundaries and diagnostics

Records 01–34 are one unchanged development sequence. Records 35–42 are a
separate unchanged transport-lab sequence. Records 43–52 use a fresh final built
preview after adding read/delete diagnostics; 53 is its ordinary example.
JSON records preserve scoped rendered strings/attributes and host log text.
The full initial controls snapshot and actual screenshot are also retained.
No server/source changes occurred within a retained sequence.

To reproduce from the workspace root, run pnpm run dev and open the
[contained checks](http://localhost:5173/containment-check.html). The component
controls use the normal example views. For the isolated lab, run:

```sh
pnpm --filter moonpool-example-mock-host exec node navigation-lab/serve.mjs
```

Open the [transport lab](http://127.0.0.1:5273/host.html). Stop the development
servers before using the same ports for built previews. After pnpm run build,
run these commands in separate terminals, from the workspace root:

```sh
pnpm --filter moonpool-example-mock-host exec vite preview --port 5173 --strictPort
pnpm --filter moonpool-example-hello-miniapp exec vite preview --port 5174 --strictPort
pnpm --filter moonpool-example-hello-miniapp exec vite preview --port 5175 --strictPort
```

The static diagnostic can be served from its directory using Python's HTTP
server on 5392 and 5393; open outer.html on 5392. It contains no scripts.

Development and preview logs retain a generic MutationObserver.observe error.
The same error reproduces with the retained
[HTML-only nested-frame control](../examples/mock-host/integration-results/static-control/outer.html),
which loads no Moonpool, Vite or application scripts
([control log](../examples/mock-host/integration-results/static-control-console.json)).
The blank-page and single-level transport controls contain no such error.
This demonstrates that the diagnostic does not require project scripts;
its exact browser/tooling source is not identified. No clean-console claim
is made and no SDK behavior was changed to hide it. The existing future
native-config-loader advisory from Vite is non-blocking; the pinned builds pass.

These are selected Chrome 156 cases, not all-engine/scheme/history/BFCache
certification, GC/heap/performance proof, or synchronous cancellation.
Already-dispatched effects, document epochs and peer disconnect retain the
accepted §11 limits. Production HTTPS hosting/native cores remain outside
this development contract. All created tabs and servers were stopped.

T19 was published as e2354e6 / 8f98da9 before this work. T20 verification,
instrumentation and learning notes remain local. T21 subsequently reconciled
the public roadmap and [completion record](v0.1-conformance.md), declaring the
scoped browser milestone complete. This observation record retains its bounds.
