"""Validate recorded controls without treating unavailable storage as isolation."""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--single", type=Path, help="Check a preliminary custom-scheme run")
args = parser.parse_args()
checks = 0


def require(value, label):
    global checks
    if not value:
        raise AssertionError(label)
    checks += 1


def cancellation(report):
    events = [e for e in report["events"] if e.get("view") == "cancelled-resource"]
    starts = [e for e in events if e["type"] == "scheme-start" and "delayed.html" in e["url"]]
    require(len(starts) == 1, "Delayed resource really started before cancellation")
    task = starts[0]["task"]
    lifecycle = [e["type"] for e in events if e.get("task") == task]
    require(lifecycle == ["scheme-start", "scheme-stop", "scheme-suppressed-after-stop"],
            "Cancelled task stops and suppresses callbacks rather than finishing")
    require(report["pendingSchemeTasks"] == 0, "No pending scheme task at completion")


if args.single:
    cancellation(json.loads(args.single.read_text()))
    print(f"{checks} cancellation checks passed")
    raise SystemExit(0)

metadata = None
for profile, phase, suffix in [
    ("custom-scheme", "seed", "seed"), ("custom-scheme", "restart", "restart"),
    ("http-control", "seed", "seed"), ("http-control", "restart", "restart"),
    ("custom-scheme", "restart", "offline"),
]:
    report = json.loads((args.directory / f"{profile}-{suffix}.json").read_text())
    context = f"{profile}/{suffix}"
    require(report["complete"] and report["profile"] == profile and report["phase"] == phase, context + " complete")
    require(len(report["samples"]) == 11, context + " all lifecycle/navigation samples")
    require(report["dataStorePersistent"] and not report["webkitHandlesMoonpool"] and report["webkitHandlesHTTPS"], context + " public configuration")
    current = report["buildMetadata"]
    require(metadata is None or metadata == current, "All retained runs use the same source/artifact fingerprints")
    metadata = current
    if profile == "custom-scheme":
        cancellation(report)
    for sample in report["samples"]:
        data = sample["observation"]
        label = context + "/" + sample["label"]
        if sample["label"] == "external-navigation":
            require(data.get("unavailable") if suffix == "offline" else data.get("external") and data["origin"] == "http://127.0.0.1:8877", label + " network control")
            continue
        app = data["app"]
        other = "b" if app == "a" else "a"
        origin = f"moonpool://com.example.probe.{app}" if profile == "custom-scheme" else {"a": "http://localhost:8878", "b": "http://127.0.0.1:8879"}[app]
        require(data["origin"] == origin, label + " distinct page origin")
        require(data["imageLoaded"] and data["cssMarker"] == "rgb(234, 243, 238)", label + " local assets")
        require(json.loads(data["selfFetch"]["body"])["publicMarker"] == app, label + " bundled fetch positive")
        require("error" in data["crossFetch"], label + " foreign fetch denied")
        require(data["selfFrame"].get("domMarker") == app and data["selfFrame"].get("messageOrigin") == origin, label + " loaded self frame")
        require(data["selfFrame"].get("storageMarker") == data["localStorage"]["after"], label + " self-frame storage access")
        require(data["crossFrame"].get("loadedMarker") == other, label + " foreign frame really loaded")
        require("SecurityError" in data["crossFrame"].get("domError", "") and "SecurityError" in data["crossFrame"].get("storageError", ""), label + " foreign DOM/storage denied")
        require(all(data[field].get("status") == 404 for field in ["missingFetch", "escapeFetch", "encodedEscapeFetch"]), label + " local confinement responses")
        unknown = data["unknownAppFetch"]
        require("error" in unknown or (profile == "http-control" and unknown.get("status") == 404), label + " unknown resource rejected")
        if suffix == "offline":
            require("error" in data["corsFetch"], label + " offline network fails")
        else:
            require(json.loads(data["corsFetch"]["body"])["originHeader"] == origin, label + " server-observed Origin")
        require("error" in data["noCorsFetch"], label + " no-CORS control denied")
        if profile == "http-control":
            require(data["localStorage"]["after"] == app and data["indexedDB"]["after"] == app, label + " retained partition")
            cookie = data["cookies"]["after"]
            require(cookie in ["", f"t24-http-control={app}"], label + " no foreign cookie marker")
            if phase == "seed" and sample["label"] in ["initial-a", "initial-b"]:
                require(cookie == f"t24-http-control={app}", label + " session-cookie write positive")
            if phase == "restart":
                require(data["localStorage"]["before"] == app and data["indexedDB"]["before"] == app, label + " process persistence")
        else:
            for facility in ["localStorage", "indexedDB"]:
                require(data[facility].get("after") == app, label + " app partition in " + facility)
                if phase == "restart":
                    require(data[facility].get("before") == app, label + " process persistence in " + facility)
    print(json.dumps({"run": context, "initialStorage": [
        {"app": s["observation"]["app"], **{key: s["observation"][key] for key in ["localStorage", "indexedDB", "cookies"]}}
        for s in report["samples"][:2]
    ]}))

root = Path(__file__).resolve().parent
for name, expected in metadata["sources"].items():
    require(hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name + " source fingerprint")
print(f"{checks} control assertions passed; session-cookie lifetime observations retained separately.")
