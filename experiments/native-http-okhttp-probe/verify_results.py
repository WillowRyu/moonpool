"""Turn raw observations and server receipts into findings about OkHttp as a broker's client.

A global that reaches a request or a resent request is a finding and does not fail verification.
Missing controls or receipts do. In particular, an ignored global means nothing unless the same
global reached HttpURLConnection in the same run.
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
TLS_NEGATIVES = ['tls-negative', 'tls-negative-global-trust']


def request_name(case):
    return case.get('requestCase', case['id'])


def set_cookie_shape(fields, expected):
    if fields is None:
        return 'missing'
    if fields == expected:
        return 'separate-ordered'
    return 'separate-reordered' if sorted(fields) == sorted(expected) else 'altered'


def classify(report):
    observations = {item['case']: item for item in report['observations']}
    rows = report['requests']

    def received(name, path=None):
        return [row for row in rows if row['case'] == name and row['event'] == 'arrived' and (path is None or row['path'] == path)]

    okhttp = [case for case in CASES if case.get('client') != 'huc']

    def attempts(name):
        item = observations[name]
        return {'attempts': len(received(name, '/serve')), 'targetHits': len(received(name, '/target')),
                'bodyLengths': [row['bodyLength'] for row in received(name, '/serve')], 'status': item['status'], 'error': item['error'],
                'retryAfterVisible': item.get('retryAfterVisible'), 'preservedRetryAfter': item.get('preservedRetryAfter')}

    with_cookies = [case for case in CASES if case.get('setCookie') and not case.get('acceptedSetCookie')]
    redirects = [case for case in CASES if case.get('redirect') and case.get('client') != 'default']
    attached = [case for case in CASES if case.get('attachCookie') and not case.get('handler')]
    return {
        'isolation': {
            'hostCookiesAtServer': [case['id'] for case in okhttp if any('host_' in field for row in received(request_name(case)) for field in row['cookieFields'])],
            'hostCredentialAttempts': [case['id'] for case in okhttp if any(row['authorizationValue'] == EXPECTED_AUTHORIZATION for row in received(request_name(case)))],
            'handlerCalled': [case['id'] for case in okhttp if observations[case['id']]['handlerEvents']],
            'authenticatorCalled': [case['id'] for case in okhttp if observations[case['id']]['authenticatorEvents']],
            'capturedCookiesResent': any('t28o_captured' in field for row in received('manager-capture-followup') for field in row['cookieFields']),
            'attachedWithHandler': next((row['cookieFields'] for row in received('handler-attached')), None),
            'presetAuthorization': [row['authorizationValue'] for row in received('auth-preset-authorization')],
            'storeAfterCapture': observations['manager-capture']['storeAfter'] if 'storeAfter' in observations['manager-capture'] else [],
            'challengeStatuses': {case['id']: observations[case['id']]['status'] for case in okhttp if case['id'].startswith('auth-')},
        },
        'controls': {
            'hucHostCookie': any('host_ambient' in field for row in received('huc-positive-cookie') for field in row['cookieFields']),
            'hucHostCredentials': any(row['authorizationValue'] == EXPECTED_AUTHORIZATION for row in received('huc-positive-basic')),
            'hucResponseCacheCalls': len(observations['huc-positive-response-cache']['responseCacheEvents']),
            'hucProxySelectorCalls': len(observations['huc-positive-proxy-selector']['proxySelectorEvents']),
            'hucReachedForeignHostWithGlobalTrust': observations['huc-positive-global-trust']['status'],
        },
        'otherGlobals': {
            'responseCacheCalls': len(observations['other-response-cache']['responseCacheEvents']),
            'proxySelectorCallsDefault': len(observations['other-proxy-selector-default']['proxySelectorEvents']),
            'proxySelectorCallsNoProxy': len(observations['other-proxy-selector-no-proxy']['proxySelectorEvents']),
            'globalTrustRefusal': observations['tls-negative-global-trust']['error'],
        },
        'transport': {
            'setCookie': {case['id']: set_cookie_shape(observations[case['id']]['setCookieFields'], case['setCookie']) for case in with_cookies},
            'ambientCookieSent': any(row['cookieFields'] for name in ['control-plain', 'after-multi-echo'] for row in received(name)),
            'attachedCookieExact': all(row['cookieFields'] == [case['attachCookie']] for case in attached for row in received(case['id'])),
            'redirects': {case['id']: {'status': observations[case['id']]['status'], 'locationVisible': observations[case['id']]['location'] is not None,
                                       'cookieVisible': bool(observations[case['id']]['setCookieFields']), 'targetHits': len(received(case['id'], '/target'))}
                          for case in redirects},
            'errorStatuses': {name: {'status': observations[name]['status'], 'bodyVisible': name in (observations[name]['bodyText'] or ''),
                                     'cookieVisible': bool(observations[name]['setCookieFields'])} for name in ['status-404', 'status-500']},
            'cacheServerHits': len(received('cache-pair')),
            'holds': {'respondedBeforeHeaderRelease': observations['hold-headers']['respondedBeforeRelease'],
                      'headersBeforeBodyRelease': observations['hold-body']['headersBeforeRelease'],
                      'headersBeforeBodyReleaseFirstByte': observations['hold-body-first-byte']['headersBeforeRelease'],
                      'bodyBeforeBodyRelease': observations['hold-body']['bodyBeforeRelease']},
        },
        'resends': {case['id']: attempts(case['id']) for case in CASES if case['id'].startswith(('resend-', 'default-'))},
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
    require(start['cookieHandlerNull'] and start['authenticatorNull'] and start['responseCacheNull'], 'globals were already set before the first case')
    rows = report['requests']
    require(all(row['tls'] and row['run'] == report['run'] for row in rows), 'non-TLS or foreign run row')
    allowed = {None, EXPECTED_AUTHORIZATION} | {case['presetAuthorization'] for case in CASES if case.get('presetAuthorization')}
    require(all(row['authorizationValue'] in allowed for row in rows), 'a value other than the public fixture credential was sent')
    observations = {item['case']: item for item in report['observations']}
    require([item['case'] for item in report['observations']] == [case['id'] for case in CASES], 'missing/extra cases')

    def selected(name):
        return [row for row in rows if row['case'] == name]

    for case in CASES:
        name, item = request_name(case), observations[case['id']]
        if case.get('expectNoReceipt'):
            # Without this, a pass elsewhere could come from validation being off.
            require(item['status'] is None and item['error'], case['id'] + ': TLS negative was not refused')
            require(selected(name) == [], case['id'] + ': TLS negative reached the server')
            continue
        require(any(row['path'] == case['path'] for row in selected(name)), case['id'] + ': no server receipt')
        require(item['handlerVisible'] is bool(case.get('handler')), case['id'] + ': handler state wrong at send')
        require(item['authenticatorVisible'] is bool(case.get('authenticator')), case['id'] + ': authenticator state wrong at send')
        if case.get('kind', '').startswith('hold'):
            require(any(row['event'] == 'released' for row in selected(name)), case['id'] + ': server never released it')

    # An ignored global means nothing unless the same global reached the other client in this run.
    require(any('host_ambient' in field for row in selected('huc-positive-cookie') for field in row['cookieFields']), 'cookie handler never reached HttpURLConnection')
    require(any(row['authorizationValue'] == EXPECTED_AUTHORIZATION for row in selected('huc-positive-basic')), 'authenticator never reached HttpURLConnection')
    require(observations['huc-positive-basic']['authenticatorEvents'], 'authenticator was not called for HttpURLConnection')
    require(observations['huc-positive-response-cache']['responseCacheEvents'], 'response cache never reached HttpURLConnection')
    require(observations['huc-positive-proxy-selector']['proxySelectorEvents'], 'proxy selector never reached HttpURLConnection')
    require(observations['huc-positive-global-trust']['status'] == 200, 'global trust never let HttpURLConnection reach the foreign host')

    for name in PLAIN_CONTROLS:
        arrived = selected(name)
        require(observations[name]['status'] == 200, name + ': positive control failed')
        require(len(arrived) == 1 and arrived[0]['cookieFields'] == [] and arrived[0]['authorizationValue'] is None, name + ': ambient state reached a clean request')
    for name in CHALLENGE_CONTROLS:
        arrived = selected(name)
        require(observations[name]['status'] == 401, name + ': challenge not returned')
        require(len(arrived) == 1 and arrived[0]['authorizationValue'] is None, name + ': clean challenge was retried or answered')
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
