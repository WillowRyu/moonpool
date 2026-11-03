# T28 Android hasCookies in a new process

Bounded Android follow-up requested on 2026-11-03, after iOS's first enumeration in a new
process [falsely reported empty](../../docs/native-cookie-partition-writer-verification.md).
The accepted baseline relies on the selected Profile's `hasCookies()` on Android, and that had
never been measured against a server witness across a process restart. Research only: no
production SDK, protocol change, cookie import or native cookie deletion, no iOS work and no
crash-control execution. Earlier probes stay byte-for-byte unchanged.

## Retained result

Read the [verification report](../../docs/native-cookie-android-restart-verification.md). Fifteen reports hold 250 checked stores, 788
server receipt rows and 1817 verifier checks. `hasCookies()` was correct in every store and every
order, including as the first question a process asked. The deny policy was not retained across
a process restart.

## Criteria written before collection

A profile is written in one process. After `am force-stop`, a new process asks
`hasCookies()`. Each answer is compared with the HTTPS server's `Cookie` receipts from a
first-party page and from the seeding context, read afterward.

What runs before the first answer varies, because this is what changed the iOS result:

| Order | Before the first `hasCookies()` |
| --- | --- |
| `bare` | Nothing touches this profile beyond obtaining it |
| `view` | A never-loaded WebView on this profile |
| `policy` | `setAcceptCookie(false)`, the accepted baseline order |

Every store then also answers under deny, and again one second later.

| Outcome | Meaning | Why it matters |
| --- | --- | --- |
| `correct-admit` | No cookies reported, no witness | The healthy case |
| `correct-refuse` | Cookies reported, witness | The case the gate exists for |
| `false-admit` | No cookies reported, witness | **Dangerous:** the iOS blocker, on Android |
| `over-refuse` | Cookies reported, no witness | **Costly:** a healthy store would be refused |

**Witnesses run under allow, and verification rejects any that do not.** An earlier experiment
found Android's deny policy withholds retained cookies from requests, so a witness under deny
would hide the very cookie it is meant to reveal. This is the main difference from the iOS
probe, where cookies are still sent under deny.

Store kinds:

- **Cookie-free:** created in the checking process; obtained earlier and never used, with and
  without deny; holding only localStorage and IndexedDB from the guest origin, with and without
  deny; having visited an HTTPS page that set no cookie, with and without deny.
- **Cookie-bearing:** first-party, never denied, HttpOnly and first-party partitioned.
- **Ambiguous, truth from the witness only:** a write under deny, a cookie the server removed
  with `Max-Age=0`, a cookie that expired naturally, a session cookie, cookies written just
  before exit, and cross-site partitioned cookies under an HTTPS top page, under the guest origin
  and with third-party cookies enabled. Whether Android stores those is itself being observed.

Each kind has six stores per cycle, two for each order, interleaved across two seed/check
cycles. A third seed cycle backs the first-call test below. False admits and over-refusals are findings and do not fail verification. Missing
controls do: cookie kinds need a server witness, cookie-free kinds must have none, local data
must survive, and every witness context must load.

### Changed after the first cycle

The first cycle verified cleanly, but its review found a gap. A process's first native cookie
question always went to the cookie-free `brand-new` store, while a real app may ask about a
cookie-bearing store first. So each `--only` launch now makes one `bare` store the only store,
and therefore the first, that its process asks about. Ten such launches cover eight stores with
cookies and two without. The first cycle stays in ignored local results because this changed
the app's source. Outcome definitions did not change.

## Safety and scope

Use public fixture values and the existing dedicated AVD on its fixed serial only. Record the
adb and AVD state first. The fixture's CA ships only in this probe APK for `localhost` and
`127.0.0.1`; TLS validation stays on and host trust is unchanged. Traffic uses an owned
`adb reverse` mapping. The only cookie removal is the fixture server's own `Max-Age=0` response
in one store kind. An unexpected process exit stops the run without retry. At the end, stop only
the probe app, remove the owned mapping, stop the owned emulator and close the fixture.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
python3 -u -B fixture.py
python3 -u -B run_probe.py --run seed-c --cycle c --mode seed --install
python3 -u -B run_probe.py --run check-c --cycle c --mode check
python3 -u -B run_probe.py --run seed-d --cycle d --mode seed
python3 -u -B run_probe.py --run check-d --cycle d --mode check
python3 -u -B run_probe.py --run seed-e --cycle e --mode seed
python3 -u -B run_probe.py --run first-1 --cycle e --mode check --only cookie-denied-b1
```

The remaining first-call launches use the same command with these stores:
`cookie-denied-b2`, `cookie-never-denied-b1`, `cookie-never-denied-b2`, `httponly-denied-b1`,
`httponly-denied-b2`, `partitioned-first-party-b1`, `partitioned-first-party-b2`,
`local-data-b1` and `local-data-b2`.

```sh
python3 -B verify_results.py --summary results/*.json
```

## Limits

One emulator image and WebView version, not a support matrix or a physical-device result.
Loopback hosts only. `force-stop` is one way to end a process; device reboot, ITP-like
long-term behavior, service workers and redirects are not covered.
