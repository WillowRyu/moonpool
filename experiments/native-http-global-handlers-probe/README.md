# T28 Android global HTTP handlers

Bounded experiment requested on 2026-11-04, the first item under "Before building on this" in the
[HTTP transport report](../../docs/native-http-transport-verification.md). A host app can set the process-wide
`java.net.CookieHandler` and `java.net.Authenticator`, and Capacitor sets the former. The earlier run had neither.
This asks whether they reach requests a broker sends with `HttpURLConnection`, because they could carry
host credentials to a mini app's server. Research only: no broker, cookie jar, guest bridge, public API, SPEC or
protocol change. No WebView is used.

## Retained result

Read the [verification report](../../docs/native-http-global-handlers-verification.md). Both handlers reach broker requests
and this client has no per-request way to turn them off, which conflicts with the proposed contract. Two reports hold 62
observations, 110 server receipts and 216 verifier checks. A decision is open.

## Criteria written before collection

One app plays the host. Each case gets fresh handlers and clears them afterwards. Server receipts are the witness for
everything the server can see, and handler callbacks are the witness for what the host's code could see.

| Question | Why it matters | Evidence |
| --- | --- | --- |
| Does a global `CookieHandler` add cookies to a request? | The contract says no ambient cookies, and these are host cookies | Exact `Cookie` fields at the server for GET and POST |
| What happens to a cookie the broker attached? | The broker must be the only one selecting cookies | Exact fields with a handler returning a cookie, and returning nothing |
| Does the handler receive `Set-Cookie`, including `HttpOnly`? | Protected cookies would reach host code | `put` callback, including on a returned 302 |
| Does a real `CookieManager` send seeded and captured cookies? | This is the class hosts actually extend | Receipts for a seeded cookie, another domain and a follow-up request |
| Does a global `Authenticator` answer a challenge? | Host credentials would reach the mini app's server | `Authorization` at the server, attempts, status the client sees, for GET and POST |
| Does this depend on the scheme or on the answer? | Limits how far the exposure goes | `Basic`, `Bearer`, `Digest`, no header, a `null` answer, a server that keeps rejecting |
| What happens to a preset `Authorization`? | A broker or guest may set one | Exact value at the server per attempt |
| Does streaming mode or a per-connection `setAuthenticator` opt out? | A broker needs a per-request answer, since it may not change a host's globals | Callback counts, receipts and any exception. The method is desktop Java and absent from `android.jar`, so only reflection can look for it |
| When is each global read? | Decides whether checking first and then opening can be trusted | Installing and clearing after `openConnection`, before anything is sent |
| Can an SDK see that they are set? | Admission could refuse | `getDefault` by reflection on this API level, and asking the global with `requestPasswordAuthentication`, which sends nothing but runs host code |

The first launch stopped before any request because the harness assumed `Authenticator.getDefault`, which only desktop
Java has. Reading `android.jar` directly shows neither it nor `setAuthenticator` is declared. That launch produced no
observations. The `requestPasswordAuthentication` question was added to measure detection, with no other definition changed.

Findings do not fail verification. Missing controls do: requests with no globals must carry no cookie or credential both
before and after every case, which also proves clearing works; a global that was not in place at send time cannot count as
ignored; every request needs a server receipt; only the public fixture credential may appear; and a TLS negative must be
refused with no receipt, which proves validation is on.

## Safety and scope

Public fixture values only, and the existing dedicated AVD only, recording its state first and restoring it after.
**Nothing is added to any device trust store.** The CA is scoped to `localhost` and `127.0.0.1` in this APK. An
unexpected process exit stops the run without retry. No iOS device is used, because these are Android APIs.

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

One emulator configuration over HTTP/1.1 on loopback. One app plays both host and broker in one process. Other process-wide
state a host can set is not covered: `ResponseCache`, `ProxySelector`, and the default `SSLSocketFactory` and hostname
verifier. Neither are OkHttp, Cronet or `android.net.http.HttpEngine`.
