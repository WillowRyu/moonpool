"""Verify the frame and worker evidence collected by the WebKit fixture."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import UUID
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parent / "local-document-frames/assets"
GATE = ROOT.parent.parent / "native-cookie-admission-probe/ios/AdmissionGate.swift"
PRESENCE = ROOT.parent / "profile-retirement-ios/CookiePresence.swift"
POLICY = "default-src 'none'; script-src 'self' 'unsafe-inline'; frame-src 'self'; worker-src 'none'; base-uri 'none'"
KINDS = ("same", "blob", "data")
INHERITED_URLS = {"blank": "about:blank", "srcdoc": "about:srcdoc", "blank-navigation": "about:blank"}
DOCUMENT_SETS = {"local": KINDS, "inherited": ("blank", "srcdoc"), "navigation": ("blank-navigation",)}
MODES = ("control", "guarded")
FRAME_SOURCES = ("self", "origin")
EMPTY_COOKIES = {"policyDisallowed": True, "records": False, "cookies": False}


def frame_refusal(page, kind):
    events = page.get("frameViolations", [])
    if len(events) != 1:
        return False
    event = events[0]
    return (
        page.get("starts") == []
        and page.get("workers") == []
        and page.get("workerViolations") == []
        and page.get("trace") == ["attach", "frame-violation", "detach"]
        and event.get("directive") == "frame-src"
        and event.get("disposition") == "enforce"
        and event.get("trusted") is True
        and event.get("scheme") == kind
    )


def document_started(origin, kind, starts):
    if not isinstance(starts, list) or len(starts) != 1 or not isinstance(starts[0], dict):
        return False
    child_origin = "null" if kind == "data" else origin
    protocol = "moonpool:" if kind == "same" else kind + ":"
    expected = {"name": kind, "protocol": protocol, "origin": child_origin, "messageOrigin": child_origin}
    if kind in INHERITED_URLS:
        secure = starts[0].get("secureContext")
        service_worker = starts[0].get("serviceWorkerRegistration")
        if type(secure) is not bool or type(service_worker) is not bool:
            return False
        expected.update(protocol="about:", url=INHERITED_URLS[kind], secureContext=secure,
                        serviceWorkerRegistration=service_worker)
    return starts == [expected]


def frame_failures(frame, origin, mode, kind, store, *, frame_source="self"):
    page = frame.get("page", {})
    entry = f"/entry/{kind}"
    if frame.get("parentUrl") != origin + entry or page.get("parentUrl") != origin + entry or frame.get("store") != store:
        return ["parent document or store binding differs"]

    failures = []
    documents = [entry, "/same-frame"] if kind == "same" else [entry]
    policy = ""
    if mode == "guarded":
        policy = POLICY.replace("frame-src 'self'", f"frame-src {origin}") if frame_source == "origin" else POLICY
    policies = dict.fromkeys(documents, policy)
    expected_requests = Counter(documents + ["/probe.js"] * len(documents))
    if kind == "blank-navigation":
        policies["/before-blank"] = ""
        expected_requests["/before-blank"] = 1
    if frame.get("policies") != policies:
        failures.append("document response policies differ")
    request_paths = frame.get("requests", [])
    requests = Counter(request_paths)
    worker_receipts = requests.pop("/worker.js", 0)
    if requests != expected_requests:
        failures.append("document or script receipts differ")
    elif (mode == "control" and kind == "blank-navigation" and worker_receipts
            and request_paths.index("/worker.js") < request_paths.index("/before-blank")):
        failures.append("worker receipt precedes the previous document")

    refused = kind == "data" or (kind == "blob" and frame_source == "origin")
    if mode == "guarded" and refused:
        if not frame_refusal(page, kind) or worker_receipts:
            failures.append("no attributable enforcing frame refusal")
        return failures

    if not document_started(origin, kind, page.get("starts")) or page.get("frameViolations") != []:
        failures.append("the frame start, document origin or enforcing events differ")
    trace_prefix = ["attach", "ready"]
    if kind == "blank-navigation":
        navigation = page.get("navigation")
        expected = {"previousUrl": origin + "/before-blank", "replacementUrl": "about:blank", "documentReplaced": True}
        if navigation != expected or navigation["documentReplaced"] is not True:
            failures.append("replacement document evidence differs")
        trace_prefix = ["attach", "previous-document", "blank-navigation", "replacement-document", "ready"]

    workers = page.get("workers")
    worker_violations = page.get("workerViolations")
    trace = page.get("trace")
    if not all(isinstance(values, list) for values in (workers, worker_violations, trace)):
        return [*failures, "the worker observation is incomplete"]
    worker_signals = []
    if kind == "data":
        if workers or worker_violations or worker_receipts:
            failures.append("the data frame made an unexpected worker attempt")
    else:
        worker_signals.append("worker-result")
        if mode == "guarded":
            worker_signals.append("worker-violation")
        if (len(workers) != 1
                or not worker_evidence(workers[0], worker_violations, origin, mode, receipts=worker_receipts)):
            failures.append("the worker outcome lacks matching evidence")
    if (trace[:len(trace_prefix)] != trace_prefix or trace[-1:] != ["detach"]
            or Counter(trace[len(trace_prefix):-1]) != Counter(worker_signals)):
        failures.append("the frame observation sequence differs")
    return failures


def classify(report):
    run = report.get("run", "")
    if not re.fullmatch(r"ios-[a-z0-9-]{1,24}", run):
        return ["invalid native run tag"]
    if (report.get("complete") is not True or report.get("platform") != "ios"
            or report.get("initializedWebKit") is not True or not report.get("release")):
        return [report.get("error", "native collection did not complete")]
    frame_source = report.get("frameSource", "self")
    if frame_source not in FRAME_SOURCES:
        return ["invalid frame source"]
    document_set = report.get("documentSet", "local")
    if not isinstance(document_set, str) or document_set not in DOCUMENT_SETS:
        return ["invalid document set"]
    kinds = DOCUMENT_SETS[document_set]
    samples = report.get("samples", {})
    if set(samples) != set(MODES):
        return ["both identified stores are required"]

    failures = []
    stores = set()
    for mode in MODES:
        sample = samples[mode]
        store = sample.get("store", "")
        try:
            identifier = UUID(store)
        except ValueError:
            failures.append(f"{mode}: missing identified store")
            continue
        if identifier.version != 4 or identifier in stores or sample.get("persistent") is not True:
            failures.append(f"{mode}: the fixture needs a distinct persistent store")
        stores.add(identifier)
        cookies = sample.get("cookies", {})
        if set(cookies) != set(EMPTY_COOKIES) or any(cookies[key] is not value for key, value in EMPTY_COOKIES.items()):
            failures.append(f"{mode}: empty, disallowed cookie evidence is required")

        origin = f"moonpool://com.example.localframes.{run}.{mode}"
        frames = sample.get("frames", {})
        if set(frames) != set(kinds):
            failures.append(f"{mode}: frame cases differ")
            continue
        for kind in kinds:
            failures.extend(f"{mode}/{kind}: {failure}"
                            for failure in frame_failures(frames[kind], origin, mode, kind, store, frame_source=frame_source))
    return failures


def worker_evidence(worker, events, origin, mode, *, receipts):
    if worker.get("messageOrigin") != origin:
        return False
    outcome = worker.get("outcome")
    if mode == "control":
        return outcome == "message" and receipts == 1 and events == []

    if outcome != "rejected" or receipts != 0 or not isinstance(events, list) or len(events) != 1:
        return False
    event = events[0]
    return (
        event.get("directive") == "worker-src"
        and event.get("disposition") == "enforce"
        and event.get("trusted") is True
        and event.get("blockedURI") == origin + "/worker.js"
        and event.get("messageOrigin") == origin
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints(source_archive=None):
    paths = (ROOT / "Probe.swift", ROOT / "check.py", ROOT / "run_probe.py", ROOT.parent / "runner.py",
             GATE, PRESENCE, ASSETS / "probe.js", ASSETS / "worker.js")
    if source_archive is not None:
        with ZipFile(source_archive) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate archived source")
            return {Path(os.path.relpath(path, ROOT)).as_posix():
                    hashlib.sha256(archive.read(path.relative_to(ROOT.parents[2]).as_posix())).hexdigest()
                    for path in sorted(paths)}
    return {Path(os.path.relpath(path, ROOT)).as_posix(): sha(path) for path in sorted(paths)}


def execution_environment(report):
    build = report["build"]
    simulator = report.get("simulator")
    if not isinstance(simulator, dict):
        simulator = {}
    return (report.get("release"), build.get("sdk"), build.get("xcode"),
            simulator.get("runtime"), simulator.get("deviceType"))


def verify_report(report, *, expect_retained_outcomes=False, source_archive=None):
    build = report.get("build")
    if not isinstance(build, dict) or build.get("sources") != source_fingerprints(source_archive):
        return ["changed build sources"]

    failures = []
    digest = report.get("installedArtifactSha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != build.get("artifactSha256"):
        failures.append("installed app digest is missing or differs from the build")
    if not all(isinstance(value, str) and value.strip() for value in execution_environment(report)):
        failures.append("missing simulator or build environment")
    pid = report.get("pid")
    if type(pid) is not int or pid <= 0:
        failures.append("missing native process identifier")
    failures.extend(classify(report))
    if not failures and expect_retained_outcomes and report.get("documentSet") in ("inherited", "navigation"):
        for mode, sample in report["samples"].items():
            for kind, frame in sample["frames"].items():
                start = frame["page"]["starts"][0]
                if start["secureContext"] is not True or start["serviceWorkerRegistration"] is not False:
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
    stores = {UUID(sample["store"]) for report in (first, repeat) for sample in report["samples"].values()}
    if len(stores) != 2 * len(MODES):
        failures.append("store identifiers were reused across runs")
    if first["installedArtifactSha256"] != repeat["installedArtifactSha256"]:
        failures.append("installed app digests differ across runs")
    if execution_environment(first) != execution_environment(repeat):
        failures.append("execution environments differ across runs")
    if first.get("frameSource", "self") != repeat.get("frameSource", "self"):
        failures.append("frame sources differ across runs")
    if first.get("documentSet", "local") != repeat.get("documentSet", "local"):
        failures.append("document sets differ across runs")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--repeat", type=Path, help="Verify both runs and the shared experiment conditions")
    parser.add_argument("--source-archive", type=Path, help="Verify the report against its archived build inputs")
    parser.add_argument("--expect-retained-outcomes", action="store_true",
                        help="Require the measured inherited capability observations")
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
    for failure in failures:
        print(failure)
    print(f"{label}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
