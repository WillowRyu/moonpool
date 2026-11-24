# Android C10 shared-profile retirement probe

This fixture uses the existing research admission gate with real Android
WebViews. A1 and A2 use the same named profile and origin. B1 uses its own
profile. After a native write to A's test cookie jar, A3 requests admission
through the gate and the owner rechecks A. The probe records handle
invalidation, detachment and destruction of A1/A2, refusal of A3 and a
later A4, and a second observation of B1's original document.

The fixture serves local content under synthetic HTTPS origins. An
inspection view reads the existing A marker after retirement using
host-supplied HTML. The app writes no real cookie values.

From this directory, run the host tests and build the APK.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect on the specific, owned emulator with a fresh tag. The collector
checks the AVD name and installed artifact hash, then stops the fixture
app after the run.

```sh
python3 -B run_probe.py run --run retirement-recheck --owner /path/to/android-owner.json
```

Verify the retained reports offline.

```sh
python3 -B check.py results/android-profile-retirement.json
python3 -B check.py results/android-profile-retirement-repeat.json
```

[Verification and scope](../../../docs/android-profile-retirement-verification.md)
