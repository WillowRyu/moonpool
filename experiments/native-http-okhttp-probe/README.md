# T28 OkHttp as the Android broker's client

Bounded experiment requested on 2026-11-04, after [Android global handlers](../../docs/native-http-global-handlers-verification.md)
reached `HttpURLConnection` with no per-request opt-out. This asks whether OkHttp 5.5.1 avoids that and still meets what
the [contract](../../docs/native-cookie-http-contract.md) assumes. Research only: OkHttp is a dependency of this probe alone.
No broker, cookie jar, guest bridge, public API, SPEC or protocol change. No WebView is used.

## Criteria written before collection

One app plays the host and sets process-wide state. Each case gets fresh state and clears it afterwards. Server receipts are
the witness for what left the client, and callbacks are the witness for what host code could see.

The client is configured as a broker would need: `followRedirects(false)`, `followSslRedirects(false)`,
`retryOnConnectionFailure(false)` and no cache. **The cookie jar and authenticator are left at their defaults**, because those
defaults are what is being measured.

| Question | Why it matters | Evidence |
| --- | --- | --- |
| Do a global `CookieHandler` and `Authenticator` reach OkHttp requests? | The conflict that started this | Receipts and callback counts, for GET and POST, a real `CookieManager`, every challenge scheme, and globals set after the client exists |
| Does the same run show those globals are live? | Otherwise "ignored" proves nothing | The same globals on `HttpURLConnection` in the same run must apply, or verification fails |
| Do other globals reach it? | The earlier report left them open | `ResponseCache`, `ProxySelector`, and default `SSLSocketFactory` and hostname verifier, each with an `HttpURLConnection` control |
| Does it still meet the [transport requirements](../../docs/native-http-transport-verification.md)? | Results there were for `HttpURLConnection` | Same vector: separate `Set-Cookie` fields, attached cookies, five redirects, 4xx and 5xx, no cache, header timing |
| Does anything resend a request? | The contract says the SDK never retries | Attempts at the server for 408, 503 with `Retry-After`, and a connection closed after the request |
| Can a broker stop a resend? | Source shows 503 with `Retry-After: 0` resends regardless of `retryOnConnectionFailure` | One-shot body and a network interceptor hiding the header, for GET and POST |
| What do the defaults do? | Shows which settings a broker must change | The default client on a redirect, a 408 and a closed connection |

Findings do not fail verification. Missing controls do: requests with no globals must stay clean before and after every case; a
global must be in place at send time; every request needs a server receipt; only the public fixture credential may appear; and
both TLS negatives must be refused with no receipt.

## Safety and scope

Public fixture values only, and the existing dedicated AVD only, recording its state first and restoring it after. **Nothing is
added to any device trust store.** The CA is scoped to `localhost` and `127.0.0.1` in this APK. A trust-everything socket factory
exists in this app to stand for a careless host, is installed only for two cases that talk to the owned fixture, and is cleared
afterwards. An unexpected process exit stops the run without retry. No iOS device is used.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
python3 -u -B fixture.py
python3 -u -B run_probe.py --run first --install
python3 -u -B run_probe.py --run repeat
python3 -B verify_results.py --summary results/*.json
```

## Limits

One emulator configuration over HTTP/1.1 on loopback, with one app playing both host and broker in one process and one OkHttp
version. HTTP/2 and its 421 path, real proxies, mid-body network failure and cancellation are not covered. Cronet and
`HttpEngine` are not measured. A pass shows OkHttp could serve a broker, not that one exists.
