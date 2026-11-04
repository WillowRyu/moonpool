"""Collect from the explicit owned simulator. An unexpected process exit ends the run without retry."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
from build import artifact_digest, sha

ROOT = Path(__file__).resolve().parent
PACKAGE = 'org.moonpool.iosfailureresponseprobe'
DEADLINE_SECONDS = 120


def sim(*parts, check=True):
    return subprocess.run(['xcrun', 'simctl', *parts], capture_output=True, text=True, check=check, timeout=60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    tag = 'ios-' + args.run
    if not re.fullmatch(r'[a-z0-9-]+', tag):
        raise ValueError('Invalid public run tag')
    owner = json.loads((ROOT / 'local-results/owner.json').read_text())
    metadata = json.loads((ROOT / 'local-results/build.json').read_text())
    for path, digest in metadata['sources'].items():
        assert sha(ROOT / path) == digest, 'Changed built source: ' + path
    assert sha(ROOT / 'local-results/tls/ca.pem') == metadata['caSha256']
    port = json.loads((ROOT / 'local-results/server.json').read_text())['port']
    rows_path = ROOT / 'local-results/tls/requests.jsonl'
    if rows_path.exists() and any(json.loads(line)['run'] == tag for line in rows_path.read_text().splitlines()):
        raise ValueError(f'Run tag {tag} already has receipts; use a new tag')
    device = owner['owned']
    assert device not in owner['protected']
    devices = json.loads(sim('list', 'devices', 'available', '-j').stdout)['devices']
    current = next(d for group in devices.values() for d in group if d['udid'] == device)
    assert current['name'] == owner['name'] and current['state'] == 'Booted'
    try:
        if args.install:
            sim('install', device, str(ROOT / 'build/FailureResponseProbe.app'))
        installed = artifact_digest(Path(sim('get_app_container', device, PACKAGE, 'app').stdout.strip()))
        assert installed == metadata['artifactSha256'], 'Installed artifact differs from the build'
        sim('terminate', device, PACKAGE, check=False)
        output = Path(sim('get_app_container', device, PACKAGE, 'data').stdout.strip()) / 'Documents/report.json'
        output.unlink(missing_ok=True)
        launched = sim('launch', device, PACKAGE, '--run', tag, '--port', str(port)).stdout.strip()
        pid = int(launched.rsplit(':', 1)[1].strip())
        started = time.monotonic()
        while not output.exists():
            if time.monotonic() - started > DEADLINE_SECONDS:
                raise TimeoutError('No final report; stopped without retry')
            try:
                os.kill(pid, 0)
            except ProcessLookupError as error:
                raise RuntimeError('Probe process exited unexpectedly; stopped without retry') from error
            time.sleep(0.5)
        report = json.loads(output.read_text())
    finally:
        sim('terminate', device, PACKAGE, check=False)
    assert report['run'] == tag
    report['build'] = metadata
    report['installedArtifactSha256'] = installed
    report['requests'] = [row for row in map(json.loads, rows_path.read_text().splitlines()) if row['run'] == tag]
    report['capturedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    results = ROOT / 'results'
    results.mkdir(exist_ok=True)
    (results / (tag + '.json')).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f"{tag}: complete={report.get('complete')}, observations={len(report.get('observations', []))}, requests={len(report['requests'])}, errors={report.get('errors')}")


if __name__ == '__main__':
    main()
