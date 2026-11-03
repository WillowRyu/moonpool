"""Build only the Android restart research app with existing tools and a scoped test CA."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from fixture import create_certificates
from vectors import expand
from verify_results import source_paths

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assets = ROOT / 'build/assets'
    assets.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local-results').mkdir(exist_ok=True)
    for name in ['frame.html', 'storage.html']:
        shutil.copy2(ROOT / name, assets / name)
    (assets / 'config.json').write_text(json.dumps({'stores': expand()}, indent=2) + '\n')
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    raw = ROOT / 'build/res/raw'
    raw.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tls / 'ca.pem', raw / 'probe_ca.pem')
    metadata = {'sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted(source_paths())},
                'fixtureConfigSha256': sha(assets / 'config.json'), 'caSha256': sha(tls / 'ca.pem')}
    env = os.environ.copy()
    env.setdefault('JAVA_HOME', '/Applications/Android Studio.app/Contents/jbr/Contents/Home')
    env.setdefault('ANDROID_HOME', str(Path.home() / 'Library/Android/sdk'))
    wrapper = ROOT.parent / 'android-origin-probe/gradlew'
    subprocess.run([str(wrapper), '-p', str(ROOT / 'android'), '--no-daemon', ':app:assembleDebug', ':app:lintDebug'],
                   env=env, check=True)
    metadata['apkSha256'] = sha(ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk')
    metadata['wrapperSha256'] = sha(wrapper)
    (ROOT / 'local-results/android-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Android restart artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
