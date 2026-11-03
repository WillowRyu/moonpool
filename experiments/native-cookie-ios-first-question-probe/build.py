"""Build only the iOS first-question research app with existing tools and a scoped test CA."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import create_certificates
from vectors import expand
from verify_results import SOURCES

ROOT = Path(__file__).resolve().parent
EXECUTABLE = 'CookieFirstQuestionProbe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    app = ROOT / 'build' / (EXECUTABLE + '.app')
    fixtures = app / 'Fixtures'
    fixtures.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local-results').mkdir(exist_ok=True)
    for name in ['frame.html', 'storage.html']:
        shutil.copy2(ROOT / name, fixtures / name)
    (fixtures / 'config.json').write_text(json.dumps({'stores': expand()}, indent=2) + '\n')
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    paths = [ROOT / name for name in SOURCES] + [path for path in (ROOT / 'ios').rglob('*') if path.is_file()]
    metadata = {'sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)},
                'fixtureConfigSha256': sha(fixtures / 'config.json'), 'caSha256': sha(tls / 'ca.pem')}
    (app / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': EXECUTABLE, 'CFBundleIdentifier': 'org.moonpool.ioscookiefirstquestionprobe',
        'CFBundleName': 'Cookie First Question Probe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
        'CFBundleShortVersionString': '0.0.1', 'MinimumOSVersion': '17.0', 'UIDeviceFamily': [1, 2],
        'UILaunchScreen': {}, 'LSRequiresIPhoneOS': True,
    }))
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], text=True).strip()
    subprocess.run(['xcrun', '--sdk', 'iphonesimulator', 'swiftc', '-swift-version', '5', '-parse-as-library',
                    '-sdk', sdk, '-target', 'arm64-apple-ios17.0-simulator', '-framework', 'UIKit', '-framework', 'WebKit',
                    str(ROOT / 'ios/Probe.swift'), '-o', str(app / EXECUTABLE)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    metadata['executableSha256'] = sha(app / EXECUTABLE)
    metadata['signatureSha256'] = sha(app / '_CodeSignature/CodeResources')
    metadata['xcode'] = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
    metadata['sdk'] = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], text=True).strip()
    (ROOT / 'local-results/ios-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('iOS first-question artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
