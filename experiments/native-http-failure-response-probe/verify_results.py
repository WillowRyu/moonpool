"""Compare what failureResponse reported with what the fixture actually served on each arrival.

Whether the first cookie is carried is the finding, so a "no" still verifies. Missing evidence or a failed control
rejects the report, because then nothing else in the run can be trusted.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())


def folded(fields):
    """URLSession's own view of several Set-Cookie fields."""
    return ', '.join(fields) if fields else None


def observation(report, case):
    return next(item for item in report['observations'] if item['case'] == case['id'])


def arrivals(report, case):
    return sorted((row for row in report['requests'] if row['case'] == case['id']), key=lambda row: row['arrival'])


def classify_case(report, case):
    item, received = observation(report, case), arrivals(report, case)
    challenges, responses = item.get('challenges', []), item.get('responses', [])
    first = folded(received[0]['served']) if received else None
    last = folded(received[-1]['served']) if received else None
    challenge = challenges[0] if challenges else {}
    reported = challenge.get('setCookie')
    delivered = responses[-1].get('setCookie') if responses else None
    return {'arrivals': len(received), 'challenges': len(challenges), 'responses': len(responses), 'status': item.get('status'),
            'hasFailureResponse': challenge.get('hasFailureResponse'), 'failureStatus': challenge.get('status'), 'previousFailureCount': challenge.get('previousFailureCount'),
            'firstServed': first, 'lastServed': last, 'failureResponseSetCookie': reported, 'delivered': delivered,
            'carriesFirst': bool(challenge.get('hasFailureResponse')) and challenge.get('status') == case['status'] and reported == first,
            'deliveredIsLast': delivered == last, 'authorizations': [row['authorization'] for row in received], 'bodyLengths': [row['bodyLength'] for row in received]}


def finding(reports):
    """Usable means every Basic case, in every run, showed the first attempt's fields at the challenge."""
    not_carried = {case['id'] for report in reports for case in CASES if case.get('challenge') == 'Basic' and not classify_case(report, case)['carriesFirst']}
    return {'usable': not not_carried, 'notCarried': sorted(not_carried)}


def verify(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'collection incomplete')
    require(report.get('errors') == [], 'native errors recorded')
    require([item['case'] for item in report['observations']] == [case['id'] for case in CASES], 'missing/extra cases')
    for row in report['requests']:
        require(row['tls'] and row['run'] == report['run'], 'non-TLS or foreign run row')
    for case in CASES:
        found = classify_case(report, case)
        require(found['arrivals'] >= 1, f"{case['id']}: never reached the server")
        require(found['status'] == case['status'], f"{case['id']}: status {found['status']}")
        require(found['responses'] >= 1, f"{case['id']}: no response delivered")
        if case.get('control'):
            require(found['arrivals'] == 1, f"{case['id']}: {found['arrivals']} arrivals")
            require(found['challenges'] == 0, f"{case['id']}: unexpected challenge")
            require(found['deliveredIsLast'], f"{case['id']}: delivered {found['delivered']}")
    return count


def compare(first, second):
    return [case['id'] for case in CASES if classify_case(first, case) != classify_case(second, case)]


def integrity(report):
    metadata = report['build']
    for path, digest in metadata['sources'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['artifactSha256']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--summary', action='store_true')
    arguments = parser.parse_args()
    loaded = {path.stem: json.loads(path.read_text()) for path in arguments.reports}
    for name, report in loaded.items():
        integrity(report)
        print(f'{name}: {verify(report)} checks')
    names = list(loaded)
    for left, right in zip(names, names[1:]):
        print(f'{left} vs {right}: {compare(loaded[left], loaded[right]) or "same measurements"}')
    print('finding:', json.dumps(finding(list(loaded.values()))))
    if arguments.summary:
        report = loaded[names[0]]
        print(json.dumps({case['id']: classify_case(report, case) for case in CASES}, indent=1))
