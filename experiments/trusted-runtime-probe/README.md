# T27 trusted runtime compatibility probe

Experimental evidence for the accepted runtime/ownership decision, not a native
SDK implementation or new protocol. Baseline: published b4b7721. Preserve
the earlier probes and the intentionally red 0.1 generation regression suite.

## Criteria before implementation

| Case | Required evidence |
| --- | --- |
| R01 | Bundle the real existing protocol/client/host code without modifying it; record source/artifact/tool hashes. No replacement native dispatcher. |
| R02 | Execute the same bundle in DOM-free JavaScriptCore on the owned iOS simulator and an app-owned JavaScriptSandbox isolate on the separately owned Android emulator, if supported. Record unsupported rather than installing an implicit fallback. |
| R03 | Real initialize/ping/profile projection/storage/permission outcomes using explicitly labeled public provider test doubles. Native provider integration remains T42/T43. |
| R04 | Promise, Map, Reflect, descriptors, JSON inspection and finite-value validation work without requiring window/document in the kernel. |
| R05 | Client timeout, timer cancellation and microtask ordering work with installed-runtime primitives/adapters; no claim about suspended/background timers. |
| R06 | A separate guest realm cannot see the trusted probe's kernel control globals. Realm separation is not a universal process-security guarantee. |
| R07 | Native-created runtime owners serialize calls, retire terminally and fence a queued old-owner callback from replacement runtimes. No guest id selects a native owner. |
| R08 | Native bootstrap/control values are public JSON text snapshots; no credentials or live JS/application objects cross the guest boundary. |
| R09 | Native app owns the packaged host bundle. It never loads guest/remote code into the trusted runtime. Fixed test URLs are controls, not adopted production origins. |
| R10 | Record actual threads/actors and ownership/lifetime: runtime/HostConnection per Portal; retained app registry/providers outside that disposable owner in the proposed model. |
| R11 | State limits: test-double storage/snapshot seeding does not establish real provider durability, native codec conformance, renderer-loss policy or pool capacity. |
| R12 | Present facade/runtime options and concrete tradeoffs for maintainer input; T27 stays pending until the host/runtime model is explicitly accepted. |

Node VM contract checks run before native harnesses. Both engine candidates need
host-supplied scheduler primitives. The probe's poll-driven timer/microtask/error
sink demonstrates compatibility and ownership only; it is not an adopted
production polling/diagnostic policy. Kernel packages retain their existing
platform boundary and no runtime dependency. The Android experiment pins Google's
JavaScriptEngine 1.1.1; runtime support must be checked first. Private host WebViews
and RN runtimes remain comparison options, with view cost/framework dependencies
explicit; no automatic fallback is assumed. Real native provider integration,
wire/codec validation and performance/background behavior remain later gates.

## Reproduction and retained observations

From the workspace root using Node 22.19.0 / pnpm 11.1.3:

```sh
python3 experiments/trusted-runtime-probe/build_bundle.py
pnpm exec vitest run --config experiments/trusted-runtime-probe/vitest.config.ts
pnpm exec tsc --noEmit -p experiments/trusted-runtime-probe/tsconfig.kernel.json
python3 experiments/trusted-runtime-probe/verify_results.py experiments/trusted-runtime-probe/results
```

The first command uses the existing workspace Vite dependency. The Node VM tests
require the generated bundle; it is ignored along with native build products,
generated Android assets, logs and local device ownership records. Root Vitest
discovery remains unchanged. The separate generation-contract probe stays red.

Native harnesses have their own `ios/build.py`, `ios/run_probe.py`,
`android/build.py` and `android/run_probe.py`. Read the scripts before a new run;
run drivers offer `--help`. iOS builds use the installed Xcode SDK and ad-hoc simulator signing. Android
reuses the T23 wrapper and installed SDK/JDK, building offline by default; the
initial pinned Google dependency resolution used `--online`. Build the platform
harnesses sequentially because they regenerate the same common output directory.
Run drivers require ignored `local-results` ownership records before targeting a
device; never populate them by claiming a pre-existing user device. No boot,
installation or native rerun is necessary to verify retained results.

Four retained first/repeat reports cover three owners per platform/run: first A,
recreated A seeded from a native-owned public fixture snapshot, and independent B.
All 180 common-kernel vectors and 120 report/source checks pass; two Node VM tests
pass. The verifier checks report structure, all 15 vectors per owner, scheduler
cleanup, private diagnostic counts, native executors, old-owner callback drops
and current native/common source hashes. It does not replace a new device run.
Native build metadata records bundle, scheduler, platform source and artifact
hashes; `results/environment.json` records tools, lint warnings and cleanup.

Only owned probe apps/devices were started/stopped. Pre-existing Android devices
and other simulator states were preserved. Engine crashes, background execution,
real providers/guest transport, resource limits and RN/Flutter bindings remain
unverified. See [the evidence report](../../docs/trusted-runtime-verification.md)
and [accepted ADR 0025](../../docs/adr/0025-own-native-kernels-in-private-runtimes.md).
