# T28 — Android global HTTP handlers

Date: 2026-11-04 (Asia/Seoul)
Status: Bounded research complete for the cases below. **It found a conflict with the
[proposed contract](native-cookie-http-contract.md).** The maintainer resolved it on 2026-11-04 by accepting OkHttp as the Android
broker's client; see [ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md). This does not close T28 or accept the rest of [ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md). This
work concerns SPEC §9 and the "never expose host credentials" invariant. It does not amend the SPEC or the protocol.

## Result

The [transport report](native-http-transport-verification.md) measured Android `HttpURLConnection` with no process-wide
handlers set. A host app can set `java.net.CookieHandler` and `java.net.Authenticator` for its whole process, so this
run repeated requests with them set. Server receipts are the witness.

**Both handlers reach broker requests, and this client has no per-request way to turn them off.**

The contract says native clients "must disable their ambient cookie handlers and shared credential stores" and "never
modify application-global native settings". On `HttpURLConnection` those two sentences cannot both hold while a host has
set either handler. With neither set, the earlier result stands: the plain and `Basic` 401 controls before and after every
case sent no cookie, no credential and one attempt.

## CookieHandler

| Case | Measured |
| --- | --- |
| Handler returns a host cookie, GET and POST | Host cookie arrives at the server |
| Same, and the broker attached a `Cookie` | Two separate `Cookie` fields: broker's first, then the host's |
| Handler returns nothing, and the broker attached a `Cookie` | Broker's field arrives once and unchanged |
| Response sets cookies, including `HttpOnly` | Handler receives every `Set-Cookie`, and the client still sees them |
| Returned 302 with `Set-Cookie` | Handler receives it. Redirect still not followed |
| Real `CookieManager` seeded with a cookie for this host | Arrives at the server, as `$Version="1"; host_session="host-fixture";$Path="/";$Domain="localhost"` |
| Real `CookieManager` seeded for another domain | Not sent |
| Real `CookieManager`, response then a second request | `HttpOnly` cookie stored, and both cookies sent on the second request |

So traffic runs both ways: host cookies reach the mini app's server, and that server's cookies, including `HttpOnly`,
reach host code and any jar behind it. Each callback also receives the full URL including the query string. The request
header map it receives lists a broker-attached `Cookie`; only header names were recorded, not values.

## Authenticator

| Case | Attempts | With host credentials | Client sees |
| --- | --- | --- | --- |
| `Basic` 401, server accepts, GET | 2 | 1 | 200 |
| `Basic` 401, server accepts, POST | 2, body sent both times | 1 | 200 |
| `Basic` 401, server keeps rejecting | 21 | 20 | `ProtocolException`, no status |
| `Basic` 401, authenticator answers `null` | 1 | 0 | 401, but host code ran and saw the URL and realm |
| `Basic` 401, broker preset `Authorization: Bearer` | 2 | 1, replacing the preset | 200 |
| `Basic` 401 with both handlers | 2 | 1 | 200. Handler received the 401's and the 200's cookies; the client saw only the 200's |
| `Bearer`, `Digest`, or 401 with no `WWW-Authenticate` | 1 | 0 | 401, authenticator not called |

A server only has to answer `Basic` to receive whatever the host's authenticator returns, base64 encoded. A rejecting
server turns one request into 21, which is automatic retrying the contract rules out, and a 401 stops being a normal
result. Credentials did not reach the mini app's JavaScript in these cases, only its server.

## Opting out and detecting

| Candidate | Measured | Does it help? |
| --- | --- | --- |
| Per-connection `setAuthenticator` | Absent: not in `android.jar` and `NoSuchMethodException` at run time. It is desktop Java | No |
| Per-connection cookie handler | No such API exists in `android.jar` | No |
| `setFixedLengthStreamingMode` on POST | Authenticator still called, nothing resent, `HttpRetryException` and no status | Partly: credentials stay home, but host code runs, the 401 is lost, and GET has no body to stream |
| `CookieHandler.getDefault()` | Available, and shows the handler | Detects at that moment |
| `Authenticator.getDefault()` | Absent, as above | No |
| `Authenticator.requestPasswordAuthentication` | Tells an installed answering authenticator from a cleared one, and sends nothing | Runs host code with a made-up request. By its nature it cannot see one that answers `null` for that request |

Timing limits any check made first. Installed or cleared after `openConnection` but before anything was sent, the
`CookieHandler` kept its state from `openConnection`, while the `Authenticator` used whatever was set when the challenge
arrived. A check before opening has a window for the handler, and for the authenticator it says nothing about later.

## How similar projects handle this

Read from source at pinned commits on 2026-11-04. None were run or device tested, so any effect on requests is inferred from
the measurements above. A code search finding nothing is weak evidence, so absence below is checked in the named files.

