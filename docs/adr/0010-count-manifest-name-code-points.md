# 10. Count manifest names in Unicode code points

Date: 2026-10-23
Status: Accepted

## Context

SPEC §7 limited the display name to 1–40 characters without defining the
counting unit. JavaScript string length counts UTF-16 code units, so a
supplementary-plane character such as U+1F600 contributes two. A parser could
therefore reject a name containing 40 such characters while accepting 40
ordinary Latin characters.

## Decision

The maintainer approved counting Unicode code points on 2026-10-23. Update
SPEC §7 before implementation. U+1F600 counts as one; combining marks and
multi-code-point emoji components count separately. This is not a count of
user-perceived grapheme clusters.

Use JavaScript's string iterator to count code points. Enforce the existing
inclusive 1–40 limit without relying on UTF-16 string length.

## Consequences

- Names containing supplementary-plane characters have the same code-point
  limit as other names.
- The count does not require a platform API, Unicode segmentation library,
  or runtime dependency in the pure host package.
- Tests must cover 40 and 41 supplementary-plane characters, and combining
  sequences, rather than proving only ASCII boundaries.
