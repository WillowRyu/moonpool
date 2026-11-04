# T28 — A native broker measured against the proposed cookie/HTTP contract

Date: 2026-11-05 (Asia/Seoul)
Status: Bounded research complete for the 58 cases below, after the maintainer resumed the experiment paused on
2026-11-04 and then asked for the code review findings to be fixed. It measures the [proposed contract](native-cookie-http-contract.md) and
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md) with the accepted clients: OkHttp 5.5.1 on
Android and `URLSession` on iOS. **It does not complete T28 and changes no SPEC or protocol text.** C04, C09–C12,
real Portals and the bridge are still not covered, OkHttp remains a dependency of this probe alone, and the broker's
field names and error values stay proposals under test.

## Result

Two research brokers ran the same 58 cases against one owned loopback HTTPS fixture, two collections per platform.

**All 58 cases met the oracle on both platforms in all four collections, and the normalized guest-visible result,
including response headers, server receipts and jar effects are identical across platforms and across runs.** No host cookie and no host
credential reached a broker request in any case, while the same process kept both of them live for its own client.

One platform difference survives, and the cases declare it a measurement rather than judging it: the iOS resend after a
`Basic` 401. The resend itself was already measured and accepted — follow the OS, keep the 401, document it — in the
[transport report](native-http-transport-verification.md). What is new is its two consequences, both of which that
report listed as open questions: **iOS leaves the second response's cookie in the jar, and it replays the guest's own
`Authorization` on the extra attempt.** Everything else is parity, within these cases. One accepted limit is also newly
measured, and the contract now states it: a comma in a cookie value can drop `HttpOnly` on both platforms.

## What the 58 cases establish

| Group | Cases | What the paired evidence shows |
| --- | --- | --- |
| Controls | 3 | A plain request succeeds; default validation with the device's own roots refuses the probe certificate; a host ambient cookie and a host `Basic` credential are live in the same process, answer the host's own client, and never appear on a broker request |
| C01 ownership and dispatch | 2 | Two apps keep separate jars, and the second Portal of one app reuses its app's jar; a missing `http` grant, a `cookies`-only grant, an unapproved target and a retired Portal are refused `-32000`; forged `appId`, `jar` and `context` params are refused `-32602` with no receipt; cookie values never reach guest-visible output |
| C02 credentials | 7 | Cookies are included by default; `credentials: "omit"` suppresses both the send and the store, and leaves an earlier login intact; a guest's own `Authorization` still travels under `omit`; ten forbidden request headers, including case variants and `Sec-*`, are refused `-32602` with no receipt, while an ordinary header passes; a field of the wrong type, including `credentials: false`, a missing `url` and unsafe header text, is refused `-32602` with no receipt |
| C03 `HttpOnly` and projection | 8 | An `HttpOnly` cookie is sent by the broker but is unreadable to the guest, and guest overwrite, expiry and delete attempts on it are refused `-32000`; a guest asking for `httpOnly: true` is refused `-32602`; `Set-Cookie` never appears in guest-visible headers; one parse pipeline splits a comma-joined field but not an `Expires` comma; the same name on two paths is returned deep-first; script cookies must follow the RFC 6265 grammar, so `1; prot=guest` cannot add a pair; an empty `Set-Cookie` field is ignored; a server cookie that could not be sent back is dropped instead of blocking later requests |
| C05 service context | 8 | `SameSite` attributes do not change what a native send carries, and `SameSite=None` without `Secure` is dropped; `http`, userinfo, a fragment and a forged first-party claim are refused `-32602`; a foreign host and an unapproved second port are refused `-32000`; when both ports are approved they share one jar, and two approved hosts do not; an omitted port means 443 and an IPv6 literal has one spelling |
| C06 redirects and status | 18 | 301, 302, 303, 307 and 308 are returned to the guest and never followed, including to a forbidden target and under `omit`; 404, 500 and an empty 204 arrive intact; `Bearer` 401 takes exactly one attempt; a 503 with `Retry-After: 0` reaches the guest with that header and exactly one attempt; a mid-body failure keeps the cookie that was already committed; POST, PUT, PATCH, DELETE, OPTIONS and HEAD work without a body, while a body on GET or HEAD and any other method are refused `-32602`; a response taking 12 seconds still arrives |
| C07 ordering and Portal lifetime | 4 | An awaited set and delete are visible to the other Portal of the same app before the next send; two held responses commit in release order rather than request order, and the last commit wins; a recreated Portal reuses the app jar but needs its own grant; closing a Portal with work in flight withholds the result from the closed Portal and still commits the cookie — closing a Portal is not logout |
| C08 reset and stale work | 8 | Reset settles stale work with `-32007` and the proposed `reason: "sessionReset"`; a reset before headers fences the stale commit and leaves nothing of it in the jar or in guest output; a reset after headers clears an already committed cookie and the late body does not re-add it; an already settled response is untouched; queued work never reaches the network; two resets followed by a fresh login keep only the fresh cookie; reset needs the `http` grant; the host's own cookies survive it; and work queued on a closed Portal never reaches the network |

