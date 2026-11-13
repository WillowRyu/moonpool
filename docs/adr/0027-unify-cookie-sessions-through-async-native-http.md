# 27. Unify cookie sessions through asynchronous native HTTP

Date: 2026-11-03
Status: Proposed overall; admission baseline, iOS presence-evidence rule and native HTTP transport
rules accepted as design directions on 2026-11-03, the Android broker client on 2026-11-04,
the shared parser reaffirmed on 2026-11-09, D2-A, D3-B, D4-A, D5, D6, D8 and D9 accepted on 2026-11-11, and
ASCII whitespace in the line split and canonical request hosts on 2026-11-13.
Cross-platform cookie parity is a maintainer requirement;
option 1 is preferred, while its compatibility cost is under review. No SPEC,
capability, SDK implementation or new native measurement is adopted here.

## Context

T28 measured working Android local HTTPS cookies and unavailable iOS custom-
scheme cookies. The maintainer explicitly requires the same application-facing
behavior on Android and iOS. Recording the difference does not satisfy that
requirement. Portals/Capacitor supplies native cookie/HTTP support, but its
document.cookie compatibility path includes synchronous native calls. Moonpool's
all-async bridge and host-credential isolation remain binding constraints.

The maintainer prefers a common asynchronous API and asked whether migration
would inconvenience developers. The [contract proposal](../native-cookie-http-contract.md)
defines automatic session handling, explicit API migration and the remaining gates.
The [paired evidence plan](../native-cookie-http-conformance-plan.md) records
the review, C01–C12 procedures and C09/C10 as the first feasibility experiment.
The subsequent [bounded C09/C10 evidence](../native-cookie-suppression-verification.md)
shows isolated policy effects but retained-cookie read/send on iOS. Empty stores
blocked before load pass. The maintainer subsequently accepted the
[admission baseline](../native-cookie-store-admission.md); recovery/migration,
the remaining HTTP contract and final normative approval stay open.

## Accepted admission baseline — 2026-11-03

On both platforms, require verified absence of browser cookies under trusted
per-app ownership before admission. Refuse cookie-present or unverified stores
without clearing data or remapping origins/stores. A failed shared gate retires
that app's Portals; other apps and the host remain independent. Preserve browser
and provider data and the separate native HTTP session. No automatic cookie
deletion or import. A future explicit host recovery needs separate approval/proof.

The maintainer accepted this design direction, not all of ADR 0027. Complete
inventory, concurrency, native integration, T29/T31 details and final SPEC work
remain gated. The retained iOS failure is unchanged; no implementation is implied.

Subsequent [bounded admission research](../native-cookie-admission-verification.md)
checks native presence, preserved data and private request/owner identity guards.
These experimental controllers are not a production scheduler or a wire change.
Complete iOS partitioned inventory and real writer exclusion remain open.

## Accepted iOS presence-evidence rule — 2026-11-03

[iOS partition and writer verification](../native-cookie-partition-writer-verification.md) found that a new process's first
`getAllCookies` can report empty for a store holding cookies. The maintainer accepted this
rule as a design direction, in addition to the baseline above:

1. An enumeration counts as evidence only after the same process has awaited cookie-policy
   completion for that store. An enumeration before that point is never evidence.
2. `fetchDataRecords` and `getAllCookies` must both report no cookies. Any disagreement is
   unknown and refuses admission.
3. Support is claimed per measured iOS version. An unmeasured or failing version is unknown
   and refuses admission.

