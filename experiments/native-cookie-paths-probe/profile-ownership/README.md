# Android C09 profile ownership probe

This fixture compares the cookie policy and state observed by two native
lookups of the same named AndroidX profile in one app process. One trial
makes a native cookie write while deny is in effect. A separate trial
changes the policy through the second lookup and restores deny after the
write. A distinct control profile holds its own marker for the same
synthetic HTTPS URL. The fixture loads no guest document and makes no
request to that URL.

From this directory, run the host test and assemble the APK.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect on the explicitly owned, booted emulator using a new tag and an
owner record. The collector verifies the AVD name and the installed APK
hash and stops its app after collection.

```sh
python3 -B run_probe.py run --run ownership-recheck --owner /path/to/android-owner.json
```

## Verify the retained measurements

The retained reports use the [original source archive](results/android-profile-ownership-original-sources.zip)
for their recorded fingerprints. Both reports are expected to show that
the direct native write was stored while deny was active.

```sh
sources=results/android-profile-ownership-original-sources.zip
python3 -B check.py results/android-profile-ownership.json --source-archive "$sources" --expect-direct stored
python3 -B check.py results/android-profile-ownership-repeat.json --source-archive "$sources" --expect-direct stored
```

For a new collection, use the current source fingerprints. The collection
reports either observed write outcome. Select `--expect-direct stored` or
`--expect-direct refused` when a given outcome is required.

New builds fingerprint the Gradle Wrapper JAR, build settings, manifest,
Java sources and probe scripts. Machine-local Android and IDE files are
outside that list.
[Verification and scope](../../../docs/android-profile-ownership-verification.md)
