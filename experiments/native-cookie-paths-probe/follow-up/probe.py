"""Build and collect the C09 follow-up on an explicitly owned device."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import time

from check import sha, sources
from https_fixture import ROOT, TLS_DIR, certificates
from runner import command, poll

EXPERIMENTS = ROOT.parent.parent
ADMISSION = EXPERIMENTS / "native-cookie-admission-probe"
LOCAL = ROOT / "local-results"
PACKAGES = {"android": "org.moonpool.cookiepaths.followup", "ios": "org.moonpool.ioscookiepaths.followup"}
APK = ROOT / "android/app/build/outputs/apk/debug/app-debug.apk"
APP = ROOT / "build/CookiePathsFollowup.app"


def app_digest(app):
    names = ["CookiePathsFollowup", "Fixtures/images.js", "Fixtures/ca.der", "_CodeSignature/CodeResources"]
    return hashlib.sha256("".join(sha(app / name) for name in names).encode()).hexdigest()


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build(platform):
    certificates(TLS_DIR)
    metadata = {"sources": sources(platform), "caSha256": sha(TLS_DIR / "ca.pem")}
    if platform == "android":
        for name in ("images.js", "worker.js", "worker-seed.html", "worker-entry.html"):
            copy(ROOT / name, ROOT / "build/assets" / name)
        copy(TLS_DIR / "ca.pem", ROOT / "build/res/raw/probe_ca.pem")
        copy(ADMISSION / "android/app/src/main/res/xml/network_security_config.xml",
             ROOT / "build/res/xml/network_security_config.xml")
        gate = "org/moonpool/cookieadmission/AdmissionGate.java"
        copy(ADMISSION / "android/app/src/main/java" / gate, ROOT / "build/shared" / gate)
        env = os.environ.copy()
        env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
        env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
        subprocess.run([str(EXPERIMENTS / "android-origin-probe/gradlew"), "-p", str(ROOT / "android"),
                        "--no-daemon", ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
        metadata["artifactSha256"] = sha(APK)
    else:
        copy(ROOT / "images.js", APP / "Fixtures/images.js")
        subprocess.run(["openssl", "x509", "-in", str(TLS_DIR / "ca.pem"), "-outform", "DER",
                        "-out", str(APP / "Fixtures/ca.der")], check=True)
        (APP / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleExecutable": "CookiePathsFollowup", "CFBundleIdentifier": PACKAGES["ios"],
            "CFBundleName": "Cookie Paths Follow-up", "CFBundlePackageType": "APPL",
            "CFBundleVersion": "1", "CFBundleShortVersionString": "0.0.1", "MinimumOSVersion": "17.0",
            "UIDeviceFamily": [1, 2], "UILaunchScreen": {}, "LSRequiresIPhoneOS": True,
        }))
        sdk = subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip()
        subprocess.run(["xcrun", "--sdk", "iphonesimulator", "swiftc", "-swift-version", "5",
                        "-parse-as-library", "-sdk", sdk, "-target", "arm64-apple-ios17.0-simulator",
                        "-framework", "UIKit", "-framework", "WebKit", str(ROOT / "ios/Probe.swift"),
                        "-o", str(APP / "CookiePathsFollowup")], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(APP)], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(APP)], check=True)
        metadata["artifactSha256"] = app_digest(APP)
        metadata["xcode"] = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    (LOCAL / f"{platform}-build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def android(owner, tag, port, expected):
    path = Path.home() / "Library/Android/sdk/platform-tools/adb"
    package = PACKAGES["android"]

    def adb(*parts, **options):
        return command([str(path), "-s", owner["serial"], *parts], **options)

    assert adb("emu", "avd", "name").stdout.splitlines()[0] == owner["avd"]
    mapping = f"tcp:{port}"
    adb("reverse", mapping, mapping)
    try:
        adb("install", "-r", str(APK))
        installed_path = adb("shell", "pm", "path", package).stdout.strip().removeprefix("package:")
        installed = hashlib.sha256(adb("exec-out", "cat", installed_path, binary=True).stdout).hexdigest()
        assert installed == expected
        adb("shell", "am", "force-stop", package)
        adb("shell", "run-as", package, "rm", "-f", "files/report.json")
        launch = adb("shell", "am", "start", "-W", "-n", package + "/org.moonpool.cookieadmission.FollowupActivity",
                     "--es", "run", tag, "--es", "base", f"https://localhost:{port}")
        assert "Error" not in launch.stdout, launch.stdout
        report = poll(lambda: adb("exec-out", "run-as", package, "cat", "files/report.json", check=False).stdout,
                      lambda: bool(adb("shell", "pidof", package, check=False).stdout.strip()), tag)
        return report, installed
    finally:
        adb("shell", "am", "force-stop", package, check=False)
        adb("reverse", "--remove", mapping, check=False)


def ios(owner, tag, port, expected):
    device, package = owner["owned"], PACKAGES["ios"]

    def sim(*parts, **options):
        return command(["xcrun", "simctl", *parts], **options)

    assert device not in owner["protected"]
    devices = json.loads(sim("list", "devices", "available", "-j").stdout)["devices"]
    state = next(item for group in devices.values() for item in group if item["udid"] == device)
    assert state["name"] == owner["name"] and state["state"] == "Booted"
    sim("install", device, str(APP))
    sim("terminate", device, package, check=False)
    installed = app_digest(Path(sim("get_app_container", device, package, "app").stdout.strip()))
    assert installed == expected
    output = Path(sim("get_app_container", device, package, "data").stdout.strip()) / "Documents/report.json"
    output.unlink(missing_ok=True)
    launch = sim("launch", device, package, "--run", tag, "--base", f"https://localhost:{port}")
    pid = int(launch.stdout.rsplit(":", 1)[1].strip())

    def alive():
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    try:
        return poll(lambda: output.read_text() if output.exists() else None, alive, tag), installed
    finally:
        sim("terminate", device, package, check=False)


def run(platform, name, owner_path):
    tag = f"{platform}-{name}"
    if not re.fullmatch("[a-z0-9-]{1,48}", tag):
        raise ValueError("Invalid run tag")
    metadata = json.loads((LOCAL / f"{platform}-build.json").read_text())
    assert metadata["sources"] == sources(platform) and metadata["caSha256"] == sha(TLS_DIR / "ca.pem")
    owner = json.loads(owner_path.read_text())
    port = json.loads((LOCAL / "server.json").read_text())["port"]
    log = TLS_DIR / "receipts.jsonl"
    if log.exists() and any(json.loads(line)["run"] == tag for line in log.read_text().splitlines()):
        raise ValueError("Run tag already has receipts")
    collect = android if platform == "android" else ios
    report, installed = collect(owner, tag, port, metadata["artifactSha256"])
    rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    report.update(build=metadata, installedArtifactSha256=installed,
                  receipts=[row for row in rows if row["run"] == tag],
                  capturedUtc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (LOCAL / f"{tag}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{tag}: complete={report['complete']}, receipts={len(report['receipts'])}")
    if not report["complete"]:
        print(report["errors"])
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "run"])
    parser.add_argument("platform", choices=PACKAGES)
    parser.add_argument("--run")
    parser.add_argument("--owner", type=Path)
    args = parser.parse_args()
    if args.action == "build":
        build(args.platform)
    elif args.run is not None and args.owner is not None:
        run(args.platform, args.run, args.owner)
    else:
        parser.error("run needs a tag and the device owner record")


if __name__ == "__main__":
    main()
