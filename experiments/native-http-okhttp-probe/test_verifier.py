"""A finding never fails verification. Missing controls do, because then nothing can be claimed."""
import copy
import unittest
from fixture import EXPECTED_AUTHORIZATION
from verify_results import CASES, classify, verify

SENTINEL = 'host_ambient=sentinel'


def request_name(case):
    return case.get('requestCase', case['id'])


def observation(case):
    late = case.get('install') == 'after-call'
    return {'case': case['id'], 'status': case.get('status', 200), 'error': None, 'location': None, 'bodyText': None, 'setCookieFields': case.get('setCookie'),
            'handlerEvents': [], 'authenticatorEvents': [], 'responseCacheEvents': [], 'proxySelectorEvents': [],
            'handlerVisible': bool(case.get('handler')), 'authenticatorVisible': bool(case.get('authenticator')), 'late': late,
            'headersBeforeRelease': False, 'bodyBeforeRelease': False, 'respondedBeforeRelease': False}


def row(name, path='/echo', cookies=(), authorization=None, event='arrived', body=0):
    return {'run': 'android-test', 'case': name, 'path': path, 'event': event, 'method': 'GET', 'tls': True,
            'bodyLength': body, 'cookieFields': list(cookies), 'authorizationValue': authorization}


def report():
    """OkHttp ignores every global while the HttpURLConnection controls show the globals were live."""
    observations = [observation(case) for case in CASES]
    rows = []
    for case in CASES:
        if not case.get('expectNoReceipt'):
            rows.append(row(request_name(case), case['path']))
        if case.get('kind', '').startswith('hold'):
            rows.append(row(request_name(case), case['path'], event='released'))
        if case.get('closeWithoutResponse'):
            observed_item = next(item for item in observations if item['case'] == case['id'])
            observed_item.update(status=None, error='IOException')
        if case.get('expectNoReceipt'):
            observed_item = next(item for item in observations if item['case'] == case['id'])
            observed_item.update(status=None, error='SSLPeerUnverifiedException')
    data = {'platform': 'android', 'run': 'android-test', 'complete': True, 'errors': [], 'observations': observations, 'requests': rows,
            'globalsAtStart': {'cookieHandlerNull': True, 'authenticatorNull': True, 'responseCacheNull': True}}
    receipts(data, 'huc-positive-cookie')[0]['cookieFields'] = [SENTINEL]
    data['requests'].append(row('huc-positive-basic', '/serve', authorization=EXPECTED_AUTHORIZATION))
    observed(data, 'huc-positive-basic').update(status=200, authenticatorEvents=[{'scheme': 'Basic'}])
    observed(data, 'huc-positive-cookie')['handlerEvents'] = [{'op': 'get'}]
    observed(data, 'huc-positive-response-cache')['responseCacheEvents'] = [{'op': 'get'}]
    observed(data, 'huc-positive-proxy-selector')['proxySelectorEvents'] = [{'uri': 'https://localhost/'}]
    return data


def observed(data, case):
    return next(item for item in data['observations'] if item['case'] == case)


def receipts(data, case):
    return [item for item in data['requests'] if item['case'] == case]


class ControlTests(unittest.TestCase):
    def rejects(self, mutate):
        data = copy.deepcopy(report())
        mutate(data)
        with self.assertRaises(AssertionError):
            verify(data)

    def test_the_clean_report_passes(self):
        self.assertGreater(verify(report()), 0)

    def test_incomplete_collection_or_native_errors_are_rejected(self):
        self.rejects(lambda data: data.update(complete=False))
        self.rejects(lambda data: data['errors'].append({'error': 'boom'}))

    def test_missing_case_or_receipt_is_rejected(self):
        self.rejects(lambda data: data['observations'].pop())
        self.rejects(lambda data: data['requests'].remove(receipts(data, 'handler-get')[0]))

    def test_foreign_run_or_non_tls_receipt_is_rejected(self):
        self.rejects(lambda data: receipts(data, 'handler-get')[0].update(run='android-other'))
        self.rejects(lambda data: receipts(data, 'handler-get')[0].update(tls=False))

    def test_globals_set_before_the_first_case_are_rejected(self):
        self.rejects(lambda data: data['globalsAtStart'].update(cookieHandlerNull=False))
        self.rejects(lambda data: data['globalsAtStart'].update(responseCacheNull=False))

    def test_ignored_handlers_mean_nothing_unless_they_reached_http_url_connection(self):
        self.rejects(lambda data: receipts(data, 'huc-positive-cookie')[0].update(cookieFields=[]))
        self.rejects(lambda data: data['requests'].remove(receipts(data, 'huc-positive-basic')[-1]))
        self.rejects(lambda data: observed(data, 'huc-positive-response-cache').update(responseCacheEvents=[]))
        self.rejects(lambda data: observed(data, 'huc-positive-proxy-selector').update(proxySelectorEvents=[]))

    def test_a_refused_foreign_host_means_nothing_unless_global_trust_let_the_control_through(self):
        self.rejects(lambda data: data['requests'].remove(receipts(data, 'huc-positive-global-trust')[0]))

    def test_tls_negatives_must_be_refused_without_a_receipt(self):
        for name in ['tls-negative', 'tls-negative-global-trust']:
            self.rejects(lambda data, n=name: observed(data, n).update(status=200, error=None))
            self.rejects(lambda data, n=name: data['requests'].append(row(n)))

    def test_clean_controls_must_stay_clean_before_and_after_every_case(self):
        for name in ['control-plain', 'control-after-plain']:
            self.rejects(lambda data, n=name: receipts(data, n)[0].update(cookieFields=[SENTINEL]))
            self.rejects(lambda data, n=name: observed(data, n).update(status=500))
        for name in ['control-basic-401', 'control-after-basic-401']:
            self.rejects(lambda data, n=name: data['requests'].append(row(n, '/serve')))
            self.rejects(lambda data, n=name: receipts(data, n)[0].update(authorizationValue=EXPECTED_AUTHORIZATION))

    def test_an_uninstalled_global_cannot_count_as_ignored(self):
        self.rejects(lambda data: observed(data, 'handler-get').update(handlerVisible=False))
        self.rejects(lambda data: observed(data, 'auth-basic-get').update(authenticatorVisible=False))

    def test_hold_cases_must_be_released(self):
        self.rejects(lambda data: data['requests'].remove(next(r for r in receipts(data, 'hold-body') if r['event'] == 'released')))

    def test_a_credential_other_than_the_fixture_value_is_rejected(self):
        self.rejects(lambda data: receipts(data, 'auth-basic-get')[0].update(authorizationValue='Basic something-real'))


