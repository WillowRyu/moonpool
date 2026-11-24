"""Verify CSP and cold admission observations from the Android probe."""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ("managed", "retained", "unknown", "unconfirmed")
POLICY = "worker-src 'none'"
SCOPES = {"main": "/", "frame": "/child/"}
DOCUMENTS = ("/entry", "/child/frame")


def origin_for(run, case):
    return f"https://mp-{run}-{case}.invalid"


def profile_for(run, case):
    return f"worker-prevention-{run}-{case}"


def worker_src_violation(origin, path):
    return {
        "directive": "worker-src",
        "disposition": "enforce",
        "blockedURI": origin + path + "worker.js",
    }


def policy_failures(origin, page, *, guarded, frame_event_withheld=False):
    failures = []
    attempts = page.get("attempts", {})
    for name, path in SCOPES.items():
        attempt = attempts.get(name, {})
        if attempt.get("origin") != origin:
            failures.append(f"{name}: registration attempt lacks the bound origin")
        if guarded:
            error = attempt.get("error")
            if attempt.get("outcome") != "rejected" or not isinstance(error, str) or not error:
                failures.append(f"{name}: registration was not rejected")
            if name == "frame" and frame_event_withheld:
                if "violation" in attempt:
                    failures.append("frame: the enforcement event was not withheld")
            elif attempt.get("violation") != worker_src_violation(origin, path):
                failures.append(f"{name}: enforcing worker-src violation missing")
        elif attempt.get("outcome") != "activated" or attempt.get("scope") != origin + path:
            failures.append(f"{name}: control did not activate the expected registration")
    expected = [] if guarded else [origin + path for path in SCOPES.values()]
    if page.get("scopes") != expected:
        failures.append("observed registration scopes differ")
    return failures


def view_failures(origin, view, *, guarded, frame_event_withheld=False):
    page = view.get("guest") or {}
    failures = policy_failures(origin, page, guarded=guarded, frame_event_withheld=frame_event_withheld)
    if frame_event_withheld and view.get("withheldFrameEvent") != worker_src_violation(origin, SCOPES["frame"]):
        failures.append("the withheld frame event differs")
    if page.get("origin") != origin or page.get("entryScript") is not True:
        failures.append("native loader's entry script was not observed")
    if guarded and ("controller" not in page or page["controller"] is not None):
        failures.append("guarded document did not establish an empty controller")
    if view.get("documentPolicies") != dict.fromkeys(DOCUMENTS, POLICY if guarded else ""):
        failures.append("entry and frame response headers differ")
    expected_requests = [] if guarded else sorted(path + "worker.js" for path in SCOPES.values())
    if sorted(view.get("workerRequests", [])) != expected_requests or "workerRequests" not in view:
        failures.append("native worker script requests differ")
    return failures


def admission_failures(run, case, check):
    failures = []
    managed = case == "managed"
    origin = origin_for(run, case)
    if check.get("profile") != profile_for(run, case) or check.get("profilePresent") is not True:
        failures.append("the existing profile was not opened")
    if check.get("cookieDeny") is not True or check.get("cookiePresent") is not False:
        failures.append("admission lacks cookie-deny and empty-store evidence")
    if check.get("provenance") is not managed or check.get("verdict") != ("empty" if managed else "unknown"):
        failures.append("ownership evidence or native verdict differs")
    if check.get("events") != ["policy", "decision", "guest" if managed else "refuse"]:
        failures.append("policy, decision and load events differ")
    if type(check.get("guestLoads")) is not int or check["guestLoads"] != int(managed):
        failures.append("guest load count differs")
    if check.get("marker") != f"{run}-{case}" or check.get("markerOrigin") != origin:
        failures.append("stored marker did not survive")
    if managed:
        failures.extend(view_failures(origin, check, guarded=True))
    elif check.get("guest") is not None or check.get("documentPolicies") != {} or check.get("workerRequests") != []:
        failures.append("a refused profile received guest content")
    return failures


def seed_failures(run, seed):
    if seed.get("complete") is not True or seed.get("phase") != "seed" or seed.get("run") != run:
        return ["seed process did not complete"]
    failures = []
    profiles = seed.get("profiles", {})
    if set(profiles) != set(CASES):
        failures.append("seed profiles differ")
    for case in CASES:
        entry = profiles.get(case, {})
        origin = origin_for(run, case)
        if (entry.get("profile") != profile_for(run, case) or entry.get("created") is not True
                or entry.get("marker") != f"{run}-{case}" or entry.get("markerOrigin") != origin
                or entry.get("cookieDeny") is not True):
            failures.append(f"seed/{case}: fresh profile or marker evidence differs")
        if entry.get("provenance") is not (case == "managed"):
            failures.append(f"seed/{case}: unexpected provenance record")
        if case != "unknown":
            issues = view_failures(origin, entry, guarded=case != "retained", frame_event_withheld=case == "unconfirmed")
            failures.extend(f"seed/{case}: {issue}" for issue in issues)
    return failures


def classify(report):
    run = report["run"]
    seed = report["seed"]
    checks = report["checks"]
    failures = seed_failures(run, seed)
    if [check.get("case") for check in checks] != list(CASES):
        failures.append("cold cases differ")
    pids = [sample.get("pid") for sample in (seed, *checks)]
    if any(type(pid) is not int or pid <= 0 for pid in pids) or len(set(pids)) != len(pids):
        failures.append("each phase requires a different app process")
    configurations = [
        (sample.get("sdk"), sample.get("release"), sample.get("provider"))
        for sample in (seed, *checks)
    ]
    if not all(configurations[0]) or any(config != configurations[0] for config in configurations):
        failures.append("the operating system or WebView provider changed")
    for check in checks:
        case = check.get("case")
        if check.get("complete") is not True or check.get("phase") != "check" or check.get("run") != run:
            failures.append(f"{case}: cold process did not complete")
        if case in CASES:
            failures.extend(f"{case}: {issue}" for issue in admission_failures(run, case, check))
    return failures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    experiments = ROOT.parent.parent
    worker_admission = ROOT.parent / "worker-admission"
    gate = experiments / "native-cookie-admission-probe/android/app/src/main/java/org/moonpool/cookieadmission"
    files = [
        ROOT / "check.py",
        ROOT / "run_probe.py",
        ROOT / "register.js",
        worker_admission / "store.js",
        worker_admission / "worker.js",
        gate / "AdmissionGate.java",
        ROOT.parent / "runner.py",
        experiments / "android-origin-probe/gradlew",
        experiments / "android-origin-probe/gradle/wrapper/gradle-wrapper.properties",
    ]
    files.extend(path for path in (ROOT / "android").rglob("*") if path.is_file()
                 and not {"build", ".gradle"} & set(path.relative_to(ROOT).parts))
    return {os.path.relpath(path, ROOT): sha(path) for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["build"]["sources"] != source_fingerprints():
        raise RuntimeError("Changed build sources")
    if report["installedArtifactSha256"] != report["build"]["artifactSha256"]:
        raise RuntimeError("Installed APK differs")
    failures = classify(report)
    for issue in failures:
        print(issue)
    print(f"{args.report.stem}: {len(report['checks'])} cold admissions, {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
