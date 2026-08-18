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

`error.data` SHOULD carry structured context and MUST NOT contain host
credentials, tokens, or data belonging to another mini app.

### 4.5 Timeouts

Clients MUST apply a timeout to every request. Default: 30 000 ms.
On expiry the client MUST reject with `-32003` and discard the pending entry.
A late response for a discarded id MUST be ignored.

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
  with `-32004` and MUST NOT service further calls.
- `grantedScopes` is the authoritative permission set for the connection. It is
  the intersection of the manifest's declared permissions and what the host
  actually granted. Clients SHOULD use it to hide unavailable features.
- `platform` is one of `browser`, `ios`, `android`.

Version negotiation is exact-match in `0.x`. Semantic compatibility rules will
be defined at `1.0`.

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
- **Rate limiting.** `-32006` is reserved but no policy is defined.
