# Android C09 local document frames

The probe compares a regular same-origin iframe and two locally generated
documents using `blob:` and `data:`. For each mode the native loader
uses its own fresh AndroidX profile and synthetic HTTPS origin. The
guarded loader serves `worker-src 'none'` and selects either `'self'` or
the literal synthetic HTTPS origin as its `frame-src` source.
Each frame runs in a separate parent document and WebView. The child
reports its first script execution immediately and sends any worker
result separately. The parent records DOM `MessageEvent.origin` and
retains frame and worker policy events during the observation window.

The inherited document set uses an initial `about:blank` iframe and a
`srcdoc` iframe. Both report their document URL, origin and worker
evidence. The probes also record secure-context state and the presence
of the service-worker registration method.

Run the host tests and build the app from this directory.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
node --test test_probe.mjs
python3 -B run_probe.py build
```

Use a fresh tag and the explicitly owned Android emulator record.
The runner checks the AVD name and installed APK hash and stops its app.

```sh
python3 -B run_probe.py run --run inherited-a --owner /path/to/android-owner.json \
  --frame-source origin --document-set inherited
python3 -B run_probe.py run --run inherited-b --owner /path/to/android-owner.json \
  --frame-source origin --document-set inherited
```

## Verify the inherited frame reports

Use both reports and the archive of the inputs to their native build.
The verifier requires distinct run tags and four profile names, a valid
matching APK digest, and matching SDK, OS and WebView versions. It also
checks the same frame source and document set in both runs.
[Inherited frame source archive](results/local-document-frames-inherited-sources.zip)

```sh
archive=results/local-document-frames-inherited-sources.zip
python3 -B check.py results/android-inherited-document-frames.json \
  --repeat results/android-inherited-document-frames-repeat.json --source-archive "$archive" \
  --expect-frame-source origin --expect-document-set inherited --expect-retained-outcomes
```

Each control frame must return a worker marker and have one native worker
script receipt. Each guarded child must start and report a worker
rejection and an enforcing worker event. The `trusted` field must be the
JSON boolean `true`. Retained verification requires a secure context and
an available service-worker registration method in both child types.
[Paired inherited frame evidence](../../../docs/native-inherited-frames-verification.md)

## Verify a later navigation to about:blank

The `navigation` set loads a same-origin marker document first and then
navigates that iframe to `about:blank`. It checks a distinct replacement
document before starting the worker probe. Navigation and worker
observation each have their own 6.5-second window. The control verifier
requires the worker receipt to follow the previous document receipt.
Use fresh tags to collect both runs.

```sh
python3 -B run_probe.py run --run blank-final-a --owner /path/to/android-owner.json \
  --frame-source origin --document-set navigation
python3 -B run_probe.py run --run blank-final-b --owner /path/to/android-owner.json \
  --frame-source origin --document-set navigation
python3 -B check.py results/android-blank-navigation-review.json \
  --repeat results/android-blank-navigation-review-repeat.json \
  --expect-frame-source origin --expect-document-set navigation --expect-retained-outcomes
```

[Paired navigation evidence](../../../docs/native-inherited-frames-verification.md#later-navigation-to-aboutblank)

## Replay the earlier navigation reports

The source archive preserves the original build inputs. The current
verifier checks those reports with the same receipt ordering rule.
[Navigation source archive](results/local-document-frames-blank-navigation-sources.zip)

```sh
archive=results/local-document-frames-blank-navigation-sources.zip
python3 -B check.py results/android-blank-navigation.json \
  --repeat results/android-blank-navigation-repeat.json --source-archive "$archive" \
  --expect-frame-source origin --expect-document-set navigation --expect-retained-outcomes
```

## Replay the explicit origin reports

The default local document set covers ordinary, blob and data frames.
Replay its explicit-origin reports with the corresponding source archive.
[Explicit origin source archive](results/local-document-frames-explicit-origin-sources.zip)

```sh
archive=results/local-document-frames-explicit-origin-sources.zip
python3 -B check.py results/android-local-document-frames-explicit-origin.json \
  --repeat results/android-local-document-frames-explicit-origin-repeat.json \
  --source-archive "$archive" --expect-frame-source origin --expect-retained-outcomes
```

## Replay the worker event reports

Verify the earlier `'self'` runs with the current boolean trust checks
and their archived build inputs.
[Worker event source archive](results/local-document-frames-worker-events-sources.zip)

```sh
archive=results/local-document-frames-worker-events-sources.zip
python3 -B check.py results/android-local-document-frames-worker-events.json \
  --repeat results/android-local-document-frames-worker-events-repeat.json \
  --source-archive "$archive" --expect-frame-source self --expect-retained-outcomes
```

## Replay the reviewed reports

The shared source archive preserves the reviewed Android inputs and the
first iOS collection's inputs before the worker event follow-up.
[Shared source archive](results/local-document-frames-pre-worker-event-sources.zip)

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e results/local-document-frames-pre-worker-event-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/local-document-frames/check.py"
python3 -IB "$checker" results/android-local-document-frames-review.json --expect-retained-outcomes
python3 -IB "$checker" results/android-local-document-frames-review-repeat.json --expect-retained-outcomes
```

## Replay the original reports

The [original source archive](results/android-local-document-frames-original-sources.zip)
retains the initial verifier and its fingerprinted inputs.

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e results/android-local-document-frames-original-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/local-document-frames/check.py"
python3 -IB "$checker" results/android-local-document-frames.json
python3 -IB "$checker" results/android-local-document-frames-repeat.json
```

[Verification and scope](../../../docs/android-local-document-frames-verification.md)
