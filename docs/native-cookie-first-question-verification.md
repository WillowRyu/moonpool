# T28 — iOS evidence rule as a process's first cookie question

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. It does not close T28 or the iOS admission
gate. This work concerns SPEC §8 and §9 and does not amend the SPEC, the protocol or the
[accepted iOS presence-evidence rule](native-cookie-store-admission.md).

## Result

The [iOS empty-store run](native-cookie-empty-store-verification.md) asked about many stores in each
process, and the first one was always cookie-free. An app may ask about a cookie-bearing store first,
so that path was unmeasured. Here one process wrote 36 stores, and **each store then got its own new
process**, as the only store that process asked about.

| Store | Stores | Both sources | Server witness | Result |
| --- | --- | --- | --- | --- |
| No cookies: unused, local data only, HTTPS-visited | 12 | None | None | Admitted correctly |
| First-party cookie: denied, never denied, HttpOnly, hazard control | 16 | Both report it | Received | Refused correctly |
| Partitioned cookie only: HTTPS and `moonpool://` top pages | 8 | Both report it | Received | Refused correctly |

**36 of 36 correct: no store with cookies admitted, and no healthy store refused.** Both source orders
gave identical outcomes (18 stores each), answers one second later matched, and local data survived.

The blocker still reproduces at this position. In the four hazard-control stores, an enumeration before
the policy was that process's first cookie question and returned nothing. After the policy, on the same
store, both sources reported the cookie.

## What this does not establish

- "First question" means first cookie question, not first WebKit call. WebKit is still initialized with
  an empty never-loaded view first, because enumerating as the first WebKit call is the known crash
  path. That crash path was not run, and an SDK must keep this startup order.
- The two sources again never disagreed, so that safeguard remains unexercised.
- The ordering stays undocumented and its cause unknown, so this is evidence for one configuration.
- A physical device, other iOS versions, device reboot, service workers, redirects and real Portal
  teardown remain unmeasured.

## Environment, verification and cleanup

iOS 26.4.1 on the dedicated iPhone 17 Pro simulator, Xcode 26.4.1 / SDK 26.4, deployment 17.0. Loopback
HTTPS hosts only. This is a measured configuration, not a support matrix.

The [isolated experiment](../experiments/native-cookie-ios-first-question-probe/README.md) retains
[the seed report](../experiments/native-cookie-ios-first-question-probe/results/ios-seed.json) and
[36 launches](../experiments/native-cookie-ios-first-question-probe/results/ios-first.json), with 100
server receipt rows and 404 verifier checks. The host suite has 24 tests, written and failing before the
helpers. Criteria were written before collection and did not change.

Only the dedicated simulator ran. It reused the empty-store experiment's local CA, so no new trust root
was added. The Claude desktop app's simulator panel attached during the run, so it was detached before
shutdown. The simulator is off, all 13 simulator states match the baseline, the fixture is closed and
there are no crash reports. No cookie deletion or import, data wipe, Android work, intentional crash or
known first-call enumeration ran. T28 stays incomplete at 6/44 native tasks. SPEC, production packages,
public API, wire version and release state are unchanged.
