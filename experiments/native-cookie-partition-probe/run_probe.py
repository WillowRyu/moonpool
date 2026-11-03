"""Collect from the explicit owned simulator. An unexpected process exit ends the run."""
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
PACKAGE = 'org.moonpool.ioscookiepartitionprobe'
EXECUTABLE = 'CookiePartitionProbe'
DEADLINE_SECONDS = 420


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--mode', choices=['collect', 'reopen', 'warmup-seed', 'warmup'], default='collect')
    args = parser.parse_args()
    tag = 'ios-' + args.run
    if not re.fullmatch(r'[a-z0-9-]+', tag):
        raise ValueError('Invalid public run tag')
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
    sim('terminate', device, PACKAGE, check=False)
    container = Path(sim('get_app_container', device, PACKAGE, 'data').stdout.strip())
    output = container / 'Documents/report.json'
    output.unlink(missing_ok=True)
    launched = sim('launch', device, PACKAGE, '--run', tag, '--base', base, '--mode', args.mode).stdout.strip()
    pid = int(launched.rsplit(':', 1)[1].strip())

    started = time.monotonic()
    while True:
        report = parse_report(output.read_text() if output.exists() else None, tag)
        if report is not None:
            break
        if time.monotonic() - started > DEADLINE_SECONDS:
            raise TimeoutError('No final report; stopped without retry')
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            raise RuntimeError('Probe process exited unexpectedly; stopped without retry') from None
        time.sleep(0.5)

    sim('terminate', device, PACKAGE, check=False)
    report['build'] = metadata
    report['installedArtifactSha256'] = installed
    rows = [json.loads(line) for line in (ROOT / 'local-results/tls/requests.jsonl').read_text().splitlines()]
    report['requests'] = [row for row in rows if row['run'] == tag]
    report['capturedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / (tag + '.json')).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f"{tag}: complete={report.get('complete')}, samples={len(report.get('samples', []))}, "
          f"writers={len(report.get('writers', []))}, reopened={len(report.get('reopened', []))}, "
          f"seeded={len(report.get('seeded', []))}, warmups={len(report.get('warmups', []))}, "
          f"requests={len(report['requests'])}")
    if not report.get('complete'):
        print({key: report[key] for key in ['error', 'errors'] if key in report})


if __name__ == '__main__':
    main()
