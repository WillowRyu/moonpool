# Android admission and native writer order probe

The fixture puts admission and its test-owned cookie writer on the same
native owner queue for each named Android WebView profile. The admission-first
trial holds admission after a real empty result, queues a write, and observes
the first guest script before releasing the queue. The writer-first trial
queues admission during the real cookie write and waits for its callback
before inspecting the store.

Run the host tests and build the APK from this directory.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect on the explicitly owned, booted emulator with a fresh tag. The
collector checks the AVD name and installed APK hash and stops its app
after collection.

```sh
python3 -B run_probe.py run --run writer-order-recheck --owner /path/to/android-owner.json
```

## Verify the reviewed reports

```sh
python3 -B check.py results/android-admission-writer-order-review.json
python3 -B check.py results/android-admission-writer-order-review-repeat.json
```

The verifier checks callback arrival, completed cookie readback and
inspection entry as separate events. It also requires the exact marker
again after the writer-first admission is refused.

## Replay the original reports

The [original source archive](results/android-admission-writer-order-original-sources.zip)
contains the verifier and all source fingerprints from the initial
measurements. Replay those reports with that version.

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e results/android-admission-writer-order-original-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/admission-writer-order/check.py"
python3 -IB "$checker" results/android-admission-writer-order.json
python3 -IB "$checker" results/android-admission-writer-order-repeat.json
```

[Verification and scope](../../../docs/android-admission-writer-order-verification.md)
