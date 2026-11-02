"""Run the Swift metadata admission contract without booting a simulator."""

from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="moonpool-t26-test-") as directory:
    executable = str(Path(directory) / "admission-test")
    subprocess.run(["xcrun", "--sdk", "macosx", "swiftc", "-swift-version", "5", "-parse-as-library",
        str(root / "Admission.swift"), str(root / "test/AdmissionTest.swift"), "-o", executable], check=True)
    subprocess.run([executable], check=True)
