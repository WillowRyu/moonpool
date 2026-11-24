"""Verify shared-store retirement and independent WKWebView continuity."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from posixpath import relpath as archive_relpath
from uuid import UUID
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
RELEASED = {
    "live": False, "loads": 1, "retireCalls": 1, "released": True,
    "attached": False, "groupInactiveAtRelease": True,
}
REFUSED = {
    "live": False, "loads": 0, "retireCalls": 1, "released": False,
    "attached": False, "groupInactiveAtRelease": False,
}
PENDING = dict(REFUSED, live=True, retireCalls=0)
LIVE = dict(PENDING, loads=1, attached=True)
EMPTY_COOKIE_STATE = {"policyDisallowed": True, "records": False, "cookies": False, "fixturePresent": False}
PRESENT_COOKIE_STATE = {"policyDisallowed": True, "records": True, "cookies": True, "fixturePresent": True}


def retirement_failures(states):
    failures = []
    for name in ("a1", "a2"):
        if states.get(name) != RELEASED:
            failures.append(f"{name}: admitted WebView retirement differs")
    for name in ("a3", "a4"):
        if states.get(name) != REFUSED:
            failures.append(f"{name}: new admission was not refused before a guest load")
    return failures


def cookie_verdict(sample):
    records = sample.get("records")
    cookies = sample.get("cookies")
    if (sample.get("policyDisallowed") is not True
            or type(records) is not bool or type(cookies) is not bool or records != cookies):
        return "unknown"
    return "present" if records else "empty"


def classify(report):
    failures = []
    run = report["run"]
    if (report.get("complete") is not True or report.get("platform") != "ios" or report.get("initializedWebKit") is not True
            or not all(report.get(key) for key in ("release", "pid"))):
        failures.append("native collection or WebKit initialization did not complete")
    origins = {key: f"moonpool://com.example.retirement.{run}.{key}" for key in ("a", "b")}
    stores = report.get("stores", {})
    identifiers = {key: stores.get(key, {}).get("id", "") for key in origins}
    try:
        uuids = {UUID(value) for value in identifiers.values()}
    except (TypeError, ValueError, AttributeError):
        uuids = set()
    if (len(uuids) != 2 or UUID(int=0) in uuids
            or stores != {key: {"id": identifiers[key], "origin": origins[key]} for key in origins}):
        failures.append("the assigned persistent stores or origins differ")

    initial = report.get("initial", {})
    if set(initial) != {"a1", "a2", "b1"}:
        failures.append("initial WebView samples differ")
    for name in ("a1", "a2", "b1"):
        sample = initial.get(name, {})
        document = sample.get("document", {})
        key = name[0]
        if sample.get("state") != LIVE or sample.get("store") != identifiers[key]:
            failures.append(f"{name}: initial attached WebView state differs")
        if (document.get("name") != name or document.get("origin") != origins[key]
                or document.get("marker") != f"{run}-{key}" or document.get("cookie") != ""
                or not document.get("instance") or type(document.get("pulse")) is not int or document["pulse"] <= 0):
            failures.append(f"{name}: initial fixture document evidence differs")

    if report.get("writer") != {"completed": True, "name": "mp_retirement", "value": "fixture"}:
        failures.append("the fixture write did not complete")
    if report.get("pending") != {"a3": PENDING, "a1": LIVE, "a2": LIVE}:
        failures.append("a3 was not pending without a load during the live recheck")
    inspections = report.get("inspections", {})
    expected = {name: EMPTY_COOKIE_STATE for name in ("a1", "a2", "b1")}
    expected["a3"] = PRESENT_COOKIE_STATE
    if inspections != expected or cookie_verdict(inspections.get("a3", {})) != "present":
        failures.append("the two native cookie sources or verified policy differ")

    states = report.get("states", {})
    failures.extend(retirement_failures(states))
    if states.get("b1") != LIVE or report.get("bPolicy") != EMPTY_COOKIE_STATE:
        failures.append("the separate B view or browser cookie state changed")
    before = initial.get("b1", {}).get("document", {})
    after = report.get("continuedB", {})
    pulse = after.get("pulse")
    initial_pulse = before.get("pulse")
    if (not before.get("instance") or type(pulse) is not int or type(initial_pulse) is not int
            or pulse <= initial_pulse or after != dict(before, pulse=pulse)):
        failures.append("b1: the original document did not continue")
    retained = {
        "store": identifiers["a"], "origin": origins["a"], "marker": f"{run}-a",
        "nonceMatched": True, "hostReceipts": 1, "cookieState": PRESENT_COOKIE_STATE,
    }
    if report.get("preservedA") != retained:
        failures.append("the original A store's data preservation was not established")
    expected_events = [f"{name}:{event}" for name in ("a1", "a2", "b1") for event in ("inspect", "empty", "load")]
    expected_events.extend(["a:write-complete", "a3:inspect", "a3:pending", "a3:present",
                            "a1:release", "a2:release", "a3:refuse", "a4:refuse"])
    if report.get("events") != expected_events:
        failures.append("admission, inspection or retirement order differs")
    if report.get("loader") != ["a1", "a2", "b1"]:
        failures.append("guest document receipts differ")
    if report.get("retiredAccess") != {"a1": False, "a2": False}:
        failures.append("a retired handle can still select its WebView")
    weak = report.get("weakReferencesCleared", {})
    if set(weak) != {"a1", "a2"} or any(type(value) is not bool for value in weak.values()):
        failures.append("the post-release weak-reference observation is missing")
    return failures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    experiments = ROOT.parent.parent
    files = [
        ROOT / "check.py", ROOT / "run_probe.py", ROOT / "Probe.swift", ROOT / "CookiePresence.swift", ROOT / "guest.js",
        ROOT.parent / "runner.py", ROOT.parent / "worker-admission/store.js",
        experiments / "native-cookie-admission-probe/ios/AdmissionGate.swift",
    ]
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(files)}


def archived_fingerprints(path):
    probe = ROOT.relative_to(ROOT.parents[2]).as_posix()
    sources = {}
    with ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = archive_relpath(entry.filename, probe)
            if name in sources:
                raise ValueError(f"Duplicate archived source: {name}")
            sources[name] = hashlib.sha256(archive.read(entry)).hexdigest()
    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--expect-cleared-weak-references", action="store_true",
                        help="Require the observed A1 and A2 weak references to clear")
    parser.add_argument("--source-archive", type=Path, help="Verify against the report's archived sources")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    sources = archived_fingerprints(args.source_archive) if args.source_archive else source_fingerprints()
    if report["build"]["sources"] != sources:
        raise RuntimeError("Changed build sources")
    if report["installedArtifactSha256"] != report["build"]["artifactSha256"]:
        raise RuntimeError("Installed simulator app differs")
    failures = classify(report)
    if args.expect_cleared_weak_references and report.get("weakReferencesCleared") != {"a1": True, "a2": True}:
        failures.append("both weak references must clear")
    for issue in failures:
        print(issue)
    print(f"{args.report.stem}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
