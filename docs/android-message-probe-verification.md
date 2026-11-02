# T25 — Android message-channel/authentication research

Date: 2026-11-02 (Asia/Seoul)
Status: Bounded research for the recorded emulator/provider. Not a native SDK,
accepted origin change or complete SPEC §9 conformance claim.
Baseline: published 6c5576e; T23/T24 source and retained evidence are preserved.

## Result and consequence

The tested WebView supports all six checked AndroidX messaging features.
WebMessageListener supplies the actual WebView, sourceOrigin, isMainFrame and a
reply proxy. Registering it before loading makes it available to the fixture's
inline head script before page-finished. HTTPS origin rules exclude the foreign
frame's pinned object, but same-origin subframes still receive it: native
main-frame and instance checks remain necessary. Forged payload origin/frame
claims never select authority in this probe.

Both native-created and guest-created MessageChannels exchange ordered strings
and replies. The guest-created channel's transferred endpoint arrives in an
origin/frame-attested listener callback, demonstrating authenticated initial
port handoff without a native targetOrigin transfer race. The listener is an
experimental control/bootstrap, not adoption of a production transport replacing
SPEC §3.1's WebMessagePort entry.
That attestation identifies the offering frame; it does not independently prove
where the entangled peer was created or prevent the peer from being transferred.

Two separate limits are observed:

- An old native-created port transfer addressed only to the correct origin can
  reach a replacement document at that same origin. A document-scoped reply-proxy
  challenge denies the stale proof in the experiment; current proof succeeds.
- An authorized top frame can deliberately transfer its established port and
  proof to a loaded foreign subframe. Subsequent native port callbacks lack
  per-message origin/frame metadata and accept the valid proof. Authenticated
  initial handoff alone does not establish ongoing frame/origin provenance.

These are decision inputs, not approved solutions. T26 supplies paired iOS
evidence; T27–T31 must resolve runtime ownership, origin/channel contract,
document identity, codec and teardown before production native transport work.
In particular, no blanket SPEC §9.1 claim follows from port possession or a
successful bootstrap. Navigation containment is not implemented by this probe.

Same-origin document replacement within the same app/grants is not itself an
isolation breach. SPEC §11 explicitly records the known risk of an old response
matching a new document's reused request id as wrong data within one principal.
Repeat initialize resets initialization/id tracking, but the common kernel has
no per-document response epoch. Such corruption depends on a transport delivering
old replies into the new document; a document-bound reply/channel can prevent
that path. T25 reproduces stale port delivery, not a full stale JSON-RPC response
or application data-overwrite scenario. A replacement document receiving a port
can be valid reconnection if ownership and pending work are handled correctly.

## Environment and isolation of the experiment

The standalone [harness](../experiments/android-message-probe/README.md) uses
org.moonpool.messageprobe, separate from T23's installed package. It builds
offline with T23's unchanged Gradle 9.6.1 wrapper/checksum, AGP 9.3.1, Studio JDK
21.0.10, AndroidX WebKit 1.14.0, compile/target SDK 36, Build-Tools 36.0.0 and
probe-only minSdk 31. No new runtime dependency, image or SDK is installed.

The session boots the existing shutdown Pixel 7 Pro AVD separately, without a
data wipe or snapshot save. An already-running user emulator is not an install,
launch, stop or reverse-port target. Explicit ownership/serials stay locally
ignored. Only the newly installed probe package's private report is exported.

Measured configuration: Android 17 / API 37, build CP21.260330.012, arm64-v8a,
actual page size 16384, WebView com.google.android.webview 145.0.7632.218.
HTTPS .test hosts are fixed, local research controls. All non-fixture resource
requests receive a local rejection; no test server, network fallback, cleartext
permission, file access, certificate exception or private engine switch is used.
The custom profile uses public interception only to reproduce the known origin
collapse; it is not a conforming native loader.

The fixed-origin diagnostic observer admits public marker messages from both
test origins so negative metadata can be recorded. The separate pinned listener
and Admission gate reject unauthorized metadata. Neither exposes a capability,
provider, kernel, credential or JavascriptInterface. Saved snapshots and payload
claims are diagnostic observations, not sender authentication.

## Tests and observation matrix

M01–M13 are recorded in the harness README before their native implementation.
An 11-case standalone JVM Admission contract fails before implementation and
passes afterward. It isolates active binding, actual instance, exact origin and
main-frame checks with a valid positive. It does not replace device evidence or
add a JDK requirement to the root TypeScript/Python suites.

