# T28 — Native HTTP transport primitives

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. It does not close T28 or accept the rest of
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md). It found three conflicts with
the [proposed contract](native-cookie-http-contract.md). The maintainer accepted the decisions below as a design
direction on 2026-11-03. This work concerns SPEC §9 and does not amend the SPEC or the protocol.

## Result

The contract has a native broker own cookies. Before building that, one vector ran on Android
`HttpURLConnection` and iOS `URLSession`, each configured as a broker would need: no ambient cookies,
credentials or cache, and no automatic redirects. Server receipts are the witness.

**A broker can be built on these clients, but the contract needs three changes first.**

| Requirement | Android | iOS | Status |
| --- | --- | --- | --- |
| Client sends no cookies by itself | Yes | Yes | Holds |
| Broker-attached `Cookie` arrives once and unchanged | Yes | Yes | Holds |
| 301, 302, 303, 307, 308 returned, with `Location` and cookies visible, zero target hits | Yes | Yes | Holds |
| 4xx and 5xx are results, with body and cookies | Yes | Yes | Holds |
| No shared response cache (two server hits) | Yes | Yes | Holds |
| Normal TLS validation, no device trust added | Yes | Yes | Holds |
| Lowercase `set-cookie` found | Yes | Yes | Holds |
| `Set-Cookie` fields read separately | Yes | **No: folded** | **Conflict 1** |
| A 401 challenge is not sent twice | Yes | **No: resent for `Basic`** | **Conflict 2** |
| Headers visible before any body byte | Yes | **No** | **Conflict 3** |

## Conflict 1: iOS folds `Set-Cookie`

`URLSession` exposes multiple `Set-Cookie` fields as one value joined by `, `. Neither
`value(forHTTPHeaderField:)` nor `allHeaderFields` returned them separately. The contract says to "preserve separate Set-Cookie fields" and to reject invalid
values without repairing them. On iOS, the broker never sees the original boundaries.

Splitting at each comma before a `name=` recovered every case except one. A value containing a comma and a
`name=` cannot be told apart from two cookies:

```text
Sent:    t28h_comma=a, t28h_fake=b; Path=/
         t28h_real=c; Path=/
iOS:     t28h_comma=a, t28h_fake=b; Path=/, t28h_real=c; Path=/
```

The platforms' own parsers disagree on this input. Android's produces two cookies, with the value
`a, t28h_fake=b`. iOS's produces three, including `t28h_fake`. So neither parser can serve a parity
requirement, as the contract already suspected.

## Conflict 2: iOS resends a request after a `Basic` challenge

A 401 with `WWW-Authenticate: Basic` is delivered to the delegate as a challenge. Every disposition that keeps
the response **sends the request a second time, including a POST with its full body**, without credentials.

| iOS disposition or response | GET: status / server hits | POST: status / server hits |
| --- | --- | --- |
| `Basic`, `.rejectProtectionSpace` | 401 / **2** | 401 / **2** |
| `Basic`, `.performDefaultHandling` | 401 / **2** | 401 / **2** |
| `Basic`, `.useCredential` with no credential | 401 / **2** | 401 / **2** |
| `Basic`, `.cancelAuthenticationChallenge` | Error -999, no response / 1 | Not run |
| `Bearer` challenge, no callback | 401 / 1 | 401 / 1 |
| 401 with no `WWW-Authenticate`, no callback | 401 / 1 | 401 / 1 |

Android sent each once and returned 401. The contract says "Never retry requests automatically", because a
second POST can repeat a server effect. Only `Basic` was measured; `Digest`, `NTLM` and `Negotiate` were not.

## Conflict 3: iOS delivers headers with the first body byte

During a held body, Android showed the response immediately. iOS showed nothing until at least one body byte
arrived, with or without `nosniff`, and showed it at once after one byte. The contract commits cookies as
response headers enter the broker's queue, and C08 tests a window "after headers, before body". That window
does not exist on iOS with no body bytes sent.

## Accepted decisions

Accepted by the maintainer as a design direction on 2026-11-03 and recorded in
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md) and the
[contract](native-cookie-http-contract.md). **The principle: follow OS behavior unless it changes what a mini
app sees differently per platform.**

| Conflict | Does the app see a difference? | Decision |
| --- | --- | --- |
| 1. Folded `Set-Cookie` | **Yes:** cookie counts differ | One pipeline: each adapter folds with `, `, both split the same way, one shared parser |
| 2. Resend after `Basic` | No: both give 401 and a body; only server hits differ | Follow the OS, keep the 401 result and document the resend |
| 3. Headers with first body byte | No, after `await` | Follow the OS, and define the commit point as header delivery by the client |

**One pipeline** gave identical lines on both platforms in all 34 cases. Its cost is that a cookie value containing
`, name=` becomes an extra cookie on both. RFC 6265's server grammar excludes commas from cookie values, so this
affects non-conforming servers, and it is a documented limit.

**Following the OS on `Basic`** replaces an earlier proposal to cancel the challenge and return a fixed error. That
would have discarded a 401 both platforms deliver correctly, added an error Android has no need for, and required
matching scheme lists, only to equalize server hits. A 401 normally means the server refused the work, so a resend
rarely repeats an effect. It can matter where a server acts before refusing, or where it counts attempts, such as rate
limits or lockouts. The SDK itself never retries. **Ambient credential and cookie stores stay disabled**, so following
the OS never exposes host credentials.

