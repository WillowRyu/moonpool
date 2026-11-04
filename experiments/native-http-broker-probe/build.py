"""Build only the broker research apps with existing tools and an app-scoped test CA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import create_certificates
from verify_results import EXCLUDED

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', choices=['android', 'ios'])
    platform = parser.parse_args().platform
    (ROOT / 'local-results').mkdir(exist_ok=True)
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'cases.json']]
    paths += [path for path in (ROOT / platform).rglob('*') if path.is_file() and not EXCLUDED & set(path.relative_to(ROOT).parts)]
    metadata = {'sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}, 'caSha256': sha(tls / 'ca.pem')}
    if platform == 'android':
        assets = ROOT / 'build/assets'
        raw = ROOT / 'build/res/raw'
        assets.mkdir(parents=True, exist_ok=True)
        raw.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'cases.json', assets / 'cases.json')
        shutil.copy2(tls / 'ca.pem', raw / 'probe_ca.pem')
        env = os.environ.copy()
        env.setdefault('JAVA_HOME', '/Applications/Android Studio.app/Contents/jbr/Contents/Home')
        env.setdefault('ANDROID_HOME', str(Path.home() / 'Library/Android/sdk'))
        wrapper = ROOT.parent / 'android-origin-probe/gradlew'
        subprocess.run([str(wrapper), '-p', str(ROOT / 'android'), '--no-daemon', ':app:assembleDebug', ':app:lintDebug'], env=env, check=True)
        metadata['artifactSha256'] = sha(ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk')
        metadata['wrapperSha256'] = sha(wrapper)
    else:
        app = ROOT / 'build/HttpBrokerProbe.app'
        fixtures = app / 'Fixtures'
        fixtures.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'cases.json', fixtures / 'cases.json')
        subprocess.run(['openssl', 'x509', '-in', str(tls / 'ca.pem'), '-outform', 'DER', '-out', str(fixtures / 'ca.der')], check=True)
        (app / 'Info.plist').write_bytes(plistlib.dumps({
            'CFBundleExecutable': 'HttpBrokerProbe', 'CFBundleIdentifier': 'org.moonpool.ioshttpbrokerprobe',
            'CFBundleName': 'HTTP Broker Probe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
            'CFBundleShortVersionString': '0.0.1', 'MinimumOSVersion': '17.0', 'UIDeviceFamily': [1, 2],
            'UILaunchScreen': {}, 'LSRequiresIPhoneOS': True,
        }))
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], text=True).strip()
        subprocess.run(['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-swift-version', '5', '-parse-as-library', '-sdk', sdk,
                        '-target', 'arm64-apple-ios17.0-simulator', '-framework', 'UIKit', str(ROOT / 'ios/Probe.swift'),
                        '-o', str(app / 'HttpBrokerProbe')], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
        metadata['artifactSha256'] = sha(app / 'HttpBrokerProbe')
        metadata['xcode'] = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
        metadata['sdk'] = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], text=True).strip()
    (ROOT / 'local-results' / f'{platform}-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(platform + ' broker artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