| Case | Recorded observation / interpretation |
| --- | --- |
| M01 | WEB_MESSAGE_LISTENER, CREATE_WEB_MESSAGE_CHANNEL, POST_WEB_MESSAGE, WEB_MESSAGE_PORT_POST_MESSAGE, WEB_MESSAGE_PORT_SET_MESSAGE_CALLBACK and WEB_MESSAGE_PORT_CLOSE are supported. The unsupported branch has no fallback; an unsupported provider was not independently tested. |
| M02 | Inline head messages arrive before page-finished with actual main-frame/source metadata; load callbacks do not authorize a sender. |
| M03 | Actual A/B top-frame and loaded same/foreign iframe messages identify their native origin/frame. Payloads deliberately claim a forged origin and main-frame status. |
| M04 | Exact-origin pinned object is absent in the foreign frame and present in the same-origin frame; native gate rejects the latter as a subframe. |
| M05 | A captured second WebView's actual callback metadata routed through A's gate receives wrong-view, even when both load A's origin. This is a labeled host-routing replay, not a claim that WebView itself misroutes callbacks. |
| M06 | Replacement and actual same-URL reload use different reply proxies; late old-proxy replies do not reach the new document in the observed runs. Foreign navigation is rejected by the origin gate; return is separately observed. |
| M07 | Native-created port: three ordered messages and three replies. Callback signature lacks origin/isMainFrame; Java callback wrapper differs from the registration wrapper in real callbacks. |
| M08 | Wrong targetOrigin yields no guest bootstrap or native callback, paired with successful correct-target control. A held origin-only transfer reaches the replacement same-origin document. |
| M09 | Reply-proxy challenge reaches the authenticated current document. Old-document proof fails after replacement/reload; current proof succeeds. The random proof is omitted from the transfer envelope and saved evidence. |
| M10 | A intentionally forwards its port and proof to loaded B iframe. B's listener independently reports native B origin/subframe status, but port callback still admits the valid proof: ongoing provenance gap. |
| M11 | Explicit host retirement rejects both real later listener calls and clearly labeled host-replayed callbacks. Closing twice succeeds; posting after close throws IllegalStateException. No abrupt renderer/peer-loss claim. |
| M12 | Custom hostname rules throw IllegalArgumentException. Scheme-only observer reports moonpool:// for A/B; no custom host passes the expected-origin gate. Both profiles repeat. |
| M13 | Guest-created MessageChannel endpoint is transferred through the main-frame exact-origin listener; one actual port arrives, then ordered messages/replies succeed. Later port messages still lack origin/frame metadata. |

Four final runs retain 44 snapshots: HTTPS first/repeat have 19 each; custom
first/repeat have three each. Each run restarts only the research package.
The final APK and source fingerprints are identical across those reports.
The retained-report verifier passes 175 controls; the native Admission JVM
contract separately passes 11 cases. [Environment and fingerprints](../experiments/android-message-probe/results/environment.json)
also record the tested feature matrix and exact lint warning categories.
Positive controls accompany negative results; absent delivery alone is not an
authentication proof. The current verified scope is one emulator/WebView pairing.

## Instrumentation correction and limits

The first port control incorrectly required callbackPort == registeredPort.
Real AndroidX callbacks provided another wrapper; six round-trip snapshots were
unavailable and the verifier failed. The corrected instrumentation binds the
callback to the native endpoint at registration, sends replies through that
retained endpoint and records wrapper equality only as an observation. No guest
id or claimed origin selects a port binding. The failing records stay locally
separate from final evidence.

Document-scoped proof and label fields are research diagnostics, not proposed
Moonpool protocol members. The experiment deliberately keeps old handles and
permits navigation to expose races. It does not implement automatic production
retirement, all queued native work, renderer termination or credential-bearing
dispatch. The host-replay negatives are distinguished from real platform events.
Codec/coercion behavior, malicious nested JSON and size policy remain T29 work.
Reply-proxy identity numbers are local observation labels, not a wire epoch or
a general API guarantee about object identity across providers.

The native build and lint succeed with 29 warnings and Gradle 10
deprecation notes. The RequiresFeature warnings reflect aggregate feature gating
before constructing any Slot; do not infer independent feature-false coverage.
Warnings about target SDK, JavaScript enablement, experimental UI/resources and
backup configuration do not establish release readiness. No source suppression
or platform security relaxation is used to make the tests pass.

Warning counts: RequiresFeature 16; SetTextI18n 8; OldTargetApi,
GradleDependency, SetJavaScriptEnabled, DataExtractionRules and
MissingApplicationIcon one each. No lint error remains. Root pnpm run check
passes 1134 TypeScript tests / 40 files, nine Python tests, both typechecks,
Biome and both browser example builds, with the known nonblocking Vite warning.

## Reproduction and evidence

Use the harness README's explicit owner setup and commands. Native sources,
assets, Gradle inputs and runner/build hashes are retained with the actual
installed APK hash; private local paths/serials and ephemeral proof values are
excluded. Existing T23/T24 results are not overwritten by these new runs.

```sh
python3 experiments/android-message-probe/test_gate.py --java-home "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
python3 experiments/android-message-probe/verify_results.py experiments/android-message-probe/results
pnpm run check
```

T25 completes experimental evidence, not production authentication approval.
Next: T26's iOS sender/frame/reply/content-world probe; then the existing shared
decision gates. Production hostname selection and the current moonpool origin
requirement remain unchanged until explicit approval.

Primary references: [WebViewCompat](https://developer.android.com/reference/androidx/webkit/WebViewCompat),
[WebMessagePortCompat](https://developer.android.com/reference/androidx/webkit/WebMessagePortCompat),
[JavaScriptReplyProxy](https://developer.android.com/reference/androidx/webkit/JavaScriptReplyProxy).
The pinned 1.14.0 source JAR from Google's Maven repository was also inspected;
it documents the optional MessagePorts argument on the listener object.
