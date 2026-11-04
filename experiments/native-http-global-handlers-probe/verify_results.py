"""Turn raw observations and server receipts into findings about a host's global HTTP handlers.

A global that reaches a request is a finding and does not fail verification. Missing controls or
receipts do, because then nothing can be claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fixture import EXPECTED_AUTHORIZATION

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())
EXCLUDED = {'build', '.gradle'}
PLAIN_CONTROLS = ['control-plain', 'control-after-plain']
CHALLENGE_CONTROLS = ['control-basic-401', 'control-after-basic-401']


def classify(report):
    observations = {item['case']: item for item in report['observations']}
    rows = report['requests']

    def received(case_id, path=None):
        return [row for row in rows if row['case'] == case_id and row['event'] == 'arrived' and (path is None or row['path'] == path)]

    def cookie_sent(case_id, name):
        return any(name in field for row in received(case_id) for field in row['cookieFields'])

    def puts(case_id):
        return [value for event in observations[case_id]['handlerEvents'] if event.get('op') == 'put' for value in event['setCookie']]

    def credential_attempts(case_id):
        return sum(row['authorizationValue'] == EXPECTED_AUTHORIZATION for row in received(case_id))

    def authenticator(case_id):
        item = observations[case_id]
        return {'attempts': len(received(case_id)), 'credentialAttempts': credential_attempts(case_id),
                'authorizationValues': [row['authorizationValue'] for row in received(case_id)],
                'bodyLengths': [row['bodyLength'] for row in received(case_id)],
                'callbacks': len(item['authenticatorEvents']),
                'schemes': sorted({event.get('scheme') or '' for event in item['authenticatorEvents']}),
                'status': item['status'], 'error': item['error']}

    credentials = [case['id'] for case in CASES if case['id'].startswith('auth-')]
    opt_out = observations['opt-out-noop-authenticator']
    probe = observations['detect-authenticator-probe']
    return {
        'detection': {**report['api'], 'probeTellsInstalledFromCleared': probe['probeAnswered'] is True and probe['probeAnsweredAfterClear'] is False,
                      'probeHostCallbacks': len(probe['authenticatorEvents'])},
        'cookieHandler': {
            'ambientSentOnGet': cookie_sent('handler-get', 'host_ambient'),
            'ambientSentOnPost': cookie_sent('handler-post', 'host_ambient'),
            'attachedFields': next((row['cookieFields'] for row in received('handler-attached')), None),
            'attachedAloneFields': next((row['cookieFields'] for row in received('handler-empty-attached')), None),
            'setCookieDelivered': bool(puts('handler-set-cookie')),
            'httpOnlyDelivered': any('HttpOnly' in value for value in puts('handler-set-cookie')),
            'clientSeesSetCookie': bool(observations['handler-set-cookie']['setCookieFields']),
            'redirectSetCookieDelivered': bool(puts('handler-redirect')),
            'redirectTargetHits': len(received('handler-redirect', '/target')),
        },
        'cookieManager': {
            'seededHostCookieSent': cookie_sent('manager-seeded', 'host_session'),
            'otherDomainSent': cookie_sent('manager-other-domain', 'host_other'),
            'storedNames': sorted(entry['name'] for entry in observations['manager-capture']['storeAfter']),
            'httpOnlyStored': any(entry.get('httpOnly') for entry in observations['manager-capture']['storeAfter']),
            'capturedSentOnFollowup': cookie_sent('manager-capture-followup', 't28g_captured'),
        },
        'authenticator': {name: authenticator(name) for name in credentials},
        'perConnection': {
            'available': report['api']['setAuthenticator'],
            'result': opt_out['perConnectionResult'],
            'perConnectionCallbacks': len(opt_out['perConnectionEvents']),
            **authenticator('opt-out-noop-authenticator'),
        },
        'timing': {
            'handlerInstalledAfterOpenApplied': cookie_sent('handler-installed-after-open', 'host_ambient'),
            'handlerClearedAfterOpenStillApplied': cookie_sent('handler-cleared-after-open', 'host_ambient'),
            'authenticatorInstalledAfterOpenApplied': credential_attempts('auth-installed-after-open') > 0,
            'authenticatorClearedAfterOpenStillApplied': credential_attempts('auth-cleared-after-open') > 0,
        },
        'combined': {'handlerReceived': puts('combined-basic-cookie'), 'clientSees': observations['combined-basic-cookie']['setCookieFields'],
                     **authenticator('combined-basic-cookie')},
    }


def verify(report):
    count = 0

    def require(value, message):
        nonlocal count
        assert value, message
        count += 1

    require(report.get('complete') is True, 'collection incomplete')
    require(report.get('errors') == [], 'native errors recorded')
    start = report['globalsAtStart']
    require(start['cookieHandlerNull'] and start['authenticatorNull'], 'globals were already set before the first case')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run row')
    allowed = {None, EXPECTED_AUTHORIZATION} | {case['presetAuthorization'] for case in CASES if case.get('presetAuthorization')}
    require(all(row['authorizationValue'] in allowed for row in rows), 'a value other than the public fixture credential was sent')
    observations = {item['case']: item for item in report['observations']}
    require([item['case'] for item in report['observations']] == [case['id'] for case in CASES], 'missing/extra cases')

    def selected(name):
        return [row for row in rows if row['case'] == name]

    for case in CASES:
        name = case['id']
        if case.get('kind') == 'tls-negative':
            # Without this, a pass elsewhere could come from validation being off.
            require(observations[name]['status'] is None and observations[name]['error'], 'TLS negative was not refused')
            require(selected(name) == [], 'TLS negative reached the server')
            continue
        if case.get('kind') == 'detect-probe':
            # This also stands in for getDefault, which the running platform may not expose.
            require(observations[name]['probeAnswered'] is True, 'probe did not see the installed authenticator')
            require(observations[name]['probeAnsweredAfterClear'] is False, 'probe still saw a cleared authenticator')
            require(selected(name) == [], 'the probe sent a request')
            continue
        require(any(row['path'] == case['path'] for row in selected(name)), name + ': no server receipt')
        # A global that was never in place cannot count as ignored, and a timing case must show its claimed state.
        cleared = case.get('install') == 'cleared-after-open'
        require(observations[name]['handlerVisible'] is (bool(case.get('handler')) and not cleared), name + ': handler state wrong at send')
        require(observations[name]['authenticatorVisible'] is (bool(case.get('authenticator')) and not cleared), name + ': authenticator state wrong at send')

    for name in PLAIN_CONTROLS:
        arrived = selected(name)
        require(observations[name]['status'] == 200, name + ': positive control failed')
        require(len(arrived) == 1 and arrived[0]['cookieFields'] == [] and arrived[0]['authorizationValue'] is None, name + ': ambient state reached a clean request')
    for name in CHALLENGE_CONTROLS:
        arrived = selected(name)
        require(observations[name]['status'] == 401, name + ': challenge not returned')
        require(len(arrived) == 1 and arrived[0]['authorizationValue'] is None, name + ': clean challenge was retried or answered')
        require(observations[name]['authenticatorEvents'] == [], name + ': a cleared authenticator was called')
    return count


def integrity(report):
    metadata = report['build']
    assert report['platform'] == 'android', 'this probe is Android only'
    paths = [ROOT / name for name in ['build.py', 'fixture.py', 'cases.json']]
    paths += [path for path in (ROOT / 'android').rglob('*') if path.is_file() and not EXCLUDED & set(path.relative_to(ROOT).parts)]
    assert set(metadata['sources']) == {str(path.relative_to(ROOT)) for path in paths}, 'missing/extra source fingerprints'
    for path, digest in metadata['sources'].items():
        target = (ROOT / path).resolve()
        assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'changed source ' + path
    assert report['installedArtifactSha256'] == metadata['artifactSha256']
    artifact = ROOT / 'android/app/build/outputs/apk/debug/app-debug.apk'
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == metadata['artifactSha256'], 'local artifact changed'


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
