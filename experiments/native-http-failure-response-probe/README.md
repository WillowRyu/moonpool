# T28 `failureResponse` measurement

Bounded experiment requested by the maintainer on 2026-11-05. The [broker report](../../docs/native-http-broker-verification.md) found that
after the accepted iOS `Basic` 401 resend, the jar keeps the second response's cookie while Android keeps the first, because the
first 401 reaches the challenge handler and never the response callback. This asks whether the handler can read that first
response's `Set-Cookie` through `URLAuthenticationChallenge.failureResponse`. Research only, iOS only, separate from the broker probe so
its evidence stays valid: no broker, cookie jar, public API, SPEC or protocol change.

## Retained result

Read the [verification report](../../docs/native-http-failure-response-verification.md). `failureResponse` carried the first attempt's
`Set-Cookie` in all 8 `Basic` cases in both runs, so it is usable under the criteria below. Nothing was applied to the broker.

## Criteria written before collection

The session is configured like the research broker's. The fixture serves a different response per arrival, and its receipts say what
each arrival was served, so the app's report is checked against an independent witness.

**Usable** means that in every `Basic` case and every run, the first challenge callback has a `failureResponse` with status 401 and a
`Set-Cookie` equal to what the fixture served on arrival 1, folded with `, ` as `URLSession` shows it, and no `Set-Cookie` when arrival 1
served none. Any other result is **not usable**, and it is a finding rather than a failed verification.

| Case | What it adds |
| --- | --- |
| `basic-cookie-per-attempt` | Tells the two attempts apart by value |
| `basic-first-attempt-only`, `basic-second-attempt-only` | A cookie on only one attempt, including one iOS would otherwise lose |
| `basic-two-fields` | Several fields, and whether they fold the same way as a delivered response |
| `basic-no-cookie` | The empty answer must stay empty |
| `basic-post`, `basic-preset-authorization` | A request with a body, and with a guest's own `Authorization` |
| `basic-default-handling` | `.performDefaultHandling` instead of the broker's `.rejectProtectionSpace` |
| `control-plain`, `control-bearer`, `control-no-challenge` | One arrival and no challenge. A failed control rejects the report |

## Rerun

Retained results in `results/` need no device. To collect again, from this directory:

```sh
python3 -B -m unittest discover -s . -p 'test_*.py'
python3 -B build.py
```

Start `fixture.py`, write `local-results/owner.json` for the dedicated simulator only, then run `run_probe.py --run first --install` and
`--run repeat`, and check them with `verify_results.py --summary results/*.json`. A run tag can be used once.

Nothing is added to a device trust store. An unexpected process exit stops the run without retry.
