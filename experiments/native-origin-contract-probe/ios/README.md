# T28 iOS identified-store and exact-origin research

This simulator-only fixture supplements T24/T26. It is not a production loader,
SDK, supported-OS declaration, credential/authentication flow or SPEC amendment.
The final reports use iPhone 17 Pro / iOS 26.4.1, Xcode 27.0 / simulator SDK 27.0,
with a 17.0 deployment target. API availability is separate from measured support.
No dependency/runtime downloads or global Xcode settings were required.

## Observations and scope

- After preparatory registration, four app processes (`first`/`repeat`, each `seed` then read-only `restart`) retain
  the same exact full id → nonzero UUID mappings and actual persistent identified
  `WKWebsiteDataStore` objects. Same-app second views, reloads, view recreation and
  process restart retain localStorage/IndexedDB and public remote-cookie markers.
- All 15 valid shared input vectors preserve exact `moonpool`/host/port-zero native
  security origins, including numeric, hyphen-only/boundary, 63/64-character labels,
  253/254/1028-character ids and a punycode-shaped label. Eight invalid ids are
  rejected. Three authorityless diagnostics additionally load invalid candidates
  (uppercase/explicit port/percent escape) to retain native normalization/port
  observations (uppercase JS hostname remains mixed-case while native origin is
  lowercase; explicit port is retained; percent escape remains literal); they never receive bridge or registration authority. This finite
  matrix establishes no arbitrary maximum length or universal-id support claim.
- Real same/foreign frames send known ready messages with actual `event.source`
  matching and recorded `event.origin`; successful scheme bytes are retained.
  Same-origin DOM/storage works, foreign-origin DOM/storage access fails. A B-origin
  top document in A's store reads empty localStorage and IndexedDB while A retains
  its markers, distinguishing origin storage keys from store partitioning.
- Actual system-validated `https://example.com/` pages return native HTTP 200 and
  `Example Domain`; native message security origins are independently recorded.
  A/B/host-sentinel partitions see only their own host-only, Secure, persistent
  `t28_remote` cookies, including pre-write snapshots, same-app new views and
  process restart. Public-suffix `Domain=com` and sibling `Domain=other.example.com`
  writes are absent alongside the working host-only control. Only `t28_` cookie
  names/values are retained. The host sentinel is another dedicated identified
  store, never an integrating application's real authentication store.
- The HTTPS experiment measures first-party website-store cookie partitioning at
  one real shared TLS origin. It does **not** observe a server's received Cookie
  headers or prove cross-origin fetch, third-party-cookie/ITP, CORS or authenticated
  service behavior from a local moonpool page. Custom-scheme document.cookie stays
  unavailable; empty custom cookies do not count as successful cookie isolation.
  Android `.invalid` parent-cookie admission is a separate platform experiment.

The pure Swift registration tests were added incrementally through failing
compilation/assertions then minimal implementations. They cover malformed ids,
exact origin checks, duplicate ids/UUIDs, zero UUIDs, allocation collisions,
unsupported API, missing/remapped assignments and complete metadata loss with
retained stores. Unsupported API/store-loss branches are explicitly **modeled**;
no data was erased and no older iOS runtime was exercised. Actual existing store
UUIDs are enumerated before reopening known stores so the public initializer's
automatic empty-store creation cannot mask an observed missing store. A trusted
atomic registry file is paired with a separate persisted id→UUID anchor; known
missing/mismatched assignments fail before guest load. The helper has one serialized
trusted owner, not a multiprocess or power-loss durability guarantee. Total loss
of metadata and every platform store is indistinguishable from a new installation
within this bounded fixture; general recovery/backup remains out of scope.

## Measured startup limitation

The six `startup-*` reports run the same signed executable in fresh processes,
with zero guest document loads. Two cold Swift-async enumerations and two cold
explicit MainActor completion-handler enumerations crash with `EXC_BAD_ACCESS` /
`SIGSEGV` in public store enumeration, `WTF::RunLoop::dispatch` and
`os_unfair_lock_lock`. Each sanitized crash was correlated to that exact launch
process locally; no PID, device id or private crash path is retained.

