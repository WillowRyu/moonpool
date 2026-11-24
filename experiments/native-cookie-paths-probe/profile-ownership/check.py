"""Validate same-process Android profile and cookie-manager observations."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from posixpath import relpath as archive_relpath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
CASES = ("control", "direct", "policy")


def snapshot(accept, marker=None):
    return {"accept": accept, "hasCookies": marker is not None, "cookie": marker}


def write_failures(evidence, *, accept, marker, require_success=False):
    callback = evidence.get("callback")
    if type(callback) is not bool or (require_success and not callback):
        return ["the native write callback did not give the expected result"]
    if evidence.get("owner") != snapshot(accept, marker if callback else None):
        return ["the original handle did not observe the reported write"]
    return []


def classify(report):
    run = report["run"]
    failures = []
    if report.get("complete") is not True or not all(report.get(field) for field in ("provider", "release", "sdk", "pid")):
        failures.append("native collection did not complete")
    if report.get("url") != f"https://mp-{run}.invalid/":
        failures.append("the synthetic cookie URL differs")
    cases = report.get("cases", {})
    if set(cases) != set(CASES):
        failures.append("expected a separate control and both mutation trials")
    for case in CASES:
        sample = cases.get(case, {})
        profile = f"profile-ownership-{run}-{case}"
        if sample.get("profile") != profile or sample.get("created") is not True:
            failures.append(f"{case}: the fresh profile was not established")
        if sample.get("before") != snapshot(case == "control"):
            failures.append(f"{case}: the original policy or empty jar differs")
        if case != "control":
            peer = sample.get("peer", {})
            if peer != {"listed": True, "profile": profile, "before": snapshot(False)}:
                failures.append(f"{case}: the second caller did not resolve the same profile")
        if case == "policy" and sample.get("ownerAfterPolicy") != snapshot(True):
            failures.append("policy: the original handle did not observe the second caller's policy change")
        write = sample.get("write", {})
        failures.extend(f"{case}: {issue}" for issue in write_failures(
            write, accept=case != "direct", marker=f"mp_fixture={case}", require_success=case != "direct",
        ))
        if case != "control" and write.get("peer") != write.get("owner"):
            failures.append(f"{case}: the two handles disagree after the write")
    if cases.get("policy", {}).get("restored") != snapshot(False, "mp_fixture=policy"):
        failures.append("policy: restoring deny did not retain the marker")
    if cases.get("control", {}).get("final") != snapshot(True, "mp_fixture=control"):
        failures.append("control: the other profile was changed")
    direct = cases.get("direct", {}).get("write", {}).get("callback")
    return failures, {True: "stored", False: "refused"}.get(direct, "unverified")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    android = ROOT / "android"
    wrapper = ROOT.parent.parent / "android-origin-probe"
    files = [
        ROOT / "check.py",
        ROOT / "run_probe.py",
        ROOT.parent / "runner.py",
        wrapper / "gradlew",
        wrapper / "gradle/wrapper/gradle-wrapper.jar",
        wrapper / "gradle/wrapper/gradle-wrapper.properties",
        android / "settings.gradle",
        android / "build.gradle",
        android / "gradle.properties",
        android / "app/build.gradle",
        android / "app/src/main/AndroidManifest.xml",
    ]
    files.extend(path for path in (android / "app/src/main/java").rglob("*.java") if path.is_file())
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(files)}


def archived_fingerprints(path):
    base = ROOT.relative_to(ROOT.parents[2]).as_posix()
    sources = {}
    with ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            relative = archive_relpath(entry.filename, base)
            if relative in sources:
                raise ValueError(f"Duplicate archived source: {relative}")
            sources[relative] = hashlib.sha256(archive.read(entry)).hexdigest()
    return sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--expect-direct", choices=("stored", "refused"),
                        help="Require the observed native write outcome to match")
    parser.add_argument("--source-archive", type=Path,
                        help="Verify a retained report against its archived sources")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    sources = archived_fingerprints(args.source_archive) if args.source_archive else source_fingerprints()
    if report["build"]["sources"] != sources:
        raise RuntimeError("Changed build sources")
    if report["installedArtifactSha256"] != report["build"]["artifactSha256"]:
        raise RuntimeError("Installed APK differs")
    failures, direct = classify(report)
    if args.expect_direct is not None and direct != args.expect_direct:
        failures.append(f"direct native write under deny: expected {args.expect_direct}, observed {direct}")
    for issue in failures:
        print(issue)
    print(f"{args.report.stem}: {len(failures)} failures, direct native write under deny: {direct}")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
