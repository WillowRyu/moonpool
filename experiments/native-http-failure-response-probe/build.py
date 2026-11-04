"""Build only this research app with existing tools and an app-scoped test CA."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import create_certificates

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_digest(app):
    """What the app actually runs, including its scenario file and CA."""
    digest = hashlib.sha256()
    for part in ['FailureResponseProbe', 'Fixtures/cases.json', 'Fixtures/ca.der']:
        digest.update(f'{part}:{sha(app / part)}\n'.encode())
    return digest.hexdigest()


def main():
    (ROOT / 'local-results').mkdir(exist_ok=True)
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    app = ROOT / 'build/FailureResponseProbe.app'
    fixtures = app / 'Fixtures'
    fixtures.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'cases.json', fixtures / 'cases.json')
    subprocess.run(['openssl', 'x509', '-in', str(tls / 'ca.pem'), '-outform', 'DER', '-out', str(fixtures / 'ca.der')], check=True)
    (app / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'FailureResponseProbe', 'CFBundleIdentifier': 'org.moonpool.iosfailureresponseprobe',
        'CFBundleName': 'Failure Response Probe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.0.1', 'MinimumOSVersion': '17.0', 'UIDeviceFamily': [1, 2],
        'UILaunchScreen': {}, 'LSRequiresIPhoneOS': True,
    }))
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], text=True).strip()
    subprocess.run(['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-swift-version', '5', '-parse-as-library', '-sdk', sdk,
                    '-target', 'arm64-apple-ios17.0-simulator', '-framework', 'UIKit', str(ROOT / 'ios/Probe.swift'),
                    '-o', str(app / 'FailureResponseProbe')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    metadata = {'sources': {name: sha(ROOT / name) for name in ['build.py', 'fixture.py', 'cases.json', 'ios/Probe.swift']}, 'caSha256': sha(tls / 'ca.pem'),
                'artifactSha256': artifact_digest(app), 'xcode': subprocess.check_output(['xcodebuild', '-version'], text=True).strip(),
                'sdk': subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], text=True).strip()}
    (ROOT / 'local-results/build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
