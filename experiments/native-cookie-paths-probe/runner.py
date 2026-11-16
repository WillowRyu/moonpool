"""Build and collect the C09 probe on a specifically owned, booted device."""

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

from server import ROOT, TLS_DIR, certificates
from verify import sha, source_fingerprints

ADMISSION = ROOT.parent / "native-cookie-admission-probe"
PACKAGES = {"android": "org.moonpool.cookiepaths", "ios": "org.moonpool.ioscookiepaths"}
APP = ROOT / "build/CookiePathsProbe.app"
APK = ROOT / "android/app/build/outputs/apk/debug/app-debug.apk"
OUTPUT = ROOT / "local-results"


def app_digest(app):
    names = ["CookiePathsProbe", "Fixtures/paths.js", "Fixtures/ca.der", "_CodeSignature/CodeResources"]
    return hashlib.sha256("".join(sha(app / name) for name in names).encode()).hexdigest()


def build(platform):
    certificates(TLS_DIR)
    metadata = {"sources": source_fingerprints(platform), "caSha256": sha(TLS_DIR / "ca.pem")}
    if platform == "android":
        paths = {
            ROOT / "paths.js": ROOT / "build/assets/paths.js",
            TLS_DIR / "ca.pem": ROOT / "build/res/raw/probe_ca.pem",
            ADMISSION / "android/app/src/main/res/xml/network_security_config.xml":
                ROOT / "build/res/xml/network_security_config.xml",
            ADMISSION / "android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java":
                ROOT / "build/shared/org/moonpool/cookieadmission/AdmissionGate.java",
        }
        for source, target in paths.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        env = os.environ.copy()
        env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
        env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
        wrapper = ROOT.parent / "android-origin-probe/gradlew"
        subprocess.run([str(wrapper), "-p", str(ROOT / "android"), "--no-daemon",
                        ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
        metadata["artifactSha256"] = sha(APK)
    else:
        fixtures = APP / "Fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "paths.js", fixtures / "paths.js")
        subprocess.run(["openssl", "x509", "-in", str(TLS_DIR / "ca.pem"), "-outform", "DER",
                        "-out", str(fixtures / "ca.der")], check=True)
        (APP / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleExecutable": "CookiePathsProbe", "CFBundleIdentifier": PACKAGES["ios"],
            "CFBundleName": "Cookie Paths Probe", "CFBundlePackageType": "APPL", "CFBundleVersion": "1",
            "MinimumOSVersion": "17.0", "UIDeviceFamily": [1, 2], "UILaunchScreen": {}, "LSRequiresIPhoneOS": True,
        }))
        sdk = subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip()
        subprocess.run(["xcrun", "--sdk", "iphonesimulator", "swiftc", "-swift-version", "5",
                        "-parse-as-library", "-sdk", sdk, "-target", "arm64-apple-ios17.0-simulator",
                        "-framework", "UIKit", "-framework", "WebKit",
                        str(ADMISSION / "ios/AdmissionGate.swift"), str(ROOT / "ios/Probe.swift"),
                        "-o", str(APP / "CookiePathsProbe")], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", str(APP)], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(APP)], check=True)
        metadata["artifactSha256"] = app_digest(APP)
        metadata["xcode"] = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    (OUTPUT / f"{platform}-build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def command(parts, *, binary=False, check=True):
    return subprocess.run(parts, capture_output=True, text=not binary, check=check, timeout=45)


def poll(read, alive, tag):
    started = time.monotonic()
    while time.monotonic() - started < 180:
        try:
            report = json.loads(read() or "null")
        except json.JSONDecodeError:
            report = None
        if isinstance(report, dict) and report.get("run") == tag:
            return report
        if time.monotonic() - started > 5 and not alive():
            raise RuntimeError("Probe process exited unexpectedly")
        time.sleep(0.5)
    raise TimeoutError("No report before the collection deadline")


def collect_android(owner, tag, base, port, expected):
    adb_path = Path.home() / "Library/Android/sdk/platform-tools/adb"
    package = PACKAGES["android"]

    def adb(*parts, **options):
        return command([str(adb_path), "-s", owner["serial"], *parts], **options)

    assert adb("emu", "avd", "name").stdout.splitlines()[0] == owner["avd"], "Wrong emulator"
    mapping = f"tcp:{port}"
    adb("reverse", mapping, mapping)
    try:
        adb("install", "-r", str(APK))
        installed_path = adb("shell", "pm", "path", package).stdout.strip().removeprefix("package:")
        installed = hashlib.sha256(adb("exec-out", "cat", installed_path, binary=True).stdout).hexdigest()
        assert installed == expected, "Unexpected APK"
        adb("shell", "am", "force-stop", package)
        adb("shell", "run-as", package, "rm", "-f", "files/report.json")
        launch = adb("shell", "am", "start", "-n", package + "/org.moonpool.cookieadmission.PathsActivity",
                     "--es", "run", tag, "--es", "base", base)
        assert "Error" not in launch.stdout, launch.stdout
        report = poll(lambda: adb("exec-out", "run-as", package, "cat", "files/report.json", check=False).stdout,
                      lambda: bool(adb("shell", "pidof", package, check=False).stdout.strip()), tag)
        return report, installed
    finally:
        adb("shell", "am", "force-stop", package, check=False)
        adb("reverse", "--remove", mapping, check=False)


def collect_ios(owner, tag, base, expected):
    device = owner["owned"]
    package = PACKAGES["ios"]

    def sim(*parts, **options):
        return command(["xcrun", "simctl", *parts], **options)

    assert device not in owner["protected"]
    devices = json.loads(sim("list", "devices", "available", "-j").stdout)["devices"]
    state = next(item for group in devices.values() for item in group if item["udid"] == device)
    assert state["name"] == owner["name"] and state["state"] == "Booted", "Wrong simulator"
    sim("install", device, str(APP))
    sim("terminate", device, package, check=False)
    installed_app = Path(sim("get_app_container", device, package, "app").stdout.strip())
    installed = app_digest(installed_app)
    assert installed == expected, "Unexpected simulator app"
    output = Path(sim("get_app_container", device, package, "data").stdout.strip()) / "Documents/report.json"
    output.unlink(missing_ok=True)
    launch = sim("launch", device, package, "--run", tag, "--base", base)
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
    if not re.fullmatch("[a-z0-9-]+", tag):
        raise ValueError("Invalid run tag")
    metadata = json.loads((OUTPUT / f"{platform}-build.json").read_text())
    assert metadata["sources"] == source_fingerprints(platform)
    assert metadata["caSha256"] == sha(TLS_DIR / "ca.pem")
    owner = json.loads(owner_path.read_text())
    port = json.loads((OUTPUT / "server.json").read_text())["port"]
    base = f"https://localhost:{port}"
    log = TLS_DIR / "receipts.jsonl"
    if log.exists() and any(json.loads(line)["run"] == tag for line in log.read_text().splitlines()):
        raise ValueError("Run tag already has receipts")
    if platform == "android":
        report, installed = collect_android(owner, tag, base, port, metadata["artifactSha256"])
    else:
        report, installed = collect_ios(owner, tag, base, metadata["artifactSha256"])
    rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    report.update(build=metadata, installedArtifactSha256=installed,
                  receipts=[row for row in rows if row["run"] == tag],
                  capturedUtc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    target = OUTPUT / f"{tag}.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{tag}: complete={report['complete']}, samples={len(report['samples'])}, receipts={len(report['receipts'])}")
    if not report["complete"]:
        print({"errors": report["errors"]})
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
    else:
        if args.run is None or args.owner is None:
            parser.error("run needs an explicit tag and device owner record")
        run(args.platform, args.run, args.owner)


if __name__ == "__main__":
    main()
