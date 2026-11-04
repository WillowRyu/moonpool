"""Compare raw observations and server receipts with the oracle in cases.json.

A case that misses the oracle is a contract finding: state "fail", and verification still passes. Missing
evidence or a failed control does fail verification, because then nothing else in the run can be trusted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from fixture import EXPECTED_AUTHORIZATION

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())
EXCLUDED = {'build', '.gradle'}
BARRIERS = {'held', 'release', 'await', 'awaitEvent', 'startQueued'}
GUEST_OPS = {'request', 'cookiesGet', 'cookiesSet', 'cookiesDelete', 'reset'}
FORBIDDEN_RESPONSE_HEADERS = {'set-cookie', 'set-cookie2'}
VOLATILE_RESPONSE_HEADERS = {'date'}


def observation(report, case):
    return next(item for item in report['observations'] if item['case'] == case['id'])


def arrived(report, case, label):
    return [row for row in report['requests'] if row['case'] == case['id'] and row['step'] == label and row['event'] == 'arrived']


def outcome_problems(label, expected, actual):
    problems = []
    if actual is None:
        return [f'{label}: no outcome']
    headers = actual.get('headers') or {}
    for key, value in expected.items():
        if key == 'hasHeaders':
            problems += [f'{label}: header {name} missing' for name in value if name not in headers]
        elif key == 'headerValues':
            problems += [f'{label}: header {name} is {headers.get(name)!r}' for name, wanted in value.items() if headers.get(name) != wanted]
        elif key == 'bodyContains':
            if value not in (actual.get('bodyText') or ''):
                problems.append(f'{label}: body lacks {value!r}')
        elif actual.get(key) != value:
            problems.append(f'{label}: {key} is {actual.get(key)!r}, expected {value!r}')
    return problems


def receipt_problems(label, expected, rows):
    problems = []
    if 'count' in expected and len(rows) != expected['count']:
        problems.append(f'{label}: {len(rows)} receipts, expected {expected["count"]}')
    if 'cookie' in expected and (not rows or rows[0]['cookieFields'] != expected['cookie']):
        problems.append(f'{label}: cookie {[row["cookieFields"] for row in rows]}, expected {expected["cookie"]}')
    if 'authorization' in expected and any(row['authorization'] != expected['authorization'] for row in rows):
        problems.append(f'{label}: authorization {[row["authorization"] for row in rows]}')
    if expected.get('noAuthorization') and any(row['authorization'] for row in rows):
        problems.append(f'{label}: authorization was sent')
    if expected.get('noAuthorization') and not rows:
        problems.append(f'{label}: no receipt')
    if 'cookieContains' in expected and not any(expected['cookieContains'] in field for row in rows for field in row['cookieFields']):
        problems.append(f'{label}: {expected["cookieContains"]} never arrived')
    if expected.get('authorizationSeen') and not any(row['authorization'] == EXPECTED_AUTHORIZATION for row in rows):
        problems.append(f'{label}: fixture credential never arrived')
    if 'method' in expected and any(row['method'] != expected['method'] for row in rows):
        problems.append(f'{label}: method {[row["method"] for row in rows]}, expected {expected["method"]}')
    if 'bodyLength' in expected and any(row['bodyLength'] != expected['bodyLength'] for row in rows):
        problems.append(f'{label}: body length {[row["bodyLength"] for row in rows]}, expected {expected["bodyLength"]}')
    return problems


def classify_case(report, case):
    expect = case['expect']
    item = observation(report, case)
    steps = {step['label']: step for step in item['steps']}
    host_labels = {step['label'] for step in case['steps'] if step['op'] == 'hostRequest'}
    problems = []
    for label, expected in expect.get('outcomes', {}).items():
        problems += outcome_problems(label, expected, steps.get(label, {}).get('outcome'))
    for label, expected in expect.get('receipts', {}).items():
        problems += receipt_problems(label, expected, arrived(report, case, label))
    for label, expected in expect.get('jar', {}).items():
        actual = steps.get(label, {}).get('jar')
        if actual is None or sorted(actual) != sorted(expected):
            problems.append(f'{label}: jar {actual}, expected {expected}')
    guest = [step for step in item['steps'] if step['op'] in GUEST_OPS]
    text = json.dumps([step['outcome'] for step in guest])
    problems += [f'{marker} is visible to the guest' for marker in expect.get('hidden', []) if marker in text]
    for step in guest:
        exposed = FORBIDDEN_RESPONSE_HEADERS & {name.lower() for name in (step['outcome'].get('headers') or {})}
        if exposed:
            problems.append(f'{step["label"]}: guest headers include {sorted(exposed)}')
    rows = [row for row in report['requests'] if row['case'] == case['id'] and row['event'] == 'arrived' and row['step'] not in host_labels]
    if any('host_' in field for row in rows for field in row['cookieFields']):
        problems.append('a host cookie reached a broker request')
    if any(row['authorization'] == EXPECTED_AUTHORIZATION for row in rows):
        problems.append('a host credential reached a broker request')
    events = item.get('events', [])
    if 'commitOrder' in expect:
        commits = [event['label'] for event in events if event['kind'] == 'commit' and event['label'] in expect['commitOrder']]
        if commits != expect['commitOrder']:
            problems.append(f'commit order {commits}, expected {expect["commitOrder"]}')
    for label in expect.get('fenced', []):
        if not any(event['kind'] == 'fence' and event['label'] == label for event in events):
            problems.append(f'{label}: no fence event')
        if any(event['kind'] == 'commit' and event['label'] == label for event in events):
            problems.append(f'{label}: committed despite the fence')
    return {'contract': case['contract'], 'state': 'fail' if problems else 'pass', 'problems': problems}


def classify(report):
    return {case['id']: classify_case(report, case) for case in CASES}


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
        item = observation(report, case)
        require(item.get('timedOut') == [], f'{case["id"]}: barrier timed out: {item.get("timedOut")}')
        labels = {step['label'] for step in item['steps']}
        for step in case['steps']:
            if step['op'] not in BARRIERS:
                require(step['label'] in labels, f'{case["id"]}: missing step {step["label"]}')
            if step.get('serve', {}).get('hold') and arrived(report, case, step['label']):
                released = [row for row in report['requests'] if row['case'] == case['id'] and row['step'] == step['label'] and row['event'] == 'released']
                require(released, f'{case["id"]}: {step["label"]} was never released')
    states = classify(report)
    for case in CASES:
        if case['contract'] == 'control':
            require(states[case['id']]['state'] == 'pass', f'{case["id"]}: control failed: {states[case["id"]]["problems"]}')
    return count


def guest_headers(outcome):
    """Response headers a mini app reads, without what differs by run: the clock, and a Location's run tag and port."""
    headers = {name: value for name, value in (outcome.get('headers') or {}).items() if name not in VOLATILE_RESPONSE_HEADERS}
    if 'location' in headers:
        headers['location'] = re.sub(r'(://[^/:]+):\d+', r'\1', re.sub(r'run=[a-z0-9-]+', 'run=', headers['location']))
    return headers


