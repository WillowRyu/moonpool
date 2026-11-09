"""Build only this research app with the installed toolchain. No certificate and no fixture: the probe never uses the network."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'local-results/build/CookieParserProbe.app'
PACKAGE = 'org.moonpool.cookieparserprobe'
SOURCES = ['build_ios.py', 'run_ios.py', 'ios/Probe.swift']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_digest(app):
    return sha(app / 'CookieParserProbe')


def main():
    APP.mkdir(parents=True, exist_ok=True)
    (APP / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'CookieParserProbe', 'CFBundleIdentifier': PACKAGE,
        'CFBundleName': 'Cookie Parser Probe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.0.1', 'MinimumOSVersion': '17.0', 'UIDeviceFamily': [1, 2],
        'UILaunchScreen': {}, 'LSRequiresIPhoneOS': True,
    }))
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], text=True).strip()
    subprocess.run(['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-swift-version', '5', '-parse-as-library', '-sdk', sdk,
                    '-target', 'arm64-apple-ios17.0-simulator', '-framework', 'UIKit', str(ROOT / 'ios/Probe.swift'),
                    '-o', str(APP / 'CookieParserProbe')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(APP)], check=True)
    metadata = {'sources': {name: sha(ROOT / name) for name in SOURCES}, 'artifactSha256': artifact_digest(APP),
                'xcode': subprocess.check_output(['xcodebuild', '-version'], text=True).strip(),
                'sdk': subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], text=True).strip()}
    (ROOT / 'local-results/ios-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Built; artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
