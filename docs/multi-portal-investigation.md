# Multi-Portal wrapper investigation

Date: 2026-10-26
Status: Bounded investigation complete — promising candidate, not an approved T18 implementation.

## Questions and observation plan

Use the real SDK with one coordinator, two trusted wrapper documents, and
two independently origin-bound mini apps. Keep production code and SPEC intact.
Host/wrappers use 5373, app A uses 5374, app B 5375, and a foreign target 5376.
The existing T17 origins/records remain separate.

Record these observations before drawing conclusions:

1. A/B initialize, invoke profile, and keep separate storage values concurrently.
2. Inner same-origin reload retains the wrapper's bridge and storage; B is unaffected.
3. A-to-B and A-to-foreign navigation trigger only A's policy/disposal path.
4. B's deliberately pending profile completes after A is revoked. Late A sends
   are suppressed by the experimental lifecycle wrapper.
5. Native MessageEvent source is the immediate trusted wrapper for replies and
   notifications, not the outer coordinator. Reject wrong-origin/source traffic.
6. Bootstrap uses coordinator-owned frame, Document identity, origin, grants,
   and expected wrapper URL. Guest identifiers/URL parameters are not authority.
7. Wrapper reload/policy substitution and old bootstrap references do not
   rebind authority; explicit coordinator restart creates a fresh instance.
8. A guest cannot directly access the coordinator's host-only bootstrap API.
9. Observe cross-realm object behavior when outer code calls a wrapper-owned
   sender, comparing a fresh wrapper-owned notification payload.
10. Count fixture frames/listeners before/after disposal. Do not interpret those
    counts as heap-memory or performance benchmarks.

Browser observations will be recorded separately from the existing Vitest count.
No automatic browser runner, native core, or production web-hosting contract
is introduced by this investigation.

## Observed results

Measured on 2026-10-26 in the in-app browser reporting Chrome/156.0.0.0.
The normal SDK, its protocol, and production examples were not modified.
Two served trusted wrappers share the coordinator origin, but have separate
response CSP headers. The guest apps remain distinct origins.

| Observation | Result | Evidence |
| --- | --- | --- |
| Concurrent initialization/profile/storage | A at :5374 and B at :5375 both initialized; same-key held different app-specific values. | [01](../examples/mock-host/navigation-lab/results-multi/01-initial.txt) |
| A inner reload | A repeated initialize and retained its wrapper-local stored value; B counters/state stayed unchanged. | [02](../examples/mock-host/navigation-lab/results-multi/02-a-inner-reload.txt) |
| Guest accesses host bootstrap | Direct access raised SecurityError; a forged identity/config message did not change the coordinator's binding. | [03](../examples/mock-host/navigation-lab/results-multi/03-guest-host-api-access.txt) |
| Wrong-source reply from outer host | Forged B reply used the correct host origin and pending id 6, but the wrong source window; guest stayed pending. | [05](../examples/mock-host/navigation-lab/results-multi/05-wrong-source-reply.txt) |
| A navigates to B's valid app origin | A's own enforced frame-src violation revoked only A. B's pending request remained pending; its grants were unchanged. | [07](../examples/mock-host/navigation-lab/results-multi/07-a-to-b-blocked.txt) |
| A late provider response | Releasing the old provider after revocation incremented suppressed sends, not actual sends. This guard is experimental wrapper code. | [08](../examples/mock-host/navigation-lab/results-multi/08-a-late-send-suppressed.txt) |
| B completion and stored data | B's delayed profile completed normally; its previously stored value remained readable after A was revoked. | [09](../examples/mock-host/navigation-lab/results-multi/09-b-request-completed.txt), [10](../examples/mock-host/navigation-lab/results-multi/10-b-storage-after-a-revocation.txt) |
| Explicit A restart / stale bootstrap | New instance initialized; old source/Document/API references did not obtain configuration. | [12](../examples/mock-host/navigation-lab/results-multi/12-stale-bootstrap.txt) |
| A navigates to a third origin | A alone was revoked; B remained active. | [13](../examples/mock-host/navigation-lab/results-multi/13-a-third-origin-blocked.txt) |
| Outer-realm object passed to wrapper sender | notifyEnvironmentChanged rejected with the current local TypeError; nothing was sent. | [28](../examples/mock-host/navigation-lab/results-multi/28-identical-payload-outer.txt) |
| Wrapper-owned notification payload | An identical environment payload created in the wrapper was delivered to B's subscriber. | [29](../examples/mock-host/navigation-lab/results-multi/29-identical-payload-wrapper.txt) |
| Wrapper A URL replaced with wrapper B URL | Expected URL/Document check rejected bootstrap and removed that outer A frame; B stayed active. | [18](../examples/mock-host/navigation-lab/results-multi/18-wrapper-policy-switch-rejected.txt) |
| B profile-only grants | B denied storage with -32000 before/after A revocation while profile kept working. | [23](../examples/mock-host/navigation-lab/results-multi/23-b-grants-still-profile-only.txt) |
| Wrapper reloaded at the same URL | URL matched, but Document identity changed; bootstrap was rejected before a replacement guest received authority. | [24](../examples/mock-host/navigation-lab/results-multi/24-same-url-wrapper-reload-rejected.txt) |
| Final independent revocation | Fresh A was revoked on A-to-B navigation while B completed another profile request. | [27](../examples/mock-host/navigation-lab/results-multi/27-final-independent-revocation.txt) |

