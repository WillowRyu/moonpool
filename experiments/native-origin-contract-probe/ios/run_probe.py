"""Run only the dedicated locally owned simulator; never use implicit booted targets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PACKAGE = "org.moonpool.iosorigincontractprobe"
p = argparse.ArgumentParser()
p.add_argument("--phase", choices=["seed", "restart"], required=True)
p.add_argument("--run", choices=["first", "repeat"], required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
owned = json.loads((ROOT / "local-results/simulator.json").read_text())
assert owned["owned"] not in owned["protected"]
def call(*parts, check=True):
    return subprocess.run(["xcrun", "simctl", *parts], capture_output=True, text=True, check=check, timeout=30)
devices = json.loads(call("list", "devices", "available", "-j").stdout)["devices"]
target = next(d for group in devices.values() for d in group if d["udid"] == owned["owned"])
assert target["name"] == "Moonpool T28 Origin Contract" and target["state"] == "Booted"
call("terminate", owned["owned"], PACKAGE, check=False)
installed = Path(call("get_app_container", owned["owned"], PACKAGE, "app").stdout.strip())
metadata = json.loads((ROOT / "build/build-metadata.json").read_text())
installed_hash = hashlib.sha256((installed / "OriginContractProbe").read_bytes()).hexdigest()
assert installed_hash == metadata["executableSha256"]
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(installed)], check=True, capture_output=True)
container = Path(call("get_app_container", owned["owned"], PACKAGE, "data").stdout.strip())
report_file = container / "Documents/report.json"
report_file.unlink(missing_ok=True)
call("launch", owned["owned"], PACKAGE, "--phase", args.phase, "--run", args.run)
deadline = time.monotonic() + 340
while time.monotonic() < deadline:
    if report_file.exists():
        report = json.loads(report_file.read_text())
        if report.get("complete") and report.get("phase") == args.phase and report.get("run") == args.run:
            report["buildMetadata"] = metadata
            report["installedExecutableSha256"] = installed_hash
            report["installedSignatureVerified"] = True
            report["restartBoundary"] = "terminated app process then launched same installed app and durable stores"
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            print(f"{args.run}/{args.phase}: {len(report['samples'])} samples, {len(report['identity'])} identity observations", flush=True)
            break
    time.sleep(0.4)
else:
    raise SystemExit("No completed T28 report before deadline; simulator left owned and inspectable")
