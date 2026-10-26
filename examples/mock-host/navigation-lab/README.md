# Manual navigation lab (T17)

This is a bounded research fixture, not shipped navigation protection and not
a new automated browser runner. It imports the actual Moonpool host, client,
and iframe transport. Only public dummy profile data is used.

From the repository root:

```sh
pnpm --filter moonpool-example-mock-host exec node navigation-lab/serve.mjs
```

Open `http://127.0.0.1:5273/host.html` for the baseline and
`http://127.0.0.1:5273/host-csp.html` for the CSP comparison. Stop with Ctrl-C.
Ports are fixed and fail if occupied: host 5273, allowed app 5274, foreign 5275.
These are separate from the normal 5173/5174 examples and use a separate app id.

The server uses the example's existing Vite dependency to serve TypeScript;
HMR, file watching, and dependency discovery are disabled during observations.
Restarting the server can still reload a development page: always start a
fresh run after restarting, and do not edit/restart during a recorded sequence.
The first calibration run with default development reload behavior was discarded.

## Scenarios

Start a fresh Portal before each independent experiment. Controls send only
fixture commands; navigation itself runs inside the child document.

1. Baseline: same-origin document navigation, reload, and hash change. Inspect
   the parent's readable properties and compare iframe load/message ordering.
2. Baseline: navigate foreign, send the targetOrigin marker, return without
   initialize, and send the marker again as a positive control. Provider counts
   distinguish rejected foreign calls from accepted calls after return.
3. Baseline: silent foreign bounce. The foreign page sends no parent message,
   starts a slow image request, and returns before load. The returned allowed
   page also delays load and sends profile.get id 100 without initialize.
   Read fixture server observations to independently establish the foreign hop.
4. Select "Close on every load after first", then start fresh. Repeat a normal
   same-origin navigation, then separately repeat the silent bounce. This is
   an intentionally insufficient experimental policy, not production code.
5. CSP page: test foreign navigation, silent bounce, form submission, and an
   allowed URL that redirects foreign. Start fresh after each blocked document.
   Check that same-origin navigation and reload still initialize successfully.

The slow image delay (5 seconds), bounce delay (100 ms), and 1-second client
timeout are fixture controls only, not protocol or resource-limit proposals.
`/observations` is experimental server evidence unavailable to a generic
production embedder. Logs record actual browser events; no browser state is
inferred from the unchanged src attribute or a child-supplied URL.

## Evidence and limits

Rendered accessibility snapshots are in `results/`; redundant intermediate
snapshots were removed. Trailing label whitespace and final newlines are
normalized; recorded JSON event contents are unchanged. `lab-overview.png` shows the fixture interface, not a
timing assertion. See [the findings](../../../docs/navigation-investigation.md)
for measurements, sources, and the proposed T18 contract.

Measured on 2026-10-23 using the in-app browser reporting Chrome 155.0.0.0 on
macOS. These observations are not a cross-engine certification, a statistical
timing guarantee, or a proof for every URL scheme/navigation mechanism.
The existing 995 Vitest tests are separate from these manual observations.

The lab does not install a browser automation dependency, so HANDOFF's future
reportError migration trigger has not been activated.

## T20 transport boundary controls

The baseline host deliberately permits navigation so the two transport gates
can be measured independently. It is not the conforming contained example.
"Other allowed-origin frame calls profile" sends id 900 from the correct origin
but another native source window; the provider count must stay unchanged.
"Bound peer profile positive control" must then increment it.

Navigate the bound peer foreign: its native source remains the same WindowProxy
but its origin differs, so its id 50 call must not increment the provider count.
The targetOrigin marker uses the actual SDK transport; it must not arrive there.
The separately labeled foreign-origin marker is a fixture positive control for
the foreign listener, not a change to the SDK's pinned targetOrigin. Return to
the allowed origin and verify the bound-peer call and SDK marker positive controls.

## Multi-Portal follow-up (2026-10-26)

```sh
pnpm --filter moonpool-example-mock-host exec node navigation-lab/serve.mjs --multi
```

Open `http://127.0.0.1:5373/multi-host.html`. This mode uses host/trusted wrappers
5373, guest A 5374, guest B 5375, and foreign target 5376. It serves separate CSP
response headers for the coordinator and each wrapper. Old T17 ports, pages,
and evidence remain available in the default mode.

The coordinator pins each actual wrapper Window/Document and expected URL
before returning its own public JSON configuration. The wrapper owns the real
SDK host and its transport; the guest uses the real client against its immediate
parent. Lab controls/globals are private experimental host instrumentation,
not new Moonpool wire messages or production APIs. Each wrapper has local
storage; restarting that outer wrapper resets it.

Reproduce: inspect concurrent startup; reload A's guest; hold B, forge its reply
from the outer host, hold A, navigate A to B, release A and B; verify B storage.
Restart A and test stale bootstrap and third-origin navigation. Compare outer-
object versus wrapper-local notifications. Try wrapper URL substitution and
same-URL wrapper reload. Restart B profile-only and verify storage denial before
and after A revocation. `results-multi/` and
[the follow-up findings](../../../docs/multi-portal-investigation.md) record the
observations. There is no assertion runner or cross-engine certification.

Revoked guest frames are removed; trusted wrappers are retained temporarily for
late-send inspection. The displayed listener count is fixture bookkeeping, not
an independent event-listener or GC measurement. The prototype is not T18
production integration and must not be imported into the normal example entry.
