"""Run only the new research package on this session's explicitly owned AVD."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=["https", "custom"], required=True)
parser.add_argument("--run", choices=["first", "repeat"], required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
ownership = json.loads((root / "local-results/ownership.json").read_text())
serial = ownership["owned"]
assert serial.startswith("emulator-") and serial not in [d["serial"] for d in ownership["protected"]]
package = "org.moonpool.messageprobe"


def command(*parts, check=True):
    return subprocess.run(["adb", "-s", serial, *parts], capture_output=True, text=True, timeout=20, check=check)


assert command("emu", "avd", "name").stdout.splitlines()[0] == ownership["avd"]
metadata = json.loads((root / "local-results/build-metadata.json").read_text())
for name, sha in metadata["sources"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
installed = command("shell", "pm", "path", package).stdout.strip().removeprefix("package:")
assert installed.startswith("/data/app/") and "\n" not in installed
assert command("shell", "sha256sum", installed).stdout.split()[0] == metadata["apkSha256"]
command("shell", "am", "force-stop", package)
command("shell", "run-as", package, "rm", "-f", "files/report.json")
command("shell", "am", "start", "-n", package + "/.MessageProbeActivity", "--es", "profile", args.profile, "--es", "run", args.run)
deadline = time.monotonic() + 160
while time.monotonic() < deadline:
    result = command("exec-out", "run-as", package, "cat", "files/report.json", check=False)
    if result.returncode == 0:
        try:
            report = json.loads(result.stdout)
            if report.get("complete") and report["profile"] == args.profile and report["run"] == args.run:
                report["buildMetadata"] = metadata
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2) + "\n")
                print(f"{args.profile}/{args.run}: {len(report['samples'])} snapshots exported", flush=True)
                break
        except json.JSONDecodeError:
            pass
    time.sleep(0.4)
else:
    raise SystemExit("No completed T25 report; inspect only the owned probe package")