Two controls create an empty nonpersistent WKWebView, never load it, then enumerate
identified stores successfully. The full research runs use this observed working
order, release the temporary initialization view and load every guest only in its
assigned persistent store. This is engine initialization, not a guest/default-store
fallback. It adds startup/lifecycle overhead for later T53 measurement. This pins
initialization-order sensitivity on this runtime/toolchain; it does not establish
an Apple-required workaround, the underlying root cause, crash recovery, or results
on other iOS releases. The completion-handler result does not support attributing
the failure solely to the Swift async importer.

## Crash-control restriction

The retained cold controls deliberately crash this probe application and can
produce repeated macOS quit dialogs. The maintainer reported those interruptions;
all experiments are stopped and the owned simulator is Shutdown. Use retained
JSON for routine checks. Do not rerun crash-producing startup controls unless
explicitly requested. The commands below document reproduction, not an instruction
to resume stopped experiments. No crash-reporter setting was changed.

## Commands

Run from this directory, using the already installed Xcode tools:

```sh
mkdir -p build
xcrun swiftc Admission.swift StoreRegistry.swift test/ContractTest.swift -o build/contract-tests
build/contract-tests
python3 -B build.py
python3 -B verify_results.py results
python3 -B -m unittest test_verifier.py
```

The runner requires ignored `local-results/simulator.json` containing a **newly
created dedicated** simulator's `owned` id, exact `name` (`Moonpool T28 Origin
Contract`) and a `protected` array containing every pre-existing simulator id.
Save the complete pre-existing `simctl list devices available -j` baseline locally
before creating it. Never reuse a user's device or use the ambiguous `booted`
target. Creation used installed `com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro`
and `com.apple.CoreSimulator.SimRuntime.iOS-26-4`; explicitly boot/install only that
owned id. Record all original states, never wipe data, and shut down only the
owned simulator after the run. Installation identifier is
`org.moonpool.iosorigincontractprobe`.

After installing `build/OriginContractProbe.app` on that explicit owned id, first
run the preparation seed below. It creates/persists the trusted mappings and real
website stores used by subsequent reopen checks. Final retained runs measure
reopening/persistence after registration, not fresh-install atomicity. Preparation
also makes the no-guest initialized controls' enumerated UUID list reproducible.
Then execute these sequentially (each invocation terminates only this probe app first):

```sh
python3 -B run_probe.py --phase seed --run first --output local-results/preparation-seed.json
python3 -B startup_control.py --mode cold --repeat first --output results/startup-cold-first.json
python3 -B startup_control.py --mode cold --repeat repeat --output results/startup-cold-repeat.json
python3 -B startup_control.py --mode cold-callback --repeat first --output results/startup-cold-callback-first.json
python3 -B startup_control.py --mode cold-callback --repeat repeat --output results/startup-cold-callback-repeat.json
python3 -B startup_control.py --mode initialized --repeat first --output results/startup-initialized-first.json
python3 -B startup_control.py --mode initialized --repeat repeat --output results/startup-initialized-repeat.json
python3 -B run_probe.py --phase seed --run first --output results/first-seed.json
python3 -B run_probe.py --phase restart --run first --output results/first-restart.json
python3 -B run_probe.py --phase seed --run repeat --output results/repeat-seed.json
python3 -B run_probe.py --phase restart --run repeat --output results/repeat-restart.json
python3 -B verify_results.py results
python3 -B -m unittest test_verifier.py
```

Final full runs contain 52 named observations and 92 identity rows. Source,
fixture, signed executable and CodeResources hashes accompany each report. The
runner checks the installed executable hash and code signature. The verifier
requires complete expected file sets, exact current source hashes, fresh document
tokens/native reports, actual per-view store UUIDs, working self/loaded foreign
frame controls, pre/post cookie data and independent native HTTPS controls.
Five mutation tests reject copied A evidence presented as B, omitted hashes,
default-store metadata, stale reload documents and unloaded foreign frames.
Preliminary diagnostic reports and full crash files remain ignored locally;
historical T24/T26 sources and evidence are untouched.
