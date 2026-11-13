# C04 cookie profile tests

The `c04-1` JSON corpus covers all 70 profile rows as 102 independent cases.
Alternatives have letter suffixes and start with a fresh app jar. Expected
results come from the frozen profile.
[Profile and cases](../../docs/native-cookie-c04-profile.md#4-expected-vectors-for-c04-1),
[JSON corpus](vectors.json)

## Run the tests

Use Python 3.13 and JDK 17. Prepare the pinned `public_suffix_list.dat` using the
profile's download and checksum command. From the workspace root, run the whole
corpus or select a row and all its variants. `--subject` is required, so a
baseline run is never mistaken for a reference run.
[PSL snapshot](../../docs/native-cookie-c04-profile.md#public-suffix-list-snapshot)

```sh
python3 -B -m unittest discover -s experiments/native-cookie-profile -p 'test_*.py'
python3 -B experiments/native-cookie-profile/check.py --subject reference --psl /path/to/public_suffix_list.dat
python3 -B experiments/native-cookie-profile/check.py --subject reference --psl /path/to/public_suffix_list.dat --case E01
python3 -B experiments/native-cookie-profile/check.py --subject baseline --psl /path/to/public_suffix_list.dat
```

Exit status `0` means the selected cases pass, `1` reports behavioral
assertion failures and `2` reports setup errors such as a mismatched PSL digest
or a case with no assertions.
Run this isolated experiment separately from `pnpm run check`.

## Reference parser

`reference/src` is the c04-1 reference for the shared parser in ADR 0027. Android
and iOS will port it and run this corpus. It uses only the JDK. The runner
compiles it with no classpath and `-Xlint:all -Werror`, so a dependency cannot
slip in. Callers pass the request host, the percent-encoded path and the time
in epoch seconds. The jar has no clock, I/O or platform cookie API. The broker
still checks that each URL is an approved HTTPS service origin.

| File | Role |
| --- | --- |
| `CookieJar.java` | Folded-field split, D1 parsing, D2 domains, D3-B identity, D4 paths, D5 expiry, D6 prefixes, D7 `SameSite`, D8 order, D9 ignored attributes, script read and set |
| `PublicSuffixList.java` | Strict UTF-8 loading of both sections, and the PSL formal algorithm |
| `CookieDate.java` | RFC 6265 §5.1.1 dates with hand-written calendar arithmetic |
| `Punycode.java` | RFC 3492 encoder for Unicode PSL labels |
| `Ascii.java` | ASCII-only case and whitespace helpers |

Under `reference/test`, `ReferenceAdapter` reads the fixture URL with
`URI.getRawPath()`, the D4 input. It supplies each step's `now` and returns JSON
observations. A `jar` snapshot does not remove expired entries, so the corpus
sees what `header` and `read` removed. `ReferenceSelfTest` runs before the corpus
and checks each building block against an independent source:

- RFC 3492 samples, and every Unicode PSL label against `java.net.IDN`.
- The ICANN and PRIVATE rule counts, and public suffixes for wildcard, exception, A-label and implicit-rule hosts.
- RFC 6265 date forms and rejections, and the calendar against `java.time` for every month from 1601 to 9999.
- The folded-field split against both brokers' regex, including 200,000 seeded inputs.

The self-test exits with status 3 for failed checks, which the runner reports as
status 1. Any other JVM failure is a setup error.

Two choices keep the iOS port from drifting:

- **Own Punycode.** iOS has no IDNA API. The JDK's IDNA2003 tables (Unicode 3.2)
  reject one label of the pinned snapshot, Balinese `ᬩᬮᬶ`, unless unassigned code
  points are allowed. Both SDKs encode labels the same way, and the self-test
  compares all 493 Unicode labels with the JDK's result.
- **ASCII whitespace in the split.** The brokers split folded fields with
  `,\s*(?=[^;,=\s]+=)`. Java's `\s` is ASCII-only, but `NSRegularExpression`
  matches Unicode spaces. On macOS Foundation (Swift 6.3.1) the retained iOS split
  turns `a=1,<U+00A0>b=2` into `a=1` and `b=2`. Java keeps `<U+00A0>b=2`, which
  D1 then rejects. The reference uses Java's ASCII set. This byte sequence has not
  been checked on a device, and whether `URLSession` passes U+00A0 through is unknown.

## Reference result

On 2026-11-13, two runs on Zulu JDK 17.0.18 and Python 3.13.3 produced identical
output. **All 102 cases and 236 assertions passed**, and the self-test passed
552 checks.

Eleven mutated copies, each breaking one rule, all exited with status 1 and failed
the expected cases:

| Rule broken | Failed |
| --- | --- |
| Public-suffix check skipped | D04, D05, D08, D09, D11, D12, D13 |
| `Expires` not capped at 400 days | P10, E08a |
| Expired entries kept for header selection | E01a |
| `__Host-` accepts a default root path | X07a, X07b |
| Case-sensitive prefix check | X01b, X02b, X02c, X04a, X04b, X07a, X07b, X08a, X08b, X09b |
| Identity without the host-only flag | I01, I04, I05a, I05b, I06, O02, O03 |
| Replacement gets a new creation order | P02, O01, O02, U02, U03a, U03b |
| First valid `Max-Age` wins | E12b |
| IP hosts accept partial `Domain` values | D06a, D06b |
| Wrong Punycode digit | 361 of 552 self-test checks |
| Split without a name before `=` | 7 of 552 self-test checks |

The research brokers still run the baseline parser. Porting the reference
changes files the four retained 63-case collections fingerprint, so those
collections need a new collection on the devices. That needs an explicit
resume, as the profile's verification sequence states.

## Dependencies

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
no HTTP requests. The baseline broker stores host-only session entries and
has no PSL or expiry clock. The reference subject needs only `org.json`, for its adapter.
[Baseline broker source](../native-http-broker-probe/android/app/src/main/java/org/moonpool/httpbroker/Broker.java)

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
keeps creation order). Rerunning with `--subject baseline` on 2026-11-13 gave the
same totals. The [reference result](#reference-result) passes all 102 cases.
Paired native evidence is pending.
