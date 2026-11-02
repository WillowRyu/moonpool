from pathlib import Path
import hashlib
import json
import plistlib
import shutil
import subprocess

root=Path(__file__).resolve().parent;common=root.parent
subprocess.run(['python3',str(common/'build_bundle.py')],check=True)
app=root/'build/RuntimeProbe.app';app.mkdir(parents=True,exist_ok=True)
fixtures=app/'Fixtures';fixtures.mkdir(exist_ok=True)
shutil.copyfile(common/'build/kernel-probe.js',fixtures/'kernel-probe.js')
shutil.copyfile(common/'timer-adapter.js',fixtures/'timer-adapter.js')
info={'CFBundleExecutable':'RuntimeProbe','CFBundleIdentifier':'org.moonpool.iosruntimeprobe','CFBundleName':'Moonpool T27 runtime probe',
 'CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'0.0.1','MinimumOSVersion':'17.0',
 'UIDeviceFamily':[1,2],'UILaunchScreen':{},'LSRequiresIPhoneOS':True}
with (app/'Info.plist').open('wb') as f:plistlib.dump(info,f)
sdk=subprocess.check_output(['xcrun','--sdk','iphonesimulator','--show-sdk-path'],text=True).strip()
subprocess.run(['xcrun','--sdk','iphonesimulator','swiftc','-swift-version','5','-parse-as-library','-sdk',sdk,
 '-target','arm64-apple-ios17.0-simulator','-framework','UIKit','-framework','JavaScriptCore',str(root/'Probe.swift'),'-o',str(app/'RuntimeProbe')],check=True)
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
version=subprocess.check_output(['xcrun','vtool','-show-build',str(app/'RuntimeProbe')],text=True)
assert 'platform IOSSIMULATOR' in version and 'sdk 26.4' in version
meta={'common':json.loads((common/'build/bundle-metadata.json').read_text()),
 'executableSha256':hashlib.sha256((app/'RuntimeProbe').read_bytes()).hexdigest(),
 'sources':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['Probe.swift','build.py','run_probe.py']}}
(root/'build/build-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
