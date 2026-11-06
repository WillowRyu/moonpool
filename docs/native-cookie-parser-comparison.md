# T28 — OkHttp cookie parser against the C04 draft

Date: 2026-11-06
Status: Step 1 of a two-step comparison, requested by the maintainer to judge option W
(per-app jars that keep each OS's own cookie parser) against the current broker, option X (one shared parser).
Desktop JVM only; no device was started. Nothing is accepted, and SPEC, the contract and the probes are unchanged.
This concerns SPEC §9 where noted.

## Question

How often does the cookie parser that the Android broker already pins, OkHttp 5.5.1, disagree with the
[C04 profile draft](native-cookie-c04-profile-draft.md), and are the disagreements on cookies that real
servers send? Step 2, not run, would put the same vectors through iOS `HTTPCookie` on the simulator; only
then can W's actual cross-platform differences be counted.

## Method

[`experiments/native-cookie-parser-comparison`](../experiments/native-cookie-parser-comparison/README.md) holds 61 vectors:
49 from the C04 draft table and 12 shapes common servers send (Tomcat, Express, Django, Laravel, ASP.NET,
Rails, Spring-style, a CDN cookie, a load balancer, analytics, remember-me). Each vector records whether it
follows the RFC 6265 §4.1 server grammar. A Java probe calls only OkHttp's public `Cookie.parse`,
`Cookie.matches` and `HttpUrl.get`. OkHttp has no cookie store, so replacement, order and eviction are not
measured. The run used the published `okhttp-jvm-5.5.1.jar` (SHA-1 checked against Maven Central) on
Zulu 17. Its public-suffix data is byte-identical to the Android artifact's asset (SHA-256 `c75ab827…`),
and the parsing code is shared between the two artifacts. 17 harness tests pass.

## Result

**13 of 61 differ from the draft; among the 12 common server shapes, only one does.** All 11 other common
shapes, including every session cookie, match field for field: name, value, host-only, domain, path,
`HttpOnly`, `Secure`, expiry and which follow-up URLs receive the cookie.

| Behavior | Vectors | Well-formed | How often servers send it |
| --- | --- | --- | --- |
| **No 400-day lifetime cap**: a 730-day cookie keeps 730 days | P10, E08a, R05 | yes | Common: more than 10% of cookies exceed 400 days ([Web Almanac 2024](https://almanac.httparchive.org/en/2024/security)) |
| **No prefix rules** (§9): `__Secure-` without `Secure`, `__Host-` with `Domain` or a non-root `Path`, and `__host-` are all stored | X01a, X02b, X02c, X03 | yes | Rare: 0.17% `__Host-`, 0.05% `__Secure-`. But a prefix exists to promise a guarantee, and OkHttp gives none |
| `SameSite=None` without `Secure` is stored | S01 | yes | Uncommon; every service is HTTPS, so the cookie is still sent only over TLS |
| A host that is itself a public suffix, with `Domain=` itself, makes a domain cookie sent to every subdomain (§9) | D05 | yes | Rare: the service host would have to be a listed suffix such as `github.io` |
| An IP host with `Domain=` itself is not marked host-only | D06a | yes | Rare, and no subdomain of an IP exists, so sending is unchanged |
| No size limit: name plus value of 4097 octets is stored | P07b | yes | Rare |
| `Max-Age=+5` is read as 5 seconds | E03b | no | Rare |
| `SameSite=bogus` is kept as written rather than normalized | S02b | no | Representation only; sending is unchanged |

Where OkHttp matches the draft: it rejects `Domain=co.uk` from `shop.co.uk` and other public-suffix or
sibling domains, matches the percent-encoded path (D4's recommendation), gives `Max-Age` precedence over `Expires`
and follows the RFC date rules, and rejects the non-ASCII and control-character lines that accepted D1 rejects.
It accepts `a="q r"` and spaces around `=` just as the draft does.

One more observation, already known in kind: given the single field `sid=abc, x=y; Path=/; HttpOnly`,
OkHttp stores one cookie `sid` with value `abc, x=y` and `HttpOnly`. The accepted pipeline splits it into
two, and iOS's own parser was measured making three. Under W, Android would receive separate header fields
and not see this field at all, while iOS still folds them.

## What this means for W, before step 2

- For ordinary session cookies, OkHttp already behaves as the draft does. If iOS also does, W's
  differences are confined to the rows above.
- **The lifetime cap is not a rare case.** If iOS caps at 400 days and OkHttp does not, a long-lived
  cookie such as remember-me or analytics expires on one platform and not the other. Whether `URLSession`'s
  cookie storage applies the cap is unknown until step 2.
- **The prefix rows are rare but a security property.** Under W, a mini app's server could rely on
  `__Host-` on one platform and lose the guarantee on the other.
- **W does not remove Android jar code.** OkHttp parses but does not store, so replacement, order, expiry
  removal and reset stay in Moonpool's code either way. A mixed design, OkHttp parsing plus Moonpool rules
  for the rows above, is possible on Android; iOS cannot hand the broker separate `Set-Cookie` fields, so it
  still needs the accepted folding pipeline.

## Limits

Desktop JVM, not an Android device: the parsing code and the public-suffix data are the same, but header
decoding before `Cookie.parse`, and Android's own runtime, are not exercised. Lines reach the parser already
decoded to text, so non-ASCII byte transport is not measured. One OkHttp version. The common shapes are
written from each framework's typical output, not captured from live servers. No iOS data yet.
