# Android C09 worker-prevention probe

This probe compares a CSP-guarded entry and same-origin frame with the same
loader serving an unguarded control. It uses synthetic HTTPS origins, named
profiles and local resource interception. A profile with the matching native
record can reopen through the guarded loader when the existing cookie gate
passes. The negative cases have seeded workers, no record, or a frame
enforcement event withheld during provisioning. Each cold check uses a
separate process and preserves the IndexedDB marker.
[Fixture decision](../../../docs/adr/0030-measure-worker-prevention-on-owned-android-profiles.md)

From this directory, run the host tests and build the APK.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect only on the explicitly owned, booted Android emulator. Supply its
owner record and a new tag. The collector checks the AVD name before install
and verifies the installed APK hash. It validates the seed observations
before starting cold checks. It stops the probe app between phases and
preserves the profiles.

```sh
python3 -u -B run_probe.py run --run csp-recheck --owner /path/to/android-owner.json
```

Verify the retained reports without a device.

```sh
python3 -B check.py results/android-worker-prevention-review.json
python3 -B check.py results/android-worker-prevention-review-repeat.json
```

The verifier checks actual enforcement events and native script requests in
addition to registration outcomes. Both reports cover a single WebView
configuration.

## Verify the initial reports

The [initial source archive](results/android-worker-prevention-initial-sources.zip)
contains every fingerprinted file, including the original verifier. From
this directory, extract it to a temporary directory and run that verifier
in isolated Python mode so environment settings cannot disable its checks.

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e results/android-worker-prevention-initial-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/worker-prevention/check.py"
python3 -IB "$checker" results/android-worker-prevention.json
python3 -IB "$checker" results/android-worker-prevention-repeat.json
```

[Verification and limits](../../../docs/native-worker-prevention-verification.md)
