# C09 Android worker evidence before guest load

This probe checks whether a host-supplied inspection page can identify a
retained worker in the exact named Android WebView profile and origin. It
holds the inspected view's network and the profile worker's network closed.
The seed phase writes public fixture data and activates two registrations.
The runner then starts a separate app process for each check.
[Accepted store admission](../../../docs/native-cookie-store-admission.md)

From this directory, build the APK with the existing toolchain.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Boot the dedicated emulator, use a fresh tag, and supply its owner record.

```sh
python3 -u -B run_probe.py run --run worker-repeat --owner /path/to/android-owner.json
```

The collector checks the installed APK and waits for activity launch. A
process exit stops the collection. The synthetic HTTPS origins use local
resource interception. The reported guest verdict comes from the native
gate. The scripts-disabled diagnostic runs after refusal to witness the
cached worker response on the owned profile.

Verify the retained report with the corresponding oracle.

```sh
python3 -B check.py --expect-unavailable results/android-worker-admission.json
python3 -B check.py results/android-worker-admission.json
```

The first command verifies the observed rejections and zero guest loads.
The second command returns status 1 because the worker-absence hypothesis
requires a valid registration list. Retained profiles and public fixture data
remain on the owned emulator.
[Verification report](../../../docs/native-worker-admission-verification.md)
