# T28 native HTTP transport primitives

Bounded experiment requested on 2026-11-03 as the first step of the
[common cookie/HTTP plan's](../../docs/native-cookie-http-conformance-plan.md) broker work. Before
building an app-owned cookie jar, this asks whether each platform's standard HTTP client provides what
the [contract](../../docs/native-cookie-http-contract.md) assumes. Research only: no cookie jar, broker,
guest bridge, public API, SPEC or protocol change. No cookie store is written and no WebView is used.

## Retained result

Read the [verification report](../../docs/native-http-transport-verification.md). Four reports hold 136 observations, 164 server receipt rows
and 184 verifier checks. A broker looks buildable on these clients, but iOS folds `Set-Cookie`, resends a
request after a `Basic` challenge and delivers headers only with the first body byte. The maintainer accepted
one cookie pipeline and otherwise following OS behavior as a design direction.

## Criteria written before collection

The same vector runs on Android `HttpURLConnection` and iOS `URLSession`, each configured as a broker would
need: no ambient cookies, credentials or cache, and no automatic redirects. Server receipts are the
witness for everything the server can see.

| Question | Why the contract needs it | Evidence |
| --- | --- | --- |
| Can every `Set-Cookie` field be read separately and in order? | It says to preserve separate fields and reject invalid ones without repair | Client's view compared with the exact fields sent |
| If fields are folded, can splitting recover them? | Otherwise a common parser sees different input per platform | Includes an `Expires` date and a value containing a comma and `name=` |
| Are header names matched regardless of case? | HTTP/2 sends lowercase names | Lowercase `set-cookie` response |
| Does the client send cookies by itself? | Selection belongs to the broker | Server sees no `Cookie` after a response set some |
| Does a broker-attached `Cookie` arrive unchanged, once? | Otherwise the broker cannot attach its selection | Exact raw field at the server, for GET and POST |
| Are 301, 302, 303, 307 and 308 returned instead of followed? | Redirects must be manual, with the original cookies still visible | Status and `Location` seen, zero target hits, plus a target control |
| Are 4xx and 5xx ordinary results with body and cookies? | HTTP status must not become a bridge failure | Status, body and `Set-Cookie` visible |
| Is a 401 challenge returned without credential reuse? | No ambient authentication | One attempt, no `Authorization` |
| Does anything cache? | The contract has no shared response cache | Two server hits for one cacheable URL |
| Are headers visible before the body arrives? | Cookies commit at header time, and reset fences that moment | Response visible during a held body, and not during held headers |

The first collection, kept only in ignored local results, showed iOS folding `Set-Cookie`, sending a
challenged request twice and hiding headers while the body was held. Added to narrow those without changing
any definition: challenge responses with each iOS disposition, for GET and POST, plus `Bearer` and no `WWW-Authenticate`; held bodies with
`nosniff`, one early byte and one early kilobyte; and a check that one fold-then-split pipeline gives both
platforms the same cookie lines.

Findings do not fail verification. Missing controls do: a plain request and the redirect target must
work, every request needs a server receipt, held requests must be released, and a TLS negative must be
refused with no receipt, which proves validation is on rather than disabled for the test.

Each platform's own cookie parser runs on the same input as a diagnostic only. The contract says not to
derive the oracle from either, so its output is reported, not judged.

## Safety and scope

Use public fixture values and the existing dedicated simulator and AVD only, recording their state first
and restoring it after. **Nothing is added to any device trust store.** iOS pins server trust to a CA
bundled in this probe through its session delegate, and Android scopes it to `localhost` and `127.0.0.1` in
this APK. Hold controls use a separate listener. An unexpected process exit stops the run without retry.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py android
python3 -B build.py ios
python3 -u -B fixture.py
python3 -u -B run_probe.py android --run first --install
python3 -u -B run_probe.py ios --run first --install
python3 -u -B run_probe.py android --run repeat
python3 -u -B run_probe.py ios --run repeat
python3 -B verify_results.py --summary results/*.json
```

## Limits

One emulator and simulator configuration over HTTP/1.1 on loopback. HTTP/2, proxies, mid-body network
failure, cancellation and third-party clients such as OkHttp or Cronet are not covered. Passing here shows
a broker could be built on these clients, not that one exists.
