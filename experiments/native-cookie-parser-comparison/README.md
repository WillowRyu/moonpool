# T28 cookie parser comparison

Research only. It feeds the same cookie lines to a platform's own cookie parser and compares the result
with the [C04 profile draft](../../docs/native-cookie-c04-profile-draft.md). Findings are in
[the report](../../docs/native-cookie-parser-comparison.md).

`vectors.json` holds 61 vectors: the C04 draft table and 12 common server shapes. Each says whether it
follows the RFC 6265 §4.1 server grammar, and what the draft expects. `compare.py` reports the differing
fields; `results/` keeps each platform's observations.

Step 1, OkHttp 5.5.1 on the desktop JVM, is collected. Step 2, iOS `HTTPCookie` on the simulator, is not
built and needs an explicit request.

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
