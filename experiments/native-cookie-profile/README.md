# C04 cookie profile tests

The `c04-1` JSON corpus covers all 70 profile rows as 102 independent cases.
Alternatives have letter suffixes and start with a fresh app jar. Expected
results come from the frozen profile.
[Profile and cases](../../docs/native-cookie-c04-profile.md#4-expected-vectors-for-c04-1),
[JSON corpus](vectors.json)

## Run the tests

Use Python 3.13 and JDK 17. The Swift subject also needs macOS with the Xcode
Swift 6 toolchain, and no simulator. Prepare the pinned `public_suffix_list.dat` using the
profile's download and checksum command. From the workspace root, run the whole
corpus or select a row and all its variants. `--subject` is required, so a
baseline run is never mistaken for a reference run. Repeat it to run several
subjects in one invocation.
[PSL snapshot](../../docs/native-cookie-c04-profile.md#public-suffix-list-snapshot)

```sh
python3 -B -m unittest discover -s experiments/native-cookie-profile -p 'test_*.py'
python3 -B experiments/native-cookie-profile/check.py --subject reference --psl /path/to/public_suffix_list.dat
python3 -B experiments/native-cookie-profile/check.py --subject reference --psl /path/to/public_suffix_list.dat --case E01
python3 -B experiments/native-cookie-profile/check.py --subject swift --psl /path/to/public_suffix_list.dat
python3 -B experiments/native-cookie-profile/check.py --subject reference --subject swift --generated 20000 --psl /path/to/public_suffix_list.dat
python3 -B experiments/native-cookie-profile/check.py --subject baseline --psl /path/to/public_suffix_list.dat
```

Exit status `0` means the selected cases pass, `1` reports behavioral
assertion failures or a difference between the two ports, and `2` reports setup
errors such as a mismatched PSL digest or a case with no assertions.
Run this isolated experiment separately from `pnpm run check`.

## Reference parser

`reference/java/src` is the c04-1 reference for the shared parser in ADR 0027. Android
and iOS will port it and run this corpus. The [Swift port](#swift-port) is the first. It uses only the JDK. The runner
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

Under `reference/java/test`, `ReferenceAdapter` reads the fixture URL with
`URI.getRawPath()`, the D4 input. It supplies each step's `now` and returns JSON
observations. A `jar` snapshot does not remove expired entries, so the corpus
sees what `header` and `read` removed. `ReferenceSelfTest` runs before the corpus
and checks each building block against an independent source:

- RFC 3492 samples, and every Unicode PSL label against `java.net.IDN`.
- The ICANN and PRIVATE rule counts, and public suffixes for wildcard, exception, A-label and implicit-rule hosts.
- RFC 6265 date forms and rejections, and the calendar against `java.time` for every month from 1601 to 9999.
- The folded-field split against both brokers' regex, including 200,000 seeded inputs.
- Canonical request hosts, including an IPv6 literal with and without brackets.

It also prints a SHA-256 digest of the canonical PSL rules, which the runner
compares with the Swift port's. The self-test exits with status 3 for failed checks, which the runner reports as
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
  D1 then rejects. The reference uses Java's ASCII set, which the maintainer
  accepted on 2026-11-13 as part of ADR 0027 rule 1 and contract §4. This byte
  sequence has not been checked on a device, and whether `URLSession` passes
  U+00A0 through is unknown.

## Reference result

On 2026-11-13, two runs on Zulu JDK 17.0.18 and Python 3.13.3 produced identical
output. **All 102 cases and 236 assertions passed**, and the self-test passed
552 checks. The later IPv6 host fix added 15 checks, and the current self-test
passes 567.

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

## Swift port

`reference/swift/src` ports the Java reference file by file for the iOS SDK. It
uses only the Swift standard library. The runner rejects any `import` in these
files and builds them as their own module with Swift 6 language mode and
`-warnings-as-errors`. Foundation is where the retained iOS split diverged, so
the port does not use Foundation text APIs.

Swift's `String` compares, splits and matches prefixes by `Character`, with
Unicode canonical equivalence. The port works on UTF-8 bytes wherever Java works
on chars. Every split point and comparison involves only ASCII bytes, so both
ports cut the same text.

Under `reference/swift/test`, one harness runs the self-test or the corpus
adapter. The self-test uses sources independent of the port:

- RFC 3492 samples, PSL rule counts and public suffixes, and request hosts, as in Java.
- RFC 6265 dates and the calendar against Foundation's Gregorian calendar.
- The split against an `NSRegularExpression` that spells out Java's ASCII `\s`, with 200,000 seeded inputs.

Apple platforms have no IDNA API, so the Unicode PSL labels are checked through
the rules digest. The runner fails if it differs from the Java reference's.

The adapter reads fixture URLs the way an iOS adapter should:

- **`URL.host(percentEncoded: true)` for the host.** `URLComponents.host` decodes
  an A-label to Unicode. It turns `shop.xn--55qx5d.cn` into `shop.公司.cn`, and
  `percentEncodedHost` percent-encodes that Unicode. The retained iOS broker uses
  `URLComponents.host`, while Android's `URI.getHost()` keeps the A-label. The
  reference's `Request.of` rejects a non-ASCII host, so that mistake stops a run
  with a setup error. D11 alone cannot catch it in a broker: a cookie rejected
  for a mangled host looks the same as one the PSL rejected.
- **IPv6 brackets restored by the jar.** `URL.host` drops them and
  `URI.getHost()` keeps them. `Request.of` now adds them in both ports, so
  `[::1]` names the same host.
- `URL.path(percentEncoded: true)` for the D4 path, which keeps `%2F`.

## Port comparison

With both `--subject reference` and `--subject swift`, the runner also compares
every observation of every case between the two ports. That includes jar fields
no expected value names. `--generated N` adds N seeded cases with no expected
values. Each case uses one family of related hosts, such as `example.com` and its
subdomains, `co.uk`, `www.ck`, an IP and `[::1]`. Steps receive, send, read, snapshot
and set cookies over boundary attributes, D1 rejections and delays up to the
400-day cap. Only agreement between the ports is checked.

## Swift result

On 2026-11-13, with Swift 6.3.1 and the macOS 26.4 SDK, **the Swift port passed
all 102 cases and 236 assertions**, and its self-test passed 75 checks. Both ports
reported 10,414 canonical PSL rules with the same digest,
`94796a25c73fe70eaaa66ca2e6677b7d59ed6ac32d9a497b991bc0b323ffe8a4`.

Comparing the ports found **0 differences** over the corpus and 20,000 generated
cases with the default seed, and over 100,000 with seed 1. Two runs of all three
subjects produced identical output. The baseline stays at 52 of 102.

In the 20,000 default cases, 7,950 of 32,517 header steps carried a cookie and
2,465 carried two or more. Snapshots held 1,165 domain cookies, 1,269 persistent
cookies, 545 `HttpOnly` cookies and 787 cookies on `[::1]`. `__Host-` cookies are
rare, with one stored.

Two mutated Swift copies show what each layer catches:

| Swift change | Corpus | Self-test | Port comparison |
| --- | --- | --- | --- |
| `Domain=.` rejects the line instead of falling back to host-only | 102/102 passed | Passed | 1,352 differences, status 1 |
| IPv6 brackets not restored | Not reached | 2 checks failed, status 1 | Not reached |

The self-test runs first, so the second copy stopped before its corpus run.

The retained iOS regex split 2,616 of the 200,000 seeded inputs differently
from the reference. The seeded alphabet includes U+00A0.

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
