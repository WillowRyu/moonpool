# 1. JSON-RPC 2.0 as the bridge protocol

Date: 2026-08-18
Status: Accepted

## Context

The bridge needs a message format. Every hand-rolled web view bridge eventually
reinvents the same four things: correlating requests with responses, a
convention for errors, a way to send events that expect no reply, and timeout
handling. Getting these wrong is cheap to do and expensive to change, because
the format becomes a public contract with every mini app the moment one ships.

## Decision

Use JSON-RPC 2.0 unmodified, with a small profile restriction (no batching, and
integer ids only) documented in `SPEC.md` §4.

Moonpool-specific error codes live in the implementation-defined range
`-32000` to `-32099`.

## Consequences

- The four problems above are solved by the specification rather than by us.
- Mini app authors can use off-the-shelf JSON-RPC clients, and the contract can
  be explained in one sentence.
- The format is already the substrate for LSP and MCP, so it is familiar to a
  large share of the people who might integrate or contribute.
- JSON-RPC has no concept of authentication, permissions, or streaming. All
  three must be layered on top; permissions are specified in `SPEC.md` §6 and
  §9, streaming remains an open question.
- JSON encoding costs more than a binary format. This is accepted: bridge calls
  are not on a render path, and `SPEC.md` §9 already forbids the patterns where
  the cost would matter.
