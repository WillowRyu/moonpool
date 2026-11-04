# T28 — Reading the first 401 through `failureResponse`

Date: 2026-11-05 (Asia/Seoul)
Status: Bounded research complete for the cases below, iOS only, requested by the maintainer after the
[broker report](native-http-broker-verification.md). It measures one question and applies nothing: the research broker, the
[contract](native-cookie-http-contract.md), the SPEC and the protocol are unchanged by it.

## Result

After the accepted iOS `Basic` 401 resend, the jar keeps the second response's cookie and Android's keeps the first, because the first
401 goes to the challenge handler and never to the response callback. The question was whether that handler can read the first
response's `Set-Cookie`.

**It can. `URLAuthenticationChallenge.failureResponse` showed exactly what the fixture served on arrival 1 in all 8 `Basic` cases, in
both runs, so the criteria [written before collection](../experiments/native-http-failure-response-probe/README.md) call it usable.**

| Case | Fixture served on arrival 1 | `failureResponse` showed | Response callback delivered |
| --- | --- | --- | --- |
| Cookie per attempt | `attempt=1` | `attempt=1` | `attempt=2` |
| First attempt only | `first=1` | `first=1` | None, so iOS loses this cookie today |
| Second attempt only | None | None | `second=2` |
| Two fields | `a=1`, `b=2; HttpOnly` | Both, folded with `, ` | `c=3` |
| No cookie | None | None | None |
| POST, with a body on both attempts | `attempt=1` | `attempt=1` | `attempt=2` |
| Guest's own `Authorization` on both attempts | `attempt=1` | `attempt=1` | `attempt=2` |
| `.performDefaultHandling` instead of `.rejectProtectionSpace` | `attempt=1` | `attempt=1` | `attempt=2` |

Every `Basic` case had one challenge callback with `previousFailureCount` 0 and status 401, and two server arrivals. The three controls,
a plain 200, a `Bearer` 401 and a 401 with no challenge, had one arrival and no callback.

## What it would and would not fix

A broker could commit from `failureResponse` and ignore the resend's cookies, which would leave the same jar as Android in every case
above. That closes the parity item in the broker report.

It would not change the rest of the resend:

- The server still receives two attempts, and the guest's own `Authorization` still goes on both.
- The status and body the guest receives still come from the second attempt: `bodyText` named arrival 2 in every `Basic` case, while
  Android delivers its only attempt. Both are a 401, so this shows only if a server changes its 401 body between attempts.

OPEN, the maintainer's decision, not made: whether to apply this to the research broker. It would refine an accepted rule, "commit at
header delivery", because on iOS a `Basic` 401's cookies would commit at the challenge instead, and the session reset fence would have to
cover that point too. It also changes the broker's sources, so all 58 cases would be collected again on both platforms.

## Evidence and limits

Two collections with one artifact and the same measurements: 22 observations, 38 fixture receipt rows, every row over TLS, 64 verifier
checks per run and 25 host tests. iOS 26.4.1 on the dedicated `Moonpool T28 Origin Contract` simulator (iPhone 17 Pro profile), built with
Xcode 27.0 (27A266a) and simulator SDK 27.0 at deployment target iOS 17.0.

- One simulator configuration and one OS version, HTTP/1.1 over loopback, with a session configured like the research broker's but no
  broker or jar. The SDK header says the property holds the response representing the authentication failure, and it promises nothing
  about the header fields, so this is a measured behavior and should be rerun on each OS version a release supports.
- `Digest`, `NTLM`, `Negotiate`, `.useCredential`, HTTP/2 and proxies are not measured.
- Android was not run. Its behavior is the first attempt's cookie, as retained in the broker report.

Nothing was added to a device trust store, because server trust is pinned to the probe's own CA inside the app. The simulator was booted by
this task and is stopped, and all 26 simulator baseline states match. No emulator or `adb` server was started. The fixture is closed, no
crash occurred, and the generated test keys went to the macOS Trash, so the maintainer still empties it. The probe app stays installed on
the simulator.

## Reproduce

Retained results need no device:

```sh
cd experiments/native-http-failure-response-probe
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B verify_results.py --summary results/*.json
```
