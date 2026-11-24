# iOS admission and native writer order probe

The fixture runs admission and its test cookie writer through a single
native owner queue per identified `WKWebsiteDataStore`. It uses the
existing Swift gate and two-source cookie classifier. Each store receives
cookie deny before its cookie sources are read. WebKit starts with the
established never-loaded, nonpersistent initializer view.

Run the host tests and assemble the simulator app from this directory.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect on the owned, booted simulator with a new tag. The collector
checks the simulator identity and installed bundle hash and stops its app.

```sh
python3 -B run_probe.py run --run writer-order-recheck --owner /path/to/ios-owner.json
```

## Verify the reviewed reports

```sh
python3 -B check.py results/ios-admission-writer-order-review.json
python3 -B check.py results/ios-admission-writer-order-review-repeat.json
```

The verifier requires the native writer callback and completed readback
before the admission inspector enters.

## Replay the original reports

The [original source archive](results/ios-admission-writer-order-original-sources.zip)
contains the verifier and all source fingerprints from the initial
measurements. Replay those reports with that version.

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e results/ios-admission-writer-order-original-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/admission-writer-order-ios/check.py"
python3 -IB "$checker" results/ios-admission-writer-order.json
python3 -IB "$checker" results/ios-admission-writer-order-repeat.json
```

[Verification and scope](../../../docs/ios-admission-writer-order-verification.md)
