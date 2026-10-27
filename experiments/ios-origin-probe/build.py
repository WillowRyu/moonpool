"""Build a simulator-only probe with the installed Xcode tools; no packages."""

from pathlib import Path
import hashlib
import json
import plistlib
import shutil
import subprocess

root = Path(__file__).resolve().parent
app = root / "build/OriginProbe.app"
app.mkdir(parents=True, exist_ok=True)
source = root.parent / "android-origin-probe/app/src/main/assets"
fixtures = app / "Fixtures"
shutil.copytree(source, fixtures, dirs_exist_ok=True)
base_script = (source / "common/probe.js").read_text()
script = base_script.replace("t23", "t24")
script = script.replace(
    "const cross = `${location.protocol}//${otherHost}/assets/`;",
    "const cross = params.get('cross') || `${location.protocol}//${otherHost}/assets/`;",
)
script = script.replace(
    "fetchResult(`${location.protocol}//com.example.probe.unknown.test/assets/data.json`)",
    "fetchResult(params.get('unknown') || `${location.protocol}//com.example.probe.unknown/assets/data.json`)",
)
assert script != base_script and "params.get('cross')" in script and "params.get('unknown')" in script
(fixtures / "common/probe.js").write_text(script)
for html in fixtures.glob("apps/*/*.html"):
    html.write_text(html.read_text().replace("T23", "T24").replace("t23", "t24"))
info = {
    "CFBundleExecutable": "OriginProbe", "CFBundleIdentifier": "org.moonpool.iosoriginprobe",
    "CFBundleName": "Moonpool T24 probe", "CFBundlePackageType": "APPL",
    "CFBundleVersion": "1", "CFBundleShortVersionString": "0.0.1", "MinimumOSVersion": "17.0",
    "UIDeviceFamily": [1, 2], "UILaunchScreen": {}, "LSRequiresIPhoneOS": True,
    "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True,
        "NSExceptionDomains": {"localhost": {"NSExceptionAllowsInsecureHTTPLoads": True,
                                               "NSIncludesSubdomains": False}}},
}
with (app / "Info.plist").open("wb") as file:
    plistlib.dump(info, file)
sdk = subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip()
subprocess.run(["xcrun", "swiftc", "-swift-version", "5", "-parse-as-library", "-sdk", sdk,
    "-target", "arm64-apple-ios17.0-simulator", "-framework", "UIKit", "-framework", "WebKit",
    str(root / "Probe.swift"), "-o", str(app / "OriginProbe")], check=True)
subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
metadata = {"baseAndroidScriptSha256": hashlib.sha256(base_script.encode()).hexdigest(),
    "executableSha256": hashlib.sha256((app / "OriginProbe").read_bytes()).hexdigest(),
    "probeSwiftSha256": hashlib.sha256((root / "Probe.swift").read_bytes()).hexdigest(),
    "adaptedScriptSha256": hashlib.sha256(script.encode()).hexdigest()}
(root / "build/build-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print("Built and ad-hoc signed arm64 simulator research app.")
