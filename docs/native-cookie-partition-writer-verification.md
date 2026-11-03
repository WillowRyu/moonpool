# T28 — iOS partitioned-cookie coverage and writer-exclusion verification

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. It closes neither T28 nor the
iOS admission gate, and it found a new blocker. The maintainer accepted the evidence rule
below as a design direction on 2026-11-03. This work concerns SPEC §8 and §9 and does not
amend the SPEC or the protocol.

## Main finding: the first enumeration in a new process can falsely report empty

The admission baseline relies on `getAllCookies` to show that a store has no cookies.
In a new process, on a store written by an earlier process, the first enumeration
returned **an empty list while the store held cookies**. The same store then sent those
cookies to the server, so the list was wrong rather than the store being empty.

| What ran before the first enumeration | Stores | False empty |
| --- | --- | --- |
| Nothing, one enumeration | 4 stored cases + 16 | 20 of 20 |
| Nothing, second enumeration with no added delay | 16 | 16 of 16 (both calls empty) |
| Nothing, waiting (list complete at the 0.5 s sample) | 2 | 2 of 2 at the first call |
| `await setCookiePolicy(.disallow)` | 16 | 0 of 16 |
| `await getCookiePolicy` | 16 | 0 of 16 |
| `await fetchDataRecords(ofTypes: cookies)` | 16 | 0 of 16 |
| Load `about:blank` | 2 | 0 of 2 |
| Load a local `moonpool://` page | 2 | 0 of 2 |
| Real network load (control) | 2 | 0 of 2 |

The 16-store strategies are interleaved across two seed/reopen cycles, so the no-action
control also ran late in the process. Position in the process does not explain the
result. Every store's cookies were confirmed by server receipts afterward. In the
`records` case the API also named the cookie domain before the enumeration ran.

**Why earlier evidence missed this.** The
[admission verification](native-cookie-admission-verification.md) reopened stores within
one process, after that store's policy had been set. Its results stay valid for what they
measured; they did not exercise a new process enumerating first.

**What this does and does not establish.**

- A gate that enumerates first would admit a guest into a store holding cookies. On iOS
  those cookies are also sent under the deny policy, which is the failure the admission
  baseline exists to prevent. An enumeration alone is therefore not evidence of emptiness.
- The measured sequence of accepted admission steps 3 and 4, awaiting the policy and then
  enumerating, gave the correct answer in all 16 stores here. That is an observation, not
  a guarantee: Apple does not document this ordering. We have not established a cause.
  A plain IPC round trip cannot be the whole explanation, because a repeated enumeration
  stayed empty.
- Every reopened store had been set to deny earlier, and reported deny at open.
  [A later run](native-cookie-empty-store-verification.md) measured never-denied and cookie-free stores under the accepted rule.

## Partitioned-cookie coverage

| Written by | Stored? | Listed by inventory | Sent: same context / other top site / first-party | Sent after deny |
| --- | --- | --- | --- | --- |
| Cross-site iframe, header, `Partitioned` | Yes | Yes | Yes / No / No | Yes |
| `moonpool://` top page, iframe, header, `Partitioned` | Yes | Yes | Yes / No / No | Yes |
| First-party, header, `Partitioned` | Yes | Yes | Yes / No / Yes | Yes |
| First-party, header, not partitioned (control) | Yes | Yes | Yes / No / Yes | Yes |
| Cross-site iframe, header, not partitioned | No | No | None | None |
| Cross-site iframe, `document.cookie` + `Partitioned` | No | No | None | None |
| Cross-site iframe, `cookieStore.set` with `partitioned` | No | No | None | None |
| `moonpool://` top page, iframe, `document.cookie` + `Partitioned` | No | No | None | None |
| Empty control | No | No | None | None |

This answers the question the admission report left open. **iOS does store these cookies
separately by top-level site, and the inventory does list them.** Sends differ by top
site, and the server confirmed cross-site context through `Sec-Fetch-Site`. These stores were
seeded after an explicit `setCookiePolicy(.allow)`; [a later run](native-cookie-empty-store-verification.md) found that a store
with no policy call stores no cross-site partitioned cookie. Within a
running process there were no false empties in any partition case.

Limits remain. `HTTPCookie.properties` shows no partition field, and `cookieStore.getAll`
gave no `partitioned` value, so an inventory entry cannot say which top site owns it.
Whole-store presence does not need that, but a future cookie-only recovery might. Two
top sites were tested, not every partition key. Script writes silently produced nothing
and reported no error, in this configuration only.

## Writer exclusion

Each case began with an inventory reporting empty while a real writer was active.

