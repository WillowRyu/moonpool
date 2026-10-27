"""Run only this research app on the explicitly owned T24 simulator."""

import argparse
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--profile", required=True, choices=["custom-scheme", "http-control"])
parser.add_argument("--phase", required=True, choices=["seed", "restart"])
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
ownership = json.loads((root / "local-results/simulator.json").read_text())
owned = ownership["owned"]
assert owned not in [device["id"] for device in ownership["protected"]]
devices = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "--json"], text=True))["devices"]
target = next(d for group in devices.values() for d in group if d["udid"] == owned)
assert target["name"] == "Moonpool T24 Origin Probe" and target["state"] == "Booted"
package = "org.moonpool.iosoriginprobe"


def command(*parts, check=True):
    return subprocess.run(["xcrun", "simctl", *parts], capture_output=True, text=True, timeout=25, check=check)


command("terminate", owned, package, check=False)
container = Path(command("get_app_container", owned, package, "data").stdout.strip())
report_file = container / "Documents/report.json"
report_file.unlink(missing_ok=True)
command("launch", owned, package, "--profile", args.profile, "--phase", args.phase)
deadline = time.monotonic() + 220
while time.monotonic() < deadline:
    if report_file.exists():
        try:
            report = json.loads(report_file.read_text())
            if report.get("complete") and report["profile"] == args.profile and report["phase"] == args.phase:
                report["buildMetadata"] = json.loads((root / "build/build-metadata.json").read_text())
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
                print(f"{args.profile}/{args.phase}: {len(report['samples'])} observations exported", flush=True)
                break
        except json.JSONDecodeError:
            pass
    time.sleep(0.5)
else:
    raise SystemExit("No completed research report before the deadline")
