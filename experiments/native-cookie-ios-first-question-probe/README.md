# T28 iOS rule as a process's first cookie question

Bounded iOS follow-up requested on 2026-11-03. The
[Android review](../../docs/native-cookie-android-restart-verification.md) found that in the
[iOS empty-store run](../../docs/native-cookie-empty-store-verification.md) a process's first store
was always cookie-free. An app may ask about a cookie-bearing store first, so that path was
unmeasured under the accepted rule. Research only: no production SDK, protocol change, cookie import
or deletion, no Android work and no crash-control execution. Earlier probes stay unchanged.

## Retained result

Read the [verification report](../../docs/native-cookie-first-question-verification.md). All 36 stores, each the first a new process asked
about, got the correct verdict, with 100 server receipt rows and 404 verifier checks. The hazard
control still shows the original false empty before the policy.

## Criteria written before collection

One process writes every store. Then **each store gets its own new process**, and is the only store
that process asks about. Each process applies the accepted rule: await the deny policy, then ask
`fetchDataRecords` and `getAllCookies`, in either order. The verdict is then compared with the HTTPS
server's `Cookie` receipts from a first-party page and from the seeding context.

| Outcome | Meaning |
| --- | --- |
| `correct-admit` | Both sources report none, no witness |
| `correct-refuse` | Both sources report cookies, witness |
| `safe-refuse` | Sources disagree, witness |
| `false-admit` | Both sources report none, witness: **dangerous** |
| `over-refuse` | Sources report a cookie, no witness: **costly** |

Stores have four samples per kind, two for each source order: unused, local data only and
HTTPS-visited stores without cookies, and first-party, never-denied, HttpOnly and partitioned stores
with them. All but the never-denied kind were denied earlier.

Findings do not fail verification. Missing controls do: cookie kinds need a server witness, cookie-free
kinds must have none, local data must survive, every witness context must load, and every store needs
its own launch. A hazard control enumerates before the policy, as that process's first cookie question,
and must show the original false empty and then a non-empty verdict on the same store.

## Safety and scope

WebKit is still initialized with an empty never-loaded view before any identified store, so the known
crashing first-WebKit-call enumeration never runs. "First question" here means first cookie question,
not first WebKit call. Use public fixture values and the existing dedicated simulator only, recording
every simulator's state first and restoring it after. This reuses the empty-store experiment's local CA,
which the simulator already trusts, so no new trust root is added. An unexpected process exit stops the
run without retry.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
python3 -u -B fixture.py
python3 -u -B run_probe.py --mode seed --install
python3 -u -B run_probe.py --mode first
python3 -B verify_results.py --summary
```

## Limits

One simulator and OS version, not a support matrix or a physical-device result. Loopback hosts only.
Device reboot, service workers, redirects and real Portal teardown are not covered.
