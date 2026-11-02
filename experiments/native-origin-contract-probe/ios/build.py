"""Build the simulator-only T28 app with installed tools, no downloads."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
APP = ROOT / "build/OriginContractProbe.app"
APP.mkdir(parents=True, exist_ok=True)
shutil.copytree(ROOT / "fixtures", APP / "Fixtures", dirs_exist_ok=True)
shutil.copy2(ROOT.parent / "identity-vectors.json", APP / "Fixtures/identity-vectors.json")
info = {"CFBundleExecutable": "OriginContractProbe", "CFBundleIdentifier": "org.moonpool.iosorigincontractprobe",
        "CFBundleName": "Moonpool T28 probe", "CFBundlePackageType": "APPL", "CFBundleVersion": "1",
        "CFBundleShortVersionString": "0.0.1", "MinimumOSVersion": "17.0", "UIDeviceFamily": [1, 2],
        "UILaunchScreen": {}, "LSRequiresIPhoneOS": True}
(APP / "Info.plist").write_bytes(plistlib.dumps(info))
sdk = subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip()
subprocess.run(["xcrun", "--sdk", "iphonesimulator", "swiftc", "-swift-version", "5", "-parse-as-library", "-sdk", sdk,
                "-target", "arm64-apple-ios17.0-simulator", "-framework", "UIKit", "-framework", "WebKit",
                *[str(ROOT / file) for file in ["Admission.swift", "StoreRegistry.swift", "Probe.swift"]],
                "-o", str(APP / "OriginContractProbe")], check=True)
subprocess.run(["codesign", "--force", "--sign", "-", str(APP)], check=True)
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(APP)], check=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
version = subprocess.check_output(["xcrun", "vtool", "-show-build", str(APP / "OriginContractProbe")], text=True)
metadata = {"executableSha256": sha(APP / "OriginContractProbe"), "bundleSignatureSha256": sha(APP / "_CodeSignature/CodeResources"),
            "sources": {str(path.relative_to(ROOT)): sha(path) for path in sorted(ROOT.rglob("*"))
                        if path.is_file() and path.suffix in {".py", ".swift", ".js", ".html"} and not any(p in {"build", "local-results"} for p in path.relative_to(ROOT).parts)},
            "fixtures": {str(path.relative_to(APP / "Fixtures")): sha(path) for path in sorted((APP / "Fixtures").rglob("*")) if path.is_file()},
            "buildPlatform": [line.strip() for line in version.splitlines() if any(x in line for x in ["platform ", "minos ", "sdk "])],
            "xcode": subprocess.check_output(["xcodebuild", "-version"], text=True).strip(),
            "swift": subprocess.check_output(["xcrun", "swiftc", "--version"], text=True).strip(),
            "sdk": subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], text=True).strip(),
            "codesignVerified": True}
(ROOT / "build/build-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print("Built and ad-hoc signed T28 research app.")
