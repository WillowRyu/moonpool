# T24 iOS origin probe

Standalone platform research, not a Moonpool native SDK or a new dispatcher.
T23's local work and recorded Android evidence are preserved. The pure
TypeScript kernel and normative origin contract remain unchanged.

## Criteria recorded before implementation

Use T22's P01–P10 criteria with the same public app ids/markers as T23. Measure
WKURLSchemeHandler delivery at moonpool://com.example.probe.a/b, including actual
page origin, native frame-origin metadata where available, localStorage,
IndexedDB, cookies, bundled fetch, loaded self/foreign frame access, navigation,
missing/escape resources and process lifetime. Record supported/failed/unavailable
facilities separately. No private scheme registration or security preference.

Use a shared default persistent WKWebsiteDataStore for both apps in the probe,
so per-origin isolation is measured rather than manufactured by per-app stores.
App data belongs only to this new research app on its dedicated simulator.
The loopback HTTP control uses localhost:8878 for A and 127.0.0.1:8879 for B;
different hosts permit meaningful cookie partition checks as well as origin
checks. The CORS/external control is 127.0.0.1:8877. No external network host,
TLS bypass or handler for WebKit-owned HTTP(S) schemes is needed.

Also verify scheme-task start/stop bookkeeping with an explicitly cancelled
delayed load. No data/finish callbacks may be sent after stop. Native-owned
evaluateJavaScript polling collects public diagnostic data, not authenticated
guest messages. Actual bridge/reply/content-world authentication remains T26.

## Simulator ownership

Before setup, record existing booted device ids locally. Create a separate
Moonpool T24 Origin Probe device with the installed iOS 26.4 runtime and iPhone
17 Pro device type. Every mutating simctl command must name this new owned id;
never use booted, all, erase or the maintainer's existing device as a target.
Keep ids in ignored local-results only. Shut down the owned device afterward;
retain its configuration for reproduction and verify the existing device state.

## Build and execution

Use Xcode 26.4.1's bundled swiftc, the installed iOS Simulator SDK 26.4 and
arm64 simulator target. build.py creates a minimal local .app and ad-hoc signs
it for this simulator; no project generator, account, provisioning profile,
package dependency, OS runtime download or production artifact is required.
The minimum target 17.0 is a probe build setting, not a product support promise.

The fixture script derives its base from the T23 public fixtures while adapting
only profile URLs/report names and adding cancellation observation. Record both
the base hash and final source hashes; never rewrite the Android evidence.
Run seed/restart phases for custom and HTTP control plus an offline control.
Retain JSON/error/navigation/resource evidence and the tested build fingerprint,
without personal paths, device ids or unrelated app/system information.

## Cleanup while T24 is paused

The shared host-side HTTP Module is in experiments/probe_support. Run
pnpm run test:probes from the repository root: tests verify public CORS/control
responses and app-root confinement with temporary files/free ports. Absolute
paths and symlinks escaping the selected root were reproduced before the fix.
These tests do not boot/install/launch a simulator app or complete T24.
