"""Build only the HTTP globals research app with existing tools and an app-scoped test CA."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from fixture import create_certificates
from verify_results import EXCLUDED

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    (ROOT / 'local-results').mkdir(exist_ok=True)
    tls = ROOT / 'local-results/tls'
    create_certificates(tls)
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'cases.json']]
    paths += [path for path in (ROOT / 'android').rglob('*') if path.is_file() and not EXCLUDED & set(path.relative_to(ROOT).parts)]
    metadata = {'sources': {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}, 'caSha256': sha(tls / 'ca.pem')}
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
    (ROOT / 'local-results/android-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Android globals artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