def normalized(report, case):
    """What a mini app and the server would see, leaving out what the case declares as a measurement."""
    measured = set(case['expect'].get('measure', []))
    item = observation(report, case)
    by_label = {step['label']: step for step in item['steps']}
    found = {}
    for step in case['steps']:
        label = step['label']
        if step['op'] in BARRIERS or label in measured or step['op'] in {'hostRequest', 'hostSeed', 'hostClear', 'hostInspect', 'tlsNegative'}:
            continue
        seen = by_label.get(label, {})
        outcome = seen.get('outcome') or {}
        found[label] = {'outcome': {key: outcome.get(key) for key in ['ok', 'status', 'code', 'reason', 'cookies', 'delivered', 'bodyText'] if key in outcome}, 'headers': guest_headers(outcome)}
        if step['op'] == 'snapshot':
            found[label]['jar'] = sorted(seen.get('jar') or [])
        if step['op'] == 'request':
            rows = arrived(report, case, label)
            found[label]['cookieFields'] = rows[0]['cookieFields'] if rows else None
            # iOS may resend after a Basic challenge. The accepted rule documents it, so the count stays a measurement.
            if step.get('serve', {}).get('challenge') != 'Basic':
                found[label]['receipts'] = len(rows)
    return found


def compare(first, second):
    differences = []
    for case in CASES:
        left, right = normalized(first, case), normalized(second, case)
        if left != right:
            labels = sorted(label for label in left if left[label] != right.get(label))
            differences.append({'case': case['id'], 'labels': {label: {first['platform']: left[label], second['platform']: right.get(label)} for label in labels}})
    return differences


def measurements(report):
    """Facts the oracle deliberately does not judge, with attempt counts from the server."""
    found = {}
    for case in CASES:
        for label in case['expect'].get('measure', []):
            step = next((s for s in observation(report, case)['steps'] if s['label'] == label), {})
            rows = arrived(report, case, label)
            outcome = step.get('outcome') or {}
            found[f"{case['id']}/{label}"] = {'jar': step.get('jar'), 'status': outcome.get('status'), 'cookies': outcome.get('cookies'), 'attempts': len(rows),
                                              'authorizations': [row['authorization'] for row in rows]}
    return found


def integrity(report):
    metadata = report['build']
    platform = report['platform']
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
    loaded = {path.stem: json.loads(path.read_text()) for path in arguments.reports}
    summary = {}
    for name, report in loaded.items():
        integrity(report)
        print(f'{name}: {verify(report)} checks')
        states = classify(report)
        summary[name] = {'failed': {key: item['problems'] for key, item in states.items() if item['state'] == 'fail'},
                         'passed': sum(item['state'] == 'pass' for item in states.values()), 'measurements': measurements(report)}
    names = list(loaded)
    for left, right in zip(names, names[1:]):
        summary[f'{left} vs {right}'] = compare(loaded[left], loaded[right])
    if arguments.summary:
        print(json.dumps(summary, indent=1))
