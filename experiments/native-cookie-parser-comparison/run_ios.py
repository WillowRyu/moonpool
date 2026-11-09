"""Collect iOS observations on the one dedicated simulator, then restore every simulator to the state it had.

Only the simulator named OWNED_NAME is touched. If it was shut down, this boots it and shuts it down again. An unexpected
app exit ends the run without retry. Usage: python3 -B run_ios.py first repeat
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from build_ios import APP, PACKAGE, artifact_digest, sha
from compare import load_vectors
from run_okhttp import encode_rows

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / 'local-results'
OWNED_NAME = 'Moonpool Cookie Suppression'
DEADLINE_SECONDS = 120


def sim(*parts, check=True, timeout=60):
    return subprocess.run(['xcrun', 'simctl', *parts], capture_output=True, text=True, check=check, timeout=timeout)


def states():
    listed = json.loads(sim('list', 'devices', '-j').stdout)['devices']
    return {d['udid']: {'name': d['name'], 'state': d['state'], 'runtime': runtime} for runtime, group in listed.items() for d in group}


def collect(device, run, metadata):
    out = ROOT / f'results/ios-{run}.json'
    if out.exists():
        sys.exit(f'{out.name} already exists; retained evidence is not overwritten')
    now_ms = int(time.time() * 1000)
    vectors = load_vectors(now_ms)
    documents = Path(sim('get_app_container', device, PACKAGE, 'data').stdout.strip()) / 'Documents'
    documents.mkdir(parents=True, exist_ok=True)
    (documents / 'input.tsv').write_text('\n'.join(encode_rows(vectors)) + '\n', encoding='utf-8')
    report_path = documents / 'report.json'
    report_path.unlink(missing_ok=True)
    try:
        launched = sim('launch', device, PACKAGE, '--run', run, '--now', str(now_ms)).stdout.strip()
        pid = int(launched.rsplit(':', 1)[1].strip())
        started = time.monotonic()
        while not report_path.exists():
            if time.monotonic() - started > DEADLINE_SECONDS:
                raise TimeoutError('No report; stopped without retry')
            try:
                os.kill(pid, 0)
            except ProcessLookupError as error:
                raise RuntimeError('Probe exited unexpectedly; stopped without retry') from error
            time.sleep(0.5)
        report = json.loads(report_path.read_text())
    finally:
        sim('terminate', device, PACKAGE, check=False)
    raw = report['observations']
    if not report['complete'] or [o['id'] for o in raw] != [v['id'] for v in vectors]:
        sys.exit(f'{run}: incomplete report {report["errors"]}')
    if not all(o.get('startedEmpty') and o.get('endedEmpty') for o in raw):
        sys.exit(f'{run}: a storage was not empty before or after a vector; vectors may have leaked into each other')
    # nowMs expanded the vectors; clockMs, when the app started parsing, judges expiry. compare.py derives the view from raw.
    result = {'platform': f"ios-{report['release']}-httpcookie", 'run': run, 'nowMs': now_ms, 'clockMs': report['appStartMs'],
              'release': report['release'], 'build': metadata, 'raw': raw,
              'capturedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{run}: {len(raw)} observations, iOS {report["release"]}')


def main(runs):
    metadata = json.loads((LOCAL / 'ios-build.json').read_text())
    for path, digest in metadata['sources'].items():
        if sha(ROOT / path) != digest:
            sys.exit(f'{path} changed after the build; rebuild first')
    before = states()
    owned = [udid for udid, d in before.items() if d['name'] == OWNED_NAME]
    if len(owned) != 1:
        sys.exit(f'expected exactly one simulator named {OWNED_NAME}, found {len(owned)}')
    device = owned[0]
    (LOCAL / 'sim-baseline.json').write_text(json.dumps(before, indent=2, sort_keys=True) + '\n')
    booted_here = before[device]['state'] == 'Shutdown'
    (LOCAL / 'ios-owner.json').write_text(json.dumps({'owned': device, 'name': OWNED_NAME, 'bootStartedByThisTask': booted_here,
                                                       'protected': sorted(u for u in before if u != device)}, indent=2) + '\n')
    try:
        if booted_here:
            sim('boot', device)
        sim('bootstatus', device, timeout=300)
        sim('install', device, str(APP))
        installed = artifact_digest(Path(sim('get_app_container', device, PACKAGE, 'app').stdout.strip()))
        if installed != metadata['artifactSha256']:
            sys.exit('installed artifact differs from the build')
        for run in runs:
            collect(device, run, metadata)
    finally:
        sim('terminate', device, PACKAGE, check=False)
        if booted_here:
            sim('shutdown', device, check=False, timeout=120)
        after = states()
        changed = sorted(u for u in before if before[u]['state'] != after.get(u, {}).get('state'))
        print('simulator states restored' if not changed else f'STATE CHANGED: {changed}')


if __name__ == '__main__':
    main(sys.argv[1:] or ['first'])
