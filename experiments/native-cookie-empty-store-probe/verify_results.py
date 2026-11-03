"""Apply the accepted iOS rule to raw answers, then compare the verdict with independent witnesses.

A false admit or an over-refusal is a research finding and does not fail verification. Missing
controls or witnesses do, because then nothing can be claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from vectors import cookie_name, expand

ROOT = Path(__file__).resolve().parent
STORES = expand()
SOURCES = ['build.py', 'fixture.py', 'vectors.py', 'frame.html', 'storage.html', 'store_kinds.json']


def verdict(answer):
    """Both native sources must report no cookies; any disagreement is unknown."""
    names, records = bool(answer['names']), bool(answer['records'])
    if names and records:
        return 'present'
    return 'unknown' if names or records else 'empty'


def classify(store, entry, rows):
    name = cookie_name(store['kind'])
    witnessed = any(row['case'] == store['id'] and name in row['cookie'] for row in rows)
    rule = verdict(entry['first'])
    if rule == 'empty':
        outcome = 'false-admit' if witnessed else 'correct-admit'
    elif not witnessed:
        outcome = 'over-refuse'
    else:
        outcome = 'correct-refuse' if rule == 'present' else 'safe-refuse'
    return {'verdict': rule, 'verdictLater': verdict(entry['later']), 'witnessed': witnessed, 'outcome': outcome,
            'names': len(entry['first']['names']), 'records': len(entry['first']['records'])}


def outcomes(reports):
    table = {}
    for report in reports:
        for store, entry in zip(STORES, report['checks']):
            counts = table.setdefault(store['kind'], {})
            outcome = classify(store, entry, report['requests'])['outcome']
            counts[outcome] = counts.get(outcome, 0) + 1
    return table


def verify_seed(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'seed collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    expected = [store for store in STORES if not store['brandNew']]
    # Late stores are seeded just before the process exits, so report order is not vector order.
    seeded = {entry['case']: entry for entry in report['seeded']}
    require(len(report['seeded']) == len(expected) and set(seeded) == {store['id'] for store in expected},
            'missing/extra stores')
    for store in expected:
        label = store['id']
        entry = seeded[label]
        name = cookie_name(store['kind'])
        require(all(entry['visitsLoaded']), label + ': seed visit did not load')
        if store['group'] == 'cookie':
            require(name in entry['inventoryAfterSeed'], label + ': seed cookie not inventoried')
        if store['group'] == 'free':
            require(entry['inventoryAfterSeed'] == [], label + ': cookie-free seed contains a cookie')
        if store['storage']:
            require(entry['storageReady'] is True, label + ': local data was not written')
    return count


def verify_check(report, seed):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'check collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    require([entry['case'] for entry in report['checks']] == [store['id'] for store in STORES], 'missing/extra stores')
    written = {entry['case']: entry['partition'] for entry in seed['seeded']}
    for store, entry in zip(STORES, report['checks']):
        label = store['id']
        result = classify(store, entry, rows)
        if not store['brandNew']:
            require(entry['partition'] == written[label], label + ': reopened a different partition')
        require(entry['policyAllowsAfterRule'] is False, label + ': deny policy not active for the rule')
        require(entry['witnessFirstLoaded'] and entry['witnessXsiteLoaded'], label + ': witness context did not load')
        if store['group'] == 'cookie':
            require(result['witnessed'], label + ': positive control has no server witness')
            require(cookie_name(store['kind']) in entry['inventoryFinal'], label + ': cookie lost during the check')
        if store['group'] == 'free':
            require(not result['witnessed'], label + ': free control has a server witness')
        if store['storage']:
            require(entry['storage'] == {'local': label, 'indexed': label}, label + ': local data lost')
        if store['hazard']:
            # The same store must show the blocker before policy and the correct verdict after it.
            require(entry['namesBeforePolicy'] == [], label + ': hazard control did not reproduce the false empty')
            require(result['verdict'] != 'empty', label + ': hazard control was not detected after policy')
    return count


def integrity(report):
    metadata = report['build']
    assert report['platform'] == 'ios', 'unknown native platform'
    paths = [ROOT / name for name in SOURCES] + [path for path in (ROOT / 'ios').rglob('*') if path.is_file()]
    assert set(metadata['sources']) == {str(path.relative_to(ROOT)) for path in paths}, 'missing/extra source fingerprints'
    for path, digest in metadata['sources'].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['executableSha256']
    artifact = ROOT / 'build/CookieEmptyProbe.app/CookieEmptyProbe'
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata['executableSha256'], 'local artifact changed'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--summary', action='store_true')
    arguments = parser.parse_args()
    checks = []
    for path in arguments.reports:
        loaded = json.loads(path.read_text())
        integrity(loaded)
        if loaded['mode'] == 'seed':
            total = verify_seed(loaded)
        else:
            total = verify_check(loaded, json.loads(path.with_name(path.name.replace('check-', 'seed-')).read_text()))
            checks.append(loaded)
        print(f'{path.name}: {total} checks')
    if arguments.summary:
        print(json.dumps(outcomes(checks), indent=1))
