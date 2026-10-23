# 9. Recreate demo Portals when host grants change

Date: 2026-10-23
Status: Accepted

## Context

T04 needs a default profile-only configuration that demonstrates -32000 and
a storage-enabled configuration that demonstrates successful storage calls.
The kernel computes grantedScopes for one connection at connect time. Runtime
consent and changes to a live connection's grants are unspecified (§11).

The example must also keep the T03 storage provider alive across document
replacement. Resetting its Map whenever a configuration is selected would
conflate connection lifetime with host-held application data.

## Decision

Offer two fixed choices in the host page. On every choice, close the previous
iframe transport, replace its iframe with a newly created element, and attach
a new host connection using the selected grants. Keep the existing pinned
origins and host-selected manifest identity. Mini-app params and URLs do not
select grants. Attach the new receiver synchronously with frame creation so
the first handshake cannot precede listener setup (§5).

Create one memory storage provider outside the connection-creation function.
Reuse it for the host page's lifetime, while retaining its per-app partition.
The initial configuration grants only profile.

The mini-app demo enables actions after initialization even when storage was
not granted, explicitly to demonstrate host enforcement (§9.3). Display the
reported grant and error code. Serialize demo actions in the UI, validate the
storage.get value before rendering, and render returned strings as text.

## Consequences

- Each configuration has a fresh document and request sequence. The previous
  frame and its inbound listener are removed; grants are never mutated on a
  live connection. A new frame also has a different source window for binding.
- Storage survives these choices within the same host page. Reloading the
  host creates a fresh provider and clears the development-only memory state.
- No runtime consent, new wire message, or Transport extension is introduced.
  Destroying the old document does not require peer-disconnect signaling.
- This does not implement general off-origin navigation containment (§9.2),
  nor resolve the §11 response-epoch race during same-iframe document swaps.
- Tests cover both grant directions, old transport closure, frame replacement,
  retained values, successful CRUD, and denial despite an installed provider.
