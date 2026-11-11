# T28 — Common native cookie and HTTP contract proposal

Date: 2026-11-03
Status: Design proposal for [ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md).
The maintainer requires Android/iOS parity and prefers the common async API,
subject to review of developer compatibility. No runtime, public API, manifest
scope or SPEC change is implemented. This concerns SPEC §3, §6–§9.

**Accepted amendments, 2026-11-03:** after [native HTTP transport evidence](native-http-transport-verification.md), the maintainer accepted
one cookie pipeline (§4), OS behavior for HTTP authentication challenges (§5) and commit at header delivery (§5) as
design directions. The Android broker client followed on 2026-11-04 (§2). On 2026-11-05 the maintainer accepted keeping the pipeline and stating
what its limit does to `HttpOnly` (§4), and committing the first response of an iOS `Basic` challenge (§5). On 2026-11-09, after
[comparing the OS parsers](native-cookie-parser-comparison.md), the maintainer reaffirmed the shared parser (§4, ADR 0027).
On 2026-11-11 the maintainer selected the D2-A public-suffix and exact-IP rules, the D3-B cookie identity, the D4-A path rule,
the D5 expiry rules including the 400-day lifetime cap, the D6 prefix rules, D8 header ordering and D9 attribute handling (§4).
Other clauses remain proposed.

## 1. Required outcome and compatibility

The same supported call sequence must produce the same cookie selection,
response projection, error categories and lifetime behavior on Android and iOS.
Do not offer Android-only raw cookies while describing iOS unavailability as an
acceptable implementation difference. A configuration is unsupported until both
adapters pass the same contract vectors; no platform-default fallback.

The proposed surface is a native service client. It retains asynchronous bridge
calls and does not promise the complete browser Fetch/cookie environment.

| Developer's situation | Migration and promise |
| --- | --- |
| New mini app using the SDK | One API on both OSes; server cookies managed automatically |
| Existing centralized API client | Replace its transport at one integration point where supported |
| Client accepting an injected request adapter | An explicit adapter can translate its supported request/result subset |
| Code reading document.cookie directly | Change to an awaited cookie API, or remove manual login-cookie handling |
| Library depending on global fetch/XHR, browser form/redirect login or workers | Compatibility is not automatic; evaluate the actual library/flow before claiming support |

All method names below are **proposed**, not existing exports. No global fetch,
XHR or cookie monkeypatch is introduced. A future request adapter needs an honest
supported-feature table, including credentials and redirects, rather than a
blanket Fetch-compatible label. It must live outside the platform-free kernel
where it uses browser Request/Response APIs.

```js
// Illustrative future API; both platforms would run this same mini-app code.
await moonpool.http.request({
  url: 'https://api.example.com/login',
  method: 'POST',
  json: { username, password },
});
// Eligible server Set-Cookie fields have committed to this app's native jar.
const me = await moonpool.http.request({ url: 'https://api.example.com/me' });
// Native session attaches eligible cookies without a JS read of the cookie jar.
```

## 2. Authority, ownership and request context

The native manager selects the full manifest id from the authenticated Portal
binding and retains one jar per app. Same-app Portals share it; different apps,
host HTTP clients and host-authenticated WebViews do not. Guest appId/jar/context
claims are rejected. Do not copy host cookies, tokens, client credentials or
default native authentication state into it. The broker keeps protected values
in native providers under ADR 0025; never directly project them into guest or
private-runtime bootstrap, cookie APIs, request metadata, header projections,
diagnostics, errors or notifications. HttpOnly cannot stop an approved service
from reflecting a received cookie in its own response body; normal service
response data remains that service's responsibility.

Proposed method namespaces are permission scopes: http and cookies. Declare and
grant them using the existing model, then check at dispatch. Reading script-
visible cookies does not grant HTTP access; HTTP use does not grant JS access
to protected cookies. HTTP requests and URL-targeted cookie operations also need
a host-selected approved HTTPS service origin for that app. App-wide resetSession
needs the bound app's http grant and has no service target. The native provider
canonicalizes a targeted operation's URL and
resolves the registration; guest URLs do not supply policy or an origin allowlist.
No endpoint-discovery API or plugin registry is added.

