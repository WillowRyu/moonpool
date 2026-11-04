# T28 — OkHttp as the Android broker's client

Date: 2026-11-04 (Asia/Seoul)
Status: Bounded research complete for the cases below. It measures option 1 of
[Android global handlers](native-http-global-handlers-verification.md). **The maintainer accepted OkHttp, pinned to 5.5.1, as the
Android broker's client on 2026-11-04,** as a design direction in
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md). This does not close T28 or accept the rest of that ADR. This
work concerns SPEC §9 and the "never expose host credentials" invariant. It does not amend the SPEC or the protocol, and OkHttp is
still a dependency of the probe alone.

## Result

OkHttp 5.5.1 was configured as a broker would need: no redirects, `retryOnConnectionFailure(false)` and no cache, with the
cookie jar and authenticator left at their defaults. It ran with the same process-wide state set as the earlier report.

**OkHttp did not use the host's global cookie or authentication handlers in any case, and it met the Android transport
requirements. A broker still needs one extra measure, because OkHttp resends on a 503 with `Retry-After: 0`.** The same run shows
those globals were live: each one applied to `HttpURLConnection`, or verification would have failed.

## Isolation from host globals

| Global the host set | `HttpURLConnection`, same run | OkHttp |
| --- | --- | --- |
| `CookieHandler` returning a cookie | Host cookie at the server | Not called, nothing at the server |
| Real `CookieManager`, seeded or capturing | Measured earlier: sent and stored | Not called; nothing sent, nothing stored, including `HttpOnly` |
| `Authenticator` with credentials | Host credentials at the server, client sees 200 | Not called, one attempt, client sees 401 |
| Same, set after the client and call existed | Measured earlier: still applies | Not called |
| `ResponseCache` | Called | Not called |
| Default `SSLSocketFactory` and hostname verifier trusting everything | **Reached a host its certificate does not cover, status 200** | **Refused, no receipt** |
| `ProxySelector` | Called | **Called**, unless `Proxy.NO_PROXY` is set |

All challenge variants returned one attempt and a 401 with no callback: `Basic` GET and POST, a server that keeps rejecting, a
`null` answer, `Bearer`, `Digest` and no header. A broker-attached `Cookie` arrived once and unchanged with a handler set, and a
preset `Authorization` arrived unchanged.

`ProxySelector` is the one global that remains. It receives only scheme, host and port in this run, not the path or query. It is
not a credential, so it is listed as a decision below rather than a conflict.

The trust row is a separate finding about `HttpURLConnection`: a host that weakened validation globally also weakens it for
requests sent with that client.

## Transport requirements

Same vector as the [transport report](native-http-transport-verification.md), with the same outcome as Android
`HttpURLConnection` there.

| Requirement | Result |
| --- | --- |
| Every `Set-Cookie` separate and in order, including `Expires`, a comma in a value, and lowercase names | Yes |
| No ambient cookie after a response set some; attached `Cookie` once and unchanged, GET and POST | Yes |
| 301, 302, 303, 307, 308 returned with `Location` and cookies, zero target hits | Yes |
| 404 and 500 are results with body and cookies | Yes |
| No cache: two server hits for a cacheable URL | Yes |
| Headers visible while the body is held, and not while headers are held | Yes |
| TLS validation on: a certificate outside the scoped CA is refused | Yes |

## Automatic resending

The contract says the SDK never retries. Attempts below are server receipts.

| Case | Broker configuration | Default client |
| --- | --- | --- |
| 408 | 1 | 2 |
| Redirect | 1, target not hit | Followed |
| Connection closed after the request, fresh connection | 1, `IOException` | 1, `IOException` |
| 503 `Retry-After: 5` | 1 | Not measured |
| **503 `Retry-After: 0`, GET and POST** | **2, POST body sent twice** | Not measured |

`retryOnConnectionFailure(false)` does not cover that 503 path, which matches the source at
[a pinned commit](https://github.com/square/okhttp/blob/16fb6aef3aee1c4645fc8d24af01f8a4dc128ebf/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/RetryAndFollowUpInterceptor.kt).
So any server can make a POST run twice by answering this way. Two measures stopped it, each at one attempt:

| Measure | Covers | Cost |
| --- | --- | --- |
| Network interceptor that renames `Retry-After` before OkHttp sees it | GET and POST. The value was kept and readable under the new name | Broker must restore the header in what it reports |
| One-shot request body | POST only | Does not help GET |

The interceptor is the measure that covers both. Source also shows a 421 path for coalesced HTTP/2 connections, which this
HTTP/1.1 run could not reach.

## Costs of depending on it

| Cost | Measured |
| --- | --- |
| Runtime dependencies | `okhttp`, `okhttp-android`, `okio`, `kotlin-stdlib`, `androidx.startup`, `androidx.tracing`, `androidx.annotation`, `annotations` |
| Minimum `compileSdk` it imposes on the app | 5.5.1 and 5.5.0: **37**. 5.4.0: 36. 5.3.2 and the earlier ones checked: none |
| Debug APK, unminified | About 4.1 MB, against about 2.5 MB for the earlier probe. Different code, so a rough difference only |

The `compileSdk` line reads each published `aar-metadata.properties`, and the build did fail against 36. It falls on host
developers, so the version choice matters. It is a build requirement only: the 5.5.1 package declares `minSdk` 21 and no
`targetSdk`, and this probe built with `targetSdk` 36. Only API 37 was run, so devices down to 21 are declared, not measured. Only one OkHttp version can exist in an app, so a host's own version would be resolved
together with the SDK's. That was not measured, and neither was whether older versions behave the same.

## Decisions

Accepted on 2026-11-04:

1. **Which client: OkHttp.** It met what was measured. Not measured: Cronet and `HttpEngine`, which needs API 34, or Android 12 and
   later with SDK extension 7 (`api-versions.xml`: `since="34" sdks="31:7,33:7,34:7,0:34"`).
2. **The OkHttp version: exactly 5.5.1,** reviewed at T56 against the selected host. No host is selected yet, and lowering the
   `compileSdk` burden above later does not break a host.

3. **`ProxySelector`: follow it.** This keeps OS and host proxy behavior and shows the host the scheme, host and port, which is not a
   credential. `Proxy.NO_PROXY` would ignore corporate proxies. Real proxies and proxy authentication are not measured yet.

## Evidence and limits

Two final runs, same artifact and identical findings: 64 observations, 70 server receipts and 213 verifier checks each, and 31 host
tests. Android lint has 0 errors and 3 warnings. OkHttp 5.5.1, API 37 / Android 17, WebView 145.0.7632.218 on the dedicated AVD.

- One emulator configuration, one OkHttp version, HTTP/1.1 over loopback, and one app playing both host and broker in one process.
- HTTP/2 and its 421 path, real proxies, proxy authentication, mid-body failure and cancellation are not measured.
- The closed connection case uses a fresh connection. A resend on a reused pooled connection, which is what that setting mainly
  governs, is not exercised.
- A pass shows OkHttp could serve a broker, not that one exists. No broker was built.

Nothing was added to the device trust store. A trust-everything socket factory exists in the probe to stand for a careless host,
for two cases against the owned fixture, and is cleared afterwards. The dedicated emulator is stopped and `adb` matches its baseline.
Fixture closed, no crashes. Test keys went to the Trash, so the maintainer still empties it. Source and criteria are in
[the probe](../experiments/native-http-okhttp-probe/README.md).

## Reproduce

Retained results need no device:

```sh
cd experiments/native-http-okhttp-probe
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B verify_results.py --summary results/*.json
```
