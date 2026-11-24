"""Verify that fixture-native writes and admission share one owner reservation."""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMPTY = {"accept": False, "present": False}
PRESENT = {"accept": False, "present": True}
MARKER = "mp_admission_order=fixture"


def admission_window_failures(sample):
    failures = []
    held = {"writerStarts": 0, "guestLoads": 0, "writerResult": "pending", "cookie": EMPTY}
    if sample.get("heldAfterRead") != held:
        failures.append("admissionFirst: writer escaped while admission was pending")
    if sample.get("heldAtGuest") != dict(held, guestLoads=1):
        failures.append("admissionFirst: writer escaped before the guest observation")
    return failures


def classify(report):
    failures = []
    run = report["run"]
    if report.get("complete") is not True or not all(report.get(field) for field in ("provider", "sdk", "release", "pid")):
        failures.append("native collection did not complete")
    cases = report.get("cases", {})
    groups = {"admissionFirst": "admission", "writerFirst": "writer"}
    if set(cases) != set(groups):
        failures.append("both fresh-profile trials are required")
    for case, key in groups.items():
        sample = cases.get(case, {})
        if (sample.get("profile") != f"admission-writer-order-{run}-{key}"
                or sample.get("origin") != f"https://mp-{run}-{key}.invalid"
                or sample.get("before") != EMPTY):
            failures.append(f"{case}: the initial bound profile, origin or cookie state differs")

    admission = cases.get("admissionFirst", {})
    failures.extend(admission_window_failures(admission))
    if (admission.get("inspection") != EMPTY or admission.get("writerResult") != "refused-live"
            or admission.get("writerStarts") != 0 or admission.get("guestLoads") != 1
            or admission.get("loader") != 1 or admission.get("after") != EMPTY):
        failures.append("admissionFirst: live guest and refused write outcome differs")
    if admission.get("guest") != {
        "origin": f"https://mp-{run}-admission.invalid", "cookie": "", "marker": f"{run}-admission",
    }:
        failures.append("admissionFirst: the actual first guest script did not report")
    if admission.get("events") != [
        "admission:request", "inspection:start", "inspection:empty", "writer:request",
        "admission:load", "guest:observed", "writer:refused-live",
    ]:
        failures.append("admissionFirst: operation order differs")

    writer = cases.get("writerFirst", {})
    if writer.get("heldWhileWriting") != {
        "writerStarts": 1, "writerCallback": None, "inspectionStarted": False, "guestLoads": 0,
    }:
        failures.append("writerFirst: admission did not wait for the native write")
    if (writer.get("writerResult") != "stored" or writer.get("writerStarts") != 1
            or writer.get("write") != {"callback": True, "state": PRESENT, "cookie": MARKER}
            or writer.get("inspection") != PRESENT or writer.get("after") != PRESENT
            or writer.get("guestLoads") != 0 or writer.get("loader") != 0):
        failures.append("writerFirst: native write, presence check or refusal differs")
    if writer.get("afterCookie") != MARKER:
        failures.append("writerFirst: marker readback after refusal differs")
    if writer.get("events") != [
        "writer:request", "writer:start", "admission:request",
        "writer:callback", "writer:readback", "inspection:start", "inspection:present", "admission:refuse",
    ]:
        failures.append("writerFirst: operation order differs")
    return failures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    experiments = ROOT.parent.parent
    wrapper = experiments / "android-origin-probe"
    android = ROOT / "android"
    files = [
        ROOT / "check.py", ROOT / "run_probe.py", ROOT.parent / "runner.py",
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
