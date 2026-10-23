# 11. Define manifest entries as unencoded relative file paths

Date: 2026-10-23
Status: Accepted

## Context

SPEC §7 required relative entry paths contained by the package root but did
not define percent escapes, backslashes, URL suffixes, or directory targets.
Different URL and filesystem loaders could interpret the same accepted text
differently. The pure host kernel cannot use platform path or filesystem APIs.

## Decision

The maintainer approved the proposed path rules on 2026-10-23. Record them in
SPEC §7 before implementation: nonempty, unencoded file paths separated by
forward slashes. Reject leading slashes, backslashes, percent signs, colons,
query/fragment delimiters, control characters, and edge whitespace. The final
segment must name a file syntactically, rather than be empty, `.` or `..`.
Do not require an extension. Literal Unicode and interior spaces are allowed.

Walk segments from left to right, ignoring empty interior segments and `.`.
A `..` removes a preceding segment; reject it immediately at depth zero.
Thus `pages/../index.html` is valid but `../pages/index.html` is not. Validate
without rewriting the accepted entry. Do not decode or repair rejected input.

Expose `parseManifest` only after composing field, entry, and scope checks.
Derive recognized scopes from the protocol's capability method namespaces,
excluding the reserved `portal` namespace. Recognition is independent of
provider installation and grants; dispatch retains SPEC §9.3 enforcement.

## Consequences

- The kernel uses strings, regular expressions, and a depth counter, with no
  platform API or runtime dependency. The parser performs no file reads.
- Encoded filenames and URL suffixes require a future approved spec change.
  Authors write ordinary paths, including literal Unicode and spaces.
- The embedder must resolve relative to the package root and keep actual
  resolution contained, including symbolic links where applicable. Lexical
  validation does not establish existence or filesystem containment by itself.
- T06 completes the parser API; T07 integrates the browser example's actual
  manifest and loading path. No native loader is introduced in this task.
