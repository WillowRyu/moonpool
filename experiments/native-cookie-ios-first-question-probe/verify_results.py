"""Each store is the first a new process asks about. Apply the accepted iOS rule to its raw answers.

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
    return {'verdict': rule, 'verdictLater': verdict(entry['later']), 'witnessed': witnessed, 'outcome': outcome}


def outcomes(report):
    table = {}
    for store, item in zip(STORES, report['launches']):
        counts = table.setdefault(store['kind'], {})
        value = classify(store, item['checks'][0], item['requests'])['outcome']
        counts[value] = counts.get(value, 0) + 1
    return table


def verify_seed(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'seed collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    require([entry['case'] for entry in report['seeded']] == [store['id'] for store in STORES], 'missing/extra stores')
    for store, entry in zip(STORES, report['seeded']):
        label = store['id']
        require(all(entry['visitsLoaded']), label + ': seed visit did not load')
        if store['group'] == 'cookie':
            require(cookie_name(store['kind']) in entry['inventoryAfterSeed'], label + ': seed cookie not inventoried')
        if store['group'] == 'free':
            require(entry['inventoryAfterSeed'] == [], label + ': cookie-free seed contains a cookie')
        if store['storage']:
            require(entry['storageReady'] is True, label + ': local data was not written')
    return count


def verify_first(report, seed):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    launches = report['launches']
    require([item['only'] for item in launches] == [store['id'] for store in STORES], 'every store needs its own launch')
    written = {entry['case']: entry['partition'] for entry in seed['seeded']}
    for store, item in zip(STORES, launches):
        label = store['id']
        require(item.get('complete') is True, label + ': launch incomplete')
        require(item.get('errors') == [], label + ': native load/TLS errors recorded')
        rows = item['requests']
        require(all(row['tls'] and row['run'] == item['run'] for row in rows), label + ': non-TLS or foreign run TLS row')
        require([entry['case'] for entry in item['checks']] == [label], label + ': process did not check exactly its store')
        entry = item['checks'][0]
        result = classify(store, entry, rows)
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
            # The same store must show the blocker before policy and a non-empty verdict after it.
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
    artifact = ROOT / 'build/CookieFirstQuestionProbe.app/CookieFirstQuestionProbe'
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata['executableSha256'], 'local artifact changed'


if __name__ == '__main__':
    results = ROOT / 'results'
    seed_report = json.loads((results / 'ios-seed.json').read_text())
    first_report = json.loads((results / 'ios-first.json').read_text())
    integrity(seed_report)
    integrity(first_report)
    print(f'ios-seed.json: {verify_seed(seed_report)} checks')
    print(f'ios-first.json: {verify_first(first_report, seed_report)} checks')
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', action='store_true')
    if parser.parse_args().summary:
        print(json.dumps(outcomes(first_report), indent=1))
