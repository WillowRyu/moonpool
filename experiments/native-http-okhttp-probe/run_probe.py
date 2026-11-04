"""Collect from the explicit owned emulator. An unexpected process exit ends the run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from fixture import vectors_digest

ROOT = Path(__file__).resolve().parent
ADB = Path.home() / 'Library/Android/sdk/platform-tools/adb'
PACKAGE = 'org.moonpool.httpokhttp'
DEADLINE_SECONDS = 240


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_report(raw, tag):
    if not raw:
        return None
    try:
        report = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return report if isinstance(report, dict) and report.get('run') == tag else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    tag = f'android-{args.run}'
    if not re.fullmatch(r'[a-z0-9-]+', tag):
        raise ValueError('Invalid public run tag')
    owner = json.loads((ROOT / 'local-results/android-owner.json').read_text())
    metadata = json.loads((ROOT / 'local-results/android-build.json').read_text())
    for path, digest in metadata['sources'].items():
        assert sha(ROOT / path) == digest, 'Changed built source: ' + path
    assert sha(ROOT / 'local-results/tls/ca.pem') == metadata['caSha256']
    server = json.loads((ROOT / 'local-results/server.json').read_text())
    assert server['vectorsSha256'] == vectors_digest(), 'Restart the fixture: running server differs from vectors'
    port, control = server['port'], server['controlPort']
    serial = owner['serial']

    def adb(*parts, check=True, binary=False):
        return subprocess.run([str(ADB), '-s', serial, *parts], capture_output=True, text=not binary, check=check, timeout=60)

    assert adb('emu', 'avd', 'name').stdout.splitlines()[0] == owner['avd']
    adb('reverse', f'tcp:{port}', f'tcp:{port}')
    adb('reverse', f'tcp:{control}', f'tcp:{control}')
    if args.install:
        adb('install', '-r', str(ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'))
    path = adb('shell', 'pm', 'path', PACKAGE).stdout.strip().removeprefix('package:')
    installed = hashlib.sha256(adb('exec-out', 'cat', path, binary=True).stdout).hexdigest()
    assert installed == metadata['artifactSha256']
    adb('shell', 'am', 'force-stop', PACKAGE)
    adb('shell', 'run-as', PACKAGE, 'rm', '-f', 'files/report.json')
    launch = adb('shell', 'am', 'start', '-n', PACKAGE + '/.ProbeActivity', '--es', 'run', tag, '--ei', 'port', str(port), '--ei', 'control', str(control))
    assert 'Error' not in launch.stdout, launch.stdout

    started = time.monotonic()
    while True:
        result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/report.json', check=False)
        report = parse_report(result.stdout if result.returncode == 0 else None, tag)
        if report is not None:
            break
        if time.monotonic() - started > DEADLINE_SECONDS:
            raise TimeoutError('No final report; stopped without retry')
        if time.monotonic() - started > 3 and not adb('shell', 'pidof', PACKAGE, check=False).stdout.strip():
            raise RuntimeError('Probe process exited unexpectedly; stopped without retry')
        time.sleep(0.5)

    adb('shell', 'am', 'force-stop', PACKAGE)
    adb('reverse', '--remove', f'tcp:{port}', check=False)
    adb('reverse', '--remove', f'tcp:{control}', check=False)
    report['build'] = metadata
    report['installedArtifactSha256'] = installed
    report['webViewPackage'] = adb('shell', 'dumpsys', 'webviewupdate', check=False).stdout.split('Current WebView package')[-1].splitlines()[0].strip()
    rows = [json.loads(line) for line in (ROOT / 'local-results/tls/requests.jsonl').read_text().splitlines()]
    report['requests'] = [row for row in rows if row['run'] == tag]
    report['capturedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / (tag + '.json')).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f"{tag}: complete={report.get('complete')}, observations={len(report.get('observations', []))}, requests={len(report['requests'])}")
    if not report.get('complete'):
        print({key: report[key] for key in ['error', 'errors'] if key in report})


if __name__ == '__main__':
    main()