| Project | Android native HTTP | Global handlers | Guest treated as |
| --- | --- | --- | --- |
| [Capacitor](https://github.com/ionic-team/capacitor/tree/8b89254e21d7af2f22067c61efa9612456a9479d) | `HttpURLConnection`, off by default (`enabled` false) | **Sets** a global `CookieHandler` when its cookie plugin loads, which `Bridge` registers by default, without checking `enabled` there. No `Authenticator` handling in its HTTP utilities | App code |
| [Ionic Portals](https://github.com/ionic-team/ionic-portals-android/tree/e4c62bce1d6118b3b515542477a109718f3533ed) | None of its own: builds a Capacitor `Bridge` and inherits the above | Inherited | App code, with host-chosen plugins |
| [Cordova advanced HTTP](https://github.com/silkimen/cordova-plugin-advanced-http/tree/1f5b0f5b492a835c137bccca32ca12f6def00ee7) | `HttpURLConnection` through a bundled wrapper | Neither named in that wrapper | App code |
| [React Native](https://github.com/facebook/react-native/tree/edf2b86e63b311cd844a53b7fba474e9b0994658) | OkHttp, one configured client | Not used. Its `CookieHandler` subclass is passed to one client's jar, forwarding to the WebView store. `withCredentials: false` selects `NO_COOKIES` per request | App code |
| [Expo fetch](https://github.com/expo/expo/tree/c59120da912d8bc1b3dadf7a75e320541e2a1a63) | React Native's OkHttp client | Same | App code |
| [Tauri HTTP plugin](https://github.com/tauri-apps/plugins-workspace/tree/74a44c1d5694324b7fb9ba5ee9271a3096da9387) | Rust `reqwest`, with its own `.cookies` jar | Outside the JVM, so these APIs are not in its path | Scoped: URL allowlist, and optionally every redirect hop |
| [Flutter `ok_http` / `cronet_http`](https://github.com/dart-lang/http/tree/1f869d02260b485e1a5b923c5f02c9697402c6a6) | OkHttp, or Cronet from Play Services or embedded | Per-client wrappers | App code |

**No surveyed project defends against a host's global handlers on purpose.** Projects on `HttpURLConnection` inherit them. Projects
on another client avoid them as a side effect. This does not show the risk is unimportant: all but Tauri treat web code as the
app's own, while Moonpool treats a mini app as untrusted, and Portals' web traffic normally goes through the WebView rather than
native HTTP. Tauri's scope model is the closest, including its reasoning that an allowed server can redirect anywhere.

What this adds for option 1:

- [OkHttp's defaults at a pinned commit](https://github.com/square/okhttp/blob/16fb6aef3aee1c4645fc8d24af01f8a4dc128ebf/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt) are `Authenticator.NONE` and `CookieJar.NO_COOKIES`, per client.
  `JavaNetCookieJar` takes a handler as an argument rather than reading the global. This is the expected behavior to measure.
- A broker would have to change two defaults: `followRedirects` is true, and `retryOnConnectionFailure` is true, which conflicts
  with "the SDK never retries" unless set false.
- OkHttp still reads one global: `ProxySelector.getDefault()` unless a selector is set. It also uses platform trust by default.
- `ok_http`'s README reports example APK sizes of 20.3 MiB for OkHttp, 20.6 for Play Services Cronet, 34.4 for embedded Cronet and
  20.4 for `dart:io`. That is a Flutter example, so it shows relative cost only. It also notes Play Services is not on all devices.

## Options for the decision

1. **Use a different Android client for the broker,** one whose cookie and authentication behavior is per client, such as
   bundled OkHttp, Cronet or `android.net.http.HttpEngine` (API 34, or Android 12 and later with SDK extension 7). This is the only option here that could satisfy both
   contract sentences. None was measured. It adds a dependency or raises the minimum API, and the
   [transport evidence](native-http-transport-verification.md) for Android would need repeating on it.
2. **Keep `HttpURLConnection` and refuse when a handler is detected.** Detection is racy for the reasons above and cannot
   see a scoped authenticator, so it cannot promise the invariant.
3. **Keep `HttpURLConnection` and make it a host requirement** not to set these handlers. This moves the invariant to host
   developers, and a host that loads Capacitor's cookie plugin already sets one.
4. **Clear the globals around each request.** This breaks the host and races with its other threads. The contract already
   forbids it.

Recommendation: option 1, with one bounded measurement of a candidate before committing to it. That measurement is done:
[OkHttp](native-http-okhttp-verification.md) ignored the host's cookie and authentication handlers and met the Android transport
requirements, with one resend path a broker must block. The maintainer accepted it on 2026-11-04.

## Evidence and limits

Two final runs, same artifact and identical findings: 31 observations and 55 server receipts each, 108 verifier checks each
and 38 host tests. Android lint has 0 errors and 4 warnings. API 37 / Android 17, WebView 145.0.7632.218 on the dedicated
AVD. An earlier collection with the same findings stays in ignored local results, set aside only because `cases.json` was
then reformatted, which changes its pinned hash. The first launch produced no observations, because the harness assumed
`Authenticator.getDefault` exists.

- One app plays both host and broker in one process, on HTTP/1.1 over loopback. One emulator configuration.
- The recording authenticator answers everyone. A real host's may check the requesting host before answering, but it still
  runs on these requests.
- Capacitor was not run. Read from source at [a pinned commit](https://github.com/ionic-team/capacitor/blob/8b89254e21d7af2f22067c61efa9612456a9479d/android/capacitor/src/main/java/com/getcapacitor/plugin/CapacitorCookies.java):
  its cookie plugin's `load` calls `CookieHandler.setDefault` with a subclass of `java.net.CookieManager`, without checking its
  `enabled` setting there.
- Other process-wide state is not covered: `ResponseCache`, `ProxySelector`, default `SSLSocketFactory` and hostname verifier.
  These could matter in the same way.
- iOS was not part of this. Its session configuration is per session and was set to no shared stores in the earlier run.

Nothing was added to the device trust store. The dedicated emulator is stopped and `adb` matches its baseline. Fixture closed.
No crashes. Test keys went to the Trash, so the maintainer still empties it. Source and criteria are in
[the probe](../experiments/native-http-global-handlers-probe/README.md).

## Reproduce

Retained results need no device:

```sh
cd experiments/native-http-global-handlers-probe
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B verify_results.py --summary results/*.json
```
