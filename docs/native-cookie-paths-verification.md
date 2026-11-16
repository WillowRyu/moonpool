# T28 C09 browser paths and C10 control verification

2026-11-16. The paired probe completed on Android 17 / API 37 with WebView
145.0.7632.218 and on an iOS 26.4.1 simulator. It uses the inherited native
admission gate, an isolated website partition, the candidate local origin/loader,
and a content security policy. Android stopped before iOS started. This work
concerns SPEC §8 and §9.
[Probe instructions](../experiments/native-cookie-paths-probe/README.md),
[Accepted admission evidence rule](native-cookie-store-admission.md#3-admission-sequence-and-shared-ownership)

| Observation | Android | iOS |
| --- | ---: | ---: |
| Empty-store admissions after policy and presence confirmation | 3/3 | 3/3 |
| Cookie-present and injected-unknown refusals before guest load | 2/2 | 2/2 |
| Host and unrelated-profile cookie observations at the server | 8/8 | 8/8 |
| Independent HTTPS receipts, including setup and redirect receipts | 26 | 26 |
| Forbidden same-host redirect target receipts | 3 | 3 |

The three admitted samples per platform are initial load, an actual reload,
and recreation of the WebView for the same app and store. Each reports policy
completion, policy readback and whole-store presence before the loader and
guest script run. iOS creates a never-loaded WebKit view first, then confirms
both cookie records and native cookie enumeration after policy installation.
The B partition holds both an ordinary and an HttpOnly cookie. Refusal leaves
both entries present. The unknown verdict is injected in the native driver and
has zero loader and guest starts.
[Android report](../experiments/native-cookie-paths-probe/results/android-c09-paired.json),
[iOS report](../experiments/native-cookie-paths-probe/results/ios-c09-paired.json)

## Guest and control behavior

- Direct and prototype cookie reads are empty before and after writes in the
  main document and in a same-origin iframe. The local image and approved
  remote image load. Their responses attempt to set cookies, and the approved
  remote echo carries an empty Cookie header. The native guest store remains empty.
- Fetch, XHR, Beacon, WebSocket, EventSource, form submission, a foreign frame
  and a popup produce no HTTPS receipts. Both native popup delegates refuse
  the creation. Android JavaScript returns a window reference, making a server
  receipt or native creation witness necessary for interpretation. The tested
  dedicated worker did not execute.
- localStorage and IndexedDB retain the fixture values through reload and
  recreation. The host test store, unrelated U store and B store send their own
  expected cookie after A's policy changes. Host and U remain live after B
  receives its own policy and refuses admission.

## Same-host redirect reached the denied path

The server received one request to `/denied` after each of the three admitted
loads per platform. Each starts with an approved image URL under `/static/`,
then follows the fixture's 302 to the same host and port. The redirected
request has an empty Cookie header. JavaScript records an image error because
the server returns 403. The redirect to the other hostname produces zero
denied-endpoint receipts.

CSP checks the path component of a source expression before redirection.
On Android, `shouldInterceptRequest` sees the initial URL in a redirect chain.
These rules explain the allowance seen by the candidate. A denied image result
alone cannot establish that the request stayed inside the approved path.
[CSP source matching](https://www.w3.org/TR/CSP3/#match-url-to-source-expression),
[Android WebViewClient redirect handling](https://developer.android.com/reference/android/webkit/WebViewClient#shouldInterceptRequest(android.webkit.WebView,%20android.webkit.WebResourceRequest))

The strict verifier reports exactly these three failures per platform.
These measurements left the redirect boundary and retained service-worker
behavior open for the follow-up. The tested Android context exposed the
service-worker API, and the tested iOS custom-scheme context did not expose it.
Actual shared-Portal retirement and writer exclusion remain C10 follow-up work.

The follow-up kept this failing pair and exercised explicit native redirect
checks and Android retained-worker control in a separate probe.
[Follow-up verification](native-cookie-paths-follow-up-verification.md)

## Preliminary storage observation

One Android run changed the named profile while keeping the earlier synthetic
origin. The initial page read both the localStorage and IndexedDB sentinels
from that earlier run. The tentative profile-replacement test is retained
locally as `android-c09-confirmed.json`. The paired fixture uses one synthetic
app origin per run and preserves it within reload and recreation. The cause
of the same-origin observation remains open.

## Reproduce

```sh
cd experiments/native-cookie-paths-probe
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B verify.py results/android-c09-paired.json results/ios-c09-paired.json
```

The host suite passes 12 tests. The strict verifier exits with status 1
for the six recorded redirect violations. It checks the full source
fingerprints and installed artifact correspondence. Both native builds and
the iOS signature check pass. The dedicated devices and loopback fixture
are stopped, with test keys retired to the local Trash. The TLS anchors
were scoped to the Android probe APK and iOS navigation delegate.
