# T28 — OS cookie parsers against each other and the C04 draft

Date: 2026-11-06 (step 1), 2026-11-09 (step 2, then corrected after code review)
Status: Both steps collected, requested by the maintainer to judge option W (per-app jars that keep each
OS's own cookie parser) against the current broker, option X (one shared parser). Nothing is accepted, and
SPEC, the contract and the broker probe are unchanged. This concerns SPEC §9 where noted.

## Question

Where do the two parsers W would rely on, OkHttp 5.5.1 on Android and `HTTPCookie` on iOS, disagree with
each other, and are the disagreements on cookies that real servers send? The
[C04 profile draft](native-cookie-c04-profile-draft.md) is a third column for reference.

## Method

[`experiments/native-cookie-parser-comparison`](../experiments/native-cookie-parser-comparison/README.md) holds 61 vectors:
49 from the C04 draft table and 12 shapes common servers send (Tomcat, Express, Django, Laravel, ASP.NET,
Rails, Spring-style, a CDN cookie, a load balancer, analytics, remember-me). Each line is one `Set-Cookie`
field. Each vector records whether it is well-formed: what RFC 6265 §4.1 asks servers to send, meaning its
grammar and its SHOULD NOT on repeating an attribute, a `Domain` without a leading dot, and `SameSite` read
as the 6265bis `samesite-av` (`Strict`, `Lax` or `None`).

- **Android, step 1:** a Java probe calls only OkHttp's public `Cookie.parse`, `Cookie.matches` and
  `HttpUrl.get`, on the published `okhttp-jvm-5.5.1.jar` (SHA-1 checked against Maven Central) and Zulu 17.
  Its public-suffix data is byte-identical to the Android artifact's asset (SHA-256 `c75ab827…`), and the
  parsing code is shared between the two artifacts. OkHttp has no cookie store.
- **iOS, step 2:** an app calls `HTTPCookie.cookies(withResponseHeaderFields:for:)`, then stores the result
  in a fresh in-memory `HTTPCookieStorage` from an ephemeral session configuration, with accept policy
  `.always`, and asks it which follow-up URLs receive the cookie. Every storage was empty before and after
  its vector. iOS 26.4.1 on the dedicated `Moonpool Cookie Suppression` simulator, Xcode 26.4.1, SDK 26.4,
  deployment target iOS 17.0. No network and no WebView. Two runs.

`compare.py` reads each platform against its own clock, and allows 5 seconds of skew in an expiry. iOS dates
`Max-Age` from the whole second in which it parses, so for iOS a parsed expiry at or before the parse time is
a deletion. The retained runs record only when the app started; the probe now also records the time just
after each parse, for any later collection. An earlier step-2 collection in this session was discarded before
retention, because its analysis judged that boundary against the runner's clock, which is about a second
earlier; the analysis moved into `compare.py`, the iOS results keep raw data only, and both runs were
collected again. A `SameSite` value that one side cannot report is marked "unobserved", never counted as
agreement. 42 harness tests pass.

## Result

**The two iOS runs are identical. Android and iOS disagree on 13 of 61 vectors; among the 12 common server
shapes, only one: the 730-day cookie.** The other 11, including every session cookie, agree on name, value,
host-only, domain, path, `HttpOnly`, `Secure`, expiry and which follow-up URLs receive it. Two of them, R08
and R10, also send `SameSite=None`, which iOS's `HTTPCookie` API cannot express, so that attribute is
unobserved on iOS for them and for S01 and S02b; see the last table row.

| Disagreement | Android (OkHttp) | iOS | Vectors | Well-formed | How often servers send it |
| --- | --- | --- | --- | --- | --- |
| **400-day lifetime cap** | No cap: 730 days stay 730 | Capped at parse time, as the draft does | P10, E08a, R05 | yes | **Common:** more than 10% of cookies exceed 400 days ([Web Almanac 2024](https://almanac.httparchive.org/en/2024/security)) |
| **Prefix rules** (§9) | None | Refuses `__Secure-` without `Secure` and `__Host-` with `Domain` or a non-root `Path` | X01a, X02b, X02c | yes | Rare: 0.17% `__Host-`, 0.05% `__Secure-`, but they carry a security promise |
| Size limit | Stores name plus value of 4097 octets | Refuses it | P07b | yes | Rare |
| Public-suffix host with `Domain=` itself (§9) | Domain cookie, sent to every subdomain | Host-only, as the draft does | D05 | yes | Rare: the service host would have to be a listed suffix |
| IP host with `Domain=` itself | Not marked host-only, as RFC 6265 §5.3 does | Host-only, as the draft chose without saying why | D06a | yes | Rare, and sending is unchanged |
| `Path=x`, no leading `/` | Uses the default path | Stores `x` literally, so the cookie is **never sent** | A02 | yes | Rare, but the cookie is lost silently |
| `Max-Age=abc` | Ignored: a session cookie | Treated as 0: deleted at once | E03a | no | Rare |
| A non-ASCII value, `a=é` | Refused | Stored | P06 | no | Unknown; bytes before parsing were not measured |
| One field folding two cookies with `, ` | One cookie `sid` with value `abc, x=y` and `HttpOnly` | Two cookies; `sid=abc` loses `HttpOnly`, like the accepted pipeline | P11 | no | Needs a server outside the grammar |
| `SameSite=None` or an unknown value | Kept as written | Not observable: `sameSitePolicy` has only Lax and Strict, so None, unknown and absent all read as nil | S01, S02b, R08, R10 | mixed | Common: 23% of first-party cookies set `None` ([Web Almanac 2024](https://almanac.httparchive.org/en/2024/security)). Sending is unchanged in the native service context, but a store built on iOS's API could not keep `None` apart from no attribute |

Where both platforms agree with each other but not with the draft: both store lowercase `__host-a` without
`Secure` (iOS checks prefixes case-sensitively), both store `SameSite=None` without `Secure`, and both read
`Max-Age=+5` as five seconds.

Both agree with the draft on public-suffix and sibling `Domain` rejection, leading dots and case in `Domain`,
the percent-encoded path, `Max-Age` precedence over `Expires`, the RFC date rules (one vector covers a
two-digit year),
quotes and spaces around `=`, control characters, and unknown attributes such as `Partitioned`.

## What this means for X and W

- **For ordinary cookies the two OS parsers already agree.** Every common session shape matched on both,
  so W's parser differences are confined to the table above.
- **The one common difference can be closed on Android.** OkHttp parses but does not store, so the
  Android jar is Moonpool code under either option, and a 400-day cap is one rule there. The same holds for
  iOS's prefix rules (case-sensitive, as iOS does), its size limit, the public-suffix-host case, and
  `Path` without `/`. Aligning Android to iOS on these rows would leave the malformed `Max-Age=abc` and
  non-ASCII rows, and the folding row, which the accepted pipeline already documents as a limit.
- That would be a third shape, call it W′: iOS's parser and storage as the reference, OkHttp plus a short
  list of Moonpool rules on Android, and no Moonpool parser or public-suffix data. The broker's fence and
  commit-timing rules stay: the broker still writes parsed cookies into a per-app storage itself, never
  through `URLSession`'s automatic cookie handling.
- **Not yet known for W or W′:** what the jars do beyond one line. Replacement and identity (D3), header
  order (D8), eviction limits, persistence across restart, and the iOS public-suffix data, which updates with
  the OS while OkHttp's is pinned. These would need a jar-level comparison before W or W′ could be accepted.

## Code review

A review of the harness on 2026-11-09 found that it treated a `SameSite` value reported on one side only as
agreement, which made this report claim the 11 common shapes agreed on every field; allowed 120 seconds of
expiry skew, so a 60-second cookie that expired at once would have passed; could misjudge a deletion when
parsing crossed a second boundary; turned an undecodable iOS row into an empty line; counted a probe error as
an acceptance difference; checked templates only in the line, not in URLs, checks or expected values; and
could fail a complete run if the app exited between two checks. Each has a regression test and a fix. Any
`{word:...}` stays a template token, so a misspelt one fails rather than becoming literal cookie text; no
vector needs literal braces. Recomparing the retained results with the fixed harness changes no platform
difference; it adds the four unobserved `SameSite` rows. It also found that D06a's expectation departs from
RFC 6265 §5.3 without saying so; the draft now lists it under D2.

## Limits

One OkHttp version on a desktop JVM, and one iOS version on one simulator. Lines reach both parsers as text,
so how each transport decodes header bytes is not measured. iOS was measured through
`HTTPCookie.cookies(withResponseHeaderFields:for:)` and an in-memory storage, not `URLSession`'s internal
handling of a live response, nor a persistent per-app storage. The common shapes are written from each
framework's typical output, not captured from live servers. Single-line parsing only: no replacement,
ordering or eviction.

Devices: only the dedicated simulator ran. It was shut down before, was booted by this task and is shut down
again, and all 12 simulators' states match the baseline taken before. No emulator or `adb` server was started.
