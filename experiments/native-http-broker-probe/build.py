"""Build only the broker research apps with existing tools and an app-scoped test CA."""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import plistlib
import shutil
import subprocess
from fixture import TLS_FOLDER, create_certificates
from verify_results import PROFILE_ROOT, cookie_profile, expand_repetitions, profile_vectors, source_fingerprints
from check import inputs_for

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ios_artifact_digest(app):
    """What the app actually runs. The executable alone would not notice a stale scenario file on the device."""
    digest = hashlib.sha256()
    for part in ['HttpBrokerProbe', 'Fixtures/cases.json', 'Fixtures/ca.der', 'Fixtures/public_suffix_list.dat', 'Fixtures/profile-inputs.json']:
        digest.update(f'{part}:{sha(app / part)}\n'.encode())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', choices=['android', 'ios'])
    parser.add_argument('--psl', type=Path, default=PROFILE_ROOT / 'local-results/public_suffix_list.dat')
    args = parser.parse_args()
    platform = args.platform
    profile = cookie_profile()
    psl = args.psl.read_bytes()
    if hashlib.sha256(psl).hexdigest() != profile['psl']['sha256']:
        raise ValueError('PSL SHA-256 differs from the C04 snapshot')
    vectors = profile_vectors()
    inputs = list(inputs_for(expand_repetitions(vectors['cases']), datetime.fromisoformat(vectors['t0']), vectors['url']))
    profile_inputs = json.dumps(inputs) + '\n'
    (ROOT / 'local-results').mkdir(exist_ok=True)
    tls = TLS_FOLDER
    create_certificates(tls)
    metadata = {'sources': source_fingerprints(platform), 'caSha256': sha(tls / 'ca.pem'), 'cookieProfile': profile}
    if platform == 'android':
        assets = ROOT / 'build/assets'
        raw = ROOT / 'build/res/raw'
        assets.mkdir(parents=True, exist_ok=True)
        raw.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'cases.json', assets / 'cases.json')
        (assets / 'public_suffix_list.dat').write_bytes(psl)
        (assets / 'profile-inputs.json').write_text(profile_inputs)
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
        (fixtures / 'public_suffix_list.dat').write_bytes(psl)
        (fixtures / 'profile-inputs.json').write_text(profile_inputs)
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
                        *map(str, sorted((PROFILE_ROOT / 'reference/swift/src').glob('*.swift'))),
                        str(PROFILE_ROOT / 'reference/swift/test/Adapter.swift'),
                        '-o', str(app / 'HttpBrokerProbe')], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
        metadata['artifactSha256'] = ios_artifact_digest(app)
        metadata['xcode'] = subprocess.check_output(['xcodebuild', '-version'], text=True).strip()
        metadata['sdk'] = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], text=True).strip()
    (ROOT / 'local-results' / f'{platform}-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(platform + ' broker artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
