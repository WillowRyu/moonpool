# Android C09 worker policy in inherited documents

Run dedicated-worker and service-worker controls from the loader entry,
an initial `about:blank` iframe and an `about:srcdoc` iframe. All three
documents run their probes in their own JavaScript contexts. The guarded
entry receives an enforcing `worker-src 'none'` header. Both inherited
documents are created locally by that entry, without loader responses
of their own.

Run the host test and assemble the app from this directory.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B run_probe.py build
```

Collect on the owned, booted Android emulator with a fresh tag. The
collector checks the AVD name and installed APK hash and stops its app.

```sh
python3 -B run_probe.py run --run contexts-recheck --owner /path/to/android-owner.json
```

Verify the retained reports offline.

```sh
python3 -B check.py results/android-worker-contexts.json
python3 -B check.py results/android-worker-contexts-repeat.json
```

The verifier requires a positive worker control in the matching document
before attributing a worker refusal to the policy. It reports any
inherited documents without a positive service-worker control.
[Verification and scope](../../../docs/native-worker-contexts-verification.md)
