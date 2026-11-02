"""Run pure JVM registration cases and the shared independently derived vectors."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
JAVA_HOME = Path(os.environ.get("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home"))

def main():
    local = ROOT / "local-results"
    local.mkdir(exist_ok=True)
    vectors = json.loads((ROOT.parent / "identity-vectors.json").read_text())["vectors"]
    table = local / "identity-vectors.tsv"
    table.write_text("\n".join("\t".join([str(v["manifestValid"]).lower(), v["id"], (v.get("key") or ""), (v.get("androidOrigin") or ""), (v.get("androidProfile") or "")]) for v in vectors))
    classes = local / "classes"
    classes.mkdir(exist_ok=True)
    subprocess.run([str(JAVA_HOME / "bin/javac"), "-d", str(classes), str(ROOT / "app/src/main/java/org/moonpool/origincontract/Registration.java"), str(ROOT / "test/RegistrationTest.java")], check=True)
    subprocess.run([str(JAVA_HOME / "bin/java"), "-cp", str(classes), "org.moonpool.origincontract.RegistrationTest", str(table)], check=True)

if __name__ == "__main__":
    main()
