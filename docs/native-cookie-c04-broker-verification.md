# T28 C04 broker verification

2026-11-16. This paired collection follows the IPv6 registration fix.
The Android API 37 emulator ran OkHttp 5.5.1. After it shut down, the iOS 26.4.1
simulator ran URLSession. Both used the same `c04-1` vectors and verified
the bundled Public Suffix List at revision `3db7776`. This concerns SPEC §9.
[C04 profile](native-cookie-c04-profile.md)

| Evidence | Android | iOS |
| --- | ---: | ---: |
| Controlled-clock C04 corpus in the app | 109/109 | 109/109 |
| Corpus assertions | 254/254 | 254/254 |
| Broker scenarios | 71/71 | 71/71 |
| C04 scenarios within that suite | 8/8 | 8/8 |
| Fixture request arrivals | 133 | 141 |
| Fixture hold-release rows | 7 | 8 |
| Evidence checks | 525 | 534 |

The 71 scenarios include the retained 63 controls and C01–C03/C05–C08
scenarios. All serialized C04 corpus observations match. The HTTPS verifier
reports zero differences in the compared guest results, cookie headers and
jar effects. iOS still makes the previously measured extra Basic attempt.
[Android observations](../experiments/native-http-broker-probe/results/android-c04.json),
[iOS observations](../experiments/native-http-broker-probe/results/ios-c04.json),
[Earlier Basic evidence](native-http-broker-verification.md#the-one-platform-difference)

## Request and cookie checks

The old brokers sent `implicit=1` to the decoded slash path on both
platforms. Before the iOS port, the server also received a request for
`%6cocalhost` as `localhost`, and received `/deep/%2e%2e/s` with the
`deep=1` cookie. The original setup passed its controls, and five new C04
scenarios failed on iOS. A follow-up run also showed that Foundation converted
fullwidth `ｌocalhost` and `lo<U+00AD>calhost` into the approved `localhost`;
the fixture got both requests before the raw authority check was added.

After the port, the fixture recorded the same values for both platforms.

| Request | Received path | Received Cookie |
| --- | --- | --- |
| Encoded-path follow-up | `/deep%2Fsegment/s` | `implicit=1; explicit=2` |
| Literal slash follow-up | `/deep/segment/s` | Empty |
| `/deep/%2e%2e/s` | `/s` | Empty |
| Follow-up after the dot-segment response | `/s` | `landed=2` |

Both reject escaped and Unicode host aliases, malformed DNS/IP forms,
IPv4-mapped IPv6 and overflowing ports before dispatch. The expanded IPv6
control passes admission for the same
approved endpoint as the compressed spelling. Its network request fails
in the fixture configuration. The live IPv4 scenario checks the
exact-IP `Domain` rule, same-identity replacement and expiry. The other
HTTPS cases cover prefix validation before expiry, controlled expiry at
selection and script read, and header order after replacement and reissue.
[URL preparation decision](adr/0028-prepare-one-service-url-in-the-broker-probes.md)

## IPv6 registration

The review reproduced a permission denial on both desktop brokers when
the configured service host was `0:0:0:0:0:0:0:1`. The broker compressed
the request host to `::1` and compared it with the registered spelling.
The regression returned `-32000` for the expanded `cookies.set` and the
compressed `cookies.get` before the fix.

The probes now canonicalize registrations and requests through the same
URL preparation. The approval key contains the canonical host and port.
On both devices, the expanded spelling stored `sid=ipv6`, the compressed
spelling read it on the registered port, and the second port returned
`-32000`. The compressed HTTP target passed service approval and reached
the expected network error for the fixture's IPv4 listener configuration.
The earlier 70-case measurements are archived under
`local-results/c04-before-ipv6-registration.*`.

## Reproduce and scope

From the workspace root, verify the retained reports with no running devices.

```sh
python3 -B experiments/native-http-broker-probe/verify_results.py --summary \
  experiments/native-http-broker-probe/results/android-c04.json \
  experiments/native-http-broker-probe/results/ios-c04.json
```

Both `failed` maps and the paired difference list are empty. The verifier
checks the build fingerprints, installed artifact, loaded PSL checksum,
and all 254 corpus assertions per platform. The desktop reference checks
also agree on 20,000 generated vectors. The fixture and both owned devices
were stopped, and the generated fixture keys moved to the local Trash.

The fixture listens on loopback. The multi-label DNS and PSL cases run in the
in-app controlled corpus. Physical devices, real Portals and the bridge remain
future verification targets. C09–C12 and final T28 contract approval are open.
