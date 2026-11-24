# 30. Measure worker prevention on owned Android profiles

2026-11-24. Applied to the isolated C09 worker-prevention probe.

## Context

On the tested Android WebView, the host-supplied pre-admission document could
read its assigned origin while worker inventory failed. Ordinary navigation
could load a cached document from an existing worker before the native loader
served any document. The admission baseline preserves the profile and refuses
guest execution if it cannot establish the required evidence.
[Worker inventory evidence](../native-worker-admission-verification.md),
[Store admission baseline](../native-cookie-store-admission.md)

## Decision

Use the same native HTTPS fixture loader for both groups. Set an enforcing
`worker-src 'none'` response header on the entry and same-origin frame in the
guarded group. Allow two registrations in the control and require the guarded
documents to report CSP violations, no worker script requests and no
registrations. This distinguishes CSP enforcement from generic failures to
register in the fixture.

Create the guarded profile under exclusive fixture ownership. After checking
the first guarded responses, the top-level document's empty registration
list and each document's enforcing CSP event for its worker script, write a
native record bound to the profile, exact origin, policy, Android API and
WebView version. The record format identifies the evidence rule used at
provisioning. Validate the seed observations before any cold check and
require the current record format alongside fresh cookie evidence at cold
admission. Inspect stored markers using host HTML after refusal.

## Consequences

The proof is limited to the fixture's loaded documents and measured
configuration. The CSP directive also restricts dedicated and shared workers.
A native record has evidentiary value only while the SDK controls the same
profile from creation and applies the approved policy to every guest document.
The probe concerns SPEC §8 and §9. Production ownership, coverage of other
document types, eligibility for arbitrary existing profiles, and final
contract approval stay open.
[CSP worker directive](https://www.w3.org/TR/CSP3/#directive-worker-src)
