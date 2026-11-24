# iOS C10 shared-store retirement probe

A1 and A2 share an identified `WKWebsiteDataStore` and B1 uses a
separate store. The fixture opens actual `WKWebView` instances only after
setting and reading back cookie deny and comparing cookie records with
the cookie list. A test-owned native cookie write to A triggers a recheck
when A3 requests admission.

The probe uses the existing Swift admission gate and the established
never-loaded WebKit initializer before identified-store operations.
The fixture serves local `moonpool://` pages. A host-supplied page reads
the original A IndexedDB marker after retirement.

From this directory, run the tests and build the Simulator app.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
node --test test_guest.mjs
python3 -B run_probe.py build
```

Use a fresh tag and the explicitly owned, booted simulator record.
The collector verifies the installed app hash and terminates that
fixture app after collection.

```sh
python3 -B run_probe.py run --run retirement-recheck --owner /path/to/ios-owner.json
```

## Verify the reviewed reports

The capture command records weak-reference observations. Verification of
the reviewed reports expects both references to have cleared.

```sh
python3 -B check.py results/ios-profile-retirement-review.json --expect-cleared-weak-references
python3 -B check.py results/ios-profile-retirement-review-repeat.json --expect-cleared-weak-references
```

## Replay the original reports

The [original source archive](results/ios-profile-retirement-original-sources.zip)
preserves the source checksums of both original reports.

```sh
sources=results/ios-profile-retirement-original-sources.zip
python3 -B check.py results/ios-profile-retirement.json --source-archive "$sources" --expect-cleared-weak-references
python3 -B check.py results/ios-profile-retirement-repeat.json --source-archive "$sources" --expect-cleared-weak-references
```

[Verification and scope](../../../docs/ios-profile-retirement-verification.md)
