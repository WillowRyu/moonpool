# T28 C09 browser paths probe

The probe exercises the accepted cookie-presence gate and a candidate
WebView policy in owned test apps. Android uses the proposed intercepted
HTTPS origin and iOS uses a local `moonpool://` handler. Each run names a
fixture app and keeps its origin and store across reload and recreation.
The native apps compile the existing admission gate sources.
[Admission baseline](../../docs/native-cookie-store-admission.md)

An HTTPS fixture independently witnesses requests from guest paths and
the three isolated control stores. The probe records actual cookie
getters, policy and presence order, guest loader entries, storage markers
and native popup denials. The `unknown` sample injects an unknown verdict
after policy installation.

## Build and collect

From this directory, use the workspace's installed native toolchains.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B runner.py build android
python3 -B runner.py build ios
python3 -u -B server.py
```

Use the server while collecting in a second terminal. Boot the dedicated
Android emulator first, run the Android collection with its explicit owner
record, and shut it down. Then boot and collect from the owned iOS simulator.

```sh
python3 -B runner.py run android --run repeat --owner /path/to/android-owner.json
python3 -B runner.py run ios --run repeat --owner /path/to/ios-owner.json
```

The Android APK and the iOS navigation delegate validate HTTPS using the
generated localhost CA. Each report binds the verified installed artifact to
the source fingerprints. A process exit ends collection for that platform.
The apps, temporary server and Android reverse mapping use the owned fixture.

## Verify a retained pair

```sh
python3 -B verify.py results/android-c09-paired.json results/ios-c09-paired.json
```

The verifier returns failure for any denied request recorded at the server,
even when the browser reports an error. The results are observations of
these probe configurations.
[Verification report](../../docs/native-cookie-paths-verification.md)

The follow-up measures native redirect checking and a retained worker
while keeping this baseline pair reproducible.
[Follow-up probe](follow-up/README.md)

The Android pre-admission probe compares host-injected and scripts-disabled
contexts after a cold app restart.
[Worker-admission probe](worker-admission/README.md)

The Android worker-prevention probe tests an enforcing CSP from first use
and reopens the same owned profile across app processes.
[Worker-prevention probe](worker-prevention/README.md)

The inherited document probe compares worker behavior in the entry,
an initial about:blank iframe and a srcdoc iframe.
[Inherited document probe](worker-contexts/README.md)

The profile ownership probe compares two native lookups of the same
Android profile with a distinct profile control.
[Profile ownership probe](profile-ownership/README.md)

The C10 retirement probe checks actual WebView cleanup and separate
profile continuity after a shared profile refuses admission.
[Android profile retirement probe](profile-retirement/README.md),
[iOS store retirement probe](profile-retirement-ios/README.md)

The writer-order probes check both orderings of the fixture's coordinated
native writer and admission.
[Android writer-order probe](admission-writer-order/README.md),
[iOS writer-order probe](admission-writer-order-ios/README.md)
