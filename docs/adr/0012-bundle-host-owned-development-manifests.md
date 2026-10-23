# 12. Bundle the development manifest as host-owned text

Date: 2026-10-23
Status: Accepted

## Context

T07 must replace the mock host's duplicated typed manifest literal with the
hello mini app's actual moonpool.json. A browser cannot read package files
directly, and a Portal must not supply its own identity or permission grants
over the bridge. SPEC §7 validation must finish before a Portal is created.

## Decision

Use Vite's existing `?raw` import to include moonpool.json as text in the
mock host's module. Call the pure host package's parseManifest at startup,
before rendering or creating an iframe. Let validation failures stop startup
as local configuration errors. No runtime configuration editor is introduced.

Select the mini app's development origin from a host-owned Map using the
validated id. An id without a pinned mapping stops startup. Resolve the
validated entry against that origin's root with the browser's URL API, then
use that URL for the iframe and the unchanged origin for transport binding.
This loader interpretation follows the approved path contract in ADR 0011.

Keep iframe insertion and receiver attachment synchronous in the same task.
The manifest declares permissions; the host buttons still select grants,
and the kernel still enforces their intersection at dispatch (SPEC §9.3).

## Consequences

- There is one manifest source of truth in the example. Importing text lets
  parseManifest diagnose malformed JSON rather than trusting a typed literal.
- File inclusion and URL resolution stay in the browser example/tooling;
  no platform API or dependency enters protocol, client, or host.
- Tests vary imported text while retaining the real parser and dispatcher.
  Actual browser checks separately verify the two pinned development origins.
- The dev server serves the mini app's files. This is not a native filesystem
  loader or a claim that URL resolution inspects files, symlinks, or redirects.
  General navigation containment remains T17–T18; production loader duties
  remain those in SPEC §7–§9. No distribution or live-update feature is added.
