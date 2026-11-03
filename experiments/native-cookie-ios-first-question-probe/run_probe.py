"""Collect from the explicit owned simulator. An unexpected process exit ends the run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from fixture import vectors_digest
from vectors import expand

ROOT = Path(__file__).resolve().parent
PACKAGE = 'org.moonpool.ioscookiefirstquestionprobe'
EXECUTABLE = 'CookieFirstQuestionProbe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sim(*parts, check=True):
    return subprocess.run(['xcrun', 'simctl', *parts], capture_output=True, text=True, check=check, timeout=60)


def parse_report(raw, tag):
    if not raw:
        return None
    try:
        report = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return report if isinstance(report, dict) and report.get('run') == tag else None


def receipts(tag):
    rows = [json.loads(line) for line in (ROOT / 'local-results/tls/requests.jsonl').read_text().splitlines()]
    return [row for row in rows if row['run'] == tag]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['seed', 'first'], required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    owner = json.loads((ROOT / 'local-results/ios-owner.json').read_text())
    metadata = json.loads((ROOT / 'local-results/ios-build.json').read_text())
    for path, digest in metadata['sources'].items():
        assert sha(ROOT / path) == digest, 'Changed built source: ' + path
    assert sha(ROOT / 'local-results/tls/ca.pem') == metadata['caSha256']
    server = json.loads((ROOT / 'local-results/server.json').read_text())
    assert server['vectorsSha256'] == vectors_digest(), 'Restart the fixture: running server differs from vectors'
    base = f"https://localhost:{server['port']}"
    device = owner['owned']
    assert device not in owner['protected']
    devices = json.loads(sim('list', 'devices', 'available', '-j').stdout)['devices']
    current = next(d for group in devices.values() for d in group if d['udid'] == device)
    assert current['name'] == owner['name'] and current['state'] == 'Booted'
    if args.install:
        sim('install', device, str(ROOT / 'build' / (EXECUTABLE + '.app')))
    app = Path(sim('get_app_container', device, PACKAGE, 'app').stdout.strip())
    installed = sha(app / EXECUTABLE)
    assert installed == metadata['executableSha256']
    assert sha(app / '_CodeSignature/CodeResources') == metadata['signatureSha256']
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    output = Path(sim('get_app_container', device, PACKAGE, 'data').stdout.strip()) / 'Documents/report.json'

    def launch(tag, mode, only, deadline):
        sim('terminate', device, PACKAGE, check=False)
        output.unlink(missing_ok=True)
        extras = ['--only', only] if only else []
        launched = sim('launch', device, PACKAGE, '--run', tag, '--base', base, '--mode', mode, *extras).stdout.strip()
        pid = int(launched.rsplit(':', 1)[1].strip())
        started = time.monotonic()
        while True:
            report = parse_report(output.read_text() if output.exists() else None, tag)
            if report is not None:
                break
            if time.monotonic() - started > deadline:
                raise TimeoutError(f'{tag}: no final report; stopped without retry')
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                raise RuntimeError(f'{tag}: process exited unexpectedly; stopped without retry') from None
            time.sleep(0.2)
        sim('terminate', device, PACKAGE, check=False)
        report['requests'] = receipts(tag)
        return report

    if args.mode == 'seed':
        result = launch('ios-seed', 'seed', None, 300)
        name = 'ios-seed'
    else:
        launches = []
        for index, store in enumerate(expand(), start=1):
            launches.append(launch(f'ios-first-{index}', 'check', store['id'], 60))
            print(f"{index}: {store['id']} complete={launches[-1].get('complete')}", flush=True)
        result = {'platform': 'ios', 'run': 'ios-first', 'mode': 'first', 'os': launches[0]['os'], 'launches': launches}
        name = 'ios-first'
    result['build'] = metadata
    result['installedArtifactSha256'] = installed
    result['capturedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / (name + '.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f'{name}: written')


if __name__ == '__main__':
    main()
