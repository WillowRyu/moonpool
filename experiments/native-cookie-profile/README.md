# C04 cookie profile tests

The `c04-1` JSON corpus covers all 70 profile rows as 102 independent cases.
Alternatives have letter suffixes and start with a fresh app jar. Expected
results come from the frozen profile.
[Profile and cases](../../docs/native-cookie-c04-profile.md#4-expected-vectors-for-c04-1),
[JSON corpus](vectors.json)

## Run the baseline

Use Python 3.13 and JDK 17. Prepare the pinned `public_suffix_list.dat` using the
profile's download and checksum command. From the workspace root, run the whole
corpus or select a row and all its variants.
[PSL snapshot](../../docs/native-cookie-c04-profile.md#public-suffix-list-snapshot)

```sh
python3 -B -m unittest discover -s experiments/native-cookie-profile -p 'test_*.py'
python3 -B experiments/native-cookie-profile/check.py --psl /path/to/public_suffix_list.dat
python3 -B experiments/native-cookie-profile/check.py --psl /path/to/public_suffix_list.dat --case E01
```

The runner reuses the comparison experiment's
`local-results/deps/okhttp-jvm-5.5.1.jar` and its published `.sha1` file. It finds
`com.squareup.okio:okio-jvm:3.18.1`, `org.jetbrains.kotlin:kotlin-stdlib:2.2.21`
and `org.json:json:20250517` in the same directory or the local Gradle cache.
On a fresh checkout, place the exact Maven Central JARs in that directory.
[Comparison dependency setup](../native-cookie-parser-comparison/README.md#rerun-step-1)

The verifier checks the corpus's PSL SHA-256 before launching the JVM. It
compiles the retained Android research `Broker.java` into a temporary directory.
The adapter calls the broker's existing fold/split, store, header selection and
script cookie operations with fixture inputs. It uses in-memory jars and makes
no HTTP requests. The baseline broker stores host-only session entries. PSL
lookup and persistent expiry are part of the reference parser step.
[Baseline broker source](../native-http-broker-probe/android/app/src/main/java/org/moonpool/httpbroker/Broker.java)

Exit status `0` means the selected cases pass, `1` reports behavioral
assertion failures and `2` reports setup errors such as a mismatched PSL digest
or a case with no assertions.
Run this isolated experiment separately from `pnpm run check`.

## Fixture format

- `t0` is `2026-11-11T00:00:00Z`. An `at` value sets the clock to that many seconds
  after `t0` and stays in effect through subsequent steps in the same case.
  The default request URL is at the top of the corpus.
- `receive` supplies ordered `Set-Cookie` field values. `{repeat:x:4095}` expands
  to 4,095 copies of the ASCII byte `x` in the size-boundary cases.
- `header` compares the exact ordered `Cookie` string. An empty string means
  the request carries no cookie header. `read` compares the ordered script-visible
  array. `set` checks acceptance of structured fields without fixing a bridge error code.
- `jar` compares all stored identities and values, and any named flags or
  expiry metadata. Entry order is checked through `header` and `read`.
  An explicit `expiresAt: null` expects a session cookie. A date is an absolute UTC instant.

## Baseline result

On 2026-11-11, two runs of the reviewed corpus on Zulu JDK 17.0.18 and Python
3.13.3 produced identical output. **52 of 102 cases passed and 50 failed**
across 236 assertions (139 passed, 97 failed). The baseline broker source is from `3cbb97a` and has
SHA-256 `353b295e702f30994bc298d2a910b18fee4cbae2c0ae4c3665d051841c595081`.

| Case | Expected | Observed on the retained broker |
| --- | --- | --- |
| P04 | A raw control byte rejects the whole line | Stores and sends `a=1` |
| P06b | Reject the line with a non-ASCII attribute and send `keep=1` from the same response | Sends `a=1; keep=1` |
| D01 | `Domain=example.com` matches approved hosts in that domain | Rejects the cookie |
| I01 | Host-only and domain entries coexist and send `a=1; a=2` | Keeps and sends only `a=2` |
| A05 | `Path=/a` excludes a request to `/a%2Fb/c` | Sends `a=1` |
| E01a | Replace at `T0+30s`. Send at `T0+89s` and expire before selection at `T0+90s` | Still sends the replacement at `T0+90s` |
| E01b | Expire before a script read 60 seconds after receipt | Still returns the cookie |
| E08a, E08b | Cap expiry at 400 days after the replacement received at `T0+30s` | Stores the replacement as a session cookie |
| X09b | A prefixed expiry without `Secure` preserves the entry | Deletes it |

The passing controls include P01 (host-only default path), P11 (folded comma
and `HttpOnly`), D05 (exact suffix), D06a (exact IP), and O01 (replacement
keeps creation order). The next step is to make the reference parser pass the
same cases using the pinned PSL and injected clock. Paired native evidence is
pending.
