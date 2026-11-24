"""Build and collect the worker-admission probe on the explicitly owned AVD."""

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

from check import CASES, ROOT, classify, sha, sources

sys.path.insert(0, str(ROOT.parent))
from runner import command, poll

EXPERIMENTS = ROOT.parent.parent
LOCAL = ROOT / "local-results"
APK = ROOT / "android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE = "org.moonpool.workeradmission"


def build():
    assets = ROOT / "build/assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("seed.js", "worker.js", "inspect.js", "store.js"):
        shutil.copyfile(ROOT / name, assets / name)
    gate = Path("org/moonpool/cookieadmission/AdmissionGate.java")
    shared = ROOT / "build/shared" / gate
    shared.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EXPERIMENTS / "native-cookie-admission-probe/android/app/src/main/java" / gate, shared)
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
    env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
    subprocess.run([str(EXPERIMENTS / "android-origin-probe/gradlew"), "-p", str(ROOT / "android"),
                    "--no-daemon", ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
    metadata = {"sources": sources(), "artifactSha256": sha(APK)}
    LOCAL.mkdir(exist_ok=True)
    (LOCAL / "android-build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def collect(name, owner_path):
    run = "android-" + name
    if not re.fullmatch("[a-z0-9-]{1,28}", run):
        raise ValueError("Invalid probe run tag")
    target = LOCAL / f"{run}.json"
    if target.exists() or (LOCAL / f"{run}-seed.json").exists():
        raise ValueError("Use a fresh tag for each collection")
    metadata = json.loads((LOCAL / "android-build.json").read_text())
    assert metadata["sources"] == sources(), "Changed build sources"
    owner = json.loads(owner_path.read_text())
    path = Path.home() / "Library/Android/sdk/platform-tools/adb"

    def adb(*parts, **options):
        return command([str(path), "-s", owner["serial"], *parts], **options)

    assert adb("emu", "avd", "name").stdout.splitlines()[0] == owner["avd"], "Wrong emulator"
    adb("install", "-r", str(APK))
    installed_path = adb("shell", "pm", "path", PACKAGE).stdout.strip().removeprefix("package:")
    installed = hashlib.sha256(adb("exec-out", "cat", installed_path, binary=True).stdout).hexdigest()
    assert installed == metadata["artifactSha256"], "Unexpected installed APK"

    def process(phase, case=None):
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "run-as", PACKAGE, "rm", "-f", "files/report.json")
        extra = ["--es", "case", case] if case else []
        launch = adb("shell", "am", "start", "-W", "-n", PACKAGE + "/org.moonpool.cookieadmission.WorkerAdmissionActivity",
                     "--es", "run", run, "--es", "phase", phase, *extra)
        assert "Error" not in launch.stdout, launch.stdout
        report = poll(lambda: adb("exec-out", "run-as", PACKAGE, "cat", "files/report.json", check=False).stdout,
                      lambda: bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip()), run)
        assert report["phase"] == phase and report.get("case") == case, "Wrong report phase"
        label = case or phase
        (LOCAL / f"{run}-{label}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"{label}: process {report['pid']}, completed={report['complete']}, verdict={report.get('verdict')}")
        return report

    try:
        seed = process("seed")
        if not seed["complete"]:
            raise RuntimeError(seed.get("error", "Seed collection failed"))
        checks = [process("check", case) for case in CASES]
    finally:
        adb("shell", "am", "force-stop", PACKAGE, check=False)
    report = {"run": run, "seed": seed, "checks": checks, "build": metadata, "installedArtifactSha256": installed,
              "capturedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    failures = classify(report)
    for issue in failures:
        print(issue)
    print(f"{target.name}: {len(checks)} cold inspections, {len(failures)} failures")
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
            parser.error("run requires a fresh tag and the emulator owner record")
        collect(args.run, args.owner)


if __name__ == "__main__":
    main()
