"""Build and collect the C09 worker-prevention probe on an owned AVD."""

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

from check import CASES, ROOT, classify, seed_failures, sha, source_fingerprints

sys.path.insert(0, str(ROOT.parent))
from runner import command, poll

EXPERIMENTS = ROOT.parent.parent
LOCAL = ROOT / "local-results"
APK = ROOT / "android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE = "org.moonpool.workerprevention"
ACTIVITY = "org.moonpool.cookieadmission.WorkerPreventionActivity"


def write_report(path, report):
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def build():
    assets = ROOT / "build/assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "register.js", assets / "register.js")
    for name in ("store.js", "worker.js"):
        shutil.copyfile(ROOT.parent / "worker-admission" / name, assets / name)
    gate = Path("org/moonpool/cookieadmission/AdmissionGate.java")
    shared = ROOT / "build/shared" / gate
    shared.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EXPERIMENTS / "native-cookie-admission-probe/android/app/src/main/java" / gate, shared)
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
    env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
    fingerprint = source_fingerprints()
    subprocess.run([str(EXPERIMENTS / "android-origin-probe/gradlew"), "-p", str(ROOT / "android"),
                    "--no-daemon", ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
    if fingerprint != source_fingerprints():
        raise RuntimeError("Sources changed during the build")
    LOCAL.mkdir(exist_ok=True)
    write_report(LOCAL / "android-build.json", {"sources": fingerprint, "artifactSha256": sha(APK)})


def collect(name, owner_path):
    run = "android-" + name
    if not re.fullmatch("[a-z0-9-]{1,28}", run):
        raise ValueError("Invalid probe run tag")
    paths = {label: LOCAL / f"{run}-{label}.json" for label in ("seed", *CASES)}
    target = LOCAL / f"{run}.json"
    if target.exists() or any(path.exists() for path in paths.values()):
        raise ValueError("Use a fresh tag for each collection")
    metadata = json.loads((LOCAL / "android-build.json").read_text())
    if metadata["sources"] != source_fingerprints():
        raise RuntimeError("Changed build sources")
    if metadata["artifactSha256"] != sha(APK):
        raise RuntimeError("Changed build artifact")
    owner = json.loads(owner_path.read_text())
    path = Path.home() / "Library/Android/sdk/platform-tools/adb"

    def adb(*parts, **options):
        return command([str(path), "-s", owner["serial"], *parts], **options)

    avd = adb("emu", "avd", "name").stdout.splitlines()
    if not avd or avd[0] != owner["avd"]:
        raise RuntimeError("Wrong emulator")
    adb("install", "-r", str(APK))
    installed_path = adb("shell", "pm", "path", PACKAGE).stdout.strip().removeprefix("package:")
    installed = hashlib.sha256(adb("exec-out", "cat", installed_path, binary=True).stdout).hexdigest()
    if installed != metadata["artifactSha256"]:
        raise RuntimeError("Unexpected installed APK")

    def process(phase, case=None):
        adb("shell", "am", "force-stop", PACKAGE)
        if adb("shell", "pidof", PACKAGE, check=False).stdout.strip():
            raise RuntimeError("App did not stop")
        adb("shell", "run-as", PACKAGE, "rm", "-f", "files/report.json")
        extra = ["--es", "case", case] if case else []
        launch = adb("shell", "am", "start", "-W", "-n", f"{PACKAGE}/{ACTIVITY}",
                     "--es", "run", run, "--es", "phase", phase, *extra)
        if "Error" in launch.stdout:
            raise RuntimeError(launch.stdout)
        report = poll(lambda: adb("exec-out", "run-as", PACKAGE, "cat", "files/report.json", check=False).stdout,
                      lambda: bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip()), run)
        label = case or phase
        write_report(paths[label], report)
        if report["phase"] != phase or report.get("case") != case:
            raise RuntimeError("Wrong report phase")
        print(f"{label}: process {report['pid']}, completed={report['complete']}, verdict={report.get('verdict')}")
        if report.get("error"):
            print(report["error"])
        return report

    try:
        seed = process("seed")
        failures = seed_failures(run, seed)
        if failures:
            raise RuntimeError("\n".join(failures))
        checks = [process("check", case) for case in CASES]
    finally:
        adb("shell", "am", "force-stop", PACKAGE, check=False)
    report = {"run": run, "seed": seed, "checks": checks, "build": metadata, "installedArtifactSha256": installed,
              "capturedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_report(target, report)
    failures = classify(report)
    for issue in failures:
        print(issue)
    print(f"{target.name}: {len(checks)} cold admissions, {len(failures)} failures")
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
