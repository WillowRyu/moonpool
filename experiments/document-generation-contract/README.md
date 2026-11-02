# Document-generation contract preparation

[ADR 0024](../../docs/adr/0024-bind-rpc-work-to-document-generations.md) records
the maintainer's selected direction. This isolated probe uses
the real existing Host/Client and the shared in-memory Transport to expose the
known SPEC §11 / protocol 0.1 limitation before T30's versioned wire contract and
T32 implementation. It does not implement a second dispatcher or pick epoch
fields, generation creation, error mappings or protocol versions.

Each document has a fresh terminal client-side transport facade over one open
physical connection. Closing that facade settles its local pending calls but
does not stop the host's already-started provider. Old replies can be delivered
to the new facade, modeling the generic current-document delivery measured in
T26 without a simulator or platform API.

```sh
pnpm exec vitest run --config experiments/document-generation-contract/vitest.config.ts
pnpm exec tsc --noEmit -p experiments/document-generation-contract/tsconfig.json
pnpm run check
```

Expected before implementation: the isolated Vitest command exits nonzero with
two controls passing and three generation-safety assertions failing. Two failures
must show old draft instead of new draft; the bootstrap failure must show the
old document locale instead of the new one. Another error is not accepted evidence.
The controls prove unknown-id handling, retained grants and completion of an
already-dispatched write. Failures cover initialization id 1, A→B and A→B→fresh A
with reused request id 2.

The ordinary root suite deliberately keeps its existing include pattern and
must continue to pass. Do not hide these failures with skips/expected-failure
flags or claim they prove generation support. Once the approved wire contract
is implemented, migrate the safety assertions into the ordinary contract suite
and require them to pass. The test facade is not a new production transport or
evidence of native sender authentication.
