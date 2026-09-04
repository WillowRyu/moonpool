# Moonpool Protocol Specification

**Version:** `0.1` (draft — unstable, breaking changes expected)
**Status:** Normative. Implementations MUST conform to this document.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Scope

Moonpool defines how a **host application** embeds a sandboxed **mini app**
(web content) and exposes a controlled set of native **capabilities** to it.

This document specifies:

- the wire protocol between host and mini app
- the handshake and lifecycle
- the capability and permission model
- the mini app manifest format
- security requirements that any conforming host MUST enforce

This document does **not** specify: bundle packaging, distribution, code
signing, or update mechanisms. Those are out of scope for `0.x`.

---

## 2. Terminology

| Term           | Meaning                                                                                |
| -------------- | -------------------------------------------------------------------------------------- |
| **Host**       | The native application embedding mini apps. Owns the runtime, enforces permissions.    |
| **Mini app**   | Web content (HTML/CSS/JS) executed inside an isolated web view.                        |
| **Portal**     | One host-managed instance of a mini app, including its web view and bridge connection. |
| **Bridge**     | The bidirectional message channel between a Portal and the host.                       |
| **Capability** | A single host-provided function callable by a mini app (e.g. `profile.get`).           |
| **Scope**      | A permission unit. Corresponds to a capability namespace.                              |
| **Transport**  | The platform-specific mechanism that moves bytes across the bridge.                    |

---

## 3. Architecture

Moonpool separates a platform-independent **kernel** from platform-specific
**transports**. All protocol logic — encoding, request/response correlation,
dispatch, permission checks — lives in the kernel and MUST NOT depend on any
platform API.

```
┌─────────────────────────── Host ───────────────────────────┐
│  Capability handlers                                        │
│  Dispatcher + permission gate      ← kernel (pure)          │
│  Transport adapter                 ← platform-specific      │
└─────────────────────────────┬───────────────────────────────┘
                              │  JSON-RPC 2.0 messages
┌─────────────────────────────┴───────────────────────────────┐
│  Transport adapter                 ← platform-specific      │
│  Client (promise correlation)      ← kernel (pure)          │
│  Mini app code                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Transport contract

A transport is the **entire** platform boundary. Both sides implement:

```ts
interface Transport {
  send(message: JsonValue): void;
  onMessage(handler: (message: JsonValue) => void): () => void; // returns unsubscribe
  close(): void;
}
```

A transport MUST deliver messages in order and MUST NOT modify payloads.
A transport MAY serialise to a string; the kernel is agnostic to this.

Known transports:

| Environment           | Mechanism                                                 |
| --------------------- | --------------------------------------------------------- |
| Browser (development) | `iframe` + `window.postMessage`                           |
| React Native          | `react-native-webview` `postMessage` / `injectJavaScript` |
| iOS                   | `WKScriptMessageHandlerWithReply`                         |
| Android               | `WebMessagePort` (Channel Messaging API)                  |

Android implementations MUST NOT use `@JavascriptInterface` for the bridge.
Reflection-based interfaces widen the attack surface and do not match
`postMessage` semantics.

---

## 4. Wire protocol

Moonpool uses [JSON-RPC 2.0](https://www.jsonrpc.org/specification) unmodified.
This section defines only the profile restrictions and Moonpool-specific
semantics layered on top.

### 4.1 Profile restrictions

- Batch requests (top-level arrays) are NOT supported in `0.x`. A receiver
  MUST respond with `-32600` Invalid Request.
- `id` MUST be a positive integer, unique per connection, monotonically
  increasing. Implementations MUST NOT reuse ids within a connection.
- Requests without an `id` are notifications. The receiver MUST NOT reply.

### 4.2 Request

```json
{ "jsonrpc": "2.0", "id": 1, "method": "profile.get", "params": {} }
```

`params` MUST be an object or omitted. Positional (array) params are not
supported; a receiver MUST respond with `-32602`.

### 4.3 Response

```json
{ "jsonrpc": "2.0", "id": 1, "result": { "displayName": "Jane" } }
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Permission denied",
    "data": { "scope": "profile" }
  }
}
```

### 4.4 Error codes

Standard JSON-RPC codes apply:

| Code     | Meaning          |
| -------- | ---------------- |
| `-32700` | Parse error      |
| `-32600` | Invalid request  |
| `-32601` | Method not found |
| `-32602` | Invalid params   |
| `-32603` | Internal error   |

Moonpool defines the following in the implementation-defined range:

| Code     | Constant                       | Meaning                                                |
| -------- | ------------------------------ | ------------------------------------------------------ |
| `-32000` | `PERMISSION_DENIED`            | Scope not granted to this mini app                     |
| `-32001` | `CAPABILITY_UNAVAILABLE`       | Method exists but is unavailable on this host/platform |
| `-32002` | `USER_CANCELLED`               | User dismissed a consent or picker UI                  |
| `-32003` | `TIMEOUT`                      | No response within the client timeout                  |
| `-32004` | `PROTOCOL_VERSION_UNSUPPORTED` | Host cannot speak the requested protocol version       |
| `-32005` | `NOT_INITIALIZED`              | Call made before `portal.initialize` resolved          |
| `-32006` | `RATE_LIMITED`                 | Too many calls; retry later                            |
| `-32007` | `HOST_UNAVAILABLE`             | Host cannot service the call in its current state      |
| `-32008` | `CONNECTION_CLOSED`            | Bridge connection closed before the call completed     |

`error.data` SHOULD carry structured context and MUST NOT contain host
credentials, tokens, or data belonging to another mini app.

### 4.5 Timeouts

Clients MUST apply a timeout to every request. Default: 30 000 ms.
On expiry the client MUST reject with `-32003` and discard the pending entry.
A late response for a discarded id MUST be ignored.

### 4.6 Connection teardown

Closing a client closes its transport, after which no response can arrive for
a request already in flight. On close a client MUST discard every pending
entry, clear its §4.5 timer, and reject the caller with `-32008`.
A client MUST NOT leave a request pending across a close.

`-32008` is terminal for the connection it is raised on: a caller MUST NOT
retry the call on that connection. Unlike `-32006` and `-32007` it says
nothing about host health — the host may be perfectly available.

---

## 5. Handshake

The mini app initiates. `portal.initialize` MUST be the first request on a
connection.

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "portal.initialize",
  "params": { "protocolVersion": "0.1" }
}
```