class FindingTests(unittest.TestCase):
    def test_ignored_globals_are_reported_as_clean(self):
        found = classify(report())['isolation']
        self.assertEqual(found['hostCookiesAtServer'], [])
        self.assertEqual(found['hostCredentialAttempts'], [])
        self.assertEqual(found['handlerCalled'], [])
        self.assertEqual(found['authenticatorCalled'], [])

    def test_a_leak_is_a_finding_not_a_failure(self):
        data = report()
        receipts(data, 'handler-get')[0]['cookieFields'] = [SENTINEL]
        data['requests'].append(row('auth-basic-get', '/serve', authorization=EXPECTED_AUTHORIZATION))
        observed(data, 'manager-capture')['handlerEvents'] = [{'op': 'put', 'setCookie': ['x=1']}]
        self.assertGreater(verify(data), 0)
        found = classify(data)['isolation']
        self.assertEqual(found['hostCookiesAtServer'], ['handler-get'])
        self.assertEqual(found['hostCredentialAttempts'], ['auth-basic-get'])
        self.assertEqual(found['handlerCalled'], ['manager-capture'])

    def test_http_url_connection_controls_are_not_counted_as_okhttp_leaks(self):
        found = classify(report())['isolation']
        self.assertNotIn('huc-positive-cookie', found['hostCookiesAtServer'])
        self.assertNotIn('huc-positive-basic', found['hostCredentialAttempts'])

    def test_resends_are_counted_from_receipts(self):
        data = report()
        data['requests'].append(row('resend-503-zero-get', '/serve'))
        found = classify(data)['resends']
        self.assertEqual(found['resend-503-zero-get']['attempts'], 2)
        self.assertEqual(found['resend-408']['attempts'], 1)

    def test_redirects_report_target_hits_and_visibility(self):
        found = classify(report())['transport']['redirects']['redirect-307']
        self.assertEqual((found['status'], found['targetHits'], found['cookieVisible']), (307, 0, True))

    def test_set_cookie_shape_is_reported(self):
        found = classify(report())['transport']['setCookie']
        self.assertEqual(found['multi'], 'separate-ordered')
        data = report()
        observed(data, 'multi')['setCookieFields'] = ['t28o_plain=one; Path=/']
        self.assertEqual(classify(data)['transport']['setCookie']['multi'], 'altered')

    def test_attached_cookies_must_match_exactly_to_be_reported_exact(self):
        data = report()
        for name in ['attach-cookie', 'attach-post']:
            case = next(c for c in CASES if c['id'] == name)
            receipts(data, name)[0]['cookieFields'] = [case['attachCookie']]
        self.assertTrue(classify(data)['transport']['attachedCookieExact'])
        receipts(data, 'attach-post')[0]['cookieFields'] = ['other=1']
        self.assertFalse(classify(data)['transport']['attachedCookieExact'])

    def test_other_globals_report_who_called_them(self):
        data = report()
        observed(data, 'other-proxy-selector-default')['proxySelectorEvents'] = [{'uri': 'https://localhost/'}]
        found = classify(data)['otherGlobals']
        self.assertEqual(found['proxySelectorCallsDefault'], 1)
        self.assertEqual(found['proxySelectorCallsNoProxy'], 0)
        self.assertEqual(found['responseCacheCalls'], 0)


if __name__ == '__main__':
    unittest.main()