`-32000` and `-32602` are the existing `PERMISSION_DENIED` and invalid-params codes. `-32007` is the existing
`HOST_UNAVAILABLE` code carrying the contract's proposed fixed `reason` value; the SPEC does not define that value yet.

## The one platform difference

| Measured on a `Basic` 401 | Android, OkHttp 5.5.1 | iOS, `URLSession` |
| --- | --- | --- |
| Attempts the server received | 1 | **2** |
| Responses that reached the broker's response callback | 1 | 1, **the second attempt's** |
| The guest's preset `Authorization` on the extra attempt | — | **Resent unchanged** |
| Cookie left in the jar, fixture serving a different one per attempt | `attempt=1` | **`attempt=2`** |
| Host credential at the server | Never | Never |
| Status the guest saw | 401 | 401 |

The resend is not reopened here. Every `URLSession` disposition that keeps the 401 makes the second attempt, and the
only one that makes a single attempt, `.cancelAuthenticationChallenge`, replaces the correct 401 with error `-999`.
The maintainer accepted following the OS and documenting the resend on 2026-11-03.

The broker's iOS session is also as closed as its configuration allows: `URLSessionConfiguration.ephemeral` with
`httpCookieStorage` nil, `httpCookieAcceptPolicy` `.never`, `httpShouldSetCookies` false, `urlCache` nil and
`urlCredentialStorage` nil, and its task-level challenge handler answers `.rejectProtectionSpace` with no credential.
So the two consequences below are not a configuration mistake.

**1. The jar keeps the second response's cookie.** The first 401 arrives as an authentication challenge and never
reaches the response callback. For two server attempts the broker recorded one `headers` event and one `commit` event,
and that commit held the cookie the fixture served on its second arrival. The probe already commits once per guest
request, so a "commit only the first response" rule cannot help: the only `Set-Cookie` it reads is the second one.

A guest that reads its cookies after this exchange sees `attempt=1` on Android and `attempt=2` on iOS. ADR 0027 requires
the same behavior on both platforms, and the accepted principle is to follow OS behavior **unless what a mini app sees
differs per platform**, so this breaks parity. The case is narrow, and the fixture builds it on purpose by changing the
cookie per attempt. By inference, not measured: a server sending the same cookie twice leaves equal jars, and one setting
a cookie only on the first attempt leaves the iOS jar without it.

**Measured on 2026-11-05:** the challenge handler can read the first response's `Set-Cookie` through
[`failureResponse`](native-http-failure-response-verification.md), so a broker could match Android. OPEN, the maintainer's decision, not
made: whether to apply that here, or to accept and document the difference. The probe keeps the measured behavior until then.

**2. The guest's own `Authorization` is replayed once.** The second attempt carried `Bearer guest-owned` unchanged. This
is the other question the transport report left open, and it is the lockout risk that report predicted: a server counting
failed attempts sees two. No host credential is involved, which the verifier asserts for every case. The challenge
handler runs between the attempts, but none of its dispositions can edit the resend's headers, and the one that stops the
resend was already rejected because it loses the 401; this reads the API and was not measured separately. Under the
accepted resend decision, the remedy is to state the doubled attempt in the contract so a mini app developer can expect it.

## A documented limit, now measured

The fold-then-split pipeline is an accepted decision, and it stays: iOS cannot expose separate `Set-Cookie` fields. The
contract records its cost as an extra cookie. This run adds a consequence the contract does not mention, on both platforms:

```text
Sent:           Set-Cookie: sid=abc, x=y; Path=/; Secure; HttpOnly
Jar:            sid=abc, x=y
A guest reads:  sid=abc
```

The attributes stay with the last piece, so `sid=abc` loses `HttpOnly` and a mini app can read it. This concerns SPEC §9.
RFC 6265's server grammar excludes commas from cookie values, so it takes a non-conforming server. A stricter rule cannot be
precise, because on iOS the same text also comes from two honest fields.

The maintainer accepted keeping the pipeline and stating this in the contract on 2026-11-05. The broker is unchanged.

## Code review fixes

A code review on 2026-11-05 listed 15 findings: 14 are fixed, and the fifteenth is the limit above. Failing cases came
first. 14 new scenarios ran against the unfixed broker and failed 11 cases on Android and 6 on iOS. Inputs that would crash
iOS or abort a whole collection were guarded before that run, because a crash opens a dialog the maintainer asked to avoid.
So `c03-cookie-fields-malformed`, the missing `url`, and on iOS the CR/LF, method and header-text inputs were not seen failing.