**Response**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "0.1",
    "miniApp": { "id": "com.example.hello", "version": "1.0.0" },
    "host": {
      "name": "moonpool-dev-host",
      "version": "0.1.0",
      "platform": "browser"
    },
    "grantedScopes": ["profile", "storage"],
    "environment": { "locale": "ko-KR", "colorScheme": "light" }
  }
}
```

Rules:

- Until `portal.initialize` resolves, the host MUST reject every other method
  with `-32005`.
- If the host cannot speak the requested `protocolVersion`, it MUST respond
  with `-32004`. The connection does not initialize, so every method other
  than `portal.initialize` MUST continue to be rejected with `-32005`. A
  failed negotiation is not terminal: a mini app MAY retry
  `portal.initialize` with a different version, and a host MUST answer that
  retry on its merits. `-32004` describes one unsupported version, not a
  poisoned connection.
- `grantedScopes` is the authoritative permission set for the connection. It is
  the intersection of the manifest's declared permissions and what the host
  actually granted. Clients SHOULD use it to hide unavailable features.
- `platform` is one of `browser`, `ios`, `android`.

Version negotiation is exact-match in `0.x`. Semantic compatibility rules will
be defined at `1.0`.

### 5.1 Repeat handshake

A Portal's document can be replaced while the connection's transport stays
alive: a reload, an in-place navigation, or a development server's hot reload.
The replacement is a new client with a fresh id sequence, and the host has to
learn that it happened.

It cannot learn it from the transport. `Transport` (§3.1) carries frames and
nothing else; teaching it to report "the peer was replaced" would widen the
platform boundary every native port must implement, in order to describe an
event only some transports can observe. Nor can it rely on an embedder-level
signal — an iframe's `load` event, a web view's navigation callback. Those are
ordered against an inbound message only by the host's task scheduler, not by
any specification, so a host built on one would be depending on unspecified
ordering for a security-relevant boundary.

The handshake is the one signal ordered correctly by construction: it *is* the
new document's first message.

Therefore:

- A host MUST accept `portal.initialize` on a connection that has already
  completed one, and MUST answer it exactly as it answers a first handshake.
- Receiving a repeat handshake means the previous document is gone.
- `portal.initialize` MUST be the first request a **document** sends. It is
  first per document, not unique per transport.

On a repeat handshake a host MUST reset exactly the following, and MUST NOT
reset anything else:

| Reset — scoped to the document                         |
| ------------------------------------------------------ |
| Initialization state                                    |
| Request-id correlation: a new document restarts at `1`  |

Everything a host holds that is not on that list is preserved, including:

| Preserved — scoped to the origin or the user |
| --------------------------------------------- |
| Rate-limit counters (`-32006`)                 |
| Granted permissions, and any record of consent already asked for |
| `storage.*` contents (§8)                      |

The list is closed on purpose. The underlying rule is that state scoped to a
document's lifetime is reset while state scoped to the origin's lifetime
survives — but a host implementer applying that rule by judgement will
occasionally judge wrong, and an open-ended instruction to "reset what belonged
to the document" fails open. Reset only what is enumerated; when in doubt,
preserve.

Two rows carry the security weight:

- **Rate-limit counters.** A mini app able to clear its own counter by
  re-handshaking would make any future `-32006` policy (§11) unenforceable.
  The boundary is normative now, before that policy exists.
- **Consent already asked for.** A repeat handshake MUST NOT re-prompt the
  user for permission, and MUST NOT reset any record of a prompt already
  answered. Repeat handshakes are ordinary traffic — a multi-page mini app
  produces one per navigation — so a host that re-prompted on each would hand
  any mini app an unlimited supply of permission dialogs, and consent obtained
  by repetition is not consent. This binds the runtime-consent design still
  open in §11.

---

## 6. Capabilities

### 6.1 Naming

Method names MUST take the form `namespace.action`, lowerCamelCase on both
sides. The namespace **is** the permission scope. There is no separate scope
registry — this is deliberate, so a new method cannot silently escape the
permission model.

The `portal` namespace is reserved for protocol methods and requires no scope.

### 6.2 Core methods (`portal`, no scope required)

| Method              | Params                | Result             | Notes                                |
| ------------------- | --------------------- | ------------------ | ------------------------------------ |
| `portal.initialize` | `{ protocolVersion }` | see §5             | MUST be first                        |
| `portal.ping`       | `{}`                  | `{ "pong": true }` | Liveness / smoke test                |
| `portal.close`      | `{ reason? }`         | `{}`               | Requests host to dismiss this Portal |

### 6.3 `v0.1` capability set

Deliberately minimal. The goal is to exercise the permission model, not to be
useful.

| Method           | Scope     | Params           | Result                           |
| ---------------- | --------- | ---------------- | -------------------------------- |
| `profile.get`    | `profile` | `{}`             | `{ displayName, avatarUrl? }`    |
| `storage.get`    | `storage` | `{ key }`        | `{ value }` or `{ value: null }` |
| `storage.set`    | `storage` | `{ key, value }` | `{}`                             |
| `storage.delete` | `storage` | `{ key }`        | `{}`                             |

`storage.*` is namespaced per mini app id by the host. A mini app MUST NOT be
able to read another mini app's keys.

`storage.set` MUST reject a missing or top-level `null` value with `-32602`.
Nested `null` values are permitted. `storage.get` returns `{ "value": null }`
only when the key is absent.

### 6.4 Host-initiated notifications

Sent host → mini app as JSON-RPC notifications (no `id`). Mini apps MUST
tolerate unknown notification methods.

| Method                      | Params                               |
| --------------------------- | ------------------------------------ |
| `portal.lifecycle`          | `{ "state": "resumed" \| "paused" }` |
| `portal.environmentChanged` | `{ "colorScheme"?, "locale"? }`      |

---

## 7. Manifest

Every mini app MUST ship a `moonpool.json` at its package root.

```json
{
  "manifestVersion": 1,
  "id": "com.example.hello",
  "name": "Hello",
  "version": "1.0.0",
  "entry": "index.html",
  "protocolVersion": "0.1",
  "permissions": ["profile", "storage"]
}
```

| Field             | Required | Rules                                                                 |
| ----------------- | -------- | --------------------------------------------------------------------- |
| `manifestVersion` | yes      | `1` for this spec                                                     |
| `id`              | yes      | Reverse-DNS. `^[a-z0-9]+(\.[a-z0-9-]+)+$`. Immutable across versions. |
| `name`            | yes      | Display name, 1–40 chars                                              |
| `version`         | yes      | SemVer                                                                |
| `entry`           | yes      | Relative path, MUST NOT escape the package root                       |
| `protocolVersion` | yes      | Protocol version the mini app targets                                 |
| `permissions`     | yes      | Array of scope strings. MAY be empty.                                 |

A host MUST reject a manifest declaring an unknown scope rather than silently
dropping it — silent drops produce mini apps that fail at runtime for
non-obvious reasons.

---

## 8. Origin and isolation

Each Portal MUST be served from an origin unique to its mini app id:

```
moonpool://<mini-app-id>/
```

Hosts MUST implement this via a custom scheme handler
(`WKURLSchemeHandler` on iOS, `WebViewAssetLoader` on Android) and MUST NOT
load mini apps from `file://`. A real origin is required for `localStorage`,
IndexedDB, cookies, and CORS to behave correctly, and it is what makes the
browser's own origin isolation do the sandboxing work for us.

