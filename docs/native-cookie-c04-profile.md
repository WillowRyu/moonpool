# T28 — C04 cookie profile

**Profile `c04-1` was frozen on 2026-11-11.** It binds the D1–D9 rules to one
Public Suffix List (PSL) snapshot. The versioned JSON corpus covers §4. The
desktop Java reference parser and its Swift port pass all 109 cases, including
seven added after the 2026-11-13 review. The broker ports and paired evidence
are pending.
[C04 tests](../experiments/native-cookie-profile/README.md),
[C04 conformance plan](native-cookie-http-conformance-plan.md#c04--cookie-syntax-and-attributes)

**This concerns SPEC §9.** Domain, public-suffix, prefix and `HttpOnly` rules decide
which service receives a session cookie and what a script can read or plant.

## 1. Scope

Both adapters will use this profile for split `Set-Cookie` lines, jar state,
expiry and ordered cookie selection. The maintainer chose the shared parser
(X) on 2026-11-09 after comparing the two OS parsers. The expected results in §4
come from this profile. RFC 6265 and 6265bis-22 are design references.
[Contract §4](native-cookie-http-contract.md#4-cookie-behavior-shared-by-both-adapters),
[ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md),
[Parser comparison](native-cookie-parser-comparison.md)

The broker extracts cookie lines under contract §4 and applies the header commit
timing and reset fence in contract §5. Counts, total size and eviction belong
to T53, durability to T48, and public API errors to T29.
[Commit ordering and reset](native-cookie-http-contract.md#5-ordering-reset-and-errors)

## 2. What the broker probe does today

The [broker probe](../experiments/native-http-broker-probe/README.md) parser is "only the subset these cases need".
Both platforms implement the same subset:

| Area | Probe behavior | Gap for C04 |
| --- | --- | --- |
| Domain | Accepted only when equal to the request host, and then still stored host-only | No domain cookies, no public-suffix data |
| Path | `Path` used if it starts with `/`, else the default path; RFC path-match | Compares the **decoded** path (`URLComponents.path`, `URI.getPath()`) |
| Expiry | `Max-Age` ≤ 0 deletes; otherwise ignored; `Expires` ignored | No expiry over time, no date parsing |
| Characters | A sendable-character check on name and value | Not pinned to a written rule |
| Prefixes, SameSite | Only `SameSite=None` without `Secure` is rejected | No prefix rules |
| Identity, order | Host, path, name; longer path first, then creation order | Matches RFC 6265 for host-only cookies only |

## 3. Profile rules and decision record

### D1 — Parsing tolerance and characters

Today: a probe-specific character check. Problem: Android (OkHttp) and iOS
(`URLSession`) may decode non-ASCII header bytes differently before the broker
sees them, so any rule that accepts them risks two different stored values.

| Option | Consequence |
| --- | --- |
| **A. Strict ASCII line rule** | Identical character handling on both platforms. A line with a raw UTF-8 value is dropped |
| B. 6265bis lenient rule — accept nameless cookies and non-ASCII octets | Closer to browsers, but needs native evidence that both adapters hand over the same bytes, and nameless cookies need extra prefix-spoofing rules |
| C. RFC 6265 §4.1 server grammar (`cookie-octet`) | Rejects many cookies real servers send, such as values with spaces |

**Accepted on 2026-11-06 (A).** Allow bytes `%x20-7E` and HTAB in each split
line. Reject the entire line if any byte falls outside that set. Trim
surrounding ASCII whitespace from the cookie name and value. Keep quotes
as part of the value. Reject a line whose cookie pair has no `=`, an empty
trimmed name or more than 4096 octets in its trimmed name plus value.
Ignore an attribute whose trimmed value exceeds 1024 octets.

Parse attributes under RFC 6265 §5.2 and the rules below. Rejecting an empty name
prevents `=__Host-x=1` from imitating a prefixed cookie. Percent-encoded and
base64 values work for servers and structured script setters. Native byte
delivery and diagnostics for a rejected line are later checks.
[RFC 6265 §5.2](https://www.rfc-editor.org/rfc/rfc6265#section-5.2)

### D2 — Domain attribute and public suffixes (§9)

Today: no domain cookies. Problem: a common login shape sets
`Domain=example.com` on `auth.example.com` for use at `api.example.com`. Without
public-suffix data, `Domain=co.uk` from `shop.co.uk` would also be accepted and
sent to every approved `*.co.uk` service of the same app: a session-fixation
path between two services the host approved for one app.

| Option | Consequence |
| --- | --- |
| **A. Domain cookies with a pinned Public Suffix List** — one snapshot, ICANN and private sections like browsers, shipped as the same data in both SDKs and named by revision in the profile | Supports the shared-parent login shape. Adds a data file and an update cadence tied to SDK releases; a stale snapshot is a known, versioned limit |
| B. Host-only only — reject every line with a `Domain` attribute that is not the request host, and store `Domain=host` as host-only (today's probe) | No data to maintain, safe. Breaks the shared-parent login shape; servers must set separate cookies per host |
| C. Accept `Domain` without public-suffix data | Rejected: cookie tossing across approved services |

**Accepted on 2026-11-11 (A).** Ignore an empty `Domain`. For a nonempty value,
strip one leading dot and lowercase in ASCII. D1 rejects a non-ASCII value.
For a DNS request host, the canonical `Domain` must equal the canonical host
or be its dot-delimited suffix. A cookie with no effective `Domain` is host-only.
For a matching `Domain`, store a domain cookie if its public suffix is shorter
than the `Domain`. If the `Domain` is itself a public suffix, store the cookie
as host-only when it equals the request host and reject the line otherwise.

Select a host-only cookie only for its exact host. A domain cookie can also
match subdomains at a dot boundary. The broker sends either kind only to
approved HTTPS service origins of the same mini app.
[RFC 6265 §5.1.3](https://www.rfc-editor.org/rfc/rfc6265#section-5.1.3),
[Contract §2](native-cookie-http-contract.md#2-authority-ownership-and-request-context)

**IP rule accepted on 2026-11-11.** When the request host is an IP address, accept
a nonempty `Domain` only if it matches that IP exactly and store the cookie as
host-only (`hostOnly=true`). Chromium and Firefox use this classification for
IP hosts. The same name, IP and path identify one cookie whether the matching
`Domain` is present or omitted, even if D3 includes the flag in the identity.
[Chromium source](https://github.com/chromium/chromium/blob/main/net/cookies/cookie_util.cc#L372-L413), [Firefox source](https://searchfox.org/firefox-main/source/netwerk/cookie/CookieValidation.cpp#1072-1085)

The D06a checks found the cookie eligible for a follow-up request to `127.0.0.1`
on both. The iOS result was classified as host-only. OkHttp marked it as a domain
cookie, consistent with RFC 6265 §5.3 step 6. [Parser comparison](native-cookie-parser-comparison.md)

#### Public Suffix List snapshot

The official download served on 2026-11-11 (KST) identified the published
version and commit below. The published file adds version and commit comments
to the pinned repository file. Both files contain the same rules in the same
order in each section. Use the immutable repository file for reproduction.
[Official PSL download](https://publicsuffix.org/list/public_suffix_list.dat),
[Upstream commit](https://github.com/publicsuffix/list/commit/3db7776283b0874634fea8b01168f785360d64f2)

| Field | Value |
| --- | --- |
| Published version | `2026-11-10_11-23-57_UTC` |
| Upstream commit | `3db7776283b0874634fea8b01168f785360d64f2` |
| Pinned source | [public_suffix_list.dat at that commit](https://raw.githubusercontent.com/publicsuffix/list/3db7776283b0874634fea8b01168f785360d64f2/public_suffix_list.dat) |
| Source file size and SHA-256 | 339,117 bytes · `22dd3a3a2bca93a9542e65998b301c751339af72681d5f47378eb355face16bc` |
| Rules (excluding comments and blank lines) | 6,951 ICANN · 3,463 PRIVATE |
| Data license | [MPL-2.0](https://github.com/publicsuffix/list/blob/3db7776283b0874634fea8b01168f785360d64f2/LICENSE) |

In a scratch directory, retrieve and verify the pinned UTF-8 source.

```sh
c04_psl_revision=3db7776283b0874634fea8b01168f785360d64f2
curl --fail --silent --show-error --location \
  "https://raw.githubusercontent.com/publicsuffix/list/${c04_psl_revision}/public_suffix_list.dat" \
  --output public_suffix_list.dat &&
  printf '%s  %s\n' '22dd3a3a2bca93a9542e65998b301c751339af72681d5f47378eb355face16bc' public_suffix_list.dat |
  shasum -a 256 -c -
```

Use these verified bytes as the common source for both SDKs and the C04
corpus. Preserve the source notice when bundling the data. Ship new data
through SDK releases on both platforms and identify it in a new profile version.

Evaluate both sections together using the PSL algorithm. Compare canonical
lowercase ASCII labels, using Punycode A-labels for Unicode PSL labels. Match
from the right, with `*` matching one label. An exception (`!`) takes
precedence and its leftmost label is excluded from the suffix. Otherwise use
the matching rule with the most labels. With no match, use the implicit
`*` rule, which treats the final label as the public suffix.
[PSL format and algorithm](https://github.com/publicsuffix/list/wiki/Format#formal-algorithm)

The PSL format permits no empty label and ignores a trailing dot. Remove one
trailing dot before the lookup and restore it in the result, so `github.io.` is
a public suffix as `github.io` is, and `example.com.` can still carry a domain
cookie. A name with any other empty label has no registrable part, so it counts
as a public suffix in full. Clarified on 2026-11-13 after a review found that a
trailing dot hid the PRIVATE rule `github.io` from both reference ports.

### D3 — Cookie identity and host-only flag

The probes key cookies by host, path and name. Under D2-A, a response from
`api.example.com` can set `a=1; Path=/` and a later response can set
`a=2; Domain=api.example.com; Path=/`. Both have the same name, canonical domain
and path. The first is host-only, and the second can match subdomains.

- **A. Key by `(name, domain, path)`.** `a=2` replaces `a=1` and takes over the
  entry's scope. A later `Max-Age=0` for that name and path at `api.example.com`
  deletes the entry even when the response omits `Domain`. This is the RFC 6265
  storage model. [RFC 6265 §5.3](https://www.rfc-editor.org/rfc/rfc6265#section-5.3)
- **B. Key by `(name, domain, path, host-only)`.** Both entries remain and are
  eligible for `api.example.com` under the profile's matching rules. A deletion
  without `Domain` removes only the host-only entry. A server may receive two
  values with the same name. The `Cookie` header carries the name and value of
  each entry. [6265bis-22 storage model](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.7), [Cookie header](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-4.2.2)

**Accepted on 2026-11-11 (B).** Within one app's jar, key by
`(name, canonical domain, path, host-only)`. Compare the name case-sensitively
and use a lowercased domain. Approved subdomains that set the same domain key
share one domain entry. The parent host-only entry survives, and both values
can reach the parent service. This affects cookie integrity under SPEC §9.
An eligible server response can replace an `HttpOnly` entry of the same identity.
Script reads omit protected entries, and script writes cannot modify them.
T29 defines how `cookies.delete` targets the exact identity.
[Chromium equivalence test](https://github.com/chromium/chromium/blob/main/net/cookies/canonical_cookie_unittest.cc#L1470-L1480), [HTTP WG decision](https://github.com/httpwg/http-extensions/issues/199)

The retained platform comparison measured one line at a time. [Probe limits](native-cookie-parser-comparison.md#limits)

### D4 — Which request path is compared

The probes derive the default path and match cookies using the decoded path.
Under that option (B), `/a%2Fb/c` is compared as `/a/b/c` and matches `Path=/a`.

**Accepted on 2026-11-11 (A).** Use the percent-encoded path sent in the request
for both cookie matching and default path calculation. Compare the parsed `Path`
value byte for byte as written, with literal `/` as the separator under the RFC
path-match rule. A request to `/a%2Fb/c` excludes a cookie scoped to `Path=/a`.
A response there that omits `Path` gets the default `/a%2Fb`. Chromium also
retains `%2F` in its URL path for this comparison.
[RFC 6265 path matching](https://www.rfc-editor.org/rfc/rfc6265#section-5.1.4), [Chromium path handling](https://github.com/chromium/chromium/blob/main/url/url_canon_path.cc#L259-L266), [Chromium cookie comparison](https://github.com/chromium/chromium/blob/main/net/cookies/cookie_base.cc#L224-L229)

The candidate adapter inputs are OkHttp `encodedPath` and iOS
`URLComponents.percentEncodedPath`. Check these against the request path the
fixture receives. The retained 63 broker cases used paths without percent escapes.

### D5 — Expiry

The research brokers implement expiry through immediate `Max-Age` deletion.

**Expiry processing accepted on 2026-11-11.** Apply these rules to accepted
cookie lines.

- Parse `Max-Age` as one or more ASCII digits with an optional leading `-`. Ignore invalid
  values such as `abc` and `+5`. Positive values set a duration from receipt.
  Zero and negative values expire immediately.
- Parse `Expires` using RFC 6265 §5.1.1, including two-digit years and rejection
  of years before 1601. Ignore a value that fails the date parser.
- For each attribute, use its last valid value. A valid `Max-Age` takes priority
  over `Expires` in either order. If only `Expires` has a valid value, use it.
  If neither supplies an expiry, store the accepted response as a session cookie
  and replace any entry with the same D3-B identity.
- An accepted response cookie whose expiry is at or before receipt deletes the
  matching D3-B entry. Commit only the deletion. A valid server expiry can
  delete the matching `HttpOnly` entry.
- Treat a stored cookie as expired when the current wall-clock time reaches
  or passes its expiry. Remove expired entries before building a `Cookie`
  header or a `cookies.get` result.

[RFC 6265 date parsing](https://www.rfc-editor.org/rfc/rfc6265#section-5.1.1), [6265bis expiry attributes](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.6), [6265bis storage model](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.7)

**Lifetime cap accepted on 2026-11-11.** Cap the effective persistent expiry
derived from `Max-Age` or `Expires` at 400 days (34,560,000 seconds) after receipt.
Use the earlier of the requested expiry and the cap. The 6265bis-22 draft
recommends this upper limit. E08 uses the same cap for both attributes.
[Lifetime limits](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.5), [Cookie policy](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-7.2)

The retained comparison found that iOS capped a 730-day `Expires` at 400 days.
OkHttp kept 730 days. T53 uses measurements to set cookie count and size limits
and eviction rules. [Parser comparison](native-cookie-parser-comparison.md), [Native implementation plan](native-implementation-plan.md)

Algorithmic vectors use a controlled clock. Native wall-clock behavior,
including a device clock change, is a separate observation.

### D6 — Prefixes

**Accepted on 2026-11-11.** The profile checks these two prefixes using ASCII
case-insensitive matching. Keep the full cookie name as received and compare
it case-sensitively for D3-B identity.

- `__Secure-` requires `Secure` on an HTTPS response. Apply the ordinary domain
  and path rules.
- `__Host-` also requires an explicit `Path=/` and omission of `Domain` from
  the `Set-Cookie` line. The root path must come from the attribute itself.
  Reject an explicit `Domain`, including an empty value or a matching IP.
  A `Domain` value over 1024 octets is ignored for scope under D1, but it is
  still explicit and rejects the line.

Validate the prefix before committing the response cookie or applying its expiry
deletion. The structured `cookies.set` rejects either prefix in any case. T29
defines its error code. Case-insensitive checks prevent a differently spelled
prefix from bypassing the attribute requirements. Chromium permits an explicit
matching IP in its `__Host-` check. [6265bis prefix matching](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.4), [Chromium IP handling](https://github.com/chromium/chromium/blob/main/net/cookies/cookie_util.cc#L109-L125)

### D7 — Secure and SameSite under the service context

Under the first-party service context, every service URL is HTTPS. Apply
`Secure` to prefix and `SameSite=None` validation. Parse `SameSite`
case-insensitively as `Strict`, `Lax` or `None`. Use the default mode for an
absent or unrecognized value. Reject `SameSite=None` without `Secure`. All
accepted modes are eligible in this service context.
[Contract §2](native-cookie-http-contract.md#2-authority-ownership-and-request-context)

### D8 — Cookie header order and form

**Accepted on 2026-11-11.** Order matching cookies by longer `Path` first. For
equal lengths, put the earlier creation first. The owner assigns an increasing
creation order to each new entry. Replacing the same D3-B identity preserves
its original order. A cookie stored after deletion gets a new order.

Serialize each matching entry as `name=value` and join the ordered pairs with
`; `, preserving repeated names. The research
brokers already use this sorting and replacement order.
[RFC 6265 header order](https://www.rfc-editor.org/rfc/rfc6265#section-5.4), [6265bis replacement](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22#section-5.7)

### D9 — Unknown and newer attributes

**Accepted on 2026-11-11.** Ignore attributes outside the profile, including
`Partitioned`, `Priority` and arbitrary extensions such as `Foo`. Apply the
profile's syntax, scope and expiry rules and store eligible cookies in the
requesting mini app's jar. This keeps cookies usable when a server adds attributes
for browsers. [RFC 6265 attribute handling](https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2)

Use the same D3-B identity for a cookie carrying `Partitioned`. Within an app's
jar, a later eligible response with that identity replaces or expires the same
entry. T53 defines the eviction rules for the jar. [App ownership](native-cookie-http-contract.md#2-authority-ownership-and-request-context)

## 4. Expected vectors for `c04-1`

Unless stated, the response comes from `https://api.example.com/x/y` at
controlled time `T0 = 2026-11-11T00:00:00Z`. Every named host in a request is an approved HTTPS
service of the same test app. Cases run against fixture inputs. "Sent" is the
`Cookie` header the broker builds for the named follow-up URL.

| Id | Input | Expected |
| --- | --- | --- |
| P01 | `a=1` | Host-only `api.example.com`, path `/x`; sent to `/x/z`, not to `/` or `www.example.com` |
| P02 | `a=1; Path=/` then `a=2; Path=/` | One cookie `a=2`, original creation time |
| P03 | `=v`, `a`, `=` | All rejected, jar unchanged (D1) |
| P04 | `a=1` + byte `%x01` | Rejected (D1) |
| P05 | `a="q r"` | Value `"q r"` with quotes |
| P06 | `a=é`, or two fields `a=1; Foo=é` and `keep=1` in one response | Reject the non-ASCII line in each case. The second case stores and sends `keep=1` |
| P07 | Name plus value of 4096 and 4097 octets | First stored, second rejected |
| P08 | `  a =  1 ; Path=/` | Name `a`, value `1` |
| P09 | `a=1; Path=/p; Path=/` | Path `/` (last wins) |
| P10 | `a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT` | One cookie, not split at the date's comma |
| P11 | `sid=abc, x=y; Path=/; HttpOnly` | Accepted limit: `sid` script-readable, `x` `HttpOnly` |
| P12 | `a=1; Path=` with `/` followed by 1023 or 1024 `p` bytes | Use the 1024-octet path in the first case. Ignore the 1025-octet attribute and use default path `/x` in the second |
| P13 | One field `a=1,` HTAB, space `b=2,` U+00A0 `c=3` | Split only at ASCII whitespace. Store `a` and `b` and send `a=1; b=2`. D1 rejects the `c` line |
| D01 | `a=1; Domain=example.com` | Domain cookie; sent to `example.com` and `www.example.com` |
| D02 | `Domain=.example.com`, `Domain=EXAMPLE.com` | Same as D01 |
| D03 | `Domain=other.com`, `Domain=www.api.example.com` | Rejected |
| D04 | From `shop.co.uk`: `a=1; Domain=co.uk` | Rejected (public suffix) |
| D05 | From `co.uk`: `a=1; Domain=co.uk` | Host-only. Sent to `co.uk` and excluded at `shop.co.uk` |
| D06 | From `127.0.0.1`: `Domain=127.0.0.1`; `Domain=0.0.1` | First host-only and eligible only at `127.0.0.1`, second rejected |
| D07 | `a=1; Domain=` | Host-only |
| D08 | From `shop.github.io`: `a=1; Domain=github.io` | Rejected by the PRIVATE rule `github.io` |
| D09 | From `shop.foo.ck`: `a=1; Domain=foo.ck` | Rejected by the ICANN rule `*.ck` |
| D10 | From `shop.www.ck`: `a=1; Domain=www.ck` | Domain cookie under exception `!www.ck`. Sent to `www.ck` and `other.www.ck` |
| D11 | From `shop.xn--55qx5d.cn`: `a=1; Domain=xn--55qx5d.cn` | Rejected by the ICANN rule `公司.cn` after A-label conversion |
| D12 | From `shop.test`: `a=1; Domain=test` | Rejected by the implicit `*` rule |
| D13 | From `shop.abyme.dev`: `a=1; Domain=abyme.dev` | Rejected by the PRIVATE rule added in the pinned commit |
| D14 | From `a.github.io.`: `sid=1; Domain=github.io.; Path=/`. From `co.uk.`: `a=1; Domain=co.uk.`. From `a.example.com.`: `a=1; Domain=example.com.; Path=/` | First rejected, and nothing is sent to `b.github.io.`. Second host-only at `co.uk.`. Third a domain cookie sent to `b.example.com.` but not to `b.example.com` |
| D15 | From `shop.xn--55qx5d.cn`: `a=1; Domain=shop.xn--55qx5d.cn; Path=/` | Domain cookie with the A-label domain. Sent to `sub.shop.xn--55qx5d.cn`, not to `other.xn--55qx5d.cn` |
| I01 | `a=1; Path=/` then `a=2; Domain=api.example.com; Path=/` | Store host-only `a=1` and domain `a=2`. Both are eligible at `api.example.com`. Only `a=2` is eligible at an approved subdomain |
| I02 | `a=r; Path=/` then `a=p; Path=/x` | Store both. To `/x/q`, send `a=p; a=r` |
| I03 | I02, then `cookies.get` for `/x/q` | Both, as an array, longer path first |
| I04 | I01, then `a=3; Domain=api.example.com; Path=/` from `shop.api.example.com` and `a=4; Domain=api.example.com; Path=/` from `billing.api.example.com` | Host-only `a=1` and domain `a=4` remain |
| I05 | After I01, receive `a=; Max-Age=0; Path=/` from `api.example.com`, with and without `Domain=api.example.com` in independent cases | With `Domain`, only the host-only `a=1` remains. Without `Domain`, only the domain `a=2` remains |
| I06 | I01, then `cookies.get` for `https://api.example.com/` | Both matching entries in the array |
| A01 | `a=1; Path=/x` | Sent to `/x`, `/x/`, `/x/q`; not to `/xq` |
| A02 | `a=1; Path=x` | Default path `/x` |
| A03 | From `/a%2Fb/c`: `a=1` | Path `/a%2Fb`; sent to `/a%2Fb/d`, not to `/a/b/d` (D4) |
| A04 | From `/y`: `a=1` | Default path `/` |
| A05 | `a=1; Path=/a` | Sent to `/a/b/c`. Excluded at `/a%2Fb/c` |
| A06 | `a=1; Path=/a%2Fb` | Stores `/a%2Fb`. Sent to `/a%2Fb/c`. Excluded at `/a/b/c` |
| E01 | `a=1; Max-Age=60`. The header case replaces a cookie at `T0+30s` | Eligible 59 seconds after receipt. Removed before header selection or `cookies.get` at 60 seconds after receipt |
| E02 | Existing `a`, then `a=; Max-Age=0` or `Max-Age=-1` | Deleted |
| E03 | `a=1; Max-Age=abc`, `Max-Age=+5` | Session cookie |
| E04 | `a=1; Max-Age=60; Expires=<past>` and the reverse order | Kept for 60 s |
| E05 | Existing `a`, then `a=1; Expires=<past>` or `a=1; Expires=<T0>` | Deleted in both cases |
| E06 | `a=1; Expires=<invalid>` | Session cookie |
| E07 | `a=1; Expires=Wed, 21 Oct 70 07:28:00 GMT` | Year 1970, past: nothing stored |
| E08 | At `T0+30s`, replace the original cookie with `a=1; Expires=<T0+730d>` or `a=1; Max-Age=999999999` | Expiry 400 days after replacement receipt in both cases (accepted D5 cap) |
| E09 | Existing `HttpOnly` `a`, response `a=; Max-Age=0` | Deleted |
| E10 | Existing `a`, then `a=; Max-Age=0; Expires=<T0+60s>` | Deleted |
| E11 | Existing `a`, then `a=1; Max-Age=abc; Expires=<T0+60s>` or the same line with `Expires=<past>` | Use `Expires`. First case expires at `T0+60s`. Second deletes the matching entry |
| E12 | Existing `a`, then `a=1; Max-Age=60; Max-Age=abc` or `a=1; Max-Age=60; Max-Age=0` | First uses 60 s. Second deletes the matching entry |
| E13 | Existing `a`, then `a=1; Expires=<T0+60s>; Expires=tomorrow` or the same line with `Expires=<past>` as the second date | First expires at `T0+60s`. Second deletes the matching entry |
| E14 | Existing persistent `a=old` with `Path=/`, then `a=new; Path=/; Max-Age=abc; Expires=tomorrow` | One session cookie `a=new` replaces the old entry |
| H01 | `a=1; Path=/; HttpOnly` then `a=2; Path=/` from the same host | Replaced, now script-readable (RFC 6265 §5.3) |
| X01 | `__Secure-a=1` and `__secure-a=1`, each with and without `Secure` | Each variant with `Secure` is stored. Each variant without it is rejected |
| X02 | `__Host-a=1; Secure; Path=/`; with `Domain=api.example.com`; with `Path=/x` | First stored, others rejected |
| X03 | `__host-a=1` without `Secure` | Rejected (D6) |
| X04 | `cookies.set` with name `__Host-a` or `__SECURE-a` | Rejected, jar unchanged |
| X05 | `__Host-a=1; Secure; Path=/` then `__host-a=2; Secure; Path=/` | Both stored under their original names |
| X06 | From `shop.api.example.com`, `__host-a=1; Secure; Path=/; Domain=api.example.com` | Rejected |
| X07 | From `/y`, `__Host-a=1; Secure` or `__Host-a=1; Secure; Path=invalid` | Rejected in both cases |
| X08 | `__Host-a=1; Secure; Path=/; Domain=` or from `127.0.0.1` with `Domain=127.0.0.1` | Rejected in both cases |
| X09 | Existing `__Host-a=1; Secure; Path=/`, then `__Host-a=; Path=/; Max-Age=0`, with and without `Secure` in independent cases | The case with `Secure` deletes the entry. The case without it preserves the entry |
| X10 | `__Host-sid=1; Secure; Path=/` with a 1025-octet `Domain`. Separately, an existing `__Host-sid`, then the same deletion line with `Max-Age=0` | Rejected. The deletion is rejected and the entry survives |
| S01 | `a=1; SameSite=None` without `Secure` | Rejected |
| S02 | `SameSite=Strict`, `SameSite=bogus` | Stored, sent to the service |
| O01 | `b=1; Path=/`, then `a=1; Path=/`, then `b=2; Path=/` | Sent `b=2; a=1` |
| O02 | I01, then `a=3; Path=/` from `api.example.com` | Send `a=1; a=2` to `api.example.com` before the replacement and `a=3; a=2` after it |
| O03 | I01, then `a=; Path=/; Max-Age=0` followed by `a=3; Path=/` from `api.example.com` | After deletion and reissue, send `a=2; a=3` to `api.example.com` |
| U01 | `a=1; Path=/; Partitioned; Priority=High; Foo=bar` | Store `a=1` in the app's jar with path `/`. Send `a=1` on a matching request |
| U02 | `a=1; Secure; Path=/` then `a=2; Secure; Path=/; Partitioned` | One entry `a=2` with the original creation order |
| U03 | After U02, `a=; Secure; Path=/; Max-Age=0`, with and without `Partitioned` in independent cases | Delete the same entry in both cases |
| U04 | `a=1; Path=/; SameSite=None; Partitioned` | Rejected by the `SameSite=None` rule requiring `Secure` |

Native clock changes and header byte delivery need separate observations.
Counts and eviction belong to T53, restart lifetime to C11, and diagnostics
for rejected lines to T29.

## 5. Verification sequence

1. The `c04-1` JSON corpus records the PSL revision and SHA-256. The isolated
   tests use a controlled clock and fresh jars to check identities, flags,
   expiry, ordered headers and script-visible results. The retained Android
   broker produced 50 failing cases on the desktop JVM before implementation.
   [Baseline result](../experiments/native-cookie-profile/README.md#baseline-result)
2. Make the reference parser pass those tests, then exercise the same corpus
   and PSL source in both probe brokers. Run algorithmic cases without devices
   where possible. On 2026-11-13 the JDK-only reference passed all 102 cases and
   236 assertions in two identical runs. Eleven single-rule mutations each failed.
   A review then found the D2 trailing-dot and D6 oversized-`Domain` defects in
   both ports. Rows P13, D14, D15 and X10 and `secure` checks were added, the
   ports were fixed, and both pass 109 cases and 254 assertions.
   [Review fixes](../experiments/native-cookie-profile/README.md#review-fixes)
   [Reference result](../experiments/native-cookie-profile/README.md#reference-result)
   The standard-library Swift port passed the same corpus on macOS without a
   simulator. It matched the Java reference on every observation of the corpus
   and of 120,000 generated cases. Both ports built the same PSL rules digest.
   [Swift result](../experiments/native-cookie-profile/README.md#swift-result)
   Both broker ports remain. A broker port invalidates the retained 63-case
   collections, so it waits for step 3.
3. A paired device run against the controlled fixture needs a separate,
   explicit resume, as before.
