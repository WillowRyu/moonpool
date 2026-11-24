"""Verify C10 profile retirement and independent WebView continuity."""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESTROYED = {
    "live": False, "loads": 1, "retireCalls": 1, "destroyed": True,
    "attached": False, "groupInactiveAtDestroy": True,
}
REFUSED = {
    "live": False, "loads": 0, "retireCalls": 1, "destroyed": False,
    "attached": False, "groupInactiveAtDestroy": False,
}
PENDING = dict(REFUSED, live=True, retireCalls=0)
LIVE = dict(PENDING, loads=1, attached=True)
EMPTY_COOKIE_STATE = {"accept": False, "present": False}
PRESENT_COOKIE_STATE = {"accept": False, "present": True}
COOKIE_MARKER = "mp_retirement=fixture"


def cleanup_failures(states):
    failures = []
    for name in ("a1", "a2"):
        if states.get(name) != DESTROYED:
            failures.append(f"{name}: admitted WebView teardown differs")
    for name in ("a3", "a4"):
        if states.get(name) != REFUSED:
            failures.append(f"{name}: new admission was not refused before a guest load")
    return failures


def continuity_failures(before, after):
    pulse = after.get("pulse")
    initial_pulse = before.get("pulse")
    if (not before.get("instance") or type(pulse) is not int or type(initial_pulse) is not int
            or pulse <= initial_pulse or after != dict(before, pulse=pulse)):
        return ["b1: original document did not continue"]
    return []


def classify(report):
    run = report["run"]
    profiles = {key: f"profile-retirement-{run}-{key}" for key in ("a", "b")}
    origins = {key: f"https://mp-{run}-{key}.invalid" for key in ("a", "b")}
    failures = []
    if report.get("complete") is not True or not all(report.get(field) for field in ("sdk", "release", "provider", "pid")):
        failures.append("native collection did not complete")
    if report.get("profiles") != {key: {"name": profiles[key], "origin": origins[key]} for key in profiles}:
        failures.append("the assigned profiles or origins differ")
    initial = report.get("initial", {})
    if set(initial) != {"a1", "a2", "b1"}:
        failures.append("initial WebView samples differ")
    for name in ("a1", "a2", "b1"):
        sample = initial.get(name, {})
        document = sample.get("document", {})
        key = name[0]
        if sample.get("state") != LIVE or sample.get("profile") != profiles[key]:
            failures.append(f"{name}: initial attached WebView state differs")
        if (document.get("name") != name or document.get("origin") != origins[key]
                or document.get("marker") != f"{run}-{key}" or document.get("cookie") != ""
                or not document.get("instance") or type(document.get("pulse")) is not int
                or document["pulse"] <= 0):
            failures.append(f"{name}: initial fixture document evidence differs")
    if report.get("writer") != {"callback": True, "state": PRESENT_COOKIE_STATE, "cookie": COOKIE_MARKER}:
        failures.append("the completed native cookie write was not observed under deny")
    if report.get("pending") != {"a3": PENDING, "a1": LIVE, "a2": LIVE}:
        failures.append("a3 was not pending without a load during the live recheck")
    expected_inspections = {name: EMPTY_COOKIE_STATE for name in ("a1", "a2", "b1")}
    expected_inspections["a3"] = PRESENT_COOKIE_STATE
    if report.get("inspections") != expected_inspections:
        failures.append("initial and subsequent native inspection results differ")
    states = report.get("states", {})
    failures.extend(cleanup_failures(states))
    if states.get("b1") != LIVE or report.get("bPolicy") != EMPTY_COOKIE_STATE:
        failures.append("the separate B view or its browser cookie state changed")
    failures.extend(continuity_failures(initial.get("b1", {}).get("document", {}), report.get("continuedB", {})))
    preserved = {
        "profile": profiles["a"], "marker": f"{run}-a", "origin": origins["a"], "nonceMatched": True,
        "unexpectedRequests": [], "cookie": COOKIE_MARKER, "state": PRESENT_COOKIE_STATE,
    }
    if report.get("preservedA") != preserved:
        failures.append("the original A profile's data preservation was not established")
    expected_events = [f"{name}:{event}" for name in ("a1", "a2", "b1") for event in ("inspect", "empty", "load")]
    expected_events.extend(["a:write-complete", "a3:inspect", "a3:pending", "a3:present",
                            "a1:destroy", "a2:destroy", "a3:refuse", "a4:refuse"])
    if report.get("events") != expected_events:
        failures.append("admission, inspection or cleanup order differs")
    if report.get("loader") != ["a1", "a2", "b1"]:
        failures.append("guest document receipts differ")
    if report.get("retiredAccess") != {"a1": False, "a2": False}:
        failures.append("a retired handle can still select its WebView")
    return failures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    experiments = ROOT.parent.parent
    wrapper = experiments / "android-origin-probe"
    android = ROOT / "android"
    files = [
        ROOT / "check.py", ROOT / "run_probe.py", ROOT.parent / "runner.py",
        ROOT.parent / "worker-admission/store.js",
        experiments / "native-cookie-admission-probe/android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java",
        wrapper / "gradlew", wrapper / "gradle/wrapper/gradle-wrapper.jar",
        wrapper / "gradle/wrapper/gradle-wrapper.properties",
        android / "settings.gradle", android / "build.gradle", android / "gradle.properties",
        android / "app/build.gradle", android / "app/src/main/AndroidManifest.xml",
    ]
    files.extend(path for path in (android / "app/src/main/java").rglob("*.java") if path.is_file())
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(files)}


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
    print(f"{args.report.stem}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
