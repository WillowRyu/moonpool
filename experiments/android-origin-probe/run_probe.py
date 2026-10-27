"""Launch only the installed research app on an explicitly selected emulator."""

import argparse
import json
import hashlib
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--serial", required=True)
parser.add_argument("--profile", required=True, choices=["asset-loader-custom", "intercept-custom", "https-control"])
parser.add_argument("--phase", required=True, choices=["seed", "restart"])
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
if not args.serial.startswith("emulator-"):
    parser.error("T23 targets an emulator, not a physical device")
package = "org.moonpool.originprobe"
adb = ["adb", "-s", args.serial]


def command(*parts, check=True):
    return subprocess.run(adb + list(parts), capture_output=True, text=True, timeout=15, check=check)


command("shell", "am", "force-stop", package)
command("shell", "run-as", package, "rm", "-f", "files/report.json")
command("shell", "am", "start", "-n", package + "/.ProbeActivity", "--es", "profile", args.profile, "--es", "phase", args.phase)
deadline = time.monotonic() + 100
while time.monotonic() < deadline:
    result = command("exec-out", "run-as", package, "cat", "files/report.json", check=False)
    if result.returncode == 0:
        try:
            report = json.loads(result.stdout)
            if report.get("complete") and report["profile"] == args.profile and report["phase"] == args.phase:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                report["apkSha256"] = hashlib.sha256(Path("app/build/outputs/apk/debug/app-debug.apk").read_bytes()).hexdigest()
                args.output.write_text(json.dumps(report, indent=2) + "\n")
                print(f"{args.profile}/{args.phase}: {len(report['samples'])} observations exported", flush=True)
                break
        except json.JSONDecodeError:
            pass
    time.sleep(0.5)
else:
    raise SystemExit("No complete report within 100 seconds; inspect only this app's logs")
