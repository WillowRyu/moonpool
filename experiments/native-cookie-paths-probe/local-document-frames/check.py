"""Validate Android observations of local generated frame documents."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
POLICY = "default-src 'none'; script-src 'self' 'unsafe-inline'; frame-src 'self'; worker-src 'none'; base-uri 'none'"
KINDS = ("same", "blob", "data")
INHERITED_URLS = {"blank": "about:blank", "srcdoc": "about:srcdoc", "blank-navigation": "about:blank"}
DOCUMENT_SETS = {"local": KINDS, "inherited": ("blank", "srcdoc"), "navigation": ("blank-navigation",)}
FRAME_SOURCES = ("self", "origin")
MODES = ("control", "guarded")


def document_started(origin, kind, starts):
    expected_origin = "null" if kind == "data" else origin
    expected = {"name": kind, "protocol": ("https" if kind == "same" else kind) + ":",
                "origin": expected_origin, "messageOrigin": expected_origin}
    if kind in INHERITED_URLS:
        if len(starts) != 1 or not isinstance(starts[0], dict):
            return False
        secure = starts[0].get("secureContext")
        service_worker = starts[0].get("serviceWorkerRegistration")
        if type(secure) is not bool or type(service_worker) is not bool:
            return False
        expected.update(protocol="about:", url=INHERITED_URLS[kind], secureContext=secure,
                        serviceWorkerRegistration=service_worker)
    return starts == [expected]


def observation_failures(origin, mode, kind, page):
    failures = []
    starts = page.get("starts")
    workers = page.get("workers")
    worker_violations = page.get("workerViolations")
    violations = page.get("frameViolations")
    trace = page.get("trace")
    if not all(isinstance(values, list) for values in (starts, workers, worker_violations, violations, trace)):
        return ["the frame observation is incomplete"]
    if not starts:
        if mode == "control" or kind == "same" or kind in INHERITED_URLS:
            failures.append("the positive document control did not report")
        expected = {"directive": "frame-src", "disposition": "enforce", "scheme": kind, "trusted": True}
        observed = violations == [expected] or (kind == "data" and violations == [dict(expected, scheme=None)])
        if not observed or violations[0]["trusted"] is not True:
            failures.append("an enforcing frame-src event was not observed")
        if workers or worker_violations or trace != ["attach", "frame-violation", "detach"]:
            failures.append("the blocked frame observation sequence differs")
        return failures

    if mode == "guarded" and kind == "data":
        failures.append("the opaque document executed")
    if not document_started(origin, kind, starts):
        failures.append("the executed document's URL scheme or origin differs")
    trace_prefix = ["attach", "ready"]
    if kind == "blank-navigation":
        navigation = page.get("navigation")
        expected = {"previousUrl": origin + "/before-blank", "replacementUrl": "about:blank", "documentReplaced": True}
        if navigation != expected or navigation["documentReplaced"] is not True:
            failures.append("replacement document evidence differs")
        trace_prefix = ["attach", "previous-document", "blank-navigation", "replacement-document", "ready"]
    if violations:
        failures.append("the executed document also reports a frame refusal")
    worker_signals = []
    if kind == "data":
        if workers or worker_violations:
            failures.append("the opaque document reported an unexpected worker")
    else:
        worker_signals.append("worker-result")
        expected_worker = {"messageOrigin": origin, "outcome": "message"}
        expected_violations = []
        if mode == "guarded":
            expected_worker["outcome"] = "rejected"
            expected_violations.append({"directive": "worker-src", "disposition": "enforce", "trusted": True,
                                        "blockedURI": origin + "/worker.js", "messageOrigin": origin})
            worker_signals.append("worker-violation")
        if (workers != [expected_worker] or worker_violations != expected_violations
                or any(event["trusted"] is not True for event in worker_violations)):
            failures.append("the executed document's worker result or violation differs")
    if (trace[:len(trace_prefix)] != trace_prefix or trace[-1:] != ["detach"]
            or Counter(trace[len(trace_prefix):-1]) != Counter(worker_signals)):
        failures.append("the frame observation sequence differs")
    return failures


def classify(report, *, expect_retained_outcomes=False):
    failures = []
    run = report["run"]
    frame_source = report.get("frameSource", "self")
    if frame_source not in FRAME_SOURCES:
        return ["invalid frame source"]
    document_set = report.get("documentSet", "local")
    if not isinstance(document_set, str) or document_set not in DOCUMENT_SETS:
        return ["invalid document set"]
    kinds = DOCUMENT_SETS[document_set]
    if report.get("complete") is not True or not all(report.get(key) for key in ("sdk", "release", "provider")):
        failures.append("native collection did not complete")
    samples = report.get("samples", {})
    if set(samples) != set(MODES):
        failures.append("both fresh profiles are required")
    for mode in MODES:
        sample = samples.get(mode, {})
        origin = f"https://mp-{run}-{mode}.invalid"
        policy = ""
        if mode == "guarded":
            policy = POLICY.replace("frame-src 'self'", f"frame-src {origin}") if frame_source == "origin" else POLICY
        if (sample.get("profile") != f"local-document-frames-{run}-{mode}" or sample.get("created") is not True
                or sample.get("cookieDeny") is not True):
            failures.append(f"{mode}: selected profile or cookie deny differs")
        frames = sample.get("frames", {})
        if set(frames) != set(kinds):
            failures.append(f"{mode}: frame samples differ")
        worker_receipts = {}
        for kind in kinds:
            frame = frames.get(kind, {})
            page = frame.get("page", {})
            entry = f"/entry/{kind}"
            url = origin + entry
            if frame.get("parentUrl") != url or page.get("parentUrl") != url:
                failures.append(f"{mode}/{kind}: the separate parent document differs")
            if frame.get("policy") != policy:
                failures.append(f"{mode}/{kind}: parent response policy differs")
            requests = frame.get("requests", [])
            expected = {entry, "/probe.js"}
            if kind == "same":
                expected.add("/same-frame")
            if kind == "blank-navigation":
                expected.add("/before-blank")
                if frame.get("previousDocumentPolicy") != "":
                    failures.append(f"{mode}/{kind}: previous document response policy differs")
            worker_receipts[kind] = requests.count("/worker.js")
            allowed = expected | {"/worker.js"} if mode == "control" and kind != "data" else expected
            if (not expected <= set(requests) <= allowed or requests.count(entry) != 1
                    or requests.count("/same-frame") != int(kind == "same")
                    or requests.count("/before-blank") != int(kind == "blank-navigation")
                    or (kind in INHERITED_URLS and requests.count("/probe.js") != 1)):
                failures.append(f"{mode}/{kind}: loader requests differ")
            elif (mode == "control" and kind == "blank-navigation" and worker_receipts[kind]
                    and requests.index("/worker.js") < requests.index("/before-blank")):
                failures.append(f"{mode}/{kind}: worker receipt precedes the previous document")
            failures.extend(f"{mode}/{kind}: {issue}" for issue in observation_failures(origin, mode, kind, page))
            if expect_retained_outcomes and mode == "guarded" and kind == "blob" and page.get("starts"):
                failures.append("guarded/blob: retained frame refusal differs")
        if mode == "control":
            if not sum(worker_receipts.values()):
                failures.append("control: no worker script reached the native loader")
            if expect_retained_outcomes and worker_receipts != {kind: int(kind != "data") for kind in kinds}:
                failures.append("control: retained worker receipt counts differ")
    return failures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints(source_archive=None):
    wrapper = ROOT.parent.parent / "android-origin-probe"
    android = ROOT / "android"
    files = [
        ROOT / "check.py", ROOT / "run_probe.py", ROOT.parent / "runner.py",
        wrapper / "gradlew", wrapper / "gradle/wrapper/gradle-wrapper.jar",
        wrapper / "gradle/wrapper/gradle-wrapper.properties",
        android / "settings.gradle", android / "build.gradle", android / "gradle.properties",
        android / "app/build.gradle", android / "app/src/main/AndroidManifest.xml",
    ]
    files.extend((ROOT / "assets").glob("*.js"))
    files.extend((android / "app/src/main/java").rglob("*.java"))
    if source_archive is not None:
        with ZipFile(source_archive) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate archived source")
            return {Path(os.path.relpath(path, ROOT)).as_posix():
                    hashlib.sha256(archive.read(path.relative_to(ROOT.parents[2]).as_posix())).hexdigest()
                    for path in sorted(files)}
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(files)}


def execution_environment(report):
    return (report.get("sdk"), report.get("release"), report.get("provider"))


def verify_report(report, *, expect_retained_outcomes=False, source_archive=None):
    build = report.get("build")
    if not isinstance(build, dict) or build.get("sources") != source_fingerprints(source_archive):
        return ["changed build sources"]
    run = report.get("run")
    if not isinstance(run, str) or not re.fullmatch(r"android-[a-z0-9-]{1,20}", run):
        return ["invalid native run tag"]

    failures = []
    digest = report.get("installedArtifactSha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != build.get("artifactSha256"):
        failures.append("installed APK digest is missing or differs from the build")
    sdk, release, provider = execution_environment(report)
    if type(sdk) is not int or sdk <= 0 or not all(isinstance(value, str) and value.strip() for value in (release, provider)):
        failures.append("missing Android execution environment")
    failures.extend(classify(report, expect_retained_outcomes=expect_retained_outcomes))
    if not failures and expect_retained_outcomes and report.get("documentSet") in ("inherited", "navigation"):
        for mode, sample in report["samples"].items():
            for kind, frame in sample["frames"].items():
                start = frame["page"]["starts"][0]
                if start["secureContext"] is not True or start["serviceWorkerRegistration"] is not True:
                    failures.append(f"{mode}/{kind}: inherited capability observations differ")
    return failures


def verify_pair(first, repeat, *, expect_retained_outcomes=False, source_archive=None):
    failures = [f"{label}: {failure}" for label, report in (("first", first), ("repeat", repeat))
                for failure in verify_report(report, expect_retained_outcomes=expect_retained_outcomes,
                                             source_archive=source_archive)]
    if failures:
        return failures

    if first["run"] == repeat["run"]:
        failures.append("run tags are identical")
    profiles = {sample["profile"] for report in (first, repeat) for sample in report["samples"].values()}
    if len(profiles) != 2 * len(MODES):
        failures.append("profile names were reused across runs")
    if first["installedArtifactSha256"] != repeat["installedArtifactSha256"]:
        failures.append("installed APK digests differ across runs")
    if execution_environment(first) != execution_environment(repeat):
        failures.append("execution environments differ across runs")
    if first.get("frameSource", "self") != repeat.get("frameSource", "self"):
        failures.append("frame sources differ across runs")
    if first.get("documentSet", "local") != repeat.get("documentSet", "local"):
        failures.append("document sets differ across runs")
    return failures


def describe(report):
    frames = report.get("samples", {}).get("guarded", {}).get("frames", {})
    return ", ".join(f"{kind}: {'executed' if frames[kind].get('page', {}).get('starts') else 'no document'}"
                     for kind in (*KINDS, *INHERITED_URLS) if kind in frames)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--repeat", type=Path, help="Verify both runs and the shared experiment conditions")
    parser.add_argument("--expect-retained-outcomes", action="store_true",
                        help="Require retained frame outcomes, control worker receipts and inherited capability observations")
    parser.add_argument("--source-archive", type=Path, help="Verify the report against its archived build inputs")
    parser.add_argument("--expect-frame-source", choices=FRAME_SOURCES)
    parser.add_argument("--expect-document-set", choices=DOCUMENT_SETS)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    label = args.report.stem
    if args.repeat is None:
        failures = verify_report(report, expect_retained_outcomes=args.expect_retained_outcomes,
                                 source_archive=args.source_archive)
    else:
        failures = verify_pair(report, json.loads(args.repeat.read_text()), expect_retained_outcomes=args.expect_retained_outcomes,
                               source_archive=args.source_archive)
        label += f" + {args.repeat.stem}"
    if args.expect_frame_source is not None and report.get("frameSource", "self") != args.expect_frame_source:
        failures.append("frame source differs from expectation")
    if args.expect_document_set is not None and report.get("documentSet", "local") != args.expect_document_set:
        failures.append("document set differs from expectation")
    for issue in failures:
        print(issue)
    print(f"{label}: {len(failures)} failures. Guarded frames: {describe(report)}")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
