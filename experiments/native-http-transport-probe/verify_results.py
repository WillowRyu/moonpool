"""Turn raw native observations and server receipts into findings about each platform's HTTP client.

A folded header or a followed redirect is a finding and does not fail verification. Missing controls
or receipts do, because then nothing can be claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())
BY_ID = {case['id']: case for case in CASES}
EXCLUDED = {'build', '.gradle'}


def split_folded(value):
    """The best a client can do with a folded value: split where a comma precedes a name=."""
    return re.split(r',\s*(?=[^;,=\s]+=)', value)


def canonical_cookie_lines(observation):
    """One pipeline for both platforms: fold what arrived as separate fields, then split it."""
    fields, folded = observation.get('setCookieFields'), observation.get('setCookieFolded')
    value = ', '.join(fields) if fields else folded
    return split_folded(value) if value else []


def canonical_differences(first, second):
    left = {item['case']: canonical_cookie_lines(item) for item in first['observations']}
    right = {item['case']: canonical_cookie_lines(item) for item in second['observations']}
    return [name for name in left if left[name] != right.get(name)]


def set_cookie(observation, expected):
    fields, folded = observation.get('setCookieFields'), observation.get('setCookieFolded')
    if fields:
        if fields == expected:
            return {'shape': 'separate-ordered', 'splitRecovers': None}
        return {'shape': 'separate-reordered' if sorted(fields) == sorted(expected) else 'altered', 'splitRecovers': None}
    if folded:
        if folded == ', '.join(expected):
            return {'shape': 'folded', 'splitRecovers': split_folded(folded) == expected}
        return {'shape': 'altered', 'splitRecovers': False}
    return {'shape': 'missing', 'splitRecovers': None}


def classify(report):
    observations = {item['case']: item for item in report['observations']}
    rows = report['requests']

    def received(case_id, path=None):
        return [row for row in rows if row['case'] == case_id and row['event'] == 'arrived' and (path is None or row['path'] == path)]

    cookies = {case['id']: set_cookie(observations[case['id']], case['setCookie']) for case in CASES if case.get('setCookie')}

    def visible(case_id):
        return cookies[case_id]['shape'] != 'missing'

    attached = [case for case in CASES if case.get('attachCookie')]
    return {
        'setCookie': cookies,
        'ambientCookieSent': any(row['cookieFields'] for name in ['control-echo', 'after-multi-echo'] for row in received(name)),
        'attachedCookieExact': all(row['cookieFields'] == [case['attachCookie']] for case in attached for row in received(case['id'])),
        'redirects': {case['id']: {'status': observations[case['id']]['status'],
                                   'locationVisible': observations[case['id']]['location'] is not None,
                                   'cookieVisible': visible(case['id']),
                                   'targetHits': len(received(case['id'], '/target'))}
                      for case in CASES if case.get('redirect')},
        'errorStatuses': {name: {'status': observations[name]['status'],
                                 'bodyVisible': name in (observations[name]['bodyText'] or ''),
                                 'cookieVisible': visible(name)} for name in ['status-404', 'status-500']},
        'challenges': {case['id']: {'status': observations[case['id']]['status'], 'attempts': len(received(case['id'])),
                                    'authorizationSent': any(row['authorization'] for row in received(case['id'])),
                                    'error': observations[case['id']]['error']}
                       for case in CASES if case.get('challenge')},
        'cacheServerHits': len(received('cache-pair')),
        'holds': {'respondedBeforeHeaderRelease': observations['hold-headers']['respondedBeforeRelease'],
                  'headersBeforeBodyRelease': observations['hold-body']['headersBeforeRelease'],
                  'bodyBeforeBodyRelease': observations['hold-body']['bodyBeforeRelease']},
        'holdBodyVariants': {case['id']: observations[case['id']]['headersBeforeRelease'] for case in CASES if case.get('kind') == 'hold-body'},
    }


def flatten(value, prefix=''):
    if not isinstance(value, dict):
        return {prefix: value}
    flat = {}
    for key, item in value.items():
        flat.update(flatten(item, f'{prefix}.{key}' if prefix else key))
    return flat


def compare(first, second):
    left, right = flatten(first), flatten(second)
    return {key: (left.get(key), right.get(key)) for key in sorted(set(left) | set(right)) if left.get(key) != right.get(key)}


def verify(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'collection incomplete')
    require(report.get('errors') == [], 'native errors recorded')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run TLS row')
    observations = {item['case']: item for item in report['observations']}
    require([item['case'] for item in report['observations']] == [case['id'] for case in CASES], 'missing/extra cases')
    for case in CASES:
        name = case.get('requestCase', case['id'])
        selected = [row for row in rows if row['case'] == name]
        if case.get('kind') == 'tls-negative':
            item = observations[case['id']]
            # Without this, a pass elsewhere could come from validation being off.
            require(item['status'] is None and item['error'], 'TLS negative was not refused')
            require(selected == [], 'TLS negative reached the server')
            continue
        require(any(row['path'] == case['path'] for row in selected), case['id'] + ': no server receipt')
        if case.get('kind', '').startswith('hold'):
            require(any(row['event'] == 'released' for row in selected), case['id'] + ': server never released it')
    require(observations['control-echo']['status'] == 200, 'positive control failed: echo')
    require(observations['target-control']['status'] == 200, 'positive control failed: redirect target')
    return count


def integrity(report):
    metadata = report['build']
    platform = report['platform']
    assert platform in ('android', 'ios'), 'unknown native platform'
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'cases.json']]
    paths += [path for path in (ROOT / platform).rglob('*') if path.is_file() and not EXCLUDED & set(path.relative_to(ROOT).parts)]
    assert set(metadata['sources']) == {str(path.relative_to(ROOT)) for path in paths}, 'missing/extra source fingerprints'
    for path, digest in metadata['sources'].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['artifactSha256']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--summary', action='store_true')
    arguments = parser.parse_args()
    results = {}
    for path in arguments.reports:
        loaded = json.loads(path.read_text())
        integrity(loaded)
        print(f'{path.name}: {verify(loaded)} checks')
        results[path.stem] = classify(loaded)
    if arguments.summary:
        print(json.dumps(results, indent=1))
