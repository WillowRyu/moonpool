# T28 browser-cookie admission probe

Bounded follow-up requested after acceptance of the admission baseline on
2026-11-03. Research only; no production SDK, protocol change, recovery/deletion
or crash-control execution. Historical probes remain unchanged.

## Retained result

Read the [verification report](../../docs/native-cookie-admission-verification.md).
Four runs retain 48 inventory/admission observations, 76 HTTPS receipt rows,
644 verifier checks and 36 controlled native callback traces (nine distinct
scenarios). Empty-store candidates execute; all observed cookie-bearing cases
refuse without deleting cookies or localStorage/IndexedDB data. Reopening retains
the same partition. iOS's Partitioned-header candidate is detected, but its
partitioned storage semantics and complete backend coverage remain unproven.
The gate is experimental; this does not close full C09 or T28.

From the workspace root:

```sh
python3 -B -m unittest discover -s experiments/native-cookie-admission-probe -p 'test_*.py'
python3 -B experiments/native-cookie-admission-probe/build.py android
python3 -B experiments/native-cookie-admission-probe/build.py ios
python3 -B experiments/native-cookie-admission-probe/verify_results.py experiments/native-cookie-admission-probe/results/*.json
pnpm run check
```

The 14 host tests include Java/JBR and Swift control-trace execution, so those
installed toolchains are needed. They do not boot a device. Four retained reports
are needed for the omitted-source-fingerprint mutation test. Rebuilding may
change signed/binary fingerprints; do not relabel old observations as new runs.

## Bounded collection

`local-results` holds fresh baseline device states, copied ownership records for
the prior session-owned devices, build hashes, local CA/private keys and server
receipts. Runners verify the exact owned identity and installed artifact. No
implicit `booted` target is used. The retained working startup order is kept and
the new probe contains no website-store enumeration or crash-control mode.

Start `python3 -u -B fixture.py` from this directory. The server binds loopback;
its presence-case digest must match the current vector file before collection.
After explicitly booting the owned devices, trust the generated CA only inside
the dedicated iOS simulator with `simctl keychain <owned-id> add-root-cert <ca.pem>`.
Android uses its APK-local CA for localhost/127.0.0.1 and an owned adb reverse.
Neither platform bypasses TLS/hostname validation or changes host-machine trust.

The final runs used these commands from this directory:

```sh
python3 -u -B run_probe.py android --run first --install
python3 -u -B run_probe.py ios --run first --install
python3 -u -B run_probe.py android --run repeat
python3 -u -B run_probe.py ios --run repeat
```

Future runs need fresh tags, explicit bounded device scope and new evidence. The
runner stops on unexpected process exit without retry. At completion terminate
only the owned probe apps, remove their reverse mapping, shut down owned devices
and close the server. Preserve device data/configuration and unrelated services.
Process restart between runs uses new fixture partitions; it is not a durable
registration/restart guarantee. The within-run reopening evidence is separate.

## Criteria written before implementation

- Real native presence checks use the assigned Android Profile's hasCookies or
  iOS identified store's getAllCookies after cookie-deny policy completes.
- Separate fresh partitions hold no cookie, an ordinary cookie, an HttpOnly
  cookie, an off-path cookie, an unrelated-host cookie, and a server-supplied
  Partitioned cookie candidate. Verify successful seeding independently; an
  ignored attribute is not proof of partitioned storage support.
- A URL-scoped/JS read is a diagnostic negative, never the admission authority.
  Cookie presence refuses a candidate guest load; native unknown/failed checks
  refuse as unknown. Cookie-free controls load and execute a guest marker.
- localStorage and IndexedDB public sentinels and existing cookies survive refusal
  and reopening the same native partition. A separate host-control partition
  retains its cookie/policy. No cookie deletion/import API is called.
- The experimental native coordinator serializes same-app admissions. Controlled
  callback traces cover queued A1/A2, present/unknown verdicts retiring the app,
  unaffected B, cancellation, duplicate callbacks, retired/replaced owners,
  explicit retry and cleanup failure/reentrancy. These deterministic traces are
  not measurements of every WebView/network race or production T31 semantics.
- The coordinator and inventory adapter are private research code. Input comes
  from the native owner, never guest app/jar claims. Full C09 containment, complete
  backend inventory coverage, real integration and durability remain separate.

Use public fixtures and owned devices only. Preserve baseline states; do not use
an implicit booted target. Initialize an empty never-loaded WKWebView before
identified stores; never execute the known crashing enumeration controls. An
unexpected process exit stops that platform without automatic retry. Stop owned
devices and fixture servers when collection ends.
