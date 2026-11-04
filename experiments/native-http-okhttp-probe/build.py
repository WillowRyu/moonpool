"""Build only the OkHttp research app with existing tools and an app-scoped test CA."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from fixture import create_certificates
from verify_results import EXCLUDED

ROOT = Path(__file__).resolve().parent
OKHTTP_CACHE = Path.home() / '.gradle/caches/modules-2/files-2.1/com.squareup.okhttp3/okhttp-android/5.5.1'


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
    tree = subprocess.run([str(wrapper), '-p', str(ROOT / 'android'), '--no-daemon', ':app:dependencies', '--configuration', 'debugRuntimeClasspath'],
                          env=env, check=True, capture_output=True, text=True).stdout
    artifact = ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'
    metadata['artifactSha256'] = sha(artifact)
    metadata['artifactBytes'] = artifact.stat().st_size
    metadata['wrapperSha256'] = sha(wrapper)
    metadata['runtimeDependencies'] = sorted(set(re.findall(r'[-+\\] ([\w.-]+:[\w.-]+:[\w.-]+(?: -> [\w.-]+)?)', tree)))
    metadata['okhttpArtifacts'] = {path.name: sha(path) for path in sorted(OKHTTP_CACHE.rglob('*')) if path.suffix in {'.aar', '.jar'} and 'sources' not in path.name}
    (ROOT / 'local-results/android-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('OkHttp probe artifact and source hashes recorded.')


if __name__ == '__main__':
    main()
