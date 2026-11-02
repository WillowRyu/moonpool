"""Minimal no-guest first-use vs initialized API-order control on the owned simulator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PACKAGE = "org.moonpool.iosorigincontractprobe"
p = argparse.ArgumentParser()
p.add_argument("--mode", choices=["cold", "cold-callback", "initialized"], required=True)
p.add_argument("--repeat", choices=["first", "repeat"], required=True)
p.add_argument("--output", required=True, type=Path)
args = p.parse_args()
ownership = json.loads((ROOT / "local-results/simulator.json").read_text())
owned = ownership["owned"]
assert owned not in ownership["protected"]
def call(*parts, check=True):
    return subprocess.run(["xcrun", "simctl", *parts], check=check, capture_output=True, text=True, timeout=30)
devices = json.loads(call("list", "devices", "available", "-j").stdout)["devices"]
target = next(d for group in devices.values() for d in group if d["udid"] == owned)
assert target["name"] == "Moonpool T28 Origin Contract" and target["state"] == "Booted"
call("terminate", owned, PACKAGE, check=False)
container = Path(call("get_app_container", owned, PACKAGE, "data").stdout.strip())
installed = Path(call("get_app_container", owned, PACKAGE, "app").stdout.strip())
metadata = json.loads((ROOT / "build/build-metadata.json").read_text())
assert hashlib.sha256((installed / "OriginContractProbe").read_bytes()).hexdigest() == metadata["executableSha256"]
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(installed)], check=True, capture_output=True)
report_file = container / "Documents/report.json"
before_file = container / "Documents/startup-before.json"
report_file.unlink(missing_ok=True)
before_file.unlink(missing_ok=True)
started = time.time()
launch = call("launch", owned, PACKAGE, "--phase", "startup", "--run", args.repeat, "--startup-control", args.mode)
launched_pid = int(launch.stdout.strip().rsplit(":", 1)[1])
result = {"mode": args.mode, "repeat": args.repeat, "buildMetadata": metadata,
          "installedExecutableSha256": metadata["executableSha256"], "installedSignatureVerified": True,
          "scope": "API-order diagnostic; zero guest document loads; no default store"}
for _ in range(150):
    if report_file.exists():
        result["outcome"] = "completed"
        result["report"] = json.loads(report_file.read_text())
        break
    # Read only crash reports belonging to this probe. Retain only public symbols and exception signature.
    crashes = [f for f in (Path.home() / "Library/Logs/DiagnosticReports").glob("OriginContractProbe*.ips")
               if f.stat().st_mtime >= started]
    matching = [json.loads(file.read_text().split("\n", 1)[1]) for file in crashes]
    matching = [crash for crash in matching if crash.get("pid") == launched_pid and crash.get("bundleInfo", {}).get("CFBundleIdentifier") == PACKAGE]
    if matching:
        crash = matching[-1]
        result["crashMatchedLaunchProcess"] = True
        thread = next(t for t in crash["threads"] if t.get("triggered"))
        result["outcome"] = "crashed"
        result["crash"] = {"exceptionType": crash["exception"]["type"], "signal": crash["exception"]["signal"],
                           "frames": [{"symbol": f.get("symbol", "unsymbolicated"),
                                       "image": crash["usedImages"][f["imageIndex"]]["name"]} for f in thread["frames"][:12]]}
        break
    time.sleep(0.2)
else:
    raise SystemExit("No completion/crash signature before startup-control deadline")
assert before_file.exists()
result["beforeCall"] = json.loads(before_file.read_text())
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(f"{args.mode}/{args.repeat}: {result['outcome']}")
