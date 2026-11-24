"""Validate worker policy observations in ordinary and inherited documents."""

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY = "worker-src 'none'"
WORKER_PATHS = {"dedicated": "/dedicated.js", "service": "/service.js"}
DOCUMENT_PATHS = {"entry": "/entry", "blank": "about:blank", "srcdoc": "about:srcdoc"}


def guard_failures(origin, document, worker):
    failures = []
    result = document.get(worker, {})
    if result.get("outcome") != "rejected" or not result.get("error"):
        failures.append(f"{worker}: worker did not reject")
    event = {
        "directive": "worker-src",
        "disposition": "enforce",
        "blockedURI": origin + WORKER_PATHS[worker],
    }
    if event not in document.get("violations", []):
        failures.append(f"{worker}: enforcing worker-src event missing")
    return failures


def classify(report):
    run = report["run"]
    failures = []
    unconfirmed = []
    if report.get("complete") is not True or not all(report.get(key) for key in ("sdk", "release", "provider")):
        failures.append("native collection did not complete")
    samples = report.get("samples", {})
    if set(samples) != {"control", "guarded"}:
        failures.append("both fresh profiles are required")
    for mode in ("control", "guarded"):
        sample = samples.get(mode, {})
        origin = f"https://mp-{run}-{mode}.invalid"
        if (sample.get("profile") != f"worker-contexts-{run}-{mode}" or sample.get("created") is not True
                or sample.get("policy") != (POLICY if mode == "guarded" else "")):
            failures.append(f"{mode}: profile or entry response policy differs")
        requests = sample.get("requests", [])
        expected = {"/entry", "/probe.js"}
        if mode == "control":
            expected.update(WORKER_PATHS.values())
        if set(requests) != expected or requests.count("/entry") != 1:
            failures.append(f"{mode}: loader requests differ")
        page = sample.get("page", {})
        documents = page.get("documents", {})
        if set(documents) != set(DOCUMENT_PATHS):
            failures.append(f"{mode}: document samples differ")
        for name, path in DOCUMENT_PATHS.items():
            document = documents.get(name, {})
            url = origin + path if name == "entry" else path
            if document.get("url") != url or document.get("origin") != origin or document.get("secure") is not True:
                failures.append(f"{mode}/{name}: document URL, origin or secure context differs")
            if mode == "control":
                if document.get("dedicated") != {"outcome": "message", "value": "context-worker"}:
                    failures.append(f"{mode}/{name}: dedicated worker did not run")
                if document.get("violations") != []:
                    failures.append(f"{mode}/{name}: unexpected CSP event")
            else:
                failures.extend(f"{mode}/{name}: {issue}" for issue in guard_failures(origin, document, "dedicated"))
        active = [result["scope"] for document in documents.values()
                  if (result := document.get("service", {})).get("outcome") == "activated"]
        if page.get("scopes") != sorted(active) or (mode == "guarded" and active):
            failures.append(f"{mode}: top-level registration inventory differs")

    control = samples.get("control", {}).get("page", {}).get("documents", {})
    guarded = samples.get("guarded", {}).get("page", {}).get("documents", {})
    for name in DOCUMENT_PATHS:
        control_result = control.get(name, {}).get("service", {})
        guarded_document = guarded.get(name, {})
        guarded_result = guarded_document.get("service", {})
        control_origin = f"https://mp-{run}-control.invalid"
        guarded_origin = f"https://mp-{run}-guarded.invalid"
        if control_result.get("outcome") == "activated":
            if control_result.get("scope") != control_origin + f"/scope/{name}/":
                failures.append(f"control/{name}: registration scope differs")
            failures.extend(f"guarded/{name}: {issue}" for issue in guard_failures(guarded_origin, guarded_document, "service"))
        elif (name != "entry" and control_result.get("outcome") in ("rejected", "unavailable")
              and control_result.get("error") and guarded_result.get("outcome") in ("rejected", "unavailable")
              and guarded_result.get("error")):
            unconfirmed.append(name)
        else:
            failures.append(f"{name}: service worker control or guarded refusal differs")
    return failures, unconfirmed


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints():
    wrapper = ROOT.parent.parent / "android-origin-probe"
    files = [ROOT / "check.py", ROOT / "run_probe.py", ROOT.parent / "runner.py",
             wrapper / "gradlew", wrapper / "gradle/wrapper/gradle-wrapper.properties"]
    files.extend((ROOT / "assets").glob("*.js"))
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
    failures, unconfirmed = classify(report)
    for issue in failures:
        print(issue)
    print(f"{args.report.stem}: {len(failures)} failures, "
          f"service worker contexts without positive controls: {', '.join(unconfirmed) or 'none'}")
    raise SystemExit(int(bool(failures)))


if __name__ == "__main__":
    main()
