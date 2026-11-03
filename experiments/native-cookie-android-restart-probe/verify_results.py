"""Compare Android hasCookies answers in a new process with independent server witnesses.

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
EXCLUDED = {'build', '.gradle'}


def source_paths():
    found = [ROOT / name for name in SOURCES]
    for path in (ROOT / 'android').rglob('*'):
        if path.is_file() and not EXCLUDED & set(path.relative_to(ROOT).parts):
            found.append(path)
    return found


def outcome(answer, witnessed):
    if answer:
        return 'correct-refuse' if witnessed else 'over-refuse'
    return 'false-admit' if witnessed else 'correct-admit'


def classify(store, entry, rows):
    name = cookie_name(store['kind'])
    witnessed = any(row['case'] == store['id'] and name in row['cookie'] for row in rows)
    return {'witnessed': witnessed, 'first': entry['first'], 'afterPolicy': entry['afterPolicy'], 'later': entry['later'],
            'firstOutcome': outcome(entry['first'], witnessed), 'ruleOutcome': outcome(entry['afterPolicy'], witnessed)}


def outcomes(reports):
    table = {}
    for report in reports:
        for store, entry in zip(STORES, report['checks']):
            row = table.setdefault(store['kind'], {'first': {}, 'rule': {}})
            result = classify(store, entry, report['requests'])
            for key, value in [('first', result['firstOutcome']), ('rule', result['ruleOutcome'])]:
                row[key][value] = row[key].get(value, 0) + 1
    return table


def outcomes_by_order(reports):
    table = {}
    for report in reports:
        for store, entry in zip(STORES, report['checks']):
            counts = table.setdefault(entry['order'], {})
            value = classify(store, entry, report['requests'])['firstOutcome']
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
    expected = [store for store in STORES if not store['brandNew']]
    # Late stores are seeded just before the process exits, so report order is not vector order.
    seeded = {entry['case']: entry for entry in report['seeded']}
    require(len(report['seeded']) == len(expected) and set(seeded) == {store['id'] for store in expected},
            'missing/extra stores')
    for store in expected:
        label = store['id']
        entry = seeded[label]
        require(all(entry['visitsLoaded']), label + ': seed visit did not load')
        if store['group'] == 'cookie':
            require(entry['hasCookies'] is True, label + ': seed cookie not present in the writing process')
        if store['group'] == 'free':
            require(entry['hasCookies'] is False, label + ': cookie-free seed contains a cookie')
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
    written = {entry['case']: entry['profile'] for entry in seed['seeded']}
    for store, entry in zip(STORES, report['checks']):
        label = store['id']
        result = classify(store, entry, rows)
        if not store['brandNew']:
            require(entry['profile'] == written[label], label + ': reopened a different profile')
        require(entry['acceptAtRule'] is False, label + ': deny policy not active for the baseline answer')
        # Android's deny policy withholds retained cookies, so a witness under it would prove nothing.
        require(entry['acceptDuringWitness'] is True, label + ': witness did not run under allow')
        require(entry['witnessFirstLoaded'] and entry['witnessXsiteLoaded'], label + ': witness context did not load')
        if store['group'] == 'cookie':
            require(result['witnessed'], label + ': positive control has no server witness')
            require(entry['finalHasCookies'] is True, label + ': cookie lost during the check')
        if store['group'] == 'free':
            require(not result['witnessed'], label + ': free control has a server witness')
        if store['storage']:
            require(entry['storage'] == {'local': label, 'indexed': label}, label + ': local data lost')
    return count


def first_call_outcomes(reports):
    counts = {}
    for report in reports:
        store = next(s for s in STORES if s['id'] == report['only'])
        value = classify(store, report['checks'][0], report['requests'])['firstOutcome']
        counts[value] = counts.get(value, 0) + 1
    return counts


def verify_first_call(report, seed):
    """The first native cookie question this process asked, on one store written by an earlier one."""
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'first-call collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    require([entry['case'] for entry in report['checks']] == [report['only']], 'process did not check exactly its store')
    store = next(s for s in STORES if s['id'] == report['only'])
    entry = report['checks'][0]
    require(store['order'] == 'bare', store['id'] + ': only a bare store answers the first-call question')
    written = {item['case']: item['profile'] for item in seed['seeded']}
    require(entry['profile'] == written[store['id']], store['id'] + ': reopened a different profile')
    require(entry['acceptDuringWitness'] is True, store['id'] + ': witness did not run under allow')
    require(entry['witnessFirstLoaded'] and entry['witnessXsiteLoaded'], store['id'] + ': witness context did not load')
    result = classify(store, entry, rows)
    if store['group'] == 'cookie':
        require(result['witnessed'], store['id'] + ': positive control has no server witness')
    if store['group'] == 'free':
        require(not result['witnessed'], store['id'] + ': free control has a server witness')
    return count


def integrity(report):
    metadata = report['build']
    assert report['platform'] == 'android', 'unknown native platform'
    assert set(metadata['sources']) == {str(path.relative_to(ROOT)) for path in source_paths()}, 'missing/extra source fingerprints'
    for path, digest in metadata['sources'].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['apkSha256']
    artifact = ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata['apkSha256'], 'local artifact changed'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--summary', action='store_true')
    arguments = parser.parse_args()
    checks = []
    firsts = []
    for path in arguments.reports:
        loaded = json.loads(path.read_text())
        integrity(loaded)
        if loaded['mode'] == 'seed':
            total = verify_seed(loaded)
        elif loaded.get('only'):
            total = verify_first_call(loaded, json.loads(path.with_name(f"android-seed-{loaded['cycle']}.json").read_text()))
            firsts.append(loaded)
        else:
            total = verify_check(loaded, json.loads(path.with_name(path.name.replace('check-', 'seed-')).read_text()))
            checks.append(loaded)
        print(f'{path.name}: {total} checks')
    if arguments.summary:
        print(json.dumps({'byKind': outcomes(checks), 'firstByOrder': outcomes_by_order(checks),
                          'firstCallInProcess': first_call_outcomes(firsts)}, indent=1))
