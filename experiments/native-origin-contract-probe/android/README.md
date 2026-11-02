# T28 Android supplementary origin/profile probe

Bounded research for proposed ADR 0026, not a native SDK or a SPEC amendment.
All data are public `t28_` sentinels. Existing T23/T25 experiments are unchanged.
This probe has no bridge, JavascriptInterface, private API, TLS bypass, credentials,
file/content loading, or remote content distribution.

## Retained observations

Four final runs (`t28-first` and `t28-repeat`, each seed then process restart)
contain 44 raw snapshots. Android 17/API 37, Google WebView 145.0.7632.218 and
AndroidX WebKit 1.14.0 report actual `MULTI_PROFILE` support. See
[`results/environment.json`](results/environment.json) for actual tools and limits.

- The full SHA-256 → lowercase, unpadded RFC 4648 base32 mapping produces exact
  `https://mp-<52 characters>.invalid` origins and `moonpool-v1-<key>` profiles.
  The pure JVM suite independently checks all 23 shared reference vectors,
  including numeric ids, hyphen-only/leading/trailing labels, 63/64-character
  labels, and 253/254/1028-character ids. Rejected ids use SPEC's exact grammar.
  Actual loaded WebViews exercise ordinary A/B ids; unusual ids are mapping/URI
  tests, not extra WebView/device admission measurements. Version is absent from
  the mapping input; no installed-app upgrade cycle is claimed.
- Every guest view selects its exact nondefault Profile before settings,
  clients, cookies, or loading. Same-A views share localStorage, IndexedDB and
  host-only persistent cookies; `WebView.reload()`, view destruction/recreation,
  and `am force-stop` followed by a fresh Activity/process retain them. Registry
  metadata is persisted and checked against the provider's existing profiles.
- A and B have different actual loaded HTTPS origins. Both same-origin and
  cross-origin frames send a ready marker; the receiver checks actual
  `event.source` and `event.origin`. Same-origin DOM/localStorage reads work;
  the loaded foreign DOM throws `SecurityError`. The foreign localStorage read
  is not independently reached after that DOM exception. A separate B-origin
  page within A's Profile has empty localStorage/IndexedDB/cookies while A's
  sentinel remains present and B's own Profile contains B's sentinel. This
  separates origin isolation from profile isolation.
- Working `document.cookie` host-only `Secure; Max-Age=86400` controls persist.
  `Domain=invalid` and the other app's exact host are rejected. Native
  profile-specific CookieManager reads corroborate both the working cookies and
  same-profile sibling-origin negatives.
- Separate A/B/host-sentinel Profiles actually load `https://example.com/`
  through normal network/TLS WebView navigation. `Example Domain`, the actual
  HTTPS origin and secure-context status are required positive controls.
  First-party public marker cookies remain distinct before and after writes,
  in a second read-only A view, and across process restarts. Only `t28_` cookies
  are retained from JS or native CookieManager. No remote interception/control
  server was used. This proves first-party cookie-store partitioning at a real
  remote origin; it does not prove server-received Cookie headers, CORS or
  third-party/fetch cookie policy.
- This provider accepts `setProfile` after `getSettings` alone. Calling
  `getProfile` first fixes the prior/default profile; subsequent `setProfile`
  throws `IllegalStateException` without loading a guest. Missing feature,
  missing registration/profile, remapping, and forced collision/duplicate
  assignment cases are pure JVM admission simulations. No unsupported real
  provider was tested and these tests do not establish a production registry.

The local interceptor deliberately resolves both app hosts for loaded foreign
frames and the within-A-profile B-origin control. That is a **test-only resolver
exception**, not compliant loader containment. T38/T40/T44 retain loader,
per-message admission, navigation and other production security work. This
research does not establish broad provider support, numeric resource limits,
reboot/reinstall/backup durability or profile erasure policy.

## Verification and reproduction

From this directory:

```sh
python3 test_contract.py
python3 build.py
python3 verify_results.py results
python3 -m unittest test_verifier.py
```

`test_contract.py` uses the Android Studio bundled JBR unless `JAVA_HOME` is set.
The build reuses `../../android-origin-probe/gradlew` (Gradle 9.6.1, unchanged),
AGP 9.3.1, compile/target SDK 36 and build-tools 36.0.0. Official dependency
resolution is allowed. No root dependency or historical wrapper is updated.
Android lint passes with zero errors; retained warnings concern pinned target/
dependency versions, feature-check flow across methods (`onCreate` gates before
all guest construction), deliberate JavaScript fixtures, and standalone app
backup/icon metadata. Biome passes the Android-owned assets/results.

Native collection requires an explicit session-owned AVD record in ignored
`local-results/owned-device.json`: `avd`, `serial`, and ownership context. Inspect
`adb devices -l` and AVD state first. Start only a shutdown `Pixel_7_Pro` on an
explicit free emulator port, with `-no-snapshot-save`; never wipe/reset it or
select an arbitrary attached device. `run_probe.py` additionally checks the
record's AVD name against `adb -s <owned serial> emu avd name` before use.

```sh
python3 run_probe.py --tag t28-first --phase seed --install
python3 run_probe.py --tag t28-first --phase restart
python3 run_probe.py --tag t28-repeat --phase seed
python3 run_probe.py --tag t28-repeat --phase restart
python3 verify_results.py results
```

The runner compares the installed APK's actual SHA-256 with the built artifact
before every run, then force-stops only this probe package. It never resets
package/profile/AVD data. Public exploratory sentinels preceded the first
retained seed; initial `before` observations preserve them. No data clears occur
between the four retained runs. Stop only the emulator started for this session.
Local machine paths, emulator serial and process ownership remain ignored.

The verifier independently recalculates SHA-256/base32, requires every positive
and negative raw sample, both frame-ready origins, exact profile assignments,
pre-write remote isolation, restart data, explicit early-use rejection, and
source/asset/wrapper/vector fingerprints. Seven mutation tests reject missing
controls, foreign pre-write cookies, wrong profiles, unloaded foreign frames,
lost IndexedDB state and altered source digests. Build metadata fingerprints
include verifier/runner/tests themselves; finish all source edits and formatting
before rebuilding/recollecting. Result-file whitespace is outside source hashes.

The test-first sequence began with a failing missing mapping implementation,
then mapping GREEN; missing admission methods RED → GREEN; a hyphen-only-label
regression RED → exact SPEC grammar GREEN. Missing final evidence made the
verifier suite RED before collection; the final raw observations and mutation
controls now pass. These are experiments against a proposed contract; final
contract approval remains separate.

## Primary API references

- [WebViewCompat.setProfile](https://developer.android.com/reference/androidx/webkit/WebViewCompat#setProfile(android.webkit.WebView,java.lang.String))
- [Profile and its profile-specific services](https://developer.android.com/reference/androidx/webkit/Profile)
- [ProfileStore](https://developer.android.com/reference/androidx/webkit/ProfileStore)
