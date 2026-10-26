# Moonpool

Run sandboxed web mini apps inside a native app, behind a permissioned bridge.

> ⚠️ **Early development.** The protocol is unstable and nothing here is ready
> for production use. There is no install path yet — see the roadmap below.

---

## What it is

A moonpool is the opening in the hull of a drilling vessel: a controlled way to
reach the water without letting the sea into the ship. This project is the same
idea for applications — a bounded opening in a native app through which web
content runs, with an explicit contract governing what it can reach.

Concretely, that's a web view plus a bridge:

- Each mini app runs in its own web view, on its own origin. Isolation is
  enforced by the browser engine, not by convention.
- The host exposes a declared set of capabilities. A mini app calls them over
  [JSON-RPC 2.0](https://www.jsonrpc.org/specification), and every call is
  checked against the permissions in its manifest.
- Mini apps are plain web apps. No specific framework, no version lockstep with
  the host.

```js
const profile = await portal.call("profile.get");
```

## Why

[Ionic Portals](https://ionic.io/blog/important-announcement-the-future-of-ionics-commercial-products)
solved this well and was discontinued as a commercial product in 2025. It was
never open source, so there is no continuation path. Meanwhile the alternatives
in the React Native ecosystem — Module Federation and friends — share a single
JavaScript runtime by design, which makes them a good fit for splitting up
first-party code and a poor fit for running code you do not control.

The gap is a small, open, framework-agnostic runtime for the second case.

## Design

The protocol is specified in [`SPEC.md`](./SPEC.md) and comes before the
implementation. All protocol logic lives in a platform-independent kernel;
each platform contributes only a transport adapter implementing a two-method
interface. Adding React Native, iOS, or Android should mean writing a transport,
not reimplementing the protocol.

## Run the browser development example

From the workspace root, using the repository's Node/pnpm environment:

```bash
pnpm install
pnpm run dev
```

Open [http://localhost:5173](http://localhost:5173). The command starts the host and two fixed mini-app
origins on ports 5174 and 5175; occupied ports fail instead of drifting. Use
the host buttons to select storage grants and open the second app concurrently.
Each Portal has a trusted served wrapper with its own enforcing CSP. Host memory
storage survives Portal recreation and is partitioned by the host-selected app id;
reloading the outer host clears it.

The separate [containment checks](http://localhost:5173/containment-check.html)
exercise navigation, independent revocation and storage/realm ownership using
the actual adapters. See [T18 verification](docs/browser-containment-verification.md)
for recorded results and limits. CSP response headers are part of this setup;
opening built HTML directly or serving it without those headers is not equivalent.
This remains browser development, not a production web-hosting contract.

## Roadmap

**v0.1 — protocol, in the browser**

- [ ] Transport interface + iframe transport
- [ ] Client: encoding, promise correlation, timeouts
- [ ] Host: dispatcher, manifest parsing, scope enforcement
- [ ] Handshake with version negotiation
- [ ] `portal.*`, `profile.get`, `storage.*`
- [ ] Runnable mock host and example mini app

**Later** — React Native transport · iOS (`WKWebView`) and Android
(`WebMessagePort`) cores · web view pooling and prewarming · bundle loading via
custom scheme handlers

Distribution, signing, and live updates are explicitly out of scope for now.

## Contributing

Too early for code contributions, but feedback on [`SPEC.md`](./SPEC.md) is
genuinely useful — particularly on the open questions in §11. Open an issue.

## License

MIT
