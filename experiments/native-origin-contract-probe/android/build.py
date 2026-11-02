"""Build the isolated T28 probe with the historical pinned Gradle wrapper."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent
WRAPPER = ROOT.parents[1] / "android-origin-probe/gradlew"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fingerprints():
    paths = [*ROOT.glob("*.py"), *ROOT.glob("*.gradle"), ROOT / "gradle.properties", ROOT / "app/build.gradle",
             *ROOT.glob("app/src/main/**/*"), *ROOT.glob("test/*.java")]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths) if p.is_file()}

def main():
    env = os.environ.copy()
    env.setdefault("JAVA_HOME", "/Applications/Android Studio.app/Contents/jbr/Contents/Home")
    env.setdefault("ANDROID_HOME", str(Path.home() / "Library/Android/sdk"))
    subprocess.run([str(WRAPPER), "-p", str(ROOT), "--no-daemon", ":app:assembleDebug", ":app:lintDebug"], env=env, check=True)
    metadata = {"apkSha256": sha(ROOT / "app/build/outputs/apk/debug/app-debug.apk"), "sources": fingerprints(),
                "identityVectorsSha256": sha(ROOT.parent / "identity-vectors.json"),
                "reusedWrapperSha256": sha(WRAPPER), "reusedWrapperPropertiesSha256": sha(WRAPPER.parent / "gradle/wrapper/gradle-wrapper.properties")}
    (ROOT / "local-results").mkdir(exist_ok=True)
    (ROOT / "local-results/build-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("T28 APK/lint complete; artifact/source/asset hashes saved.")

if __name__ == "__main__":
    main()
