# T28 native origin/store contract probe

Experimental supplementary research for the native contract proposal. The
maintainer selected the proposed direction for these probes on 2026-11-03.
The normative SPEC, production loaders and pure TypeScript kernel are unchanged.
Final contract approval follows review of the measured evidence.

## Scope recorded before implementation

Use [O01–O06](../../docs/native-origin-contract.md) to test stable app naming and
persistent guest website-data partitions on both platforms. Keep T23–T27 source
and historical measurements unchanged. Android and iOS each own their platform
harness, native tests, build/run scripts, raw reports and independent verifier.

| Case | Required observable behavior |
| --- | --- |
| O01 | The same exact app id retains its origin and data partition across concurrent Portals, recreation, updates and process restart; a different app has a different binding; no silent remap |
| O02 | Valid unusual and long ids receive an explicit native admission outcome; invalid ids and non-roundtripping representations never acquire guest authority |
| O03 | A/B page origins, DOM, localStorage and IndexedDB separation have working self/same-app controls; profile separation is distinguished from origin separation |
| O04 | Host-only and persistent HTTPS cookies work; parent/sibling cookie attempts do not expose another app's marker; iOS custom-cookie absence is labeled unavailable |
| O05 | A, B and a dedicated host-sentinel partition use the same real remote HTTPS host but retain different public cookie markers; same-app and restart controls succeed |
| O06 | Unsupported features, premature profile access and lost/conflicting assignments fail without a default-store fallback; modeled negatives are labeled separately from actual platform failures |

Begin each independently testable admission/registry behavior with a failing
native test, then implement its experimental helper. Native report verifiers
must inspect raw observed values and positive controls, not merely trust page
pass booleans. Do not adjust expected isolation results to hide an engine failure.

The [identity vectors](identity-vectors.json) pin full-id Android digest/base32
mapping independently of either native implementation. Their iOS strings are
candidates to measure, not an assertion that every syntactically valid manifest
id is supported by WKWebView. Platform fixtures may consume or independently
cross-check them. They are public synthetic app ids, not a registry of real apps.

## Native research boundaries

Use a new research application id on explicitly owned devices. Record baseline
device states and ownership in ignored local-results; never mutate or shut down
unrelated devices. Reuse installed tools/runtimes, recording actual versions.
Do not infer that a prior session's tools, caches or ownership files still exist.

Use only public sentinel data in new probe-owned website stores. The host
partition is a synthetic control, not the maintainer's logged-in host WebView.
If testing https://example.com/, retain only the probe's own cookie values and
minimal status/origin metadata; do not export unrelated remote content/cookies.
Normal HTTPS certificate validation stays enabled. Local interception is not
remote-network evidence and must be labeled when used as a complementary control.

Cross-origin frame fixtures can deliberately expose both public app pages to
measure the engine's DOM boundary. That test-only resolver exception is not the
proposed per-Portal production loader policy. No capability dispatcher, host
credential, private API, JavascriptInterface or file-origin fallback is installed.

Retain first and repeated seed/process-restart observations with matching
source/artifact/asset fingerprints. Distinguish real unsupported-provider results
from simulated API-unavailable branches and pure registry tests. Retained reports
must exclude local paths, device ids and unrelated application data.

## Completion boundary

Platform READMEs record exact reproduction commands. Run each platform's
`python3 verify_results.py results` from its directory, together with its native
contract tests/build checks. Root `pnpm run check` is separate and does not boot
devices. Once the evidence is available, the verification report and Korean
study lesson will state which proposal obligations are measured and which remain
later implementation gates (O07–O10 / T29–T45).

## Final evidence and crash-control restriction

[The verification report](../../docs/native-origin-contract-verification.md)
records Android four runs/44 snapshots, iOS four runs/52 snapshots/92 identity
rows and six no-guest startup controls. Both platform verifiers and their negative
mutation tests pass. The final iOS cold controls intentionally crash and can
produce visible macOS application-quit dialogs. The maintainer reported those
repeated dialogs; the devices and all crash-producing work are now stopped.
Routine checks must read retained evidence. Rerun intentional crash controls only
when explicitly requested; do not include them in root checks or automatic cleanup.