Consequences, which are load-bearing rather than incidental:

- Storage isolation between mini apps is enforced by the browser engine, not by
  Moonpool.
- The origin is stable across versions of a mini app, so its stored data
  survives updates.
- Changing the origin scheme is a breaking change for every deployed mini app.

### 8.1 Development transports

Web browsers provide no way for a page to register a custom scheme handler,
so a browser development transport cannot serve `moonpool://` origins
literally. What it MUST still satisfy is the invariant behind the scheme:
an origin unique to each mini app id, stable across reloads and sessions.

A development transport MAY substitute per-mini-app `http(s)` origins — for
example, one fixed localhost port per mini app. The mapping from mini app id
to origin MUST be pinned in configuration: origins are storage keys, so an
origin that drifts (such as an auto-incremented dev port) silently re-keys
the mini app's stored data.

The host page and every Portal MUST be served from distinct origins, even in
development. A same-origin Portal would make the §9.1 origin check pass
vacuously, leaving the security path untested precisely where it is
developed.

This subsection applies to development transports only. Production hosts
remain bound to the custom-scheme requirement above.

---

## 9. Security requirements

These are normative. A host that does not enforce all of them is not conforming.

1. **Origin binding.** The host MUST verify that every inbound message
   originates from the expected Portal origin, and MUST drop messages that do
   not. The bridge MUST NOT be reachable from any other origin.
