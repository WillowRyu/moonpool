# T28 iOS partitioned-cookie and writer-exclusion probe

Bounded iOS follow-up requested on 2026-11-03 after
[the admission verification](../../docs/native-cookie-admission-verification.md)
left two gaps: iOS partitioned-store coverage and real writer/owner exclusion.
Research only: no production SDK, protocol change, cookie deletion or import,
Android work, or crash-control execution. Earlier probes stay byte-for-byte unchanged.

## Retained result

Read the [verification report](../../docs/native-cookie-partition-writer-verification.md).
Seven reports retain 497 server receipt rows and pass 524 verifier checks. In a new
process, the first `getAllCookies` on a store holding cookies returned empty in all 38
stores with no prior step, and was correct in all 54 stores after an awaited policy call,
`fetchDataRecords` or a load. Partitioned cookies are separated by top site and listed.
The deny policy excluded the tested web writers but not native `setCookie`.

## Criteria written before collection

The admission baseline trusts `getAllCookies` to report emptiness. These tests ask
whether that trust holds, so inventory is compared with independent witnesses:
HTTPS server `Cookie` receipts and script reads.

### Partitioned coverage

Fresh identified stores receive a cookie through a response header, `document.cookie`
or `cookieStore`, from a first-party page or a cross-site iframe under an HTTPS or
`moonpool://` top-level page. Each is then read from the same embedding context, a
different top-level context and first-party, before and after the deny policy.

- **False empty:** a witness saw the cookie but inventory never listed it. This
  would mean an empty inventory cannot prove an empty store, so under the accepted
  policy iOS coverage would have to be treated as unknown.
- **Stored evidence** comes only from witnesses. A `Partitioned` header alone proves
  nothing, because the attribute may be ignored or the write may be blocked.
- **Separation** needs a send in the same context and none in the other loaded
  contexts. A context that failed to load establishes nothing.
- A cookie never stored in a context shows only that this configuration could not
  create one there. It does not show that partitioned cookies are always listed.

### Reopening in a new process

Admission normally runs at app start on a store written by an earlier process. A new
process therefore reopens the previous run's stores and enumerates before any page
loads, then reads from the seeding context. A witness without an inventory entry is a
false empty here too. The retained policy value at open is recorded, not assumed.

Added after the first reopen collection showed an empty inventory for retained cookies:
the positive control now requires the cookie to be retained and listed after a load,
because absence at open is the finding under test and cannot also be its control.

### Non-guest warmup strategies

Also added after that collection, to learn whether a gate could make the first
enumeration truthful without loading a guest. Each strategy owns one store seeded with
a first-party and a cross-site partitioned cookie by an earlier process. A new process
applies one strategy, enumerates, then reads from both contexts: nothing, setting or
reading the policy, repeating the enumeration, `fetchDataRecords`, waiting, loading
`about:blank`, loading a local `moonpool://` page, and a real network load as the control.

Two early collections used one store per strategy in a fixed order, which cannot
separate a real ordering guarantee from timing luck. The retained runs therefore use
eight stores for each of the first five strategies, interleaved so the no-action control
also runs late in the process, in two seed/reopen cycles.

### Writer exclusion

Each case begins with an inventory that reports empty while a real writer is active.

- **Held response:** the server parks a `Set-Cookie` response until after the check.
  The policy-free navigation and fetch controls must show the cookie landing, which
  proves the race is real. Variants apply the deny policy or tear down the view before
  release. A deny case counts only if the page confirms the response arrived, and the
  server records whether a torn-down client had already closed.
- **Script burst:** a page writes numbered cookies across the policy change. Names
  added after policy completion show whether completion excludes later writes.
- **Native writes:** whether enumeration observes a queued `setCookie`, and whether
  the deny policy applies to the native API at all.
- **Second handle:** whether another `WKWebsiteDataStore` object for the same
  identifier can read or change the first handle's policy and cookies.

Outcomes are findings and do not fail verification. Missing controls or witnesses
do: the first-party control must be stored and inventoried, the empty control must
stay empty, the cross-site context must be confirmed by `Sec-Fetch-Site`, and the
race control must demonstrate a landing.

## Safety and scope

Use public fixture values and the existing dedicated simulator only, never an
implicit `booted` target. Record every simulator's state first and restore it after.
The fixture's CA is trusted only inside that simulator; host trust and TLS validation
are unchanged. WebKit is initialized with an empty never-loaded view before any
identified store, and every store has a live view before enumeration, so the known
crashing first-call enumeration never runs. An unexpected process exit stops the run
without retry.

From this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
python3 -u -B fixture.py
python3 -u -B run_probe.py --run first --install
python3 -u -B run_probe.py --run repeat
python3 -u -B run_probe.py --run reopen --mode reopen
python3 -u -B run_probe.py --run warmup-seed-a --mode warmup-seed
python3 -u -B run_probe.py --run warmup-a --mode warmup
python3 -u -B run_probe.py --run warmup-seed-b --mode warmup-seed
python3 -u -B run_probe.py --run warmup-b --mode warmup
python3 -B verify_results.py --summary results/*.json
```

`local-results` holds baseline states, the ownership record, build hashes, local
CA/private keys and server receipts; it is not retained in Git. Future runs need
fresh tags and new evidence. Rebuilding changes binary fingerprints, so do not
relabel old observations as new runs.

## Limits

These are one simulator and OS version, not a support matrix or a physical-device
result. The fixture uses loopback hosts, not public sites. Service workers, redirects,
device reboot and ITP behavior over days of use are not covered.
Controlled timing shows that a race exists or was not observed; it cannot prove that
no other interleaving exists.