## Before building on this

- Android's global `Authenticator` and `CookieHandler`: **measured on 2026-11-04, and a conflict.** Both reach requests on
  `HttpURLConnection` with no per-request opt-out. Read [the report](native-http-global-handlers-verification.md). This
  run's Android results hold only while a host has set neither, and a decision on the Android client is open.
- A `Basic` 401 that also sets cookies: **measured on 2026-11-05.** iOS exposes the second response's cookie and Android the
  first, so a guest sees different values per platform. Read [the broker report](native-http-broker-verification.md). The
  broker now commits the first response on both, through `failureResponse`.
- A request with a preset `Authorization`: **measured on 2026-11-05, and repeated.** The iOS resend carried the guest's header
  unchanged, so a server counting failed attempts sees two. No host credential was involved.
- `Digest`, `NTLM` and `Negotiate`, HTTP/2, proxies, mid-body failure, cancellation and empty bodies.

## Comparison with similar runtimes

Read from source and documents at pinned commits; none were run or device tested. The iOS findings are `URLSession`
traits, so only a runtime using it inherits them.

| | [Capacitor](https://github.com/ionic-team/capacitor/tree/8b89254e21d7af2f22067c61efa9612456a9479d) ([Portals iOS](https://github.com/ionic-team/ionic-portals-ios/tree/2dbeb34a68bbdde46f79232e75002e47269f0795), [Android](https://github.com/ionic-team/ionic-portals-android/tree/e4c62bce1d6118b3b515542477a109718f3533ed) depend on it) | [Tauri HTTP plugin](https://github.com/tauri-apps/plugins-workspace/tree/74a44c1d5694324b7fb9ba5ee9271a3096da9387) | [Electron `net`](https://github.com/electron/electron/tree/9c80dad42fb42a445c92e83419b458bb3a785f6c) |
| --- | --- | --- | --- |
| Engine | `URLSession`, `HttpURLConnection` | Rust `reqwest` on mobile too | Chromium, desktop only |
| Set-Cookie | iOS splits at every comma, including `Expires` dates | Each header read separately | Always an array |
| `Basic` 401 | No handling; follows the OS | No handling in the plugin | No listener cancels, and reports an authentication error |
| Cookies | Shared with the WebView store | Own jar in a `.cookies` file | Session store |

**Deferred alternative: a shared HTTP layer.** Tauri shows one library can serve both mobile platforms without
`URLSession`, which would likely remove conflicts 1 and 2. It would add Rust to the SDK build and app size, leave TLS and
proxies to that library rather than the OS, and conflict with ADR 0025 and the project's ordering of native cores after
v0. Revisit it if native cores are considered. Other rejected options:

| Alternative | Why it is not used |
| --- | --- |
| Each platform's cookie parser | Measured disagreement breaks the parity requirement |
| Hand-written HTTP on iOS through `Network.framework` | Moonpool would own HTTP/2, TLS details, proxies and connection reuse |
| Cancel `Basic` challenges and return a fixed error | Loses a correct result to equalize server hits, as described above |

## What this does not establish

- Only HTTP/1.1 on loopback ran. HTTP/2, proxies, mid-body failure and cancellation are not covered.
- Empty bodies were not held, so when iOS delivers headers for them is unmeasured.
- Third-party clients such as OkHttp and Cronet were not measured.
- No cookie jar, broker, reset fence or guest bridge exists. Most of C01–C08 remains to be done.
- This is one emulator and simulator configuration, not a support matrix or a physical-device result.

## Environment, verification and cleanup

API 37 / Android 17 emulator; iOS 26.4.1 on the dedicated iPhone 17 Pro simulator, Xcode 26.4.1 / SDK 26.4.
Android lint has zero errors and 4 recorded warnings.

The [isolated experiment](../experiments/native-http-transport-probe/README.md) retains
[Android first](../experiments/native-http-transport-probe/results/android-first.json) and
[repeat](../experiments/native-http-transport-probe/results/android-repeat.json), and
[iOS first](../experiments/native-http-transport-probe/results/ios-first.json) and
[repeat](../experiments/native-http-transport-probe/results/ios-repeat.json): 136 observations, 164 server
receipt rows and 184 verifier checks. Each platform's two runs classify identically. The host suite has 49 tests,
written and failing before the helpers.

Two earlier collections stay in ignored local results. Each surfaced a question that added cases: challenge
dispositions and early body bytes after the first, and `.useCredential`, `Bearer` and plain 401s after the second.
Criteria were written before collection, and these additions changed no definition.

No device trust store changed: iOS pins trust to a CA bundled in the probe, and a separate session with default
validation was refused with no server receipt. Android scopes the CA to loopback in the APK, and the same request
to a host outside that scope was refused. Only the dedicated devices ran. The simulator and emulator are off, the
Claude desktop app's simulator panel was detached first, all 13 simulator states match the baseline, the mapping
and fixture are closed, and there were no crash reports or fatal entries. This experiment's local keys went to the
macOS Trash. T28 stays incomplete at 6/44 native tasks. SPEC, production packages, public API and wire version are
unchanged.
