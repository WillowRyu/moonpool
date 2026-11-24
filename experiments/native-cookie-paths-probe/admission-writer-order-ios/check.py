"""Verify the iOS owner-order fixture through the first guest observation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parent
EMPTY = {"policyDisallowed": True, "records": False, "cookies": False, "fixturePresent": False}
PRESENT = {"policyDisallowed": True, "records": True, "cookies": True, "fixturePresent": True}


def admission_window_failures(sample):
    failures = []
    held = {"writerStarts": 0, "guestLoads": 0, "writerResult": "pending", "cookie": EMPTY}
    if sample.get("heldAfterRead") != held:
        failures.append("admissionFirst: pending inspection lacks exclusion evidence")
    if sample.get("heldAtGuest") != dict(held, guestLoads=1):
        failures.append("admissionFirst: guest observation lacks exclusion evidence")
    return failures


def classify(report):
    failures = []
    run = report["run"]
    if (report.get("complete") is not True or report.get("platform") != "ios"
            or report.get("initializedWebKit") is not True or not report.get("release") or not report.get("pid")):
        failures.append("native collection or WebKit initialization did not complete")
    cases = report.get("cases", {})
    groups = {"admissionFirst": "admission", "writerFirst": "writer"}
    if set(cases) != set(groups):
        failures.append("both fresh-store trials are required")
    try:
        identifiers = {UUID(cases.get(case, {}).get("store", "")) for case in groups}
    except (ValueError, TypeError, AttributeError):
        identifiers = set()
    if len(identifiers) != 2 or UUID(int=0) in identifiers:
        failures.append("the identified stores differ from the fixture requirements")
    for case, key in groups.items():
        sample = cases.get(case, {})
        if sample.get("origin") != f"moonpool://com.example.writer-order.{run}.{key}" or sample.get("before") != EMPTY:
            failures.append(f"{case}: the initial origin or empty store differs")

    admission = cases.get("admissionFirst", {})
    failures.extend(admission_window_failures(admission))
    if (admission.get("inspection") != EMPTY or admission.get("writerResult") != "refused-live"
            or admission.get("writerStarts") != 0 or admission.get("guestLoads") != 1
            or admission.get("loader") != 1 or admission.get("after") != EMPTY):
        failures.append("admissionFirst: admitted view or refused write outcome differs")
    if admission.get("guest") != {
        "origin": f"moonpool://com.example.writer-order.{run}.admission", "cookie": "", "marker": f"{run}-admission",
    }:
        failures.append("admissionFirst: the actual guest document did not report")
    if admission.get("events") != [
        "admission:request", "inspection:start", "inspection:empty", "writer:request",
        "admission:load", "guest:observed", "writer:refused-live",
    ]:
        failures.append("admissionFirst: operation order differs")

    writer = cases.get("writerFirst", {})
    if writer.get("heldWhileWriting") != {
        "writerStarts": 1, "writerCallbackCompleted": False, "inspectionStarted": False, "guestLoads": 0,
    }:
        failures.append("writerFirst: admission did not wait for native completion")
    if (writer.get("writerResult") != "stored" or writer.get("writerStarts") != 1
            or writer.get("write") != {"callbackCompleted": True, "cookie": PRESENT}
            or writer.get("inspection") != PRESENT or writer.get("after") != PRESENT
            or writer.get("guestLoads") != 0 or writer.get("loader") != 0):
        failures.append("writerFirst: native write, dual-source inspection or refusal differs")
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
    files = [
        ROOT / "check.py", ROOT / "run_probe.py", ROOT / "Probe.swift", ROOT / "StoreOperations.swift",
        ROOT.parent / "runner.py", ROOT.parent / "profile-retirement-ios/CookiePresence.swift",
        experiments / "native-cookie-admission-probe/ios/AdmissionGate.swift",
    ]
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["build"]["sources"] != source_fingerprints():
        raise RuntimeError("Changed build sources")
    if report["installedArtifactSha256"] != report["build"]["artifactSha256"]:
        raise RuntimeError("Installed simulator app differs")
    failures = classify(report)
    for issue in failures:
        print(issue)
    print(f"{args.report.stem}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