HTTP inspection confirmed frame-src :5373 on the coordinator, :5374 on served
wrapper A, and :5375 on served wrapper B. The root policy did not prevent the
wrappers from applying their own narrower child-document policies. The
[HTML policy-container model](https://html.spec.whatwg.org/multipage/browsers.html#policy-containers)
explains why served documents and inherited-policy srcdoc are different; the
[CSP frame-src contract](https://www.w3.org/TR/CSP3/#directive-frame-src)
constrains each protected document's child navigations.

## Architecture lessons

1. A document-wide rule need not become an application-wide single-Portal limit.
   The measured wrapper composition bound each app to its own policy context.
2. Same origin does not mean the same authorized sender. Guest replies must
   come from that guest's immediate wrapper; accepting any host-origin window
   would admit the outer forged reply tested above.
3. WindowProxy alone is not a bootstrap lifetime. The trusted coordinator can
   inspect its same-origin wrapper Document and bind it with the expected URL.
   Replacing that Document is distinct from reloading the cross-origin guest.
4. Bootstrap metadata is host-selected. Wrapper URL/query or guest-supplied
   slot/grant claims must never select another Portal's authority. The APIs in
   this lab are host-only experimental controls, not new guest RPC methods.
5. Realm ownership matters. isJsonValue deliberately checks ordinary record
   prototypes against its own Object.prototype. A live outer-document object
   can fail that check in a wrapper. The lab serializes only trusted public
   bootstrap metadata into the wrapper and creates event payloads there; it
   does not loosen the validator or serialize/repair malformed guest requests.

The next design must decide whether the wrapper owns the kernel and creates
its own payloads, or whether a separately verified adapter keeps the kernel in
the outer host. Directly exposing a wrapper-owned sender to arbitrary outer
objects is not a transparent integration. A transport relay or configuration
proxy has **not** been validated by this experiment.

## Cleanup, footprint, and limits

Two active Portals used two wrapper iframes plus two guest iframes: four iframe
elements, excluding the coordinator document. A revocation left two wrappers
and one guest: the closed trusted wrapper was deliberately retained to inspect
late sends. Its fixture bookkeeping changed three registered listeners to zero
when SDK close/removeEventListener were called. This is not an independent
browser-wide listener census, heap/GC proof, or memory/latency benchmark.
Production disposal must also release the outer wrapper and stale control refs.

Storage is a separate Map per wrapper in this fixture: it survives inner guest
reload but resets on outer-wrapper replacement. No durability across Portal
replacement is claimed; production provider lifetime/identity still needs
integration design. The existing document-epoch issue for same-origin guest
reload and peer-disconnect signalling remain SPEC §11 questions.

First-segment snapshots cover the main sequence. A second segment added the
same-URL wrapper reload control and display-only sizing, after closing the
first tab and restarting the lab. A third short segment compared identical colorScheme/locale payloads across
realms after closing earlier tabs and restarting. No server/source changes
occurred inside any saved measurement sequence. Redundant intermediate snapshots were
removed; label trailing whitespace/final newlines are normalized. The final
PNG shows actual A revocation with B still responding.

One browser engine and a bounded set of navigations were exercised. This does
not certify all schemes/history/BFCache behavior, every engine, arbitrary host
provider callbacks, or complete navigation conformance. It is evidence for
replacing the original single-Portal proposal with a carefully specified
per-Portal design, not approval of that replacement or completion of T18.

## Tooling and comments

The repository uses Biome 2.5.10 for formatting, linting, and import organization,
not Prettier. The enabled formatter uses two spaces, single quotes in JavaScript,
and a 100-character line width. `pnpm run lint` checks; `pnpm run lint:fix` applies
fixes. No formatter dependency/settings change was requested or introduced.
English comments in the fixture explain trusted bootstrap authority, Document
identity, sender source checks, realm ownership, and experimental lifetime guards.
Korean teaching notes live in study/.
