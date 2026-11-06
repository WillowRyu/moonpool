"""Run every vector through OkHttp 5.5.1's public cookie parser on the desktop JVM.

The Android broker pins OkHttp 5.5.1. Its cookie parsing code is shared between the JVM and
Android artifacts; only how the public-suffix data is loaded differs, so this run also checks that
both artifacts carry the same public-suffix data. Needs local-results/deps/okhttp-jvm-5.5.1.jar
(from Maven Central, checked against its published SHA-1) and Okio and Kotlin from the Gradle cache.
"""
import base64
import glob
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from compare import load_vectors

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / 'local-results'
GRADLE = Path.home() / '.gradle/caches/modules-2/files-2.1'
OKHTTP_JAR = LOCAL / 'deps/okhttp-jvm-5.5.1.jar'
OKHTTP_SHA1 = LOCAL / 'deps/okhttp-jvm-5.5.1.jar.sha1'


def encode_rows(vectors):
    field = lambda text: base64.b64encode(text.encode('utf-8')).decode('ascii')
    return [f"{v['id']}\t{field(v['url'])}\t{field(v['line'])}\t{field(chr(10).join(v['checks']))}" for v in vectors]


def digest(data, kind='sha256'):
    return hashlib.new(kind, data).hexdigest()


def cached(pattern):
    found = sorted(glob.glob(str(GRADLE / pattern)))
    if not found:
        sys.exit(f'missing from the Gradle cache: {pattern}')
    return Path(found[0])


def public_suffix_data():
    """Hash the public-suffix list inside each artifact, so a JVM result can be said to use Android's data."""
    with zipfile.ZipFile(OKHTTP_JAR) as jar:
        names = [n for n in jar.namelist() if 'PublicSuffixDatabase' in n and not n.endswith('.class')]
        jvm = {name: digest(jar.read(name)) for name in names}
    with zipfile.ZipFile(cached('com.squareup.okhttp3/okhttp-android/5.5.1/*/okhttp.aar')) as aar:
        android = {name: digest(aar.read(name)) for name in aar.namelist() if 'PublicSuffixDatabase' in name}
    return {'jvm': jvm, 'android': android, 'same': sorted(jvm.values()) == sorted(android.values()) and bool(jvm)}


def main():
    if not OKHTTP_JAR.exists() or not OKHTTP_SHA1.exists():
        sys.exit(f'missing {OKHTTP_JAR} or its published .sha1')
    published = OKHTTP_SHA1.read_text().split()[0]
    actual = digest(OKHTTP_JAR.read_bytes(), 'sha1')
    if published != actual:
        sys.exit(f'okhttp-jvm SHA-1 {actual} does not match the published {published}')
    classpath = [OKHTTP_JAR, cached('com.squareup.okio/okio-jvm/3.18.1/*/okio-jvm-3.18.1.jar'),
                 cached('org.jetbrains.kotlin/kotlin-stdlib/2.2.21/*/kotlin-stdlib-2.2.21.jar')]
    joined = ':'.join(str(p) for p in classpath)
    classes = LOCAL / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run(['javac', '--release', '17', '-cp', joined, '-d', str(classes), str(ROOT / 'jvm/ParseProbe.java')], check=True)
    now_ms = int(time.time() * 1000)
    vectors = load_vectors(now_ms)
    rows = LOCAL / 'input.tsv'
    rows.write_text('\n'.join(encode_rows(vectors)) + '\n', encoding='utf-8')
    run = subprocess.run(['java', '-cp', f'{classes}:{joined}', 'ParseProbe', str(rows)], check=True, capture_output=True)
    observations = [json.loads(line) for line in run.stdout.decode('utf-8').splitlines() if line.strip()]
    if [o['id'] for o in observations] != [v['id'] for v in vectors]:
        sys.exit('the probe did not answer every vector exactly once, in order')
    java = subprocess.run(['java', '-version'], capture_output=True, text=True).stderr.splitlines()[0]
    report = {
        'platform': 'okhttp-5.5.1-jvm',
        'nowMs': now_ms,
        'java': java,
        'jars': {p.name: digest(p.read_bytes(), 'sha1') for p in classpath},
        'publicSuffixData': public_suffix_data(),
        'observations': observations,
    }
    out = ROOT / 'results/okhttp-5.5.1-jvm.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{len(observations)} observations written to {out.relative_to(ROOT)}; public-suffix data same as Android: {report["publicSuffixData"]["same"]}')


if __name__ == '__main__':
    main()