Use normal TLS validation. Reject userinfo, fragments and non-HTTPS service URLs.
Recheck the owner before queued work starts. Native clients must disable their
ambient cookie handlers and shared credential stores; Cookie and Set-Cookie
processing belongs to this broker. Never modify application-global native settings.
**Android client accepted, 2026-11-04:** [Android `HttpURLConnection`](native-http-global-handlers-verification.md) cannot meet both
sentences while a host has set a global `CookieHandler` or `Authenticator`. [OkHttp](native-http-okhttp-verification.md) ignored
both when measured, so the maintainer accepted OkHttp, pinned to 5.5.1, as a design direction; see [ADR 0027](adr/0027-unify-cookie-sessions-through-async-native-http.md).

**Native service-session context:** an initial request to an approved service
origin is treated as that service's first-party native transaction. Derive this
context from trusted registration, not from the guest's physical .invalid or
moonpool URL, a request-body flag, or claimed top-level navigation. This makes
the supported context identical on both platforms. Strict/Lax/default cookies
are eligible within this context; browser SameSite CSRF filtering is not reproduced.
Permission and service authorization are the boundary. This is a deliberate
proposal requiring review, not a statement that arbitrary browser cross-site
cookies work or a way to reuse host login state.

Native networking does not silently become subject to browser CORS. This profile
uses explicitly granted native HTTP authority. CORS headers do not decide SDK
response visibility, and a CORS failure from an ordinary browser request is not
reinterpreted as a successful SDK request. Transparent Fetch/CORS semantics would
be a different compatibility profile.

## 3. Proposed application surface

| Method | Proposed behavior |
| --- | --- |
| http.request | HTTPS service request; GET if method omitted; credentials include by default, or explicit omit; returns status, sanitized headers and supported response body |
| http.resetSession | Clear this app's entire native cookie jar and fence its old in-flight HTTP work; retain browser/provider storage and other apps |
| cookies.get | Awaited read for an approved URL. Return only script-readable matching cookies in an array that preserves separate identities with the same name |
| cookies.set | Awaited script-cookie update for an approved URL; no HttpOnly option, creation or overwrite of protected cookies |
| cookies.delete | Delete the exact script-cookie identity; no protected-cookie mutation or cross-app selection |

http.request's include mode selects outgoing jar cookies and commits eligible
response cookies before its success Promise resolves. Omit does **both**: no
jar cookies sent and no response cookie writes. It does not remove a caller's
explicit, guest-owned Authorization header or promise an anonymous request.
There is no host-credential injection. The credentials default is deliberately
stated; it is not Fetch's same-origin default.

Reject caller-supplied Cookie/Cookie2, Host, Origin, Proxy-Authorization,
Content-Length and transport-control/Sec-* headers. The native transport owns
those fields; credentials mode cannot be bypassed by spelling a Cookie header.
Header comparison is case-insensitive. Never expose raw Set-Cookie or Set-Cookie2
through success headers, errors, observers or an adapter. Guest-controlled header
fields cannot opt into another app's session.

The initial native HTTP client has no shared response cache. Disable ambient
cache and cached credential/challenge reuse; any later app-specific cache needs
the same isolation and conformance evidence. Normal TLS validation is retained.

Return HTTP 4xx/5xx as HTTP results, not bridge failures. Initial redirects are
manual: return a sanitized 3xx response, never issue the next request or navigate
a WebView automatically. Eligible cookies from that original allowed response
must commit in include mode while its session generation is current, as with
returned 4xx/5xx results. Location is data; any later explicit request passes
fresh endpoint authorization and selects its own service session. Redirect-based
browser authentication is outside this initial surface.

Proposed request/result bodies cover ordinary JSON and UTF-8 text first. Exact
schemas, byte/charset handling, header lists, cancellation and supported adapter
types must be finalized with T29/T31 before implementation. File upload,
streaming, browser Request/Response equivalence and automatic redirect policy
are not implied. No package exports or placeholder native code are scaffolded.

## 4. Cookie behavior shared by both adapters

Use the frozen `c04-1` behavior and one conformance corpus for parsing,
domain/public-suffix data, replacement, matching and expiry. The C04 profile
defines the accepted rules and names the exact snapshot. RFC 6265 and
6265bis-22 inform the design. [C04 profile](native-cookie-c04-profile.md)

