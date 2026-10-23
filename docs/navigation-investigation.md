# T17: browser navigation observations

Date: 2026-10-23
Status: Investigation complete. T18 implementation and specification decision pending.

## Conclusion

The existing iframe transport correctly rejects foreign-origin messages, but
does not implement SPEC §9.2's navigation teardown. Returning to the allowed
origin reuses the same WindowProxy and can call the old initialized host.
Parent DOM inspection and iframe load events cannot reliably distinguish all
allowed document changes from foreign excursions. Closing on every load both
breaks §5.1 and leaves a pre-load execution interval.

A host-owned CSP restricted to one mini-app origin prevented the tested foreign
loads, including form submission, redirect, and a silent bounce. This is a
promising *preventive* constraint, not a general destination observer. The
recommendation is the explicit, constrained browser-development profile in
[proposed ADR 0022](adr/0022-constrain-browser-navigation-with-host-csp.md).
No SDK/example navigation protection or normative change is included in T17.

## Method

The [manual fixture](../examples/mock-host/navigation-lab/README.md) uses the
actual host/client/iframe transport, three fixed loopback origins, and a dummy
profile provider. Parent logs include event.origin, event.source identity,
provider calls, sends, loads, src mutations, and attempts to inspect the current
location/document/Navigation API. It does not trust child-reported URLs.

Browser UA: Chrome/155.0.0.0, Macintosh, as reported by the in-app browser.
Observations are single runs of each listed scenario, not cross-browser or
statistical guarantees. HMR/watch/dependency discovery were disabled; an initial
calibration run with unexplained extra development loads was discarded. Saved
snapshots were taken before later server restarts. Restarting a development
server can reload an existing tab and reset its displayed experiment.

## Results

| Scenario | Observed result | Evidence |
| --- | --- | --- |
| Initial load, same-origin page change, reload | Each initialized and read the profile. Loads/provider calls reached 3/3. src stayed at the first URL; WindowProxy identity stayed equal. | [04](../examples/mock-host/navigation-lab/results/04-hash.txt) |
| Same-document hash change | No additional iframe load or profile call; a fixture hashchange message arrived. | [04](../examples/mock-host/navigation-lab/results/04-hash.txt) |
| Parent reads current child location or Navigation API | SecurityError for both allowed and foreign documents; contentDocument was null. Both are cross-origin to the host. | [05](../examples/mock-host/navigation-lab/results/05-foreign.txt) |
| Foreign page calls profile.get | Same WindowProxy, foreign event.origin, origin/source predicate false. Provider count stayed 3; no response to foreign id 50. | [05](../examples/mock-host/navigation-lab/results/05-foreign.txt) |
| Outbound targetOrigin marker | No foreign receipt report; after return, the allowed-page positive control reported receipt. | [08](../examples/mock-host/navigation-lab/results/08-allowed-marker.txt) |
| Foreign page returns allowed without initialize | id 100 reached the old provider and got a result; count rose from 3 to 4, bridge remained open. | [08](../examples/mock-host/navigation-lab/results/08-allowed-marker.txt) |
| Silent foreign bounce before load | Foreign page sent no message. Server observed its document/slow image. Allowed return called provider at 5463 ms; the next iframe load was at 10464 ms. | [11](../examples/mock-host/navigation-lab/results/11-silent-bounce-server-evidence.txt) |
| Close-on-every-load candidate, normal allowed navigation | Closed at the second load; the new initialize received no reply and timed out. | [14](../examples/mock-host/navigation-lab/results/14-load-policy-timeout.txt) |
| Same candidate, silent foreign bounce | Returned profile request executed at 596 ms; closure happened at 5584 ms. Eventual closure did not prevent that call. | [17](../examples/mock-host/navigation-lab/results/17-load-bounce-final.txt) |
| Parent CSP, child foreign location navigation | frame-src violation; no foreign document request appeared in the fixture server log. | [19](../examples/mock-host/navigation-lab/results/19-csp-server-evidence.txt) |
| Parent CSP, silent foreign bounce | frame-src violation; no returned id-100 request or second provider call. | [21](../examples/mock-host/navigation-lab/results/21-csp-silent-bounce.txt) |
| Parent CSP, foreign form submission | frame-src violation; server observed only the initial allowed probe. | [24](../examples/mock-host/navigation-lab/results/24-csp-form-server.txt) |
| Parent CSP, allowed URL redirects foreign | Server observed the allowed redirect endpoint, but no foreign document request; frame-src violation occurred. | [27](../examples/mock-host/navigation-lab/results/27-csp-redirect-server.txt) |
| Parent CSP, allowed navigation/reload | Initialization and profile calls remained successful, reaching 3 loads/3 calls. | [30](../examples/mock-host/navigation-lab/results/30-csp-reload.txt) |

The CSP fixture only logs violations; it deliberately does **not** close the
bridge on violation yet. Its `bridge closed=false` is not a T18 implementation
claim. The load candidate is likewise isolated experimental code.

## Interpretation against platform contracts

- The HTML iframe model explicitly retains src while navigation replaces the
  underlying document. WindowProxy identity also survives navigation, so neither
  value proves the current URL. [HTML iframe](https://html.spec.whatwg.org/multipage/iframe-embed-object.html#the-iframe-element),
  [WindowProxy](https://html.spec.whatwg.org/multipage/nav-history-apis.html#the-windowproxy-exotic-object).
- Parent access is constrained by the same-origin policy even for the allowed
  mini app, because SPEC §8.1 requires distinct host/app origins. Catching an
  access error therefore cannot classify a navigation as foreign.
  [MDN contentWindow](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/contentWindow).
- Load is not a navigation-start gate. Here the delayed-load fixture executed
  a request first; ordinary loads often preceded delivered initialize messages.
  Do not generalize either observed ordering into a universal guarantee.
- CSP frame-src constrains nested document loads and has pre/post request checks.
  The measured prevention is consistent with that contract. It does not expose
  a child URL API. [CSP Level 3](https://www.w3.org/TR/CSP3/#directive-frame-src).

A policy allowing origins A and B at the same parent would not bind an individual
frame to A alone; this is a source-list implication, not an additional browser
experiment. Thus the proposed simple profile is one active Portal / one allowed
mini-app origin per host document. Multiple unrelated allowed frames need a
separate design and are not claimed by this proposal.

## What T18 must resolve

The current SPEC cannot be claimed satisfied by an unrestricted cross-origin
iframe using only origin/source checks or load listeners. Approval is needed
to define the constrained preventive browser profile, or keep the present
requirement and leave browser navigation conformance unresolved. The proposal
keeps production requirements intact and does not introduce native cores.

T18 must verify terminal disposal on an enforced frame-src violation, suppression
of later sends/receives, explicit fresh-Portal recovery, listener cleanup, and
same-origin repeat handshakes. T17 does not implement those outcomes. History,
non-network schemes, different browser engines, and multi-Portal policy
composition are not exhaustively certified here. Existing §11 document-epoch
and peer-disconnect limitations remain separate.
