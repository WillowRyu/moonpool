"""Build and collect the generated-frame fixture on an owned iOS simulator."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import time

from check import ASSETS, DOCUMENT_SETS, FRAME_SOURCES, GATE, PRESENCE, ROOT, sha, source_fingerprints, verify_report

sys.path.insert(0, str(ROOT.parent))
from runner import command, poll

LOCAL = ROOT / "local-results"
EXECUTABLE = "LocalDocumentFramesProbe"
APP = ROOT / f"build/{EXECUTABLE}.app"
PACKAGE = "org.moonpool.ioslocaldocumentframes"
FIXTURES = ("probe.js", "worker.js")


def app_digest(app):
    files = (EXECUTABLE, "Info.plist", "_CodeSignature/CodeResources", *(f"Fixtures/{name}" for name in FIXTURES))
    return hashlib.sha256("".join(sha(app / name) for name in files).encode()).hexdigest()


def build():
    sources = source_fingerprints()
    fixtures = APP / "Fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    for name in FIXTURES:
        shutil.copyfile(ASSETS / name, fixtures / name)
    (APP / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": EXECUTABLE, "CFBundleIdentifier": PACKAGE,
        "CFBundleName": "Local Document Frames Probe", "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1", "MinimumOSVersion": "17.0", "UIDeviceFamily": [1, 2],
        "UILaunchScreen": {}, "LSRequiresIPhoneOS": True,
    }))
    sdk_command = ["xcrun", "--sdk", "iphonesimulator"]
    sdk = command([*sdk_command, "--show-sdk-path"]).stdout.strip()
    subprocess.run([*sdk_command, "swiftc", "-swift-version", "5", "-parse-as-library", "-sdk", sdk,
                    "-target", "arm64-apple-ios17.0-simulator", "-framework", "UIKit", "-framework", "WebKit",
                    str(GATE), str(PRESENCE), str(ROOT / "Probe.swift"), "-o", str(APP / EXECUTABLE)], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", str(APP)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(APP)], check=True)
    if source_fingerprints() != sources:
        raise RuntimeError("Sources changed during build")
    metadata = {
        "sources": sources, "artifactSha256": app_digest(APP),
        "xcode": command(["xcodebuild", "-version"]).stdout.strip(),
        "sdk": command([*sdk_command, "--show-sdk-version"]).stdout.strip(),
    }
    LOCAL.mkdir(exist_ok=True)
    (LOCAL / "ios-build.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def sim(*parts, **options):
    return command(["xcrun", "simctl", *parts], **options)


def owned_device(owner_path):
    owner = json.loads(owner_path.read_text())
    device = owner["owned"]
    if device in owner["protected"] or owner["name"] != "Moonpool Cookie Suppression":
        raise RuntimeError("The requested simulator is not the owned Moonpool fixture")
    devices = json.loads(sim("list", "devices", "available", "-j").stdout)["devices"]
    for runtime, entries in devices.items():
        for entry in entries:
            if entry["udid"] == device and entry["name"] == owner["name"] and entry["state"] == "Booted":
                return device, {"runtime": runtime, "deviceType": entry["deviceTypeIdentifier"]}
    raise RuntimeError("Wrong or inactive owned simulator")


def collect(tag, owner_path, frame_source, document_set):
    run = "ios-" + tag
    if not re.fullmatch(r"ios-[a-z0-9-]{1,24}", run):
        raise ValueError("Invalid run tag")
    target = LOCAL / f"{run}.json"
    if target.exists():
        raise ValueError("Use a fresh run tag")
    metadata = json.loads((LOCAL / "ios-build.json").read_text())
    if metadata["sources"] != source_fingerprints() or metadata["artifactSha256"] != app_digest(APP):
        raise RuntimeError("Changed sources or build artifact")
    device, simulator = owned_device(owner_path)

    sim("terminate", device, PACKAGE, check=False)
    sim("install", device, str(APP))
    installed = app_digest(Path(sim("get_app_container", device, PACKAGE, "app").stdout.strip()))
    if installed != metadata["artifactSha256"]:
        raise RuntimeError("Unexpected installed app")
    output = Path(sim("get_app_container", device, PACKAGE, "data").stdout.strip()) / "Documents/report.json"
    output.unlink(missing_ok=True)

    launch = sim("launch", device, PACKAGE, "--run", run, "--frame-source", frame_source, "--document-set", document_set)
    pid = int(launch.stdout.rsplit(":", 1)[1].strip())

    def alive():
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    try:
        report = poll(lambda: output.read_text() if output.is_file() else None, alive, run)
    finally:
        sim("terminate", device, PACKAGE, check=False)
    if report.get("pid") != pid:
        raise RuntimeError("The report came from a different app process")
    if report.get("frameSource") != frame_source:
        raise RuntimeError("The report used a different frame source than requested")
    if report.get("documentSet") != document_set:
        raise RuntimeError("The report used a different document set than requested")
    report.update({
        "build": metadata, "installedArtifactSha256": installed, "simulator": simulator,
        "capturedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    with target.open("x") as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write("\n")
    failures = verify_report(report)
    for failure in failures:
        print(failure)
    print(f"{run}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "run"))
    parser.add_argument("--run")
    parser.add_argument("--owner", type=Path)
    parser.add_argument("--frame-source", choices=FRAME_SOURCES, default="self")
    parser.add_argument("--document-set", choices=DOCUMENT_SETS, default="local")
    args = parser.parse_args()
    if args.action == "build":
        build()
    else:
        if args.run is None or args.owner is None:
            parser.error("run requires a fresh tag and simulator owner record")
        collect(args.run, args.owner, args.frame_source, args.document_set)


if __name__ == "__main__":
    main()
