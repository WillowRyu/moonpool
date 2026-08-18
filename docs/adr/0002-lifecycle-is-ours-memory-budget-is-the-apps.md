# 2. Lifecycle is ours, memory budget is the app's

Date: 2026-08-18
Status: Accepted

## Context

Web views are expensive and fail in well-known ways: renderer processes are
killed under memory pressure, leaving blank views behind; on Android, mishandling
`onRenderProcessGone` takes the host app down with the renderer; undestroyed
`WebView` instances are a classic leak category that can retain an entire
Activity. At the same time, the total memory cost of running mini apps is
dominated by things Moonpool does not control: the engine's per-process
baseline, and the DOM, images, and framework weight of the mini app content
itself.

This creates a temptation to drift in one of two bad directions. One is to do
nothing — ship a thin wrapper around the platform web view and leave crash
recovery, destruction order, and eviction to each integrating app. The other is
to do everything — grow into an app-wide memory manager with budgets and
dashboards. The first makes the project pointless (a bare web view plus a
documentation page); the second makes promises the library cannot keep, because
only the app knows how to trade its native screens, image caches, and Portals
against each other.

There is also a structural reason the integrating app _cannot_ own web view
lifecycle even if it wanted to: Moonpool owns the web view object, so the OS
delivers termination callbacks to Moonpool; and "you are about to be destroyed,
persist your state" is a protocol message (`portal.lifecycle`) that only the
host runtime can send.

## Decision

Moonpool follows a **mechanism, not policy** split.

**Moonpool always does (per Portal, non-negotiable, part of the contract):**

- Detect renderer/process termination (`webViewWebContentProcessDidTerminate`,
  `onRenderProcessGone`) and recover or surface a callback. On Android, handle
  `onRenderProcessGone` correctly so a renderer crash never kills the host.
- Perform correct teardown on destruction: `destroy()` on Android, listener and
  scheme-handler deregistration, removal from the view tree. Integrators must
  not be able to encounter the web view leak category at all.
- Deliver lifecycle transitions to the mini app over the bridge (`paused`
  before eviction, giving it the chance to persist via `storage.*`).
- Clean up the bridge on teardown: reject pending promises, cancel timers,
  close the transport.

**Moonpool provides with defaults, overridable (per pool, policy hooks):**

- Concurrent-active cap with LRU eviction.
- Prewarming.
- Shrinking the pool on OS memory-pressure signals
  (memory warnings / `onTrimMemory`).

Safe defaults ship out of the box; integrators who know their app's memory
situation tune them:

```ts
createPortalPool({
  maxActive: 2,
  prewarm: 1,
  onEvict: (portal) => {
    /* app-specific policy */
  },
});
```

**Moonpool never does (the app's domain):**

- App-wide memory budgeting or allocation across native screens, caches, and
  Portals.
- Memory dashboards, profiling UIs, or telemetry about the rest of the app.
- Compensating for heavy mini app content. A mini app that overspends is
  evicted first; that is the whole enforcement mechanism. Guidance belongs in
  a performance doc for mini app authors, not in runtime machinery.

## Consequences

- The value proposition is explicit: Moonpool's job is the messy distance
  between a bare platform web view and a production-safe one — and stops there.
- Feature requests can be triaged against one question: _is this about the
  lifecycle of objects Moonpool owns, or about the app's resources?_ The first
  is in scope, the second is not.
- Moonpool has almost no lever over what a single web view consumes; its real
  mitigation lever is deciding _how many web views are alive, and when_. Pool
  policy therefore is the memory story, and should be documented as such
  rather than alongside vague "low memory footprint" claims.
- `portal.lifecycle` needs a state meaning "persist now, destruction imminent"
  beyond `resumed`/`paused` (cf. the Page Lifecycle API's `frozen`/
  `discarded`). Already tracked as an open question in `SPEC.md` §11.
- All of this lands with the native cores (phase 3). Nothing in the v0 browser
  kernel changes; this ADR exists so the boundary is settled before the code
  that needs it.