| Writer | Action before it completes | Result |
| --- | --- | --- |
| Held navigation response with `Set-Cookie` | None (control) | **Cookie landed** after the empty check |
| Held `fetch` response with `Set-Cookie` | None (control) | **Cookie landed** after the empty check |
| Held navigation response | Await deny policy | Page confirmed delivery; nothing landed |
| Held `fetch` response | Await deny policy | Page confirmed delivery; nothing landed |
| Held navigation response | Tear down the view | Server saw the client close; nothing landed |
| `document.cookie` burst | Await deny policy | 84–89 further writes issued; none added |
| `cookieStore.set` burst | Await deny policy | 84–89 further writes issued; none added |
| Native `setCookie` | Under deny policy | **Stored and sent to the server** |
| Native `setCookie`, not awaited | None | Visible to the next enumeration in both runs |
| Second `WKWebsiteDataStore` for the same identifier | Change policy, write cookie | **Same object; shares both** |

What this means for the admission design:

- The controls prove the race is real. A check showing empty is not durable by itself,
  so the policy must complete before the check, as accepted steps 3 and 4 already order it.
- In these runs the awaited deny policy excluded the tested web-content writers, including
  responses already in flight. Bursts ran at one write per 10 ms, so this does not rule out
  a narrower window.
- **The policy does not exclude native writers.** The SDK must serialize its own native
  cookie writes against admission; the policy will not do it.
- **The platform provides no owner exclusion.** Any in-process code holding the identifier
  gets the same store and can flip its policy. Owner exclusion can only be SDK discipline:
  keep identifiers private and treat outside access as unsupported, as admission step 2 says.

`cookiesDidChange` reported zero changes even in the controls where a cookie landed, so it
was not usable as a witness in this harness. We have not determined why.

## Accepted evidence rule

Accepted by the maintainer as a design direction on 2026-11-03 and recorded in
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md) and
[the admission baseline](native-cookie-store-admission.md). It is not a SPEC amendment or
an implementation, and it narrows the risk rather than fixing its unknown cause.

1. On iOS, an enumeration counts as evidence only after the same process has awaited
   policy completion for that store. Enumerating first is never evidence.
2. Require `fetchDataRecords` and `getAllCookies` to agree, so a single undocumented
   behavior is not the only protection. Disagreement is `unknown` and refuses admission.
3. Keep support claims per measured OS version, and re-run this reopen test on each
   supported version, because the ordering is undocumented. A failed or unmeasured version
   is `unknown`, which already refuses admission under the accepted policy.

Before a production claim, this still needs: a physical device, other iOS versions, device
reboot, service workers, redirects and actual Portal teardown. The new-process question was
later [measured on Android](native-cookie-android-restart-verification.md). Remaining C01–C12, T29, T31, T38, T39 and the
recovery gates are unchanged.

## Environment, verification and cleanup

iOS 26.4.1 on the dedicated iPhone 17 Pro simulator, Xcode 26.4.1 / SDK 26.4, deployment
17.0. Loopback HTTPS hosts only. This is a measured configuration, not a support matrix.

The [isolated experiment](../experiments/native-cookie-partition-probe/README.md) retains
seven reports: 18 partition samples, 20 writer samples, 9 reopened stores, 88 seeded stores
and 88 warmup observations, with 497 server receipt rows and 524 verifier checks.
[first](../experiments/native-cookie-partition-probe/results/ios-first.json) and
[repeat](../experiments/native-cookie-partition-probe/results/ios-repeat.json) classify
identically. See also
[reopen](../experiments/native-cookie-partition-probe/results/ios-reopen.json) and warmup
cycles [a](../experiments/native-cookie-partition-probe/results/ios-warmup-a.json) and
[b](../experiments/native-cookie-partition-probe/results/ios-warmup-b.json).

Three earlier collections preceded these and stay in ignored local results. They showed
the same outcomes but are not retained evidence, for these reasons: the first lacked
delivery proof and a fetch control, the second used one store per strategy in a fixed
order, and the third predated vector formatting that changed source fingerprints. Two
test decisions changed after seeing data, and both are recorded in the experiment README:
adding the warmup strategies, and changing the reopen control, which had wrongly required
the very listing under test.

The host suite has 64 tests covering the fixture, classification and evidence mutations,
and they failed before each helper existed. The verifier checks source fingerprints, the
installed artifact, witnesses and controls, and treats findings as findings.

Only the dedicated simulator ran. It is shut down, all 13 baseline simulator states match,
the fixture is closed, and there are no crash reports for this probe. The fixture's CA was
trusted only inside that simulator. No cookie deletion or import, data wipe, Android work,
intentional crash or known first-call enumeration ran. T28 stays incomplete at 6/44 native
tasks. SPEC, production packages, public API, wire version and release state are unchanged.
