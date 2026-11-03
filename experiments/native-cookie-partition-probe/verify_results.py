"""Check witnesses and controls, then classify outcomes without presuming them.

A false empty or a late write is a research finding to report, so it does not fail
verification. Missing controls or witnesses do, because then nothing can be claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PARTITIONS = json.loads((ROOT / 'partition_cases.json').read_text())
WRITERS = json.loads((ROOT / 'writer_cases.json').read_text())
WARMUPS = json.loads((ROOT / 'warmup_cases.json').read_text())
READS = ['read-same', 'read-other', 'read-first', 'read-same-deny']


def script_saw(visit, name):
    result = visit.get('result') or {}
    if name in (result.get('documentCookie') or ''):
        return True
    return any(entry.get('name') == name for entry in (result.get('storeNames') or []))


def classify_partition(case, sample, rows):
    name = 't28p_' + case['id']
    selected = [row for row in rows if row['case'] == case['id']]

    def sent(step):
        return any(row['step'] == step and name in row['cookie'] for row in selected)

    visits = sample['visits']
    server_witness = any(sent(step) for step in READS)
    script_witness = any(script_saw(visit, name) for visit in visits.values())
    witnessed = server_witness or script_witness
    inventoried = any(name in sample[key] for key in
                      ['inventoryAfterSeed', 'inventoryAfterReads', 'inventoryAfterDeny', 'inventoryFinal'])
    return {
        'seedDelivered': visits['seed']['loaded'],
        'storedEvidence': witnessed,
        'inventoried': inventoried,
        'falseEmpty': witnessed and not inventoried,
        'sentSame': sent('read-same'),
        'sentOther': sent('read-other'),
        'sentFirst': sent('read-first'),
        'sentSameAfterDeny': sent('read-same-deny'),
        # A context that failed to load says nothing, so it cannot establish separation.
        'partitionSeparated': (sent('read-same') and not sent('read-other') and not sent('read-first')
                               and visits['read-other']['loaded'] and visits['read-first']['loaded']),
    }


def index_of(name):
    match = re.search(r'_(\d+)$', name)
    return int(match.group(1)) if match else -1


def classify_writer(case, sample, rows):
    name = 't28w_' + case['id']
    witness = any(row['case'] == case['id'] and row['step'] == 'echo' and name in row['cookie'] for row in rows)
    if case['kind'] == 'hold':
        inventoried = bool(sample['inventoryAfterRelease'])
        return {
            'landedAfterEmptyCheck': inventoried or witness,
            'inventoryMissedWitness': witness and not inventoried,
            'serverWitness': witness,
            'responseDelivered': sample['responseDelivered'],
            'clientClosedBeforeRelease': any(row['case'] == case['id'] and row.get('event') == 'released'
                                             and row.get('clientClosed') for row in rows),
        }
    if case['kind'] == 'burst':
        added = sorted(set(sample['inventoryLater']) - set(sample['inventoryAtCompletion']), key=index_of)
        return {
            'addedAfterCompletion': added,
            # writesAtCompletion is read after the policy completes, so this undercounts.
            'issuedAfterCompletion': [item for item in added if index_of(item) > sample['writesAtCompletion']],
            'serverWitness': witness,
        }
    if case['kind'] == 'native-unawaited':
        return {'seenImmediately': sample['seenImmediately'], 'seenAfterCompletion': sample['seenAfterCompletion']}
    if case['kind'] == 'native-under-deny':
        return {'storedUnderDeny': bool(sample['inventoryAfterSet']), 'serverWitness': witness}
    return {key: sample[key] for key in
            ['sameObject', 'firstSeesSecondPolicy', 'secondSeesFirstPolicy', 'firstSeesSecondCookie', 'policyAfterRestore']}


def verify(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    require([s['case'] for s in report['samples']] == [c['id'] for c in PARTITIONS], 'missing/duplicate partition cases')
    require([w['case'] for w in report['writers']] == [c['id'] for c in WRITERS], 'missing/duplicate writer cases')

    for case, sample in zip(PARTITIONS, report['samples']):
        label = case['id']
        result = classify_partition(case, sample, rows)
        visits = sample['visits']
        selected = [row for row in rows if row['case'] == label]
        if case['seedTop'] != 'moonpool':
            require(visits['seed']['loaded'], label + ': HTTPS seed context did not load')
        require(visits['read-first']['loaded'], label + ': first-party read did not load')
        for step, visit in visits.items():
            if visit['loaded']:
                require(any(row['step'] == step for row in selected), label + ': no receipt for loaded ' + step)
        if label == 'empty':
            require(not result['storedEvidence'] and not result['inventoried'], 'empty control contains a cookie')
        if label == 'firstparty-plain':
            require('t28p_' + label in sample['inventoryAfterSeed'] and result['sentSame'],
                    'positive control not stored and inventoried')
        if case['seedTop'] not in ['moonpool', case['service']]:
            seed = next((row for row in selected if row['step'] == 'seed'), None)
            require(seed is not None and seed['secFetchSite'] == 'cross-site', label + ': cross-site seed unproven')
        require(sample['policyAllowsAfterDeny'] is False, label + ': deny policy not active')
        require(set(sample['inventoryAfterSeed']) <= set(sample['inventoryFinal']), label + ': cookie lost')

    for case, sample in zip(WRITERS, report['writers']):
        label = case['id']
        result = classify_writer(case, sample, rows)
        if case['kind'] == 'hold':
            require(sample['heldObserved'] is True, label + ': request was not held before the action')
            require(sample['inventoryBeforeRelease'] == [], label + ': did not start from an empty check')
            require(any(row['case'] == label and row['event'] == 'released' for row in rows),
                    label + ': server never released the response')
            if case['action'] == 'deny':
                require(sample['policyAllows'] is False, label + ': deny policy not active')
                # "Nothing landed" means nothing unless the response really reached the page.
                require(sample['responseDelivered'] is True, label + ': response not delivered to the page')
            if case['action'] == 'none':
                require(result['landedAfterEmptyCheck'], 'race control did not demonstrate the landing')
        elif case['kind'] == 'burst':
            require(sample['writesAtStart'] >= 3 and sample['inventoryBeforePolicy'], label + ': writer not active')
            require(sample['policyAllows'] is False, label + ': deny policy not active')
            require(sample['stopped'] is True, label + ': writer not stopped before witness')
        elif case['kind'] == 'native-under-deny':
            require(sample['policyAllows'] is False, label + ': deny policy not active')
    return count


def classify_reopen(entry, rows):
    name = 't28p_' + entry['case']
    witness = any(row['case'] == entry['case'] and row['step'] == 'read-same-reopen' and name in row['cookie'] for row in rows)
    return {
        'inventoriedAtOpen': name in entry['inventoryAtOpen'],
        'witnessed': witness,
        'falseEmptyAtOpen': witness and name not in entry['inventoryAtOpen'],
        'policyAllowsAtOpen': entry['policyAllowsAtOpen'],
    }


def verify_reopen(report, source):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'reopen collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    require([(e['case'], e['partition']) for e in report['reopened']] == [(s['case'], s['partition']) for s in source['samples']],
            'reopened a different partition')
    for entry in report['reopened']:
        result = classify_reopen(entry, rows)
        if entry['case'] == 'empty':
            require(not result['inventoriedAtOpen'] and not result['witnessed'], 'empty control contains a cookie')
        if entry['case'] == 'firstparty-plain':
            # Absence at open is the finding under test, so it cannot also be this control.
            require(result['witnessed'] and 't28p_firstparty-plain' in entry['inventoryFinal'],
                    'positive control not retained and listed after a load')
    return count


def warmup_names(case_id):
    return ['t28u_' + case_id + '_first', 't28u_' + case_id + '_partitioned']


def classify_warmup(case, entry, rows):
    names = set(warmup_names(case['id']))
    timeline = entry['timeline']
    complete = [step['at'] for step in timeline if names <= set(step['names'])]
    witnessed = {name for name in names for row in rows if row['case'] == case['id'] and name in row['cookie']}
    return {
        'witnessed': sorted(witnessed),
        'falseEmptyAtFirstEnumeration': bool(witnessed - set(timeline[0]['names'])),
        'namesAtFirstEnumeration': len(names & set(timeline[0]['names'])),
        'listedByTimeline': bool(complete),
        'firstCompleteAt': complete[0] if complete else None,
        'dataRecordsAtFirstEnumeration': bool(timeline[0]['records']),
    }


def warmup_rates(reports):
    rates = {}
    for report in reports:
        for case, entry in zip(WARMUPS, report['warmups']):
            rate = rates.setdefault(case['action'], {'stores': 0, 'falseEmptyAtFirstEnumeration': 0})
            rate['stores'] += 1
            rate['falseEmptyAtFirstEnumeration'] += classify_warmup(case, entry, report['requests'])['falseEmptyAtFirstEnumeration']
    return rates


def verify_warmup_seed(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'seed collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    require([e['case'] for e in report['seeded']] == [c['id'] for c in WARMUPS], 'missing/duplicate seed cases')
    for entry in report['seeded']:
        require(set(warmup_names(entry['case'])) <= set(entry['inventoryAfterSeed']), entry['case'] + ': seed not inventoried')
    return count


def verify_warmup(report, seed):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'warmup collection incomplete')
    require(report.get('errors') == [], 'native load/TLS errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    require([(e['case'], e['partition']) for e in report['warmups']] == [(e['case'], e['partition']) for e in seed['seeded']],
            'reopened a different partition')
    for case, entry in zip(WARMUPS, report['warmups']):
        label = case['id']
        names = warmup_names(label)
        result = classify_warmup(case, entry, rows)
        require(sorted(result['witnessed']) == sorted(names), label + ': retained cookies lack a server witness')
        require(set(names) <= set(entry['inventoryFinal']), label + ': final inventory incomplete')
        if case['action'] == 'network':
            require(result['listedByTimeline'], 'network control did not produce a complete listing')
    return count


def summarize(report):
    if report.get('mode') == 'reopen':
        return {'reopen': {e['case']: classify_reopen(e, report['requests']) for e in report['reopened']}}
    if report.get('mode') == 'warmup-seed':
        return {'seeded': {e['case']: e['inventoryAfterSeed'] for e in report['seeded']}}
    if report.get('mode') == 'warmup':
        return {'warmup': {c['id']: classify_warmup(c, e, report['requests']) for c, e in zip(WARMUPS, report['warmups'])}}
    return {
        'partition': {c['id']: classify_partition(c, s, report['requests'])
                      for c, s in zip(PARTITIONS, report['samples'])},
        'writer': {c['id']: classify_writer(c, s, report['requests'])
                   for c, s in zip(WRITERS, report['writers'])},
    }


def integrity(report):
    metadata = report['build']
    assert report['platform'] == 'ios', 'unknown native platform'
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'frame.html', 'partition_cases.json', 'writer_cases.json', 'warmup_cases.json']]
    paths += [path for path in (ROOT / 'ios').rglob('*') if path.is_file()]
    assert set(metadata['sources']) == {str(path.relative_to(ROOT)) for path in paths}, 'missing/extra source fingerprints'
    for path, digest in metadata['sources'].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['executableSha256']
    artifact = ROOT / 'build/CookiePartitionProbe.app/CookiePartitionProbe'
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata['executableSha256'], 'local artifact changed'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--summary', action='store_true')
    arguments = parser.parse_args()
    for path in arguments.reports:
        loaded = json.loads(path.read_text())
        integrity(loaded)
        # Reopen reports are checked against the run that wrote their stores.
        if loaded.get('mode') == 'reopen':
            checks = verify_reopen(loaded, json.loads(path.with_name('ios-repeat.json').read_text()))
        elif loaded.get('mode') == 'warmup-seed':
            checks = verify_warmup_seed(loaded)
        elif loaded.get('mode') == 'warmup':
            source = path.with_name(path.name.replace('warmup-', 'warmup-seed-'))
            checks = verify_warmup(loaded, json.loads(source.read_text()))
        else:
            checks = verify(loaded)
        print(f'{path.name}: {checks} checks')
        if arguments.summary:
            print(json.dumps(summarize(loaded), indent=1))
