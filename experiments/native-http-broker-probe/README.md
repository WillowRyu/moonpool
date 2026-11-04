# T28 isolated native broker experiment

**Complete for these 58 cases, collected on 2026-11-05 after the code review fixes. Retained evidence and findings are in
[the report](../../docs/native-http-broker-verification.md); it does not complete T28.**

It asks whether a native broker built on the accepted clients, OkHttp 5.5.1 on Android and `URLSession` on iOS, meets the
[proposed contract](../../docs/native-cookie-http-contract.md) under the [C01–C08 procedures](../../docs/native-cookie-http-conformance-plan.md).
Research only: no public API, SPEC or protocol change, and OkHttp is a dependency of this probe alone. The broker's field names and
error values are proposals under test, and its cookie parser is only the subset these cases need.

`cases.json` holds 58 scenarios and their oracle, with the same input on both platforms. A case that misses the oracle is a contract
finding. Missing evidence or a failed control fails verification. Not covered: C04, which needs a frozen cookie profile, C09–C12, and
real Portals or the bridge.

## Rerun

Retained results in `results/` need no device. To collect again, from this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py android
python3 -B build.py ios
```

Start `fixture.py`, write `local-results/android-owner.json` and `ios-owner.json` for the dedicated devices only, then run
`run_probe.py <platform> --run first --install` and `--run repeat` on each platform, and check them with `verify_results.py`.
The test keys went to the Trash after collection, so `build.py` creates a new test CA: build both platforms, then restart the fixture.
A run tag can be used once, because receipts and the fixture's attempts and holds are kept by tag.

Nothing is added to a device trust store. An unexpected process exit stops the run without retry.
