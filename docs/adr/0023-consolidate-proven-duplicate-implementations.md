# 23. Consolidate proven duplication without merging different contracts

Date: 2026-10-27
Status: Accepted — implementation refactoring requested by the maintainer

## Context

The maintainer requested cleanup before resuming T24. Host/client tests had
identical in-memory Transport Adapters; four capability helpers repeated the
same awaited response/error reporting; Android/iOS fixture servers repeated
public loopback controls. Similar notification field checks, however, enforce
different contracts under ADR 0020 and ADR 0021.

The unfinished iOS fixture also lacked automated HTTP/path tests. Regression
tests exposed absolute-path and symlink escapes outside the chosen app root.
This is an implementation defect under the existing confinement requirement,
not justification for changing SPEC or selecting a new production origin.

## Decision

Consolidate only behavior shared by actual callers. Put the test Transport in
test-support/ without an SDK export. Keep capability invocation/reply/error
handling inside Host; use closures to preserve provider receivers and keep
public result projection at dispatch. Do not move validation/grant gates.

Keep probe HTTP helpers in experiments/probe_support with separate platform
Adapters. Test their public HTTP Interface with temporary roots/free ports,
including canonical per-app file confinement, and include those tests in the
local check command. Do not import platform/Python helpers into runtime packages.
Leave strict host notification input and tolerant client reading distinct.

## Consequences

Shared rules gain Locality without a plugin registry or new public Interface.
Tests protect receiver state, asynchronous completion/privacy and conversion
avoidance. Ordered guards remain guards; the UI's fixed method alternatives use
switch. Native probe measurements stay distinct from host-only test results.

No protocol/security policy changes. The fixture bug fix concerns existing
SPEC §7 / §9.6 requirements. T24 stays paused and its native/device validation
remains outstanding. The [workflow](../code-quality-workflow.md) records the
repeatable test/refactor/review sequence.
