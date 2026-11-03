# T28 iOS empty-store check under the accepted evidence rule

Bounded iOS follow-up requested on 2026-11-03, after the maintainer accepted the
[iOS presence-evidence rule](../../docs/native-cookie-store-admission.md) as a design
direction. Neither API's answer on a cookie-free store had been measured under it.
Research only: no production SDK, protocol change, cookie import or native cookie deletion,
no Android work and no crash-control execution. Earlier probes stay byte-for-byte unchanged.

## Retained result

Read the [verification report](../../docs/native-cookie-empty-store-verification.md). Four reports hold 168 checked stores, 472
server receipt rows and 990 verifier checks, with no store holding cookies admitted and no
healthy store refused. The two sources never disagreed, so that safeguard was not exercised.

## Criteria written before collection

A store is written in one process and checked in a new one. The check applies the rule and
nothing else first, because a policy read or a load would change what enumeration reports:
await the deny policy, then ask `fetchDataRecords` and `getAllCookies`, in either order.

| Verdict | Condition |
| --- | --- |
| `empty` | Both sources report no cookies, so admission could proceed |
| `present` | Both sources report cookies, so admission is refused |
| `unknown` | The sources disagree, so admission is refused |

The verdict is compared with the HTTPS server's `Cookie` receipts from a first-party page
and from the seeding context, read after the verdict:

| Outcome | Meaning | Why it matters |
| --- | --- | --- |
| `correct-admit` | `empty`, no witness | The healthy case the rule must allow |
| `correct-refuse` | `present`, witness | The case the rule exists for |
| `safe-refuse` | `unknown`, witness | Refused for the right result, by disagreement |
| `false-admit` | `empty`, witness | **Dangerous:** the rule would admit into a store with cookies |
| `over-refuse` | Not `empty`, no witness | **Costly:** a healthy store would be refused |

Store kinds:

- **Cookie-free:** created in the checking process; opened earlier and never used, with and
  without deny; holding only localStorage and IndexedDB from a `moonpool://` page, with and
  without deny; having visited an HTTPS page that set no cookie, with and without deny.
- **Cookie-bearing:** first-party, never denied, HttpOnly, and partitioned-only under an HTTPS
  and a `moonpool://` top page. Partitioned-only matters because earlier `fetchDataRecords`
  evidence always had a first-party cookie alongside it.
- **Ambiguous, truth from the witness only:** a write under deny, a cookie the server removed
  with `Max-Age=0`, a cookie that expired naturally, and a session cookie.

Each kind has four stores per cycle, two for each source order, interleaved across two
seed/check cycles. Each store also answers again one second later, which shows whether a
disagreement is timing that a retry could resolve.

False admits and over-refusals are findings and do not fail verification. Missing controls
do: cookie kinds need a server witness, cookie-free kinds must have none, local data must
survive, every witness context must load, and a hazard control must show the original false
empty before the policy and a non-empty verdict after it, on the same store.

### Changed after the first collection

The verifier rejected the first collection, which is kept only in ignored local results.
Partitioned kinds held no cookie because their seed never called `setCookiePolicy(.allow)`,
unlike earlier probes, so they tested nothing. They now set it explicitly, and
`partitioned-default` keeps the default-policy case as an observation. A never-denied cookie
written shortly before process exit also disappeared. Ordinary stores now settle for 45 s
before exit, and `late-never-denied` and `late-denied` measure that window on purpose. Neither
change alters the rule, the verdict or the outcome definitions above.

## Safety and scope

Use public fixture values and the existing dedicated simulator only, never an implicit
`booted` target. Record every simulator's state first and restore it after. The fixture's CA
is trusted only inside that simulator. The only cookie removal is the fixture server's own
`Max-Age=0` response in one store kind, on its own public cookie. WebKit is initialized with
an empty never-loaded view before any identified store, and every store has a live view
before enumeration. An unexpected process exit stops the run without retry.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
python3 -u -B fixture.py
python3 -u -B run_probe.py --run seed-a --mode seed --install
python3 -u -B run_probe.py --run check-a --mode check
python3 -u -B run_probe.py --run seed-b --mode seed
python3 -u -B run_probe.py --run check-b --mode check
python3 -B verify_results.py --summary results/*.json
```

## Limits

One simulator and OS version, not a support matrix or a physical-device result. Loopback
hosts only. The new-process test does not cover device reboot, ITP over days of use, service
workers or redirects. Agreement between the two sources does not prove either is complete.
