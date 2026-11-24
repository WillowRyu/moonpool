"""Verify cold-process worker evidence and the resulting guest admission."""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ("root", "offpath", "used", "fresh", "opaque")
SEEDED = ("used", "root", "offpath")


def origin(run, case):
    return f"https://mp-{run}-{case}.invalid"


def partition(run, case):
    return f"worker-admission-{run}-{case}"


def scope(run, case):
    if case == "root":
        return origin(run, case) + "/"
    if case == "offpath":
        return origin(run, case) + "/outside/"
    return None


def classify(report, *, expect_unavailable=False):
    problems = []

    def check(ok, message):
        if not ok:
            problems.append(message)

    run = report["run"]
    seed = report["seed"]
    checks = report["checks"]
    check(seed.get("phase") == "seed" and seed.get("complete") is True and seed.get("run") == run,
          "seed collection did not complete")
    seeded = {row["case"]: row for row in seed["profiles"]}
    check(set(seeded) == set(SEEDED) and len(seed["profiles"]) == len(SEEDED), "wrong seed cases")
    for case, row in seeded.items():
        check(row["profile"] == partition(run, case), f"{case}: wrong seed profile")
        check(row["seed"] == {"origin": origin(run, case), "data": run, "scope": scope(run, case)},
              f"{case}: storage or active registration was not seeded")
    observed = {row["case"]: row for row in checks}
    check(set(observed) == set(CASES) and len(checks) == len(CASES), "missing or duplicate check cases")
    pids = [seed["pid"], *(row["pid"] for row in checks)]
    check(all(isinstance(pid, int) and pid > 0 for pid in pids) and len(set(pids)) == len(pids),
          "seed and each first inspection must run in separate processes")

    for case, row in observed.items():
        key = "used" if case == "opaque" else case
        base = origin(run, key)
        worker = scope(run, key)
        valid_origin = case != "opaque"
        check(row.get("complete") is True and row.get("phase") == "check" and row.get("run") == run,
              f"{case}: check did not complete")
        check(row.get("profile") == partition(run, key) and row.get("profilePresent") is (key != "fresh"),
              f"{case}: profile did not have the expected retained identity")
        check(row.get("policy") == {"cookieDeny": True, "workerNetworkBlocked": True, "browserNetworkBlocked": True}
              and row.get("cookiePresent") is False, f"{case}: missing pre-load policy or cookie evidence")
        proof = row.get("proof") or {}
        check(proof.get("source") == "host" and row.get("nonceMatches") is True
              and row.get("inspectionRequests") == [], f"{case}: substituted or network-backed inspection page")
        expected_origin = base if valid_origin else "null"
        check(proof.get("origin") == expected_origin and proof.get("contextOrigin") == expected_origin,
              f"{case}: unexpected inspection origin")
        if valid_origin:
            if expect_unavailable:
                for method in ("inline", "frame"):
                    attempt = proof.get(method) or {}
                    check(attempt.get("contextOrigin") == base and attempt.get("api") is True
                          and attempt.get("error", "").startswith("InvalidStateError:"),
                          f"{case}: missing {method} enumeration rejection")
            else:
                check(proof.get("api") is True and not proof.get("error")
                      and proof.get("scopes") == ([worker] if worker else []),
                      f"{case}: worker enumeration differs")
            if case != "root":
                check("controller" in proof and proof["controller"] is None, f"{case}: unexpected controller")
            check(proof.get("data") == (None if case == "fresh" else run), f"{case}: stored data proof differs")
        expected = "unknown" if expect_unavailable or not valid_origin else ("present" if worker else "empty")
        check(row.get("verdict") == expected, f"{case}: expected {expected}, received {row.get('verdict')}")
        admitted = expected == "empty"
        check(row.get("events") == ["policy", "inspect", "verdict", "guest" if admitted else "refuse"],
              f"{case}: policy, inspection and admission order differs")
        expected_guest = {"marker": "guest", "origin": base} if admitted else None
        check(row.get("guestLoads") == int(admitted) and row.get("guest") == expected_guest,
              f"{case}: guest execution differs from the verdict")
        diagnostic = row.get("diagnostic")
        if worker:
            check(diagnostic and diagnostic.get("title") == "c09-worker" and diagnostic.get("pageScriptsEnabled") is False,
                  f"{case}: regular-navigation worker control differs")
        else:
            check(diagnostic is None, f"{case}: unexpected regular-navigation control")
    return problems


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    gate = ROOT.parent.parent / "native-cookie-admission-probe"
    files = [ROOT / name for name in ("run_probe.py", "check.py", "seed.js", "worker.js", "inspect.js", "store.js")]
    files.append(ROOT.parent / "runner.py")
    files.append(ROOT.parent.parent / "android-origin-probe/gradlew")
    files.append(gate / "android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java")
    files.extend(path for path in (ROOT / "android").rglob("*") if path.is_file()
                 and not {"build", ".gradle"} & set(path.relative_to(ROOT).parts))
    return {os.path.relpath(path, ROOT): sha(path) for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--expect-unavailable", action="store_true")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    assert report["build"]["sources"] == sources(), "Changed sources"
    assert report["installedArtifactSha256"] == report["build"]["artifactSha256"]
    failures = classify(report, expect_unavailable=args.expect_unavailable)
    for issue in failures:
        print(issue)
    mode = "retained unavailable-observation" if args.expect_unavailable else "worker-evidence hypothesis"
    print(f"{args.report.stem}: {len(report['checks'])} cold inspections, {len(failures)} {mode} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