Under D2-A, both SDKs bundle the same verified PSL source, including ICANN
and PRIVATE rules. New revisions ship through SDK releases on both platforms.
For an IP request host, a nonempty `Domain` must match the request IP exactly.
Store a matching cookie as host-only.
[C04 domain rules and snapshot](native-cookie-c04-profile.md#d2--domain-attribute-and-public-suffixes-9)

| Area | Required behavior |
| --- | --- |
| Selection | Match host-only/Domain, Path and Secure rules for the approved request URL; ports are not cookie partitions |
| Cookie header | Order matching entries by descending `Path` length and earlier creation for equal lengths. Preserve creation order on replacement. Serialize the entries as `name=value` pairs joined by `; `, preserving repeated names |
| Path | Match the parsed `Path` as written against the percent-encoded request path. Use literal `/` separators. Derive the default cookie path from that encoded path |
| Line extraction | iOS cannot expose separate Set-Cookie fields, so each adapter folds received fields with `, ` and both split them by one rule before one shared parser. A value containing `, name=` becomes an extra cookie on both platforms, and the pieces before the last lose every attribute, including `HttpOnly`, so a script can read them ([measured](native-http-broker-verification.md)). This needs a server outside RFC 6265's grammar. Native cookie parsers are not used |
| Validation | Reject public-suffix/sibling Domain escalation and invalid names/values from those lines without repairing them |
| Unsupported attributes | Ignore attributes outside the profile, including `Partitioned` and `Priority`. Store eligible cookies in the app's jar using the normal D3-B identity |
| Identity | Within an app's jar, key by `(name, canonical domain, path, host-only)`. Replacement and expiry target that exact identity. Matching cookies with the same name remain separate entries |
| HttpOnly | Server may set it; script APIs cannot directly read, create, overwrite or delete that protected cookie identity; SDK HTTP can send it when eligible. A piece that lost the attribute under the Line extraction limit is not protected |
| SameSite | Store the normalized attribute; None requires Secure; use the explicit first-party service context from §2, never claim browser cross-site filtering |
| Prefixes | Check `__Secure-` and `__Host-` case-insensitively before any response cookie commit. Both require `Secure` on HTTPS. `__Host-` also requires explicit `Path=/` and omission of `Domain`. Keep original name spelling for identity. The proposed `cookies.set` rejects either prefix |
| Expiry | Prefer the last valid `Max-Age`, falling back to the last valid `Expires` or a session cookie. Cap persistent expiry at 400 days after receipt. A valid server expiry at or before receipt deletes the matching entry, whether script-readable or `HttpOnly`. Remove expired entries before building a `Cookie` header or `cookies.get` result |
| Lifetime | Session cookies survive Portal reload/recreation but end on native host-process restart; persistent cookies retain their defined expiry across controlled restart |

Manual setters use structured fields rather than a raw Set-Cookie string and
cannot supply HttpOnly. Script values must satisfy the published cookie syntax;
Unicode encoding is caller-explicit, not platform-specific coercion. T53 supplies
measured common defaults for cookie counts, total size and eviction. T48 defines
durable-write and backup/recovery guarantees. Until these are fixed and paired tests pass, the
profile remains unimplemented and no full cookie-parity claim is made.

## 5. Ordering, reset and errors

Serialize selection/mutations in the native app owner, independently of disposable
Portal JS runtimes. Awaited set/delete completion must be visible to the next
request or read. Concurrent response-cookie batches commit in the order the HTTP client
delivers response headers to the broker, not request-start order; do not promise which
remote response arrives first. On iOS that delivery needs a first body byte or completion. When a `Basic` challenge makes iOS resend a
request, the first response reaches the challenge handler instead of the broker's response callback. The broker commits that batch from
the challenge's [`failureResponse`](native-http-failure-response-verification.md), under the same reset fence, and ignores cookies on the
resend, so the jar holds the first response's cookies on both platforms. Commit each batch
before that operation's successful result settlement. A later body/network
failure is not a rollback guarantee; T29 must pin body/error projection cases.

resetSession advances an internal native session generation, clears this app's
jar and establishes a completion barrier for subsequent work. Old requests are
prevented from committing cookies even if their underlying network operation
finishes later. They cannot restore the session in another same-app Portal.
Fence actual mutation paths, not merely late bridge callbacks. The generation is
host-owned and separate from document generations; the guest cannot choose it.
Do not use an uncontrolled platform auto-jar that writes before the fence.

An ordinary client timeout or document replacement does not undo accepted
network effects or eligible later cookie writes. The session-reset generation
is the explicit cookie-write fence; document generations control reply delivery.

Session reset is local. Server logout/revocation is a separate explicit request;
accepted server effects are not rolled back. Portal close is not session reset.
If reset fails, keep the native session unavailable rather than reviving old
credentials. Reloading a document cannot erase the jar or undo a completed reset.

Proposed bridge mappings preserve existing validation/scope precedence:
invalid request fields -32602; denied grant/service or protected-cookie mutation
-32000; unavailable implementation -32001; native network/session failures
-32007 with fixed nonsecret reason values (including sessionReset); internal
faults -32603. HTTP statuses stay in normal results. Existing client timeout,
send failure and terminal-close rules remain their own outcomes. The SDK never retries
requests: a local error does not prove remote effects were absent. iOS may send a request
once more after a `Basic` challenge, without host credentials. A guest's own `Authorization` goes on both attempts, so a server counting
failures sees two, and the status and body a guest receives come from the last attempt. This OS behavior is documented, and
a 401 stays a normal result on both platforms, because ambient credential stores stay disabled.

These are proposals requiring explicit dispatch/provider-result support. Current
Host catches provider exceptions and returns fixed -32603; throwing an exception
does not implement the proposed mappings. T29/T31 finalize the error contract.

## 6. Browser-cookie suppression and developer ergonomics

Engine-managed cookies must be unavailable on **both** native platforms before
guest code runs. No WebView/native-jar synchronization, default-host jar seeding
or Android-only fallback. Raw document.cookie reads must be empty and writes
ineffective in this profile; the SDK APIs are the supported cookie surface.
Development diagnostics can flag legacy cookie use, but a JS wrapper is not a
security boundary across prototypes, frames and newly created realms.

Public candidates are iOS per-store cookie policy disallow and the CookieManager
obtained from Android's selected Profile. Android documentation also contains
application-wide cookie-policy wording: **profile-local effects must be measured**,
including unchanged host/other profiles. If suppression cannot be enforced with
public, isolated settings, the configuration cannot claim this profile. Existing
cookies/registration migration also needs an explicit policy; never silently
erase data or alter a host's global cookie setting.

The [2026-11-03 bounded C09/C10 measurements](native-cookie-suppression-verification.md)
now establish policy locality in the tested Android/iOS configurations. Android
suppresses seeded cookies; iOS disallow blocks new writes but leaves existing
HTTPS cookies readable and transmitted. Fresh empty partitions blocked before
first load pass on both. Policy installation alone therefore does not satisfy
this contract for retained iOS cookies. The maintainer accepted cookie-bearing/
unverified partition refusal as the design baseline on 2026-11-03; recovery remains
separate. Full network containment and production integration remain unverified.

The [accepted admission baseline and recovery draft](native-cookie-store-admission.md) specify
the same refusal rule on both OSes: inspect the entire owned engine cookie store
under serialized admission; cookies present or an unknown result prevent guest
execution. Cookie-free does not mean data-free: retain localStorage, IndexedDB,
storage.* and the independent native HTTP jar. Keep stable registrations and
reject stale owner callbacks. Automatic deletion/import is excluded; cookie-only
host recovery remains a separately gated future workflow. The baseline is accepted
as a direction; it does not reopen any production implementation gate or accept
the remaining HTTP contract.

Subsequent [native admission evidence](native-cookie-admission-verification.md)
records successful refusal for prepared ordinary/hidden-cookie cases and matching
controlled callback traces on both platforms. It does not establish complete iOS
partitioned inventory, actual writer exclusion or a production admission adapter.

The managed profile routes session/API requests through the SDK. Block remote
WebView fetch/XHR/connect and form submission before enabling a guest, while
retaining same-app local resources. Separately approved remote static resources
have no broker cookies attached to their WebView resource requests. A permitted
remote script/module executes in the app's realm and can invoke its granted SDK
methods; executable resources therefore join app trust. Existing origin/frame
containment still applies. CSP alone is not proof of
every network path: workers, cached registrations, frames, redirects and initial
script timing need actual platform negatives. Do not claim that arbitrary tokens
in a guest's URL/body can be recognized or prevented as credentials.

This reduces the chance that code works only on Android. It also makes the
migration cost explicit: libraries using their own global browser requests or
document.cookie need adaptation, and browser login navigation is not supported
automatically. Favor an explicit adapter for compatible API clients; no hidden
fallback to whichever platform happens to accept cookies.

## 7. Acceptance and roadmap

The [contract review and paired evidence plan](native-cookie-http-conformance-plan.md)
expands C01–C12 into procedures, independent observations and pending decisions.
Start with isolated C09/C10 suppression feasibility before a broker experiment;
the full acceptance corpus remains required. Bounded suppression results cover
only part of C09/C10 and retain the iOS failure; other cases remain pending.

Write failing tests against this proposed contract before implementation. The
same inputs and expected outcomes run on both adapters; use public markers and
an actual controlled server to observe Cookie receipt and Set-Cookie responses.

| Cases | Required observations |
| --- | --- |
| C01 ownership | A/B/host distinct; same-app Portals shared; forged app/jar/service/context cannot select authority |
| C02 automatic login | Login Set-Cookie commits, next authorized request carries it; include/omit test both outgoing and incoming effects |
| C03 HttpOnly | Controlled server records receipt; broker does not disclose the value through cookie APIs, request metadata, headers, errors or events; script mutation cannot overwrite the protected identity |
| C04 syntax/attributes | Domain/public suffix/Path/duplicate names, expiry/deletion, Secure, SameSite and prefixes have common expected outcomes |
| C05 context | First-party service-session semantics identical despite physical guest schemes; unapproved targets/context flags denied |
| C06 redirects | Original 3xx sanitized; eligible original-response writes pinned; controlled server confirms no follow-up request |
| C07 ordering | Awaited set→request, concurrent Portals/responses, shared read/delete visibility and reload/close retention |
| C08 reset | Hold a response with Set-Cookie, reset, then release it; no stale write/restored session, proper old-call rejection |
| C09 browser paths | document.cookie unavailable, browser API requests constrained, no native jar access through frames/prototypes/resources |
| C10 isolation | Cookie suppression affects only owned guest partitions; host and other profiles keep their working controls |
| C11 lifetime/errors | Session versus persistent restart, reset failure, supported/unsupported configuration and nonsecret common error projections |
| C12 migration | A small existing API client uses the explicit adapter; incompatible cookie/global-network libraries fail clearly on both OSes |

T28 adds a cookie-parity substep under its existing task id; it is not complete.
T29 finalizes codecs/schemas/errors; T31 coordinates pending/reset; T35 defines
native provider outcomes. T38/T39 verify browser-cookie policy and containment;
T42/T43 integrate app-isolated native HTTP/cookie providers; T51/T52/T61 require
the same security/compatibility corpus. T48/T53 retain durability/resource gates.
No new task ids, production implementation or device launch is authorized merely
by writing this proposal. Original T28 evidence is preserved and does not test
the newly proposed broker, suppression or server-observed session behavior.

## Primary references

- [HTML document.cookie](https://html.spec.whatwg.org/multipage/dom.html#dom-document-cookie): non-HTTP(S) documents are cookie-averse; a synchronous native shim is a separate compatibility mechanism.
- [RFC 6265](https://httpwg.org/specs/rfc6265.html) and [6265bis-22 work in progress](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-22): cookie scope, protection and storage-profile design references.
- [Fetch credentials/CORS](https://fetch.spec.whatwg.org/#cors-protocol-and-credentials): browser semantics differ from an explicitly granted native service client; CORS rejection does not undo accepted effects.
- [Capacitor Cookies](https://capacitorjs.com/docs/apis/cookies), [HTTP](https://capacitorjs.com/docs/apis/http), and [pinned native-bridge implementation](https://github.com/ionic-team/capacitor/blob/ef3ce6e4edfbc90b678f37138f387d1f524d6b35/core/native-bridge.ts#L379-L412): native support exists; document.cookie patching is optional and the inspected iOS path is synchronous.
- [iOS cookie-policy header](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKHTTPCookieStore.h), [Android Profile](https://developer.android.com/reference/androidx/webkit/Profile) and [CookieManager](https://developer.android.com/reference/android/webkit/CookieManager): public suppression candidates; source availability does not establish isolated operation.
- [Apple HTTP cookie storage](https://developer.apple.com/documentation/foundation/urlsessionconfiguration/httpcookiestorage) and [shared session](https://developer.apple.com/documentation/foundation/urlsession/shared): ambient native session state must not select the app's credentials.
