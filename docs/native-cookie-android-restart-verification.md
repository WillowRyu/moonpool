# T28 — Android hasCookies in a new process

Date: 2026-11-03 (Asia/Seoul)
Status: Bounded research complete for the cases below. It does not close T28 or the Android
admission gate. This work concerns SPEC §8 and §9 and does not amend the SPEC, the protocol or
the [accepted admission baseline](native-cookie-store-admission.md).

## Result

iOS's first enumeration in a new process
[falsely reported empty](native-cookie-partition-writer-verification.md), and Android had never
been measured for the same failure. A Profile was written in one process, the app was stopped
with `am force-stop`, and a new process asked that Profile's `hasCookies()`. Each answer was then
compared with the `Cookie` headers an HTTPS server actually received.

**`hasCookies()` gave the correct answer every time, with nothing needed before it.** The iOS
failure did not appear.

| What ran before the first answer | Stores | With cookies | False empty | Healthy store refused |
| --- | --- | --- | --- | --- |
| Nothing beyond obtaining the Profile (`bare`) | 80 | 32 | 0 | 0 |
| A never-loaded WebView on the Profile (`view`) | 80 | 32 | 0 | 0 |
| `setAcceptCookie(false)`, the accepted order (`policy`) | 80 | 32 | 0 | 0 |
| Nothing, as the first cookie question that process ever asked | 10 | 8 | 0 | 0 |

| Store state at the check | Stores | Answer | Server witness |
| --- | --- | --- | --- |
| Cookie-free: created now, or earlier and unused, or holding only localStorage and IndexedDB, or having visited a page that set no cookie | 84 | No cookies | None |
| Cookie gone: write blocked by deny, removed by the server, expired | 36 | No cookies | None |
| Cookie written just before exit, which did not survive | 24 | No cookies | None |
| First-party cookie: denied, never denied, HttpOnly, session | 48 | Cookies | Received |
| Partitioned: first-party, cross-site, under the guest origin, third-party enabled | 48 | Cookies | Received |

Answers matched under deny and one second later in every store, and the first call took at most
71 ms. Local data was not counted as a cookie, and all sentinels survived.

**Witnesses ran under allow, and verification rejects any that did not.** An
[earlier experiment](native-cookie-suppression-verification.md) found that Android's deny policy
withholds retained cookies from requests, so a witness under deny would hide the cookie it is
meant to reveal.

## The two platforms differ

These are measured differences between one configuration of each, and causes are unknown. The SDK
cannot share assumptions about any of them across platforms.

| Behavior | iOS 26.4.1 simulator | Android 17 emulator |
| --- | --- | --- |
| First whole-store question in a new process, nothing before it | **False empty** (38 of 38) | Correct (90 of 90) |
| Deny policy after a process restart | Retained | **Not retained**: reported allow in 96 of 96 previously denied stores |
| Retained cookies under deny | Still sent | Withheld |
| Cross-site `Partitioned` header, no policy call | Not stored | Stored |
| Session cookie after the process ends | Gone | Survived (12 of 12) |
| Cookie written just before exit | Kept only if a deny call followed | Lost either way (24 of 24) |

## What this means for the gate

- The accepted Android order holds on this configuration. The iOS evidence rule stays iOS-only:
  no false empty appeared here, and Android has no second whole-store source to compare with
  `getCookie`, which is URL-scoped.
- **Deny must be installed in every process before any web content loads.** A new process starts
  at allow, so a view loaded before the policy would send retained cookies. Accepted step 3 already
  runs at every admission; this shows why a remembered policy cannot replace it.

Open question for later, not decided here: iOS support is claimed per measured OS version, but
Android WebView updates separately from the OS, so the same approach may not fit.

## What this does not establish

- One emulator and WebView version is not a support matrix or a physical-device result.
- `force-stop` is one way to end a process. Session-cookie survival in particular may depend on it.
  Device reboot, a normal task removal and `CookieManager.flush()` were not measured.
- "No witness" covers the contexts read: first-party and the seeding context.
- Service workers, redirects, long-term use and real Portal teardown are not covered.

This review found the same gap in the iOS evidence, where a process's first store was always
cookie-free. A [later iOS run](native-cookie-first-question-verification.md) measured it, and all 36 stores got the correct verdict.

## Environment, verification and cleanup

API 37 / Android 17, WebView 145.0.7632.218, AndroidX WebKit 1.14.0; existing Gradle 9.6.1 / AGP
9.3.1, compile/target SDK 36. Loopback HTTPS hosts through an owned `adb reverse` mapping. Android
lint has zero errors and 16 recorded warnings.

The [isolated experiment](../experiments/native-cookie-android-restart-probe/README.md) retains 15
reports: seeds [c](../experiments/native-cookie-android-restart-probe/results/android-seed-c.json),
[d](../experiments/native-cookie-android-restart-probe/results/android-seed-d.json) and
[e](../experiments/native-cookie-android-restart-probe/results/android-seed-e.json), checks
[c](../experiments/native-cookie-android-restart-probe/results/android-check-c.json) and
[d](../experiments/native-cookie-android-restart-probe/results/android-check-d.json), and ten
first-call launches such as
[this one](../experiments/native-cookie-android-restart-probe/results/android-first-1.json). They
hold 250 checked stores, 342 seeded stores, 788 server receipt rows and 1817 verifier checks. The
two check reports classify identically. The host suite has 45 tests, written and failing before
the helpers.

One earlier cycle verified cleanly but stays in ignored local results. Reviewing it found that a
process's first question always went to a cookie-free store, so the first-call launches were added,
which changed the app's source. Outcome criteria were written before any collection and did not
change.

Only the dedicated AVD ran, on its fixed serial. The probe app is stopped, the mapping removed, the
emulator stopped and the fixture closed; the adb device list matches its baseline, and the crash
buffer held no fatal entries. The fixture's CA shipped only in this probe APK. The only cookie
removal was the fixture server's own `Max-Age=0` response in one store kind. No native cookie
deletion or import, data wipe, intentional crash or iOS work ran during collection.

Separately, the maintainer asked to clean up the iOS environment. The dedicated simulator was shut
down, the Claude desktop app's simulator panel then booted it again, so the panel was detached and
the simulator shut down again. All 13 simulators are off. The simulator and its data were not
deleted. T28 stays incomplete at 6/44 native tasks. SPEC, production packages, public API, wire
version and release state are unchanged.
