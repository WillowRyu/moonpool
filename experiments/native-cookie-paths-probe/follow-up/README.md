# C09 redirect and retained service-worker follow-up

This probe keeps the earlier WebView configuration and its failing receipts
available for comparison. The follow-up uses a same-origin native loader
for its five registered image cases. The Android retained-worker fixture
registers and caches an entry on the exact same synthetic origin and profile
before closing the seed view. The diagnostic view measures the response and
the worker's network attempt after native network suppression.
[Initial browser paths](../README.md),
[Native loader decision](../../../docs/adr/0029-check-static-resource-redirects-in-the-native-probe.md)

From this directory, prepare and serve the owned HTTPS fixture.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B probe.py build android
python3 -B probe.py build ios
python3 -u -B https_fixture.py
```

In a second terminal, collect one owned device at a time. Shut down Android
before booting iOS. Use a fresh run tag and the explicit device owner record.

```sh
python3 -B probe.py run android --run repeat --owner /path/to/android-owner.json
python3 -B probe.py run ios --run repeat --owner /path/to/ios-owner.json
```

Each collector verifies the installed build and stops the owned probe app.
The iOS native client evaluates TLS against the fixture CA for the exact
loopback endpoint. The Android probe uses its APK-scoped CA. Stop the
fixture and the owned device after collection.

Verify the retained evidence.

```sh
python3 -B check.py results/android-c09-paired.json results/ios-c09-paired.json
```
