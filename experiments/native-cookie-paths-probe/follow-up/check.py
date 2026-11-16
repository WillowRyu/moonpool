"""Check application evidence against independent server receipts."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROUTES = {
    "direct": ["/static/direct.gif"],
    "approved": ["/static/redirect-approved", "/static/final.gif"],
    "path": ["/static/redirect-path"],
    "other": ["/static/redirect-other"],
    "encoded": ["/static/redirect-encoded"],
}


def classify(report):
    problems = []

    def check(condition, message):
        if not condition:
            problems.append(message)

    check(report.get("complete") is True and not report.get("errors"), "collection did not complete")
    platform = report["platform"]
    run = report["run"]
    origin = "https://mp-" + run + ".invalid" if platform == "android" else "moonpool://com.example.paths." + run
    gate = report.get("admission") or {}
    check(all(gate.get(key) is True for key in ("policyDisallowed", "empty", "afterEmpty")),
          "cookie policy or whole-store witness differs")
    if platform == "ios":
        check(gate.get("sources") == {"records": False, "cookies": False}, "missing two-source iOS cookie evidence")
    guest = report.get("guest") or {}
    check(guest.get("origin") == origin and guest.get("cookie") == "", "guest origin or cookie differs")
    check(guest.get("images") == {
        "direct": "loaded", "approved": "loaded", "path": "blocked", "other": "blocked", "encoded": "blocked",
    }, "guest image outcomes differ")
    receipts = report["receipts"]
    check(all(row["run"] == run and row["tls"] and row["method"] == "GET" for row in receipts),
          "foreign or invalid HTTPS receipt")
    check(all(row["host"] == "localhost" and row["cookie"] == "" and row["authorization"] is None
              for row in receipts), "unexpected host or credentials at the server")
    expected = Counter((case, path) for case, paths in ROUTES.items() for path in paths)
    if platform == "android":
        expected[("worker-control", "/worker-network")] = 1
    observed = Counter((row["case"], row["path"]) for row in receipts)
    for item, count in (expected - observed).items():
        check(False, f"{item}: {count} expected receipt(s) missing")
    for item, count in (observed - expected).items():
        check(False, f"{item}: {count} unexpected receipt(s)")

    worker = report.get("worker") or {}
    if platform == "android":
        check(guest.get("serviceWorker") is True and worker.get("state") == "retained"
              and worker.get("scope") == origin + "/worker/",
              "no worker scope from the Android candidate origin")
        for witness in ("registered", "seedViewDestroyed", "networkBlocked", "retainedRegistration"):
            check(worker.get(witness) is True, f"missing worker {witness} witness")
        check(worker.get("entry") == "cached-worker" and worker.get("loaderEntries") == 0,
              "retained worker did not supply the observed entry")
        check(worker.get("workerFetch") == "blocked", "worker network block did not reject its fetch")
        check(worker.get("admission") == "refused" and worker.get("guestLoads") == 0,
              "known retained worker reached guest admission")
    else:
        check(guest.get("serviceWorker") is False and worker.get("state") == "unsupported",
              "iOS worker capability was not observed as unavailable")
    return problems


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(platform):
    admission = ROOT.parent.parent / "native-cookie-admission-probe"
    files = [ROOT / name for name in ("probe.py", "https_fixture.py", "images.js")]
    files += [ROOT.parent / "runner.py", ROOT.parent / "server.py"]
    if platform == "android":
        files += [ROOT / "worker.js", ROOT / "worker-seed.html", ROOT / "worker-entry.html",
                  admission / "android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java",
                  admission / "android/app/src/main/res/xml/network_security_config.xml",
                  ROOT.parent.parent / "android-origin-probe/gradlew"]
        files += [path for path in (ROOT / "android").rglob("*") if path.is_file()
                  and not {"build", ".gradle"} & set(path.relative_to(ROOT).parts)]
    else:
        files += [ROOT / "ios/Probe.swift"]
    return {os.path.relpath(path, ROOT): sha(path) for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args()
    failed = False
    for path in args.reports:
        report = json.loads(path.read_text())
        assert report["build"]["sources"] == sources(report["platform"]), "Changed sources"
        assert report["installedArtifactSha256"] == report["build"]["artifactSha256"]
        problems = classify(report)
        failed |= bool(problems)
        print(f'{path.stem}: {len(report["receipts"])} HTTPS receipts, {len(problems)} failures')
        for problem in problems:
            print("  " + problem)
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