| Finding | Before | Now |
| --- | --- | --- |
| Script cookie text | `1; prot=guest` was accepted, and on iOS a name with `;` reached the server as `a;b=x`; CR/LF made Android's later requests fail `-32603` | Refused `-32602` by the RFC 6265 grammar |
| Field types on iOS | `credentials: false` sent cookies; one bad header value skipped the forbidden-header check; `as!` on guest data | Refused `-32602`, with no force cast on guest data |
| Default port | Android looked up `host:-1`, so it refused every URL without a port | Both use 443 |
| IPv6 host | The approved key never matched `[::1]` on either platform | One spelling, without brackets |
| POST without a body | Android failed `-32603` before sending | Sent empty, as on iOS |
| Method and body rules | Not checked. Android sent `TRACE` and failed `-32603` on a GET with a body. iOS failed that GET `-32007`, and **a HEAD with a body had not finished after the 40-second barrier** | One list of seven methods, and no body on GET or HEAD |
| Queued work on a closed Portal | Reached the server, and its response cookie was committed | Settles `delivered: false` with no request |
| Timeouts | OkHttp's 10 seconds against iOS's 40 | 40 on both |
| `Set-Cookie: ;` | Android turned a 200 into `-32007 network` | Ignored |
| Non-ASCII server cookie (found while fixing) | Android's later requests failed; iOS sent it back | Dropped on both |
| TLS control | Any failure counted as a refusal | Only TLS errors count. Seen: `SSLHandshakeException`, and `-1202` on iOS |
| Hold timeout | Recorded as released, and iOS ignored a failed release | Recorded as `holdTimedOut`, which fails verification |
| Reused run tag | Mixed receipts, attempts and holds from two runs | Refused before launch |
| iOS artifact hash | Covered the executable, not `Fixtures` | Covers both |
| Platform comparison | Left out response headers | Compares them, without `Date` and a `Location`'s run tag and port |
| Runner | Checked the hash after launching, and stopped the device only on success | Checks before launching, and always stops |
| iOS `committed` guard | Never ran in these cases, and its comment implied otherwise | Removed, with the measured fact in the comment |

## Evidence and limits

Four collections, two per platform, one artifact per platform, identical findings: 58 cases each and 232 case results,
all pass. 1658 verifier checks (413 per Android run, 416 per iOS run). 426 fixture receipt rows — 402 arrivals and 24 hold
releases, with no hold timed out — every row over TLS and correlated to its own run. 64 host tests. Android lint has 0 errors
and 3 warnings. The earlier 44-case collections are in Git history; these replace them, because the sources changed.

- Android 17 / API 37 on the dedicated `Pixel_7_Pro` AVD (`sdk_gphone16k_arm64`, build `CE2A.260420.050`), OkHttp
  5.5.1. iOS 26.4.1 on the dedicated `Moonpool T28 Origin Contract` simulator (iPhone 17 Pro profile), built with Xcode 27.0
  (27A266a) and simulator SDK 27.0 at deployment target iOS 17.0.
- Earlier retained iOS evidence in this series was built with Xcode 26.4.1 / SDK 26.4. This build links against SDK 27.0
  and runs on the 26.4.1 runtime. Nothing from the paused attempt was retained, so these are fresh collections, and its
  toolchain is unknown.
- One emulator and one simulator configuration, HTTP/1.1 over loopback, one app per platform playing both host and
  broker in one process. Portals here are in-process objects holding an app id and grants, not documents in a web view.
- Not covered: C04, which needs a frozen cookie profile; C09–C12; real Portals, the real kernel, the bridge and WebView
  stores; HTTP/2 and its 421 path; real proxies and proxy authentication; redirect-following login flows.
- The fixture records the method, body length, `Cookie` and `Authorization`. Headers a client adds itself, such as
  `User-Agent`, `Accept` or a default `Content-Type`, are not recorded, so a server-side difference there would not show.
- The method list and the script cookie grammar are choices made for this probe. The contract fixes neither yet.
- The broker's cookie parser is only the subset these cases need, and its request/response schema is a proposal. A pass
  shows these clients could serve a broker under the proposed contract, not that a broker exists. None does.

Nothing was added to a device trust store: server trust is pinned to the probe's own CA inside each app, and the
negative control confirms the device's own roots refuse that certificate. Both devices were booted by this task and are
stopped again; the 25 other simulators and the unrelated `HereThere_Push_API36` AVD were never started, and all
simulator baseline states match. The `adb` server was not running before this task and is stopped again. The fixture is
closed, no crash control was run, the probe apps stay installed on both owned devices, and the probe's generated test CA and server keys went to the macOS Trash, so the
maintainer still empties it. Source and criteria are in [the probe](../experiments/native-http-broker-probe/README.md).

## Reproduce

Retained results need no device:

```sh
cd experiments/native-http-broker-probe
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B verify_results.py --summary results/*.json
```
