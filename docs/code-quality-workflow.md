# Code quality and refactoring workflow

Use this at each task handoff. SPEC remains normative; accepted ADRs constrain
the refactor. Small, observable results are preferable to a repository-wide
rewrite. [Fowler's definition](https://refactoring.com/) distinguishes changing
internal structure from changing observable behavior.

## Before changing code

1. Read HANDOFF, SPEC and the relevant ADRs. Identify the current Interface:
   inputs, outputs, errors, timing, ordering, ownership and side effects.
2. Inspect real callers and existing tests. A long file or repeated `if` is
   evidence to investigate, not a reason to restructure automatically.
3. Run the existing tests. Add missing characterization tests before cleanup.
   If a bug is discovered, first reproduce it with a failing contract test.
4. State the concrete change and which behavior must stay identical. Separate
   a bug fix from behavior-preserving refactoring in the review/commit grouping.
   Policy or SPEC changes still require the existing approval process.

## Choosing the change

| Signal | Appropriate action | Check |
| --- | --- | --- |
| Actual callers repeat the same behavior and errors | Consolidate behind a small Module Interface | Removing the Module would put complexity back in those callers |
| Similar field names have different trust/ordering rules | Keep distinct implementations | Host-local notification validation and tolerant client reading differ under ADR 0020/0021 |
| One value selects among fixed alternatives | Consider `switch` or a small lookup table | Cases are explicit, terminate correctly and retain result validation |
| Several ordered validity/permission conditions | Keep guard clauses with early returns | Initialization, grants and params precedence remain per SPEC |
| Repeated async provider plumbing | Centralize await/reply/error reporting | Preserve method receivers, host-selected identity, public projections and one response |
| File/path checks rely only on text | Test actual filesystem resolution | Resolve symlinks and keep the resolved file inside the selected app root |
| Tests copy production branching or test private helpers | Move assertions to the caller's Interface | Verify actual replies, provider effects, headers, bytes and denied access |

A Module should improve Locality: the same rule should change in one place.
Two real Adapters justify a shared Seam; anticipated future platforms alone do
not. Avoid adding a registry, plugin system or public SDK export for internal
cleanup. Formatting and naming changes should not obscure the behavior diff.

## Verification commands

```sh
pnpm test                # TypeScript contract/integration tests
pnpm run test:probes     # Python loopback HTTP tests; no simulator needed
pnpm run typecheck       # pure kernel and browser targets
pnpm run lint            # Biome checks supported source/config formats
pnpm run build           # both browser example builds
pnpm run check           # all of the above, stopping on the first failure
```

The probe tests use Python's standard-library unittest with temporary roots and
free loopback ports. They require python3 (verified here with 3.13.3), add no
Python package dependency, install no app and boot no virtual device. Biome is
not a Python/native-code test runner. A Python server passing these tests does
not establish Android/iOS WebView behavior.

When a native task is active and its code changes, also run its appropriate
build/device checks, retain exact versions and refresh evidence for changed
artifacts. Respect pauses and simulator ownership. Do not silently rerun or
overwrite historical measurements: distinguish source/artifact equivalence
from a new native measurement.

## At handoff

- Review the final diff for unexpected files, public Interface or dependency
  changes. Confirm pure-package platform restrictions and instruction symlinks.
- Report what changed, why, which checks passed, and what remains unverified.
- Update HANDOFF and the Korean study guide, preserving earlier lessons.
- Record a non-obvious design decision in an ADR. Keep commits small and use
  Conventional Commits when the maintainer requests publication.

## 2026-10-27 cleanup checkpoint

Completed while T24 remains paused:

- Consolidated identical host/client/example test transports in test-support/.
- Centralized capability execution/reply/error plumbing inside Host while
  retaining projection and validation order at each dispatch call site.
- Made storage-demo SET/GET/DELETE alternatives explicit with switch.
- Added receiver/stateful-provider and inherited Array.prototype.toJSON cases.
- Shared the two loopback HTTP controls in experiments/probe_support, with
  per-platform Adapters outside the pure runtime packages.
- Added HTTP tests that first exposed four absolute-path/symlink escape cases
  in the unfinished iOS fixture. Fixed those reads using canonical app-root
  confinement. This is a bug fix concerning SPEC §7 / §9.6, not a new origin
  policy. All regression data is temporary/public test data.

The Android native source, APK/evidence fingerprints and the paused Swift probe
remain unchanged. The loopback server's existing control responses are exercised
through HTTP tests; no simulator was resumed for this checkpoint. The observed
Android custom-origin incompatibility and T28 approval gate remain in force.

References: [Python unittest discovery](https://docs.python.org/3/library/unittest.html#test-discovery),
[canonical path resolution](https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve).
