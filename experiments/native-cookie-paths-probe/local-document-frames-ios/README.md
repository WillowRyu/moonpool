# iOS C09 local generated frame probe

The fixture serves the Android probe's two JavaScript assets on a local
`moonpool://` origin. It measures ordinary same-origin, `blob:`, and
`data:` iframes using a separate parent `WKWebView` for each case. The
control and guarded groups use different persistent `WKWebsiteDataStore`
identifiers. Each group must read back cookie deny and an empty result
from both native cookie sources before loading its first document.

The inherited document set creates an initial `about:blank` iframe and
a `srcdoc` iframe. Both report their URL, origin and worker evidence,
along with secure-context state and registration method availability.

The parent records child script starts, worker results, frame CSP events
and worker CSP events separately. It collects worker events until the
parent closes the observation window. A successful dedicated worker
has a native resource receipt of its own. The parent reads the sender's
DOM `MessageEvent.origin`. The fixture contains no Moonpool bridge.

## Collect on the owned simulator

From this directory, run the host tests and build the Simulator app.

```sh
python3 -OB -m unittest discover -s . -p 'test_*.py'
node --test ../local-document-frames/test_probe.mjs
python3 -B run_probe.py build
```

Run with a fresh tag and an owner record for the booted
`Moonpool Cookie Suppression` simulator. The collector checks the
installed app digest, matches the report to its process, and terminates
that app after capture. Raw reports go into `local-results/`.

```sh
python3 -B run_probe.py run --run inherited-a --owner /path/to/ios-owner.json \
  --frame-source origin --document-set inherited
python3 -B run_probe.py run --run inherited-b --owner /path/to/ios-owner.json \
  --frame-source origin --document-set inherited
```

## Verify the inherited frame reports

Both control workers must return a marker and have one native script
receipt each. Each guarded frame must start and report both a worker
rejection and an enforcing worker event. Paired verification requires
distinct run tags and four distinct stores, a valid matching installed
app digest, matching execution environments, and the same frame source
and document set in both collections. Retained verification requires a
secure context and an unavailable service-worker registration method in
both child types. The archive preserves the inputs to the measured build.
[Inherited frame source archive](../local-document-frames/results/local-document-frames-inherited-sources.zip)

```sh
archive=../local-document-frames/results/local-document-frames-inherited-sources.zip
python3 -B check.py results/ios-inherited-document-frames.json \
  --repeat results/ios-inherited-document-frames-repeat.json --source-archive "$archive" \
  --expect-frame-source origin --expect-document-set inherited --expect-retained-outcomes
```

## Verify a later navigation to about:blank

The `navigation` set records a same-origin marker document, navigates
its iframe to `about:blank`, and starts the worker probe only once the
replacement document is present. Navigation and worker observation have
separate 6.5-second windows. The control verifier checks that the worker
receipt follows the previous document receipt. Use fresh tags to collect
the pair.

```sh
python3 -B run_probe.py run --run blank-final-a --owner /path/to/ios-owner.json \
  --frame-source origin --document-set navigation
python3 -B run_probe.py run --run blank-final-b --owner /path/to/ios-owner.json \
  --frame-source origin --document-set navigation
python3 -B check.py results/ios-blank-navigation-review.json \
  --repeat results/ios-blank-navigation-review-repeat.json \
  --expect-frame-source origin --expect-document-set navigation --expect-retained-outcomes
```

[Paired navigation evidence](../../../docs/native-inherited-frames-verification.md#later-navigation-to-aboutblank)

## Replay the earlier navigation reports

The archive preserves both platforms' original build inputs. Use it to
check the previous iOS pair with the current receipt ordering rule.
[Navigation source archive](../local-document-frames/results/local-document-frames-blank-navigation-sources.zip)

```sh
archive=../local-document-frames/results/local-document-frames-blank-navigation-sources.zip
python3 -B check.py results/ios-blank-navigation.json \
  --repeat results/ios-blank-navigation-repeat.json --source-archive "$archive" \
  --expect-frame-source origin --expect-document-set navigation --expect-retained-outcomes
```

## Replay the explicit origin reports

The default local document set covers ordinary, blob and data frames.
Its archived verifier checks the explicit-origin pair and same-app
`'self'` comparison.
[Explicit origin source archive](../local-document-frames/results/local-document-frames-explicit-origin-sources.zip)

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e ../local-document-frames/results/local-document-frames-explicit-origin-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/local-document-frames-ios/check.py"
python3 -IB "$checker" results/ios-local-document-frames-explicit-origin.json \
  --repeat results/ios-local-document-frames-explicit-origin-repeat.json --expect-frame-source origin
python3 -IB "$checker" results/ios-local-document-frames-explicit-origin-self.json --expect-frame-source self
```

## Replay the worker event reports

The earlier `'self'` runs have their own source archive and pair verifier.
[Worker event source archive](../local-document-frames/results/local-document-frames-worker-events-sources.zip)

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e ../local-document-frames/results/local-document-frames-worker-events-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/local-document-frames-ios/check.py"
python3 -IB "$checker" results/ios-local-document-frames-worker-events.json \
  --repeat results/ios-local-document-frames-worker-events-repeat.json
```

## Replay the earlier reports

The shared source archive includes the exact inputs and verifier for
the original iOS collections and the preceding Android review runs.
[Shared source archive](../local-document-frames/results/local-document-frames-pre-worker-event-sources.zip)

```sh
snapshot_dir=$(mktemp -d)
python3 -IB -m zipfile -e ../local-document-frames/results/local-document-frames-pre-worker-event-sources.zip "$snapshot_dir"
checker="$snapshot_dir/experiments/native-cookie-paths-probe/local-document-frames-ios/check.py"
python3 -IB "$checker" results/ios-local-document-frames.json
python3 -IB "$checker" results/ios-local-document-frames-repeat.json
```

[Verification and scope](../../../docs/ios-local-document-frames-verification.md)
[Paired inherited frame evidence](../../../docs/native-inherited-frames-verification.md)