2. **Navigation containment.** If a mini app navigates away from its own
   origin, the host MUST tear down the bridge for that Portal. External links
   SHOULD be opened in the system browser rather than in the Portal.
3. **Scope enforcement at dispatch.** The host MUST check the granted scope
   immediately before invoking a handler, not at registration time and not in
   the client. Client-side checks are a UX affordance only.
4. **No host credentials.** The host MUST NOT expose its own session tokens,
   cookies, or API keys to a mini app. Where a mini app needs authenticated
   access, the host MUST mint a separate, short-lived, mini-app-scoped token.
5. **Async only.** Every capability MUST be asynchronous. No synchronous bridge
   call may exist, at any layer, ever. A single synchronous API makes the
   native transports unimplementable.
6. **Input validation.** The host MUST validate `params` against a schema
   before dispatch and MUST NOT pass unvalidated input to platform APIs.
7. **No ambient authority.** A capability MUST NOT infer permission from
   context (which screen invoked it, how recently the user interacted, etc.).
   Only `grantedScopes` grants.

---

## 10. Versioning

- `protocolVersion` is independent of package versions.
- `0.x` offers no compatibility guarantees. Breaking changes MAY land in any
  release and MUST be recorded in `CHANGELOG.md`.
- From `1.0`, the protocol will follow SemVer and hosts will be expected to
  support a documented range of protocol versions.

---

## 11. Open questions

Tracked here rather than decided prematurely. Each SHOULD become an ADR in
`docs/adr/` when resolved.

- **Consent UI ownership.** Are permissions granted entirely at install time,
  or can a capability trigger a runtime consent prompt? Runtime consent implies
  `grantedScopes` is not static for the connection lifetime.
- **Streaming and progress.** JSON-RPC has no stream primitive. Server-initiated
  notifications correlated by a call id are the likely answer, but this is
  unspecified.
- **Multiple Portals in one host.** Whether Portals can address each other, and
  whether a shared broadcast channel exists.
- **Capability discovery.** Should a mini app be able to query which methods a
  host implements, beyond the scopes it was granted?
- **Rate limiting.** `-32006` is reserved but no policy is defined. §5.1
  already binds any future policy: a repeat handshake MUST NOT reset counters.
- **Responses that outlive their document.** §5.1 lets a new Portal document
  take over a live connection, and every document numbers its requests from
  `1`. A response the host had already posted for the previous document can be
  delivered after the swap and matched, by id, against an unrelated request
  from the new one. The failure mode is not an error: the new document's
  promise **resolves with the previous document's data, silently**, and neither
  side can tell. §4.5's ignore-unknown-id rule only covers ids the new document
  has not reached yet.

  Choosing the §5.1 repeat handshake makes this more frequent, not less: a
  multi-page mini app swaps documents on every navigation. Accepted knowingly —
  both documents are the same mini app on the same origin, so this is wrong
  data within one principal rather than a breach of isolation, and the
  alternative (refusing repeat handshakes) breaks multi-page mini apps
  outright. Closing it properly needs a per-document epoch in the envelope,
  which is a wire change and wants its own ADR.
- **Peer-initiated disconnect.** `Transport` (§3.1) gives neither side a way to
  learn that the other is gone, so §4.6 covers only a client-initiated close.
  This matters only where the mini app's context outlives the bridge — a host
  that destroys the whole web view leaves nobody to reject. Where it does
  matter, §4.5 timeouts are the only backstop, and a suspended web view may
  not run them on schedule. `-32008` is the code a resolution should reuse.
  Adding `onClose` to the transport contract would widen the platform boundary
  and needs its own ADR, informed by more than one real transport.
- **Lifecycle state for imminent destruction.** `portal.lifecycle` (§6.4)
  defines only `resumed` and `paused`. Pool eviction (ADR 0002) needs a state
  meaning "persist now, destruction imminent" (cf. the Page Lifecycle API's
  `frozen`/`discarded`), giving the mini app a last chance to persist via
  `storage.*` before the host destroys its Portal.
