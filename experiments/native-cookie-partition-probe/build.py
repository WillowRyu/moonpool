"""Build only the iOS partition research app with existing tools and a scoped test CA."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import create_certificates

ROOT = Path(__file__).resolve().parent
EXECUTABLE = 'CookiePartitionProbe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    app = ROOT / 'build' / (EXECUTABLE + '.app')
    fixtures = app / 'Fixtures'
    fixtures.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local-results').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'frame.html', fixtures / 'frame.html')
    config = {name: json.loads((ROOT / (name + '_cases.json')).read_text()) for name in ['partition', 'writer', 'warmup']}
    (fixtures / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'frame.html', 'partition_cases.json', 'writer_cases.json', 'warmup_cases.json']]
    paths += [path for path in (ROOT / 'ios').rglob('*') if path.is_file()]
    metadata = {'sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)},
                'fixtureConfigSha256': sha(fixtures / 'config.json'), 'caSha256': sha(tls / 'ca.pem')}
    (app / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': EXECUTABLE, 'CFBundleIdentifier': 'org.moonpool.ioscookiepartitionprobe',
        'CFBundleName': 'Cookie Partition Probe', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
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
    print('iOS partition artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
