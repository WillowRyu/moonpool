# 29. Check static resource redirects in the native probe

2026-11-16. Applied to the isolated C09 follow-up.

## Context

Both earlier WebViews requested a denied path after an approved image returned
a same-host redirect. The image error occurred after the server received the
request. CSP's path check applies before a redirect. Android's initial resource
callback also covers only the initial URL in a redirect chain.
[Earlier C09 evidence](../native-cookie-paths-verification.md#same-host-redirect-reached-the-denied-path),
[CSP source matching](https://www.w3.org/TR/CSP3/#match-url-to-source-expression)

## Decision

Expose the fixture's registered images through its same-origin native loader.
The loader maps fixed resource names to HTTPS targets. The native client turns
off automatic redirects and checks the scheme, host, port and exact encoded
path before every request, including the target of each redirect. The fixture
retains a positive redirect from an approved path to another approved path.

Use a native client with ambient cookies, credentials and caching disabled.
Expose the received image bytes with the local URL and image MIME type.
Response headers such as Set-Cookie remain on the native side.

## Consequences

Server receipts can distinguish a refused target from a failed image render.
The resource check depends on the admitted document reaching the native
loader. A pre-existing service worker can affect that condition, so the probe
measures a retained registration and its cached entry separately. This
concerns SPEC §8 and §9. Product resource registration, store admission
evidence and loader integration remain under T28 and T38/T39 review.
