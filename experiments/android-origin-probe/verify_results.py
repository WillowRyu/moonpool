"""Check positive/negative controls; preserve custom-scheme incompatibilities."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
checks = 0


def require(value, label):
    global checks
    assert value, label
    checks += 1


for phase in ["seed", "restart"]:
    report = json.loads((args.directory / f"https-control-{phase}.json").read_text())
    require(report["complete"], f"{phase} report complete")
    require(not report["officialLoaderAcceptsCustom"], "Official loader did not accept custom scheme")
    require(len(report["samples"]) == 11, f"{phase} has all lifecycle/navigation observations")
    for sample in report["samples"]:
        data = sample["observation"]
        if sample["label"] == "external-navigation":
            require(data.get("external") and data["origin"] == "http://127.0.0.1:8877", "External navigation positive control")
            continue
        app = data["app"]
        other = "b" if app == "a" else "a"
        context = phase + "/" + sample["label"]
        require(data["origin"] == f"https://com.example.probe.{app}.test", context + " actual origin")
        require(data["imageLoaded"] and data["cssMarker"] == "rgb(234, 243, 238)", context + " bundled resources")
        require(json.loads(data["selfFetch"]["body"])["publicMarker"] == app, context + " self-fetch positive")
        require("error" in data["crossFetch"], context + " cross-fetch blocked")
        require(data["selfFrame"].get("domMarker") == app, context + " self-frame positive")
        require(data["crossFrame"].get("loadedMarker") == other, context + " cross-frame really loaded")
        require("SecurityError" in data["crossFrame"].get("domError", ""), context + " cross-frame DOM blocked")
        require(data["localStorage"]["after"] == app and data["indexedDB"]["after"] == app, context + " storage partition")
        require(f"t23-https-control={app}" in data["cookies"]["after"], context + " cookie partition")
        if phase == "restart":
            require(data["localStorage"]["before"] == app and data["indexedDB"]["before"] == app, context + " process persistence")
        require(data["missingFetch"].get("status") == 404, context + " missing bundled resource")
        require(data["escapeFetch"].get("status") == 451 and data["encodedEscapeFetch"].get("status") == 451, context + " escaped root blocked")
        require("error" in data["unknownAppFetch"], context + " unknown app not readable")
        require(json.loads(data["corsFetch"]["body"])["originHeader"] == data["origin"], context + " server-observed Origin")
        require("error" in data["noCorsFetch"], context + " missing CORS permission")

for profile in ["asset-loader-custom", "intercept-custom"]:
    for phase in ["seed", "restart"]:
        report = json.loads((args.directory / f"{profile}-{phase}.json").read_text())
        require(report["complete"] and not report["officialLoaderAcceptsCustom"], profile + "/" + phase + " observed")
        # Do not turn unknown custom-origin semantics into a new normative contract.
        print(json.dumps({"profile": profile, "phase": phase, "observations": [
            {"label": s["label"], "origin": s["observation"].get("origin"),
             "localStorage": s["observation"].get("localStorage"),
             "unavailable": s["observation"].get("unavailable", False)}
            for s in report["samples"][:2]
        ]}))

offline = json.loads((args.directory / "https-control-offline.json").read_text())
for sample in offline["samples"]:
    data = sample["observation"]
    if sample["label"] == "external-navigation":
        require(data.get("unavailable"), "Offline external control cannot load")
        continue
    require(data["selfFetch"].get("status") == 200, "Offline bundled resource remains available")
    require(data["missingFetch"].get("status") == 404, "Offline missing asset stays local")
    require(data["escapeFetch"].get("status") == 451, "Offline escape stays blocked")
    require("error" in data["corsFetch"], "Offline loopback control fails")
hashes = {json.loads(p.read_text())["apkSha256"] for p in args.directory.glob("*-*.json")}
require(len(hashes) == 1, "All retained observations use the same final APK")
print(f"{checks} control assertions passed; custom-scheme observations retained without changing SPEC.")
