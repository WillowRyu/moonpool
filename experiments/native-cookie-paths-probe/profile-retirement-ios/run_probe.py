"""Build and collect the shared-store WebKit retirement probe."""

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

from check import ROOT, classify, sha, source_fingerprints

sys.path.insert(0, str(ROOT.parent))
from runner import command, poll

EXPERIMENTS = ROOT.parent.parent
LOCAL = ROOT / "local-results"
EXECUTABLE = "ProfileRetirementProbe"
APP = ROOT / f"build/{EXECUTABLE}.app"
PACKAGE = "org.moonpool.iosprofileretirement"


def app_digest(app):
    files = (EXECUTABLE, "Info.plist", "Fixtures/store.js", "Fixtures/guest.js", "_CodeSignature/CodeResources")
    return hashlib.sha256("".join(sha(app / name) for name in files).encode()).hexdigest()


def build():
    sources = source_fingerprints()
    assets = APP / "Fixtures"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT.parent / "worker-admission/store.js", assets / "store.js")
    shutil.copyfile(ROOT / "guest.js", assets / "guest.js")
    (APP / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": EXECUTABLE, "CFBundleIdentifier": PACKAGE,
        "CFBundleName": "Profile Retirement Probe", "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1", "MinimumOSVersion": "17.0", "UIDeviceFamily": [1, 2],
        "UILaunchScreen": {}, "LSRequiresIPhoneOS": True,
    }))
    sdk = command(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"]).stdout.strip()
    gate = EXPERIMENTS / "native-cookie-admission-probe/ios/AdmissionGate.swift"
    subprocess.run(["xcrun", "--sdk", "iphonesimulator", "swiftc", "-swift-version", "5", "-parse-as-library",
                    "-sdk", sdk, "-target", "arm64-apple-ios17.0-simulator",
                    "-framework", "UIKit", "-framework", "WebKit", str(gate),
                    str(ROOT / "CookiePresence.swift"), str(ROOT / "Probe.swift"),
                    "-o", str(APP / EXECUTABLE)], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", str(APP)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(APP)], check=True)
    if source_fingerprints() != sources:
        raise RuntimeError("Sources changed during build")
    metadata = {
        "sources": sources, "artifactSha256": app_digest(APP),
        "xcode": command(["xcodebuild", "-version"]).stdout.strip(),
        "sdk": command(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"]).stdout.strip(),
    }
    LOCAL.mkdir(exist_ok=True)
    (LOCAL / "ios-build.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def collect(tag, owner_path):
    run = "ios-" + tag
    if not re.fullmatch("[a-z0-9-]{1,28}", run):
        raise ValueError("Invalid run tag")
    target = LOCAL / f"{run}.json"
    if target.exists():
        raise ValueError("Use a fresh run tag")
    metadata = json.loads((LOCAL / "ios-build.json").read_text())
    if metadata["sources"] != source_fingerprints() or metadata["artifactSha256"] != app_digest(APP):
        raise RuntimeError("Changed sources or build artifact")
    owner = json.loads(owner_path.read_text())
    device = owner["owned"]
    if device in owner["protected"]:
        raise RuntimeError("The requested simulator is protected")

    def sim(*parts, **options):
        return command(["xcrun", "simctl", *parts], **options)

    devices = json.loads(sim("list", "devices", "available", "-j").stdout)["devices"]
    state = next((entry for group in devices.values() for entry in group if entry["udid"] == device), {})
    if state.get("name") != owner["name"] or state.get("state") != "Booted":
        raise RuntimeError("Wrong or inactive owned simulator")
    sim("install", device, str(APP))
    sim("terminate", device, PACKAGE, check=False)
    installed = app_digest(Path(sim("get_app_container", device, PACKAGE, "app").stdout.strip()))
    if installed != metadata["artifactSha256"]:
        raise RuntimeError("Unexpected installed app")
    output = Path(sim("get_app_container", device, PACKAGE, "data").stdout.strip()) / "Documents/report.json"
    output.unlink(missing_ok=True)
    launch = sim("launch", device, PACKAGE, "--run", run)
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
    report.update({
        "build": metadata, "installedArtifactSha256": installed,
        "capturedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    with target.open("x") as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write("\n")
    failures = classify(report)
    if report.get("error"):
        print(report["error"])
    for issue in failures:
        print(issue)
    print(f"{run}: {len(failures)} failures")
    raise SystemExit(int(bool(failures)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "run"))
    parser.add_argument("--run")
    parser.add_argument("--owner", type=Path)
    args = parser.parse_args()
    if args.action == "build":
        build()
    else:
        if args.run is None or args.owner is None:
            parser.error("run requires a fresh tag and simulator owner record")
        collect(args.run, args.owner)


if __name__ == "__main__":
    main()
