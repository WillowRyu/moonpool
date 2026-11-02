"""Build/sign a simulator-only app with the installed pinned Xcode tools."""

from pathlib import Path
import hashlib
import json
import plistlib
import shutil
import subprocess

root = Path(__file__).resolve().parent
app = root / "build/MessageProbe.app"
app.mkdir(parents=True, exist_ok=True)
shutil.copytree(root / "fixtures", app / "Fixtures", dirs_exist_ok=True)
info = {"CFBundleExecutable":"MessageProbe", "CFBundleIdentifier":"org.moonpool.iosmessageprobe",
    "CFBundleName":"Moonpool T26 probe", "CFBundlePackageType":"APPL", "CFBundleVersion":"1",
    "CFBundleShortVersionString":"0.0.1", "MinimumOSVersion":"17.0", "UIDeviceFamily":[1,2],
    "UILaunchScreen":{}, "LSRequiresIPhoneOS":True}
with (app / "Info.plist").open("wb") as file: plistlib.dump(info,file)
sdk = subprocess.check_output(["xcrun","--sdk","iphonesimulator","--show-sdk-path"],text=True).strip()
subprocess.run(["xcrun","--sdk","iphonesimulator","swiftc","-swift-version","5","-parse-as-library",
    "-sdk",sdk,"-target","arm64-apple-ios17.0-simulator","-framework","UIKit","-framework","WebKit",
    str(root/"Admission.swift"),str(root/"Probe.swift"),"-o",str(app/"MessageProbe")],check=True)
subprocess.run(["codesign","--force","--sign","-",str(app)],check=True)
version = subprocess.check_output(["xcrun","vtool","-show-build",str(app/"MessageProbe")],text=True)
assert "platform IOSSIMULATOR" in version and "minos 17.0" in version and "sdk 26.4" in version
paths=[root/name for name in ["Admission.swift","Probe.swift","build.py","run_probe.py"]]+sorted((root/"fixtures").glob("*"))
metadata={"executableSha256":hashlib.sha256((app/"MessageProbe").read_bytes()).hexdigest(),
    "sources":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(root/"build/build-metadata.json").write_text(json.dumps(metadata,indent=2)+'\n')
print('Simulator probe built, signed and fingerprinted.')