This is a stricter condition for trusting "empty", not a fix: the ordering is undocumented
and its cause is unknown. [A later bounded run](../native-cookie-empty-store-verification.md) gave the correct verdict for all 168
cookie-free and cookie-bearing stores on one iOS simulator configuration, and
[another](../native-cookie-first-question-verification.md) did for all 36 stores asked about first in a new process. No SPEC text or
implementation is adopted. [Android's `hasCookies`](../native-cookie-android-restart-verification.md) was correct in all 250 stores on one
emulator configuration, so this rule stays iOS-only.

## Accepted Android broker client — 2026-11-04

[Measured](../native-http-global-handlers-verification.md): a host's global `CookieHandler` and `Authenticator` reach Android
`HttpURLConnection` requests with no per-request opt-out. [OkHttp](../native-http-okhttp-verification.md) ignored both when measured,
but resends on a 503 with `Retry-After: 0`. The maintainer accepted this as a design direction:

1. **The Android broker uses OkHttp, pinned to exactly 5.5.1.** No dynamic version. Raising the pin means rerunning the probe first,
   because a resend or isolation behavior can change between versions. `HttpURLConnection` is not used for the broker.
2. **Configured as measured:** no redirects, `retryOnConnectionFailure(false)`, no cache, default cookie jar and authenticator. The
   accepted "SDK never retries" rule also needs a network interceptor that hides `Retry-After` from OkHttp and keeps its value.
3. **Reviewed at T56,** against the selected host's `compileSdk` and its own OkHttp version. 5.5.x asks hosts for `compileSdk` 37. That
   is accepted for now: no host is selected yet, it is a build requirement only, and lowering it later does not break a host.

4. **The broker follows `ProxySelector`;** it does not set `Proxy.NO_PROXY`. This keeps OS and host proxy behavior under the "follow OS
   behavior" principle. The selector receives only the scheme, host and port, not a credential, and the host already chooses the approved
   service origins. No proxy authenticator is set, so a host's credentials are not offered to a proxy. Real proxies and proxy
   authentication are not measured yet.

Still open: a host's newer OkHttp replacing the pin. No dependency or broker exists in production packages, and the rest of this ADR
stays proposed.

## Accepted native HTTP transport rules — 2026-11-03

[Native HTTP transport evidence](../native-http-transport-verification.md) found three iOS conflicts with the proposal below. The maintainer
accepted these rules as a design direction. The principle: follow OS behavior unless it changes what a mini
app sees differently per platform.

1. **One cookie pipeline.** Each adapter folds received `Set-Cookie` fields with `, `, then both split them
   the same way and pass the lines to one shared parser. Native cookie parsers are not used. A cookie value
   containing `, name=` becomes an extra cookie on both platforms; this limit is documented. The pieces before the
   last also lose every attribute, including `HttpOnly`. The maintainer accepted stating this on 2026-11-05 rather than
   adding a rule that would also hide honest attribute-less cookies from scripts. Amended by the maintainer on
   2026-11-13: whitespace in the split rule `,\s*(?=[^;,=\s]+=)` means only the ASCII bytes SP, HTAB, LF, VT, FF and
   CR, which is Java's default `\s`. Unicode spaces such as U+00A0 are ordinary characters, so D1 then rejects their
   line. `NSRegularExpression` treats them as `\s`, so on macOS Foundation the retained iOS split stored a cookie that
   Java rejects. [Reference result](../../experiments/native-cookie-profile/README.md#reference-parser)
2. **OS behavior for HTTP authentication challenges.** The SDK never retries a request itself. A 401 stays a
   normal result on both platforms. iOS may send a request once more after a `Basic` challenge, without
   host credentials; this is OS behavior and is documented. A guest's own `Authorization` goes on both attempts. Ambient credential and
   cookie stores stay disabled, so following the OS never exposes host credentials.
3. **Commit at header delivery.** Cookies commit when the HTTP client delivers response headers to the broker,
   and before a request's result settles. On iOS that delivery needs a first body byte or completion. Amended by the maintainer on
   2026-11-05: when a `Basic` challenge makes iOS resend, the first response reaches the challenge handler instead, so the broker commits
   from its `failureResponse`, under the same reset fence, and ignores cookies on the resend.

These accept no other part of this ADR, change no SPEC text and implement nothing.

## Shared parser reaffirmed over OS parsers — 2026-11-09

The maintainer asked whether per-app jars that keep each OS's cookie parser would cost less to maintain than
rule 1's shared parser: W (OkHttp and iOS `HTTPCookie` as they are), or W′ (iOS as the reference, with a few
Moonpool rules added on Android). The [parser comparison](../native-cookie-parser-comparison.md) fed 61 vectors
to both:

- They differ on 13. Among 12 common server shapes only one, but it is common: iOS caps lifetimes at 400 days
  and OkHttp does not. OkHttp also has no prefix rules, a security property, and iOS's API cannot express
  `SameSite=None`.
- OkHttp parses but does not store, so the Android jar is Moonpool code either way, and a persistent per-app
  iOS store would likely be too.
- Under W, an iOS update changes behavior on users' devices before an SDK update can align Android, and the
  public-suffix data differs: OkHttp 5.5.1 carries a list unchanged since 2024-12-31, while iOS's moves with
  the OS.

**Decision, accepted by the maintainer:** keep rule 1, X. Follow OS behavior where it is the same on both
platforms; where a mini app would see Android and iOS differ, Moonpool's one profile decides. Do not ask
again.

Swift and Kotlin will implement the same cookie profile and run the same vector corpus. iOS transport behavior,
such as header folding and the `Basic` resend, still needs measuring per supported OS.

## Accepted public-suffix policy (D2-A) — 2026-11-11

Both SDKs bundle the same pinned Public Suffix List revision, including ICANN and PRIVATE rules.
Profile `c04-1` pins the official snapshot at `3db7776` and records the full
commit, source checksum and retrieval command. Later revisions ship through
SDK releases on both platforms. [C04 snapshot](../native-cookie-c04-profile.md#public-suffix-list-snapshot)

This lets `auth.example.com` set `Domain=example.com` for use at `api.example.com` when both are approved
services for the same mini app. The parser rejects attempts to widen the scope to a public suffix such as
`co.uk`. The broker sends cookies only to the mini app's approved HTTPS service origins.

For an IP request host, a nonempty `Domain` must match the request IP exactly. Store a matching cookie as
host-only. The IP scope and stored flag then agree whether the server omits `Domain` or supplies that IP.
[C04 domain rules](../native-cookie-c04-profile.md#d2--domain-attribute-and-public-suffixes-9)

## Accepted canonical request hosts — 2026-11-13

A review of the reference parsers found that hosts outside the canonical form reach the jar as DNS names.
Foundation accepts `a..example.com`. Foundation and OkHttp both pass `127.0.0.1.`, `127.1` and `0x7f.0.0.1`
through. Resolvers commonly read the numeric forms as IPv4, which was not measured on a device, yet the jar let `Domain=0.0.1.` from `127.0.0.1.` reach
`10.0.0.1.`. The maintainer chose to refuse such targets (option A). Option B, rewriting them as URL parsers do, needs
a full WHATWG IPv4 parser in both SDKs, and the request on the wire would still name the original host. Option C, leaving
them to each OS, keeps the leak and the platform difference.

**Decision:** before approval, sending or any cookie step, the native provider and the shared jar accept only
canonical hosts. A DNS name has no empty label apart from one trailing dot. A last label that is a number, decimal or
`0x` hexadecimal, makes the host IPv4, and it must be four decimal octets without leading zeros or a trailing dot.
IPv6 literals stay bracketed. Compression of an expanded IPv6 literal is left to the broker port. Contract §2 states the
rule. Both reference ports implement it, and their self-tests share one table of accepted and refused hosts. This
concerns SPEC §9 and changes no SPEC text.

## Accepted cookie identity (D3-B) — 2026-11-11

Each mini app's jar identifies a cookie by `(name, canonical domain, path, host-only)`.
A response cookie replaces or expires an entry with the same identity. An approved
subdomain can write the matching domain entry while the parent host-only entry survives.
Both entries can match a request to the parent. This concerns cookie integrity under
SPEC §9. T29 defines the public selector for deleting an exact script-readable identity.
[C04 identity rules](../native-cookie-c04-profile.md#d3--cookie-identity-and-host-only-flag)

## Accepted cookie path comparison (D4-A) — 2026-11-11

Use the percent-encoded path sent in the request for cookie matching and default
path calculation. Compare the parsed `Path` value as written. The path-match
rule uses literal `/` separators, so `%2F` remains data in the path. This preserves
the declared cookie scope and concerns SPEC §9.
[C04 path cases](../native-cookie-c04-profile.md#d4--which-request-path-is-compared)

## Accepted cookie expiry (D5) — 2026-11-11

For an accepted cookie line, ignore malformed expiry attributes. Use the last
valid `Max-Age` if present, or the last valid `Expires` as a fallback. Store a
session cookie when both yield no expiry. A server response expiring at or
before receipt deletes the matching D3-B entry, whether script-readable or
`HttpOnly`. At or after their expiry, remove stored cookies before building
the `Cookie` header or a `cookies.get` result. This concerns cookie integrity
under SPEC §9.

Both SDKs cap the persistent expiry from a response cookie's `Max-Age` or `Expires` at 400 days after receipt.
This follows the 6265bis-22 recommendation and matches the observed iOS result for a 730-day `Expires`.
C04 checks the cap with a controlled clock. T53 uses resource measurements to set common count and size
limits and eviction rules. [C04 expiry rules](../native-cookie-c04-profile.md#d5--expiry)

## Accepted cookie prefixes (D6) — 2026-11-11

Check `__Secure-` and `__Host-` case-insensitively in ASCII. Use the full original
name for cookie identity. Both prefixes require an HTTPS response with `Secure`.
`__Host-` also requires an explicit `Path=/` and omission of the `Domain` attribute.
This keeps host-specific cookies scoped to the issuing host and prevents case
variants from bypassing the checks. Apply the checks before commits, including
expiry deletions. The proposed `cookies.set` rejects these prefixed names.
This concerns SPEC §9. [C04 prefix rules](../native-cookie-c04-profile.md#d6--prefixes)

## Accepted Cookie header order (D8) — 2026-11-11

Sort matching cookies by descending `Path` length, then by earlier creation
order for equal lengths. Preserve the creation order when replacing an entry
with the same D3-B identity. A new entry receives a new order, including after deletion
and reissue. Serialize each matching entry as `name=value` and join pairs with
`; ` in that order. This gives both SDKs the same header value for the same
cookie history, including when several entries share a name.
[C04 header cases](../native-cookie-c04-profile.md#d8--cookie-header-order-and-form)

## Accepted unsupported attribute handling (D9) — 2026-11-11

Ignore `Set-Cookie` attributes outside the profile, including `Priority` and
`Partitioned`. Apply the supported rules to the cookie and store eligible cookies
in the requesting mini app's jar. `Partitioned` variants with the same D3-B identity
address the same entry for replacement and expiry. This uses the app-based
cookie boundary under SPEC §9. T53 defines resource limits and eviction.
[C04 attribute cases](../native-cookie-c04-profile.md#d9--unknown-and-newer-attributes)

## Proposed decision

- Provide the same Promise-based http.request and cookies.get/set/delete
  contracts on both native platforms. Native HTTP automatically consumes and
  attaches app-owned cookies; ordinary login requests require no JS cookie read.
- Keep one native-owned authoritative cookie jar per full manifest id, shared
  by that app's Portals. Isolate it from WebView jars, host HTTP clients and
  other apps. The broker never directly projects HttpOnly cookie values; public
  header results exclude Set-Cookie. A service can still reflect its own data.
- Use an explicitly granted native service-client capability with host-approved
  HTTPS service origins. This is not Fetch/CORS emulation. Each approved initial
  service request has the declared first-party session context on both OSes;
  no automatic redirects or guest-supplied same-site claims are permitted.
- Disable engine-managed WebView cookies on both platforms before guest load.
  Raw document.cookie is unavailable on both; authenticated API traffic uses
  the SDK. Remote browser connections/forms to APIs are blocked in this profile;
  separately allowed resource requests never receive broker cookies. Permitted
  remote scripts join app trust and can invoke the app's granted SDK methods.
  Platform-local suppression and network policy must be proven, not assumed.
- Serialize native jar operations and fence actual cookie writes on app-wide
  http.resetSession. A late old response cannot restore the cleared session.
  Keep storage.* and browser data lifetimes independent of session reset.
- Offer an explicit request adapter for clients supporting injected transports.
  Do not patch global fetch/XHR or emulate synchronous document.cookie with an
  eventually synchronized cache. Document the supported adapter subset.

## Consequences

New mini apps get one API and automatic cookie sessions. Existing applications
must migrate their transport boundary; libraries directly reading document.cookie,
browser redirect login, forms, workers and arbitrary global-fetch integrations
are not drop-in compatible. An adapter reduces changes only where a client accepts
one. An async API does not alter the server's HTTP Cookie/Set-Cookie format.

The service-client context intentionally permits its own Strict/Lax/default
cookies on approved native requests. It does not recreate browser SameSite CSRF
gating; authority comes from the http grant, trusted endpoint configuration and
app-isolated credentials. This security/compatibility choice needs final review.

Native default jars, CORS bypass hidden behind a fetch label, global cookie
switches and JS-only guards cannot establish this contract. New public methods,
scope validation, protected-cookie/error handling and provider outcomes require
explicit SPEC/implementation work after approval. The current host maps provider
throws to fixed -32603; the proposed error mapping is not available automatically.

T28 remains open for this contract and paired conformance evidence. Preserve its
original measurements as evidence of the previous configuration. T29/T31/T35,
native integration, T48 durability and T53 resource defaults retain their gates.
No device or crash experiment is resumed by this design task.
