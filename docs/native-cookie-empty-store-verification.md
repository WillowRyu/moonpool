# T28 — iOS empty-store check under the accepted evidence rule

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. It does not close T28 or the iOS
admission gate. This work concerns SPEC §8 and §9 and does not amend the SPEC, the protocol
or the [accepted iOS presence-evidence rule](native-cookie-store-admission.md).

## Result

The rule had never been run against a cookie-free store, so it might have refused healthy
stores. A store was written in one process and checked in a new one: await the deny policy,
then require `fetchDataRecords` and `getAllCookies` to agree. The verdict was then compared
with the `Cookie` headers an HTTPS server actually received.

| Store state at the check | Stores | Both sources | Server witness | Result |
| --- | --- | --- | --- | --- |
| Cookie-free: created now, or earlier and unused, or holding only localStorage and IndexedDB, or having visited a page that set no cookie | 56 | None | None | Admitted correctly |
| Cookie gone: write blocked by deny, removed by the server, expired, session cookie after exit | 32 | None | None | Admitted correctly |
| Cookie never stored or not retained (see side findings) | 16 | None | None | Admitted correctly |
| First-party cookie: denied, never denied, HttpOnly, written just before exit with deny | 40 | Both report it | Received | Refused correctly |
| Partitioned cookie only: under HTTPS and `moonpool://` top pages | 24 | Both report it | Received | Refused correctly |

**168 of 168 correct: no store with cookies admitted, and no healthy store refused.** Both
source orders gave identical outcomes (84 stores each), and answers one second later matched.

- Local data does not count as a cookie, and all sentinels survived the check.
- `fetchDataRecords` lists a store holding only a partitioned cookie, under that cookie's host.
  Earlier evidence could not show this because a first-party cookie was always present.
- The blocker still reproduces. On the same eight control stores, `getAllCookies` before the
  policy returned nothing, and after the policy both sources reported the cookie.

## What this does not establish

- **The second source has not been shown to catch anything.** The two sources never disagreed
  in 168 stores, so that safeguard ran but was never needed here.
- The ordering stays undocumented and its cause unknown, so this is evidence for one
  configuration, not a guarantee. The accepted per-version rule still applies.
- "No witness" covers the contexts read: first-party and the seeding context. Every store
  began with no cookies, or with one known cookie, so nothing was expected elsewhere.

Still unmeasured: a physical device, other iOS versions, device reboot, service workers,
redirects and real Portal teardown. A process's first store here was always cookie-free; a
[later run](native-cookie-first-question-verification.md) measured a cookie-bearing store as a process's first question.

## Side findings

Both came from the first collection, which the verifier rejected, and neither changes the
rule's verdict. Causes are unknown.

**An explicit allow is not the same as never setting the policy.** A cross-site `Partitioned`
header stored a cookie after `setCookiePolicy(.allow)` (24 of 24) and stored none on a store
with no policy call (8 of 8, plus 24 in the rejected collection), although the header documents
allow as the default. The [earlier partition table](native-cookie-partition-writer-verification.md)
therefore describes explicitly allowed stores. Guest stores are denied before load, so this
does not weaken the gate.

**A listed cookie may not survive exit.** A never-denied cookie written in the process's last
seconds was listed by that process and absent from the next (8 of 8). The same timing followed
by a deny policy call survived (8 of 8), and ordinary stores that settled for 45 s survived.
This concerns data lifetime rather than admission: the rule was still right, because the cookie
was really gone. Do not treat a listing in the writing process as proof that a cookie persisted.

## Environment, verification and cleanup

iOS 26.4.1 on the dedicated iPhone 17 Pro simulator, Xcode 26.4.1 / SDK 26.4, deployment 17.0.
Loopback HTTPS hosts only. This is a measured configuration, not a support matrix.

The [isolated experiment](../experiments/native-cookie-empty-store-probe/README.md) retains
four reports across two seed/check cycles: [seed a](../experiments/native-cookie-empty-store-probe/results/ios-seed-a.json),
[check a](../experiments/native-cookie-empty-store-probe/results/ios-check-a.json),
[seed b](../experiments/native-cookie-empty-store-probe/results/ios-seed-b.json) and
[check b](../experiments/native-cookie-empty-store-probe/results/ios-check-b.json). They hold
168 checked stores, 472 server receipt rows and 990 verifier checks. The two check reports
classify identically. The host suite has 42 tests, written and failing before the helpers.

The verifier rejected one earlier collection because its partitioned controls held no cookie.
It stays in ignored local results, and the experiment README records the correction. Criteria
for outcomes were written before any collection and did not change.

Before the run, the dedicated simulator was found booted with the Claude desktop app's
simulator panel attached, and no other work on it. It was used and left booted as found, and
all 13 baseline simulator states match. The fixture is closed, the probe app is terminated and
there are no crash reports. The fixture's CA was trusted only inside that simulator. The only
cookie removal was the fixture server's own `Max-Age=0` response in one store kind. No native
cookie deletion or import, data wipe, Android work, intentional crash or known first-call
enumeration ran. T28 stays incomplete at 6/44 native tasks. SPEC, production packages, public
API, wire version and release state are unchanged.
