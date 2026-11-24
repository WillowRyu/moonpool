"""Collect the native admission and writer order comparison on the explicitly owned emulator."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from check import ROOT, classify, sha, source_fingerprints

sys.path.insert(0, str(ROOT.parent))
from runner import command, poll

LOCAL = ROOT / "local-results"
APK = ROOT / "android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE = "org.moonpool.admissionwriterorder"
ACTIVITY = "org.moonpool.cookieadmission.AdmissionWriterOrderActivity"


def build():
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
    env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
    wrapper = ROOT.parent.parent / "android-origin-probe/gradlew"
    sources = source_fingerprints()
    experiments = ROOT.parent.parent
    gate = Path("org/moonpool/cookieadmission/AdmissionGate.java")
    shared = ROOT / "build/shared" / gate
    shared.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(experiments / "native-cookie-admission-probe/android/app/src/main/java" / gate, shared)
    subprocess.run([str(wrapper), "-p", str(ROOT / "android"), "--no-daemon",
                    ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
    if sources != source_fingerprints():
        raise RuntimeError("Sources changed during build")
    LOCAL.mkdir(exist_ok=True)
    metadata = {"sources": sources, "artifactSha256": sha(APK)}
    (LOCAL / "android-build.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def collect(tag, owner_path):
    run = "android-" + tag
    if not re.fullmatch("[a-z0-9-]{1,28}", run):
        raise ValueError("Invalid probe run tag")
    output = LOCAL / f"{run}.json"
    if output.exists():
        raise ValueError("Use a fresh tag")
    metadata = json.loads((LOCAL / "android-build.json").read_text())
    if metadata["sources"] != source_fingerprints() or metadata["artifactSha256"] != sha(APK):
        raise RuntimeError("Changed build sources or artifact")
    owner = json.loads(owner_path.read_text())
    adb_path = Path.home() / "Library/Android/sdk/platform-tools/adb"

    def adb(*args, **options):
        return command([str(adb_path), "-s", owner["serial"], *args], **options)

    if adb("emu", "avd", "name").stdout.splitlines()[:1] != [owner["avd"]]:
        raise RuntimeError("Wrong emulator")
    adb("install", "-r", str(APK))
    installed_path = adb("shell", "pm", "path", PACKAGE).stdout.strip().removeprefix("package:")
    installed = hashlib.sha256(adb("exec-out", "cat", installed_path, binary=True).stdout).hexdigest()
    if installed != metadata["artifactSha256"]:
        raise RuntimeError("Unexpected installed APK")
    try:
        adb("shell", "am", "force-stop", PACKAGE)
        if adb("shell", "pidof", PACKAGE, check=False).stdout.strip():
            raise RuntimeError("App did not stop")
        adb("shell", "run-as", PACKAGE, "rm", "-f", "files/report.json")
        launch = adb("shell", "am", "start", "-W", "-n", f"{PACKAGE}/{ACTIVITY}", "--es", "run", run)
        if "Error" in launch.stdout:
            raise RuntimeError(launch.stdout)
        report = poll(lambda: adb("exec-out", "run-as", PACKAGE, "cat", "files/report.json", check=False).stdout,
                      lambda: bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip()), run)
    finally:
        adb("shell", "am", "force-stop", PACKAGE, check=False)
    report.update({
        "build": metadata,
        "installedArtifactSha256": installed,
        "capturedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    with output.open("x") as file:
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
            parser.error("run requires a fresh tag and emulator owner record")
        collect(args.run, args.owner)


if __name__ == "__main__":
    main()
