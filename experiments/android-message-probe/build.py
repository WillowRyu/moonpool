"""Build only the isolated probe using T23's unchanged pinned wrapper/cache."""

from pathlib import Path
import hashlib
import json
import os
import subprocess

root = Path(__file__).resolve().parent
env = os.environ.copy()
env["JAVA_HOME"] = "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
wrapper = root.parent / "android-origin-probe/gradlew"
subprocess.run([str(wrapper), "-p", str(root), "--offline", "--no-daemon", ":app:assembleDebug", ":app:lintDebug"],
               env=env, check=True)
apk = root / "app/build/outputs/apk/debug/app-debug.apk"
paths = sorted([*root.glob("*.gradle"), root / "gradle.properties", root / "app/build.gradle",
    root / "app/src/main/AndroidManifest.xml", *root.glob("app/src/main/java/**/*.java"),
    *root.glob("app/src/main/assets/*"), root / "build.py", root / "run_probe.py"])
metadata = {"apkSha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
    "sources": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()},
    "reusedWrapperSha256": hashlib.sha256(wrapper.read_bytes()).hexdigest(),
    "reusedWrapperPropertiesSha256": hashlib.sha256((wrapper.parent / "gradle/wrapper/gradle-wrapper.properties").read_bytes()).hexdigest()}
output = root / "local-results"
output.mkdir(exist_ok=True)
(output / "build-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print("Standalone T25 APK/lint complete; source and artifact fingerprints recorded.")
