# T28 — C04 cookie profile draft

Date: 2026-11-06
Status: **Draft for maintainer review. Only D1 is accepted (2026-11-06).** It proposes the
profile inputs that [C04](native-cookie-http-conformance-plan.md#c04--cookie-syntax-and-attributes)
says must be frozen before that case can pass, and a first vector table that
follows the recommendations. No test, probe, SPEC, protocol or package changes.
**This concerns SPEC §9:** Domain, public-suffix, prefix and `HttpOnly` rules decide
which service receives a session cookie and what a script can read or plant.

**Paused on 2026-11-06:** the maintainer asked whether per-app jars that keep each OS's parser (W)
would be simpler than one shared parser. D2–D9 wait for that comparison;
[step 1, OkHttp](native-cookie-parser-comparison.md), is recorded.

## 1. Why C04 needs a profile first

[Contract §4](native-cookie-http-contract.md#4-cookie-behavior-shared-by-both-adapters) already requires one
shared parser and forbids the native cookie parsers, because the two
[measurably disagree](native-http-transport-verification.md). So no platform can
serve as the oracle. RFC 6265 and the cited 6265bis-22 draft leave choices open
and disagree with each other in places, so "follow the RFC" is not yet an oracle
either. Each decision below fixes one input; the vector table in §4 is then
derived from the decisions, not from what either device happens to do.

Scope: what the broker does with `Set-Cookie` lines it has already split, what
it stores, and which `Cookie` header it builds. The comma pipeline, commit
timing and the reset fence are accepted and unchanged. Counts, total size and
eviction stay with T53, durability with T48, and error codes with T29.

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

## 3. Decisions

Each item: what happens today, why it must be fixed, the options and their
consequences, and a recommendation.

### D1 — Parsing tolerance and characters

Today: a probe-specific character check. Problem: Android (OkHttp) and iOS
(`URLSession`) may decode non-ASCII header bytes differently before the broker
sees them, so any rule that accepts them risks two different stored values.

| Option | Consequence |
| --- | --- |
| **A. Strict ASCII line rule** — reject the whole line if it contains a byte outside `%x20-7E` other than HTAB, or any control character; trim spaces around name and value; keep quotes as part of the value; reject a line with no `=` or an empty name; reject name plus value over 4096 octets; ignore an attribute whose value exceeds 1024 octets | Identical on both platforms by construction. Servers that send UTF-8 cookie values lose those cookies; this needs to be stated |
| B. 6265bis lenient rule — accept nameless cookies and non-ASCII octets | Closer to browsers, but needs native evidence that both adapters hand over the same bytes, and nameless cookies need extra prefix-spoofing rules |
| C. RFC 6265 §4.1 server grammar (`cookie-octet`) | Rejects many cookies real servers send, such as values with spaces |

**Accepted on 2026-11-06: A.** The maintainer confirmed the consequence: a line
carrying raw UTF-8 bytes, in its name, value or an attribute, is dropped whole,
while other lines of the same response are unaffected and percent-encoded or
base64 values work. Script values follow the same rule, so a caller encodes them
explicitly. A server that a browser accepts with raw UTF-8 values is not
supported; a development diagnostic for the drop is a T29 question, and
relaxing toward B later, after native byte evidence, does not break stored
cookies. Nameless cookies are dropped deliberately: 6265bis needs a
special rule so that `=__Host-x=1` cannot imitate a prefixed cookie, and an
empty name also fails the structured setter in contract §3. Whether both
adapters even pass non-ASCII bytes through unchanged is a later native
observation, not a precondition for this rule.

### D2 — Domain attribute and public suffixes (§9)

Today: no domain cookies. Problem: a common login shape sets
`Domain=example.com` on `auth.example.com` for use at `api.example.com`. Without
public-suffix data, `Domain=co.uk` from `shop.co.uk` would also be accepted and
sent to every approved `*.co.uk` service of the same app: a session-fixation
path between two services the host approved for one app.

| Option | Consequence |
| --- | --- |
| **A. RFC domain cookies with a pinned Public Suffix List** — one snapshot, ICANN and private sections like browsers, shipped as the same data in both SDKs and named by revision in the profile | Supports the shared-parent login shape. Adds a data file and an update cadence tied to SDK releases; a stale snapshot is a known, versioned limit |
| B. Host-only only — reject every line with a `Domain` attribute that is not the request host, and store `Domain=host` as host-only (today's probe) | No data to maintain, safe. Breaks the shared-parent login shape; servers must set separate cookies per host |
| C. Accept `Domain` without public-suffix data | Rejected: cookie tossing across approved services |

Recommend **A**, because the plan's C04 observations already require
public-suffix rejection. Cookies still go only to approved service origins of
that app (contract §2), so a domain cookie never reaches an unapproved host.
If the maintainer prefers less maintenance for the first release, **B** is the
safe fallback, and it remains a strict subset that A can later relax.
Under A: strip one leading dot, lowercase, reject a non-ASCII `Domain`
(hosts are compared in their ASCII form), ignore an empty `Domain`; a `Domain`
equal to a request host that is itself a public suffix gives a host-only
cookie, any other public suffix rejects the line; an IP-address host only
accepts `Domain` equal to itself.

### D3 — Cookie identity and host-only flag

Today: host, path, name. Problem: under D2-A, `a=1` (host-only) and
`a=2; Domain=api.example.com` from the same host have the same domain string.
RFC 6265 §5.3 treats them as one identity, `(name, domain, path)`, and the new
line replaces the old one, changing the host-only flag. Chrome keeps them as two
cookies.

Options: **A. RFC identity, host-only not part of the key** — one cookie, the
newest wins, creation time kept. B. Flag in the key — two cookies with the same
name both sent to `api.example.com`, which a server reading the first `a` may
misread. Recommend **A**: it follows the written standard, and `cookies.get` and
`cookies.delete` then address an identity with one name, domain and path. Name
is case-sensitive; domain is compared lowercased.

### D4 — Which request path is compared

Today: both probes compare the percent-decoded path. Problem: `/a%2Fb/c` decodes
to `/a/b/c` and then matches a cookie with `Path=/a`, which a browser would not
send; invalid escapes may also decode differently on each platform. Options:
**A. The percent-encoded path as sent on the wire** (OkHttp `encodedPath`, iOS
`percentEncodedPath`), compared byte for byte; B. the decoded path. Recommend
**A**. The `Path` attribute is likewise compared as written, without decoding.
This is a probe gap, not a contract change: the probe's existing 63 cases use no
encoded paths, so their results are unaffected.

### D5 — Expiry

Today: only `Max-Age` ≤ 0. Recommend, from RFC 6265 §5.2 and §5.3 unless noted:

- `Max-Age` beats `Expires` regardless of order; for a repeated attribute the
  last one wins.
- `Max-Age` must be an optional leading `-` and digits, else it is ignored; a
  value ≤ 0 means expire now. `Expires` uses the RFC 6265 §5.1.1 date algorithm,
  including the two-digit year rule and rejection of years before 1601; an
  unparseable date is ignored.
- A line that is already expired deletes the matching identity and stores
  nothing. A deletion from an HTTP response may remove an `HttpOnly` cookie.
- Expired cookies are removed before a `Cookie` header or a `cookies.get`
  result is built. A cookie is expired when the current wall-clock time is at
  or after its expiry time; this boundary is a choice the RFC leaves loose.
- **Lifetime cap, decision needed:** 6265bis caps `Max-Age` and `Expires` at
  400 days. Contract §4 says lifetime caps need T53 evidence. Options: adopt 400
  days now as a profile rule (recommended: it is a published privacy limit, not
  a resource default), or leave the cap open until T53 and mark those vectors
  pending.

Algorithmic vectors use a controlled clock. Native wall-clock behavior,
including a device clock change, is a separate observation.

### D6 — Prefixes

Today: none. Recommend: `__Secure-` requires `Secure`; `__Host-` requires
`Secure`, no `Domain` and `Path=/`; both checked **case-insensitively**, so
`__host-a` is held to the same rule. Recent 6265bis drafts made the check
case-insensitive; matching only the exact case would let a line with an
unusual case avoid the rule. The structured `cookies.set` has no `Secure` or
`Domain` field, so it rejects any name that starts with either prefix in any
case, rather than silently creating a prefixed cookie without its guarantees.
Its error code is a T29 question. Further prefixes discussed in newer drafts
are not adopted; before freezing, check the pinned draft text and list them.

### D7 — Secure and SameSite under the service context

Every service URL is HTTPS (contract §2), so `Secure` never filters a request in
this profile; it matters only for prefixes and `SameSite=None`. `SameSite` is
parsed case-insensitively as `Strict`, `Lax` or `None`; any other value is
stored as "default". All are eligible within the first-party service context
of §2. `SameSite=None` without `Secure` rejects the line, as today. No new
choice is proposed here; these vectors confirm the accepted text.

### D8 — Cookie header order and form

Recommend the RFC 6265 §5.4 order: longer path first, then earlier creation
time, where replacement keeps the old creation time. Serialize as
`name=value` joined by `; `. Ties beyond creation time cannot occur because the
broker numbers creations in one owner. Matches the probe.

### D9 — Unknown and newer attributes

Recommend: ignore every attribute the profile does not name, including
`Partitioned` and `Priority`, and keep the cookie. A `Partitioned` cookie is
then stored in the app's jar, which is already private to that app. Rejecting
such lines instead would break servers that add those attributes for browsers.

## 4. Draft vectors, profile `c04-draft-1`

These assume every recommendation above (D2-A, 400-day cap). Unless stated, the
response comes from `https://api.example.com/x/y` at controlled time `T0`, and
every host named is an approved service of the same app. "Sent" is the `Cookie`
header the broker builds for the named follow-up URL.

| Id | Input | Expected |
| --- | --- | --- |
| P01 | `a=1` | Host-only `api.example.com`, path `/x`; sent to `/x/z`, not to `/` or `www.example.com` |
| P02 | `a=1; Path=/` then `a=2; Path=/` | One cookie `a=2`, original creation time |
| P03 | `=v`, `a`, `=` | All rejected, jar unchanged (D1) |
| P04 | `a=1` + byte `%x01` | Rejected (D1) |
| P05 | `a="q r"` | Value `"q r"` with quotes |
| P06 | `a=é` | Rejected (D1) |
| P07 | Name plus value of 4096 and 4097 octets | First stored, second rejected |
| P08 | `  a =  1 ; Path=/` | Name `a`, value `1` |
| P09 | `a=1; Path=/p; Path=/` | Path `/` (last wins) |
| P10 | `a=1; Expires=Wed, 21 Oct 2099 07:28:00 GMT` | One cookie, not split at the date's comma |
| P11 | `sid=abc, x=y; Path=/; HttpOnly` | Accepted limit: `sid` script-readable, `x` `HttpOnly` |
| D01 | `a=1; Domain=example.com` | Domain cookie; sent to `example.com` and `www.example.com` |
| D02 | `Domain=.example.com`, `Domain=EXAMPLE.com` | Same as D01 |
| D03 | `Domain=other.com`, `Domain=www.api.example.com` | Rejected |
| D04 | From `shop.co.uk`: `a=1; Domain=co.uk` | Rejected (public suffix) |
| D05 | From a host that is itself a listed suffix: `Domain=` that host | Host-only cookie |
| D06 | From `127.0.0.1`: `Domain=127.0.0.1`; `Domain=0.0.1` | First host-only, second rejected |
| D07 | `a=1; Domain=` | Host-only |
| I01 | `a=1; Path=/` then `a=2; Domain=api.example.com; Path=/` | One domain cookie `a=2` (D3) |
| I02 | `a=r; Path=/` and `a=p; Path=/x` | Two cookies; to `/x/q` sent `a=p; a=r` |
| I03 | I02, then `cookies.get` for `/x/q` | Both, as an array, longer path first |
| A01 | `a=1; Path=/x` | Sent to `/x`, `/x/`, `/x/q`; not to `/xq` |
| A02 | `a=1; Path=x` | Default path `/x` |
| A03 | From `/a%2Fb/c`: `a=1` | Path `/a%2Fb`; sent to `/a%2Fb/d`, not to `/a/b/d` (D4) |
| A04 | From `/y`: `a=1` | Default path `/` |
| E01 | `a=1; Max-Age=60` | Sent at `T0+59s`, gone at `T0+60s` |
| E02 | Existing `a`, then `a=; Max-Age=0` or `Max-Age=-1` | Deleted |
| E03 | `a=1; Max-Age=abc`, `Max-Age=+5` | Session cookie |
| E04 | `a=1; Max-Age=60; Expires=<past>` and the reverse order | Kept for 60 s |
| E05 | Existing `a`, then `a=1; Expires=<past>` | Deleted |
| E06 | `a=1; Expires=<invalid>` | Session cookie |
| E07 | `a=1; Expires=Wed, 21 Oct 70 07:28:00 GMT` | Year 1970, past: nothing stored |
| E08 | `a=1; Expires=` 2099 or `Max-Age=999999999` | Expiry `T0+400d` |
| E09 | Existing `HttpOnly` `a`, response `a=; Max-Age=0` | Deleted |
| H01 | Existing `HttpOnly` `a`, response `a=2; Path=/` | Replaced, now script-readable (RFC 6265 §5.3) |
| X01 | `__Secure-a=1`; then with `; Secure` | First rejected, second stored |
| X02 | `__Host-a=1; Secure; Path=/`; with `Domain=api.example.com`; with `Path=/x` | First stored, others rejected |
| X03 | `__host-a=1` without `Secure` | Rejected (D6) |
| X04 | `cookies.set` with name `__Host-a` or `__SECURE-a` | Rejected, jar unchanged |
| S01 | `a=1; SameSite=None` without `Secure` | Rejected |
| S02 | `SameSite=Strict`, `SameSite=bogus` | Stored, sent to the service |
| O01 | `b=1; Path=/`, then `a=1; Path=/`, then `b=2; Path=/` | Sent `b=2; a=1` |
| U01 | `a=1; Partitioned; Priority=High; Foo=bar` | Stored as `a=1` |

Not yet vectors: native wall-clock changes, non-ASCII byte transport on each
adapter, counts and eviction (T53), restart lifetime (C11), and how a rejected
line is reported to diagnostics (T29).

## 5. After approval

1. Turn §4 into a versioned JSON vector file and failing algorithmic tests with
   a controlled clock, before any parser code. Proposed home:
   `experiments/native-cookie-profile/`, research only, with no package export.
2. Write one reference parser that passes them, then port the same rules to both
   probe brokers and run the vectors there without devices where possible.
3. A paired device run against the controlled fixture needs a separate,
   explicit resume, as before.

## 6. Questions for the maintainer

1. D2: public-suffix list (A, recommended) or host-only only (B)?
2. D5: adopt the 400-day cap now, or leave it to T53?
3. D3, D4, D6, D8, D9: accept as recommended, or name the item to discuss? D1 is accepted as A.
