# T28 cookie parser comparison

Research only. It feeds the same cookie lines to a platform's own cookie parser and compares the result
with the retained `c04-draft-1` expectations. Future C04 conformance uses the frozen `c04-1` profile.
[Comparison report](../../docs/native-cookie-parser-comparison.md), [C04 profile](../../docs/native-cookie-c04-profile.md)

`vectors.json` holds 61 vectors: the C04 draft table and 12 common server shapes. Each says whether it
follows the RFC 6265 §4.1 server grammar, and what the draft expects. `compare.py` reports the differing
fields; `results/` keeps each platform's observations.

Step 1, OkHttp 5.5.1 on the desktop JVM, was collected on 2026-11-06. Step 2, iOS `HTTPCookie` and a
per-vector in-memory `HTTPCookieStorage` on the dedicated simulator, was collected twice on 2026-11-09.
iOS results keep raw data only; `compare.py` derives each view against that platform's own clock.

## Rerun step 1

From this directory, with JDK 17 and the Gradle cache that the broker probe filled (Okio 3.18.1,
Kotlin stdlib 2.2.21, the OkHttp 5.5.1 Android artifact):

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
mkdir -p local-results/deps && cd local-results/deps
curl -fO https://repo1.maven.org/maven2/com/squareup/okhttp3/okhttp-jvm/5.5.1/okhttp-jvm-5.5.1.jar
curl -fO https://repo1.maven.org/maven2/com/squareup/okhttp3/okhttp-jvm/5.5.1/okhttp-jvm-5.5.1.jar.sha1
cd ../..
python3 -B run_okhttp.py
python3 -B compare.py results/okhttp-5.5.1-jvm.json
pnpm exec biome format --write results/   # whitespace only, so the repository check passes
```

`run_okhttp.py` refuses a jar whose SHA-1 differs from the published one, and records whether its
public-suffix data matches the Android artifact's.

## Rerun step 2

Needs Xcode and the simulator named `Moonpool Cookie Suppression`; no other simulator is touched.

```sh
python3 -B build_ios.py
python3 -B run_ios.py first repeat   # refuses to overwrite retained results; move them aside first
python3 -B compare.py results/ios-first.json results/ios-repeat.json
python3 -B compare.py results/okhttp-5.5.1-jvm.json results/ios-first.json
pnpm exec biome format --write results/
```

`run_ios.py` records every simulator's state, boots the dedicated one only if it was shut down, shuts it
down again, and reports whether all states match. An unexpected app exit stops the run without retry.
