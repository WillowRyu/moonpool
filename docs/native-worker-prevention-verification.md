# T28 C09 Android worker prevention on owned profiles

2026-11-24. Two collections used Android 17 (API 37), WebView
145.0.7632.218 and AndroidX WebKit 1.14.0 on the dedicated emulator.
The collected APK matched the built artifact in both runs. This probe
concerns SPEC §8 and §9.
[Probe layout and commands](../experiments/native-cookie-paths-probe/worker-prevention/README.md),
[Fixture decision](adr/0030-measure-worker-prevention-on-owned-android-profiles.md)

## First load and registration controls

The same native loader serves the entry and same-origin frame responses for
each synthetic HTTPS origin. Both responses in the guarded profile include
the `Content-Security-Policy` header `worker-src 'none'`. The control uses the
same document and worker scripts without that header. Each group attempts a
root registration in the main document and a separate subpath registration
in the frame.

| Fixture | Observation across two runs |
| --- | --- |
| Control | Four registrations activated. Both scripts reached the native loader in each run. |
| Guarded, first load and cold reopen | All eight attempts returned `SecurityError` with an enforcing `worker-src` event naming the corresponding worker script. No worker script reached the native loader. The guarded top-level document reported an empty registration list and no controller on each load. |

## Cold admission and stored data

Each collection stopped the app after seeding and restarted it for each of
the three cases. The admission check reopened the original profile, installed
cookie deny and found no engine cookies. The probe's native record binds the
guarded profile to its origin, CSP, Android API and WebView version. The loaded
fixture's worker inventory is a measurement. Cold admission uses the matching
native record and fresh cookie evidence.

| Original profile | Native result in each cold process | Guest loads per run | IndexedDB marker |
| --- | --- | --- | --- |
| Guarded from creation | Empty with a matching record, reopened through the guarded loader | 1 | Preserved and read by the fixture guest |
| Control with seeded root and subpath registrations | Unknown eligibility, refused | 0 | Preserved and read by host HTML |
| Profile without a record | Unknown eligibility, refused | 0 | Preserved and read by host HTML |

The repository-contained source archive replays both initial reports.
Both pass, with six cold admissions checked and zero evidence failures.
Android assemble and lint and the two initial host tests passed. The probe
app and dedicated emulator stopped after collection.
[First report](../experiments/native-cookie-paths-probe/worker-prevention/results/android-worker-prevention.json),
[Repeat report](../experiments/native-cookie-paths-probe/worker-prevention/results/android-worker-prevention-repeat.json),
[Initial replay instructions](../experiments/native-cookie-paths-probe/worker-prevention/README.md#verify-the-initial-reports)

## Review follow-up

The probe now requires enforcing `worker-src` events matching the origin and
worker URL in both documents before writing the native record. Cold admission
requires the new record format. The collector validates seed observations
before it starts cold checks. AVD identity, artifact hashes and process
checks remain active in Python optimization mode.

The regression fixture withholds the frame's recorded event before the native
decision. The pre-fix probe wrote a record, and seed validation stopped the
run before cold checks. After the fix, the profile received no record and its
cold check refused guest execution while preserving the IndexedDB marker.
That outcome repeated in both collections with the revised APK. A separate
check of the unversioned record from the pre-fix fixture also refused guest
execution and preserved the record and marker.

The revised APK passed all eight cold checks across two collections, with
two managed guest loads and six refusals. All eight markers survived. Both
collections used the same Android and WebView configuration as the initial
measurements. Tests with simulated device responses confirmed that a wrong
AVD halts before install and that source and APK mismatches fail verification
with Python optimization enabled.
[Reviewed APK report](../experiments/native-cookie-paths-probe/worker-prevention/results/android-worker-prevention-review.json),
[Reviewed APK repeat](../experiments/native-cookie-paths-probe/worker-prevention/results/android-worker-prevention-review-repeat.json)

## Remaining evidence

The observed guard applies to the two ordinary document paths on this WebView
version. Before approving an ownership rule for a production profile, verify
coverage for every executable document the production loader would allow,
including inherited document contexts, and verify exclusive profile ownership.
The probe's native record covers profiles the fixture created and controlled.
Eligibility for arbitrary existing profiles remains open. C09 and the final
T28 contract remain in review. Production loaders are tracked in T38/T39.
[Earlier inventory attempt](native-worker-admission-verification.md),
[C09 conformance matrix](native-cookie-http-conformance-plan.md#c09--browser-paths),
[Inherited document follow-up](native-worker-contexts-verification.md)
