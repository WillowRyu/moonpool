"""Compile/run the native admission contract without a simulator or packages."""

import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--java-home", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="moonpool-t25-test-") as output:
    subprocess.run([str(args.java_home / "bin/javac"), "-d", output,
        str(root / "app/src/main/java/org/moonpool/messageprobe/Admission.java"),
        str(root / "test/AdmissionTest.java")], check=True)
    subprocess.run([str(args.java_home / "bin/java"), "-cp", output,
        "org.moonpool.messageprobe.AdmissionTest"], check=True)
