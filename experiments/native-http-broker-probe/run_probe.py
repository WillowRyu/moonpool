"""Collect from the explicit owned device. An unexpected process exit ends the run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from fixture import vectors_digest

ROOT = Path(__file__).resolve().parent
ADB = Path.home() / 'Library/Android/sdk/platform-tools/adb'
PACKAGES = {'android': 'org.moonpool.httpbroker', 'ios': 'org.moonpool.ioshttpbrokerprobe'}
DEADLINE_SECONDS = 300


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
    parser.add_argument('platform', choices=['android', 'ios'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    platform, tag = args.platform, f'{args.platform}-{args.run}'
    if not re.fullmatch(r'[a-z0-9-]+', tag):
        raise ValueError('Invalid public run tag')
    owner = json.loads((ROOT / 'local-results' / f'{platform}-owner.json').read_text())
    metadata = json.loads((ROOT / 'local-results' / f'{platform}-build.json').read_text())
    for path, digest in metadata['sources'].items():
        assert sha(ROOT / path) == digest, 'Changed built source: ' + path
    assert sha(ROOT / 'local-results/tls/ca.pem') == metadata['caSha256']
    server = json.loads((ROOT / 'local-results/server.json').read_text())
    assert server['vectorsSha256'] == vectors_digest(), 'Restart the fixture: running server differs from vectors'
    port, second, control = server['port'], server['secondPort'], server['controlPort']
    package = PACKAGES[platform]
    if platform == 'android':
        serial = owner['serial']

        def adb(*parts, check=True, binary=False):
            return subprocess.run([str(ADB), '-s', serial, *parts], capture_output=True, text=not binary, check=check, timeout=60)

        assert adb('emu', 'avd', 'name').stdout.splitlines()[0] == owner['avd']
        for value in (port, second, control):
            adb('reverse', f'tcp:{value}', f'tcp:{value}')
        if args.install:
            adb('install', '-r', str(ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'))
        path = adb('shell', 'pm', 'path', package).stdout.strip().removeprefix('package:')
        installed = hashlib.sha256(adb('exec-out', 'cat', path, binary=True).stdout).hexdigest()
        adb('shell', 'am', 'force-stop', package)
        adb('shell', 'run-as', package, 'rm', '-f', 'files/report.json')
        launch = adb('shell', 'am', 'start', '-n', package + '/.ProbeActivity', '--es', 'run', tag,
                     '--ei', 'port', str(port), '--ei', 'second', str(second), '--ei', 'control', str(control))
        assert 'Error' not in launch.stdout, launch.stdout

        def read_report():
            result = adb('exec-out', 'run-as', package, 'cat', 'files/report.json', check=False)
            return result.stdout if result.returncode == 0 else None

        def alive():
            # A busy emulator can answer one pidof with nothing, so absence must be seen twice.
            for _ in range(2):
                if adb('shell', 'pidof', package, check=False).stdout.strip():
                    return True
                time.sleep(2)
            return False

        def stop():
            adb('shell', 'am', 'force-stop', package)
            for value in (port, second, control):
                adb('reverse', '--remove', f'tcp:{value}', check=False)
    else:
        device = owner['owned']
        assert device not in owner['protected']

        def sim(*parts, check=True):
            return subprocess.run(['xcrun', 'simctl', *parts], capture_output=True, text=True, check=check, timeout=60)

        devices = json.loads(sim('list', 'devices', 'available', '-j').stdout)['devices']
        current = next(d for group in devices.values() for d in group if d['udid'] == device)
        assert current['name'] == owner['name'] and current['state'] == 'Booted'
        if args.install:
            sim('install', device, str(ROOT / 'build/HttpBrokerProbe.app'))
        app = Path(sim('get_app_container', device, package, 'app').stdout.strip())
        installed = sha(app / 'HttpBrokerProbe')
        sim('terminate', device, package, check=False)
        output = Path(sim('get_app_container', device, package, 'data').stdout.strip()) / 'Documents/report.json'
        output.unlink(missing_ok=True)
        launched = sim('launch', device, package, '--run', tag, '--port', str(port), '--second', str(second), '--control', str(control)).stdout.strip()
        pid = int(launched.rsplit(':', 1)[1].strip())

        def read_report():
            return output.read_text() if output.exists() else None

        def alive():
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                return False

        def stop():
            sim('terminate', device, package, check=False)
    assert installed == metadata['artifactSha256']

    started = time.monotonic()
    while True:
        report = parse_report(read_report(), tag)
        if report is not None:
            break
        if time.monotonic() - started > DEADLINE_SECONDS:
            raise TimeoutError('No final report; stopped without retry')
        if time.monotonic() - started > 3 and not alive():
            raise RuntimeError('Probe process exited unexpectedly; stopped without retry')
        time.sleep(0.5)

    stop()
    report['build'] = metadata
    report['installedArtifactSha256'] = installed
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
