# T28 C09/C10 cookie-suppression feasibility probe

Explicitly authorized on 2026-11-03 for new cookie checks only. This is an
isolated experiment, not a native SDK, HTTP broker, migration or SPEC amendment.
It contains no intentional crash or website-store enumeration path. Historical
T23–T28 sources/results remain unchanged.

Read the [verification report](../../docs/native-cookie-suppression-verification.md)
and [pre-execution criteria](../../docs/native-cookie-http-conformance-plan.md).
The strict proposed contract remains RED on iOS with pre-existing HTTPS cookies.
Evidence validity and product conformance are separate outputs.

## Fixture

Five simultaneous views represent A1/A2 (one app), B, H (the default store of this
new probe app, containing only public controls) and U (another isolated control).
All visit the same controlled HTTPS service; local Android pages use stable
SHA-256/base32 `.invalid` origins and iOS pages use `moonpool` origins. The local
loaders resolve only test fixture pages/frames and do not implement production
containment. HTTPS navigation and fetch are deliberate diagnostic paths.

Each run has 50 samples: five stages × five views × HTTPS/local contexts.
Stages are baseline, A blocked, A/B blocked, view/store-handle recreation, and
fresh A/B partitions blocked before their first load. The last stage is a
separate empty-store control; it never erases or migrates the seeded partitions.
H and U keep their original partitions throughout.

`page.html` checks ordinary document.cookie, its prototype descriptor and a
fresh same-origin iframe. The HTTPS server sends independent Set-Cookie fields
on the page/frame/resource paths, then records Cookie receipt on `/observe`.
It never echoes Cookie values into the response. Each run retains 100 raw HTTPS
requests. All values are public `t28_` markers, never real user/host credentials.

The server binds only to loopback. A short-lived local CA/localhost certificate
is generated in ignored local-results. Android trusts it only for localhost in
this test APK's network-security configuration. The dedicated iOS simulator
trusts the CA via its own keychain. Host-machine trust, unrelated simulators and
certificate/hostname validation are unchanged. SSL errors are not bypassed.
Private keys, machine/device ownership, logs and preliminary reports stay ignored.

## Build and retained verification

From the workspace root, using the installed Node 22.19.0 / pnpm 11.1.3 and
native toolchains:

```sh
python3 -B -m unittest discover -s experiments/native-cookie-suppression-probe -p 'test_*.py'
python3 -B experiments/native-cookie-suppression-probe/build.py android
python3 -B experiments/native-cookie-suppression-probe/build.py ios
python3 -B experiments/native-cookie-suppression-probe/verify.py --evidence experiments/native-cookie-suppression-probe/results/*-confirmed-*.json
pnpm run check
```

`--evidence` verifies source/artifact correspondence, native partition bindings,
policy-before-load order and raw observations, then explicitly prints contract
PASS or FAIL. Without this flag the verifier exits nonzero for the iOS contract
violations; keep that failure rather than changing the expected behavior.
Artifacts are fingerprinted when present; retained source hashes can be checked
without a device. Rebuilding changes artifact fingerprints, so preserve old build
outputs/evidence or recollect against the new installed artifact.

The initial tests failed because the fixture/verifier did not exist. Negative
tests reject missing controls, outgoing cookies hidden by empty JS reads, hidden
native writes, missing frames and incorrect native bindings. Two collection bugs
were separately pinned before fixing: partial report writes and a stale server
case list. Incomplete runs are local diagnostics, not retained final measurements.

## Explicit device execution only

Do not run native collection as a routine repository check. Inspect all existing
device states first. This session created a new dedicated iPhone 17 Pro simulator
and an AVD from the installed API 37 ARM64 16 KB Google APIs image; no image/SDK
download, user-device reset or change to a user's existing AVD is required.

Ignored local-results contains `ios-owner.json` (owned id/name, protected ids and
boot ownership), `android-owner.json` (owned AVD/serial/port/pid), baseline states,
build metadata and fixture CA material. Runners check the explicit device identity
and installed artifact hash; never select an implicit `booted` device. iOS creates
an empty, never-loaded initializer WebView before identified stores and never
enumerates stores. An unexpected process exit stops collection without retry.

Start the loopback fixture with `python3 -u -B fixture.py` from this directory.
After explicitly booting only the owned devices, install its CA with
`simctl keychain <owned-id> add-root-cert <owned-ca.pem>` only on the dedicated
simulator. Android's runner creates an adb reverse mapping on its owned emulator.
The server's case-list fingerprint must match the current corpus before launch.
After build/install, the session's final runs used these commands from this directory:

```sh
python3 -u -B run_probe.py android --run confirmed-first --install
python3 -u -B run_probe.py ios --run confirmed-first --install
python3 -u -B run_probe.py android --run confirmed-repeat
python3 -u -B run_probe.py ios --run confirmed-repeat
```

Use new run tags for future collection so old server receipt rows cannot mix with
new evidence. The runner terminates only its own probe app between runs, retaining
app data. Each run creates new A/B/U partition registrations; recreation uses the
same identifiers within that run. This is not host-process durability evidence.
Finish by terminating probe apps, removing the owned reverse mapping, stopping
the owned simulator/emulator and closing the fixture. Preserve unrelated devices,
services, raw diagnostics and the newly created device configurations.
