# T28 isolated native broker experiment

**Both platforms passed 71 broker scenarios and the 109-case C04 corpus on
2026-11-16 after the IPv6 registration fix.** [Paired C04 evidence](../../docs/native-cookie-c04-broker-verification.md)

It asks whether a native broker built on the accepted clients, OkHttp 5.5.1 on Android and `URLSession` on iOS, meets the
[proposed contract](../../docs/native-cookie-http-contract.md) under the [C01–C08 procedures](../../docs/native-cookie-http-conformance-plan.md).
OkHttp is a dependency of this probe. The field names and error values are
proposals under test. Both builds compile the C04 reference jar sources and
bundle the same pinned PSL data.

`cases.json` holds the 63 previously measured scenarios and eight C04
scenarios. The in-app replay covers the full controlled-clock C04 corpus.
A case that misses the oracle is a contract finding. Missing evidence or a
failed control fails verification. C09–C12, real Portals and the bridge
remain open.

## Rerun

Verify the retained `android-c04.json` and `ios-c04.json` reports with
`verify_results.py --summary`. The four reports for the original 63-case
broker use the [historical verifier](../../docs/native-http-broker-verification.md#reproduce).
To collect again, first prepare the
[pinned PSL](../../docs/native-cookie-c04-profile.md#public-suffix-list-snapshot)
as `../native-cookie-profile/local-results/public_suffix_list.dat` or pass its
path with `--psl`. From this directory run the following.

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py android
python3 -B build.py ios
```

Start `fixture.py` after building. Write `local-results/android-owner.json`
and `ios-owner.json` for the dedicated devices. Boot Android, collect using
`run_probe.py android --run c04-repeat --install`, then shut it down. Boot
iOS for its collection, shut it down and verify the two reports.
Use a fresh run tag because fixture receipts, attempts and holds use it.
`build.py` creates a test CA under `local-results/c04-tls` on first use.

Nothing is added to a device trust store. An unexpected process exit stops the run without retry.
