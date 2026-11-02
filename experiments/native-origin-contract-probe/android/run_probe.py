"""Run only the explicitly owned Android emulator; never choose an arbitrary device."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
ADB = Path.home() / "Library/Android/sdk/platform-tools/adb"
PACKAGE = "org.moonpool.origincontract"

def run(serial, *args, binary=False):
    value = subprocess.check_output([str(ADB), "-s", serial, *args], text=not binary)
    return value if binary else value.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--phase", choices=["seed", "restart"], required=True)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    ownership = json.loads((ROOT / "local-results/owned-device.json").read_text())
    serial = ownership["serial"]
    if ownership["avd"] != "Pixel_7_Pro" or run(serial, "emu", "avd", "name").splitlines()[0] != "Pixel_7_Pro":
        raise RuntimeError("Explicit session-owned AVD mismatch")
    metadata = json.loads((ROOT / "local-results/build-metadata.json").read_text())
    if args.install:
        run(serial, "install", "-r", str(ROOT / "app/build/outputs/apk/debug/app-debug.apk"))
    remote_apk = run(serial, "shell", "pm", "path", PACKAGE).splitlines()[0].removeprefix("package:")
    installed = hashlib.sha256(run(serial, "exec-out", "cat", remote_apk, binary=True)).hexdigest()
    if installed != metadata["apkSha256"]:
        raise RuntimeError("Installed APK differs from the built fingerprint")
    run(serial, "shell", "am", "force-stop", PACKAGE)
    run(serial, "shell", "run-as", PACKAGE, "rm", "-f", "files/report.json")
    run(serial, "shell", "am", "start", "-n", PACKAGE + "/.ContractActivity", "--es", "tag", args.tag, "--es", "phase", args.phase)
    deadline = time.monotonic() + 200
    while time.monotonic() < deadline:
        try:
            raw = run(serial, "exec-out", "run-as", PACKAGE, "cat", "files/report.json")
            report = json.loads(raw)
            if report["tag"] == args.tag and report["phase"] == args.phase:
                break
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("No report before bounded deadline")
    report["build"] = metadata
    report["installedApkSha256"] = installed
    report["restartMethod"] = "am force-stop then new Activity/process; no data reset"
    report["capturedUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output = ROOT / "results" / (args.tag + "-" + args.phase + ".json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {output.name}: {len(report['samples'])} raw samples, MULTI_PROFILE={report['multiProfile']}")

if __name__ == "__main__":
    main()
