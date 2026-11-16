# 28. Prepare one service URL in the broker probes

2026-11-16. Applied to the isolated T28 C04 experiment.

## Context

The cookie profile uses the percent-encoded path sent to an approved service
for both cookie selection and default paths. The old brokers read a decoded
path. The loopback fixture showed both sending a cookie minted under
`/deep%2Fsegment/s` to `/deep/segment/s`. It also showed the old iOS broker
approving `%6cocalhost` as `localhost`. OkHttp resolved `/deep/%2e%2e/s`
to `/s` while URLSession sent the encoded dot segment as written.
[Paired evidence](../native-cookie-c04-broker-verification.md),
[OkHttp 5.5.1 path handling](https://github.com/square/okhttp/blob/parent-5.5.1/okhttp/src/commonJvmAndroid/kotlin/okhttp3/HttpUrl.kt#L1453-L1519)

## Decision

Validate the original host spelling before approval. Foundation can map
Unicode input into an ASCII alias before returning a host, so the iOS
probe checks the original authority bytes before creating a URL. Prepare
one HTTPS URL, and use its host and port for approval, its host and encoded
path for cookie selection and response commit, and the URL itself for
dispatch. Keep the original encoded bytes in ordinary path segments,
including `%2F`.

Use OkHttp's prepared URL on Android. On iOS, resolve literal and encoded
dot segments before preparing the URL so both probes select the same route.
Compress equivalent expanded IPv6 spellings. Refuse an IPv4-mapped IPv6
literal because OkHttp would change its host to the mapped IPv4 address
before dispatch, which also changes which service registration applies.

Prepare registered hosts with the same rules as request hosts. Approval
compares a canonical host and a port, so an expanded IPv6 registration
matches its compressed spelling on the registered port.

## Consequences

Both probes apply cookies to the service and path the fixture receives.
The paired vectors check rejection before network dispatch and the encoded
path on send and response commit. This concerns SPEC §9. Production URL and
error contracts remain subject to T28/T29 review.
