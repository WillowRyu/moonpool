"""A finding never fails verification. Missing controls do, because then nothing can be claimed."""
import copy
import unittest
from fixture import EXPECTED_AUTHORIZATION
from verify_results import CASES, classify, verify

SENTINEL = 'host_ambient=sentinel'


def observation(case):
    cleared = case.get('install') == 'cleared-after-open'
    return {'case': case['id'], 'status': 200, 'error': None, 'location': None, 'bodyText': None, 'setCookieFields': None,
            'handlerEvents': [], 'authenticatorEvents': [], 'perConnectionEvents': [], 'storeAfter': [],
            'handlerVisible': bool(case.get('handler')) and not cleared, 'authenticatorVisible': bool(case.get('authenticator')) and not cleared,
            'perConnectionResult': None}


def row(case, cookies=(), authorization=None, path=None, body=0):
    return {'run': 'android-test', 'case': case, 'path': path or next(c for c in CASES if c['id'] == case)['path'], 'event': 'arrived',
            'method': 'GET', 'tls': True, 'bodyLength': body, 'cookieFields': list(cookies), 'authorizationValue': authorization}


def report():
    """Every global is ignored: the clean outcome a broker would want, used as the base for mutations."""
    observations = [observation(case) for case in CASES]
    for item in observations:
        if item['case'] == 'tls-negative':
            item.update(status=None, error='SSLHandshakeException')
        if item['case'] == 'detect-authenticator-probe':
            item.update(status=None, probeAnswered=True, probeAnsweredAfterClear=False, authenticatorEvents=[{'host': 'probe.invalid'}])
        case = next(c for c in CASES if c['id'] == item['case'])
        if case.get('status') == 401:
            item['status'] = 401
    return {'platform': 'android', 'run': 'android-test', 'complete': True, 'errors': [], 'observations': observations,
            'api': {'setAuthenticator': True, 'authenticatorGetDefault': True}, 'globalsAtStart': {'cookieHandlerNull': True, 'authenticatorNull': True},
            'requests': [row(case['id']) for case in CASES if not case.get('kind')]}


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

    def test_incomplete_collection_is_rejected(self):
        self.rejects(lambda data: data.update(complete=False))

    def test_native_errors_are_rejected(self):
        self.rejects(lambda data: data['errors'].append({'error': 'boom'}))

    def test_missing_case_is_rejected(self):
        self.rejects(lambda data: data['observations'].pop())

    def test_missing_receipt_is_rejected(self):
        self.rejects(lambda data: data['requests'].remove(receipts(data, 'handler-get')[0]))

    def test_foreign_run_receipt_is_rejected(self):
        self.rejects(lambda data: receipts(data, 'handler-get')[0].update(run='android-other'))

    def test_non_tls_receipt_is_rejected(self):
        self.rejects(lambda data: receipts(data, 'handler-get')[0].update(tls=False))

    def test_globals_already_set_at_start_are_rejected(self):
        self.rejects(lambda data: data['globalsAtStart'].update(cookieHandlerNull=False))

    def test_tls_negative_must_be_refused(self):
        self.rejects(lambda data: observed(data, 'tls-negative').update(status=200, error=None))

    def test_tls_negative_must_not_reach_the_server(self):
        self.rejects(lambda data: data['requests'].append(row('tls-negative')))

    def test_clean_plain_control_must_send_no_cookie(self):
        self.rejects(lambda data: receipts(data, 'control-plain')[0].update(cookieFields=[SENTINEL]))

    def test_clean_challenge_control_must_send_once_without_credentials(self):
        self.rejects(lambda data: data['requests'].append(row('control-basic-401')))
        self.rejects(lambda data: receipts(data, 'control-basic-401')[0].update(authorizationValue=EXPECTED_AUTHORIZATION))

    def test_controls_after_every_case_prove_the_globals_were_cleared(self):
        self.rejects(lambda data: receipts(data, 'control-after-plain')[0].update(cookieFields=[SENTINEL]))
        self.rejects(lambda data: receipts(data, 'control-after-basic-401')[0].update(authorizationValue=EXPECTED_AUTHORIZATION))
        self.rejects(lambda data: observed(data, 'control-after-basic-401')['authenticatorEvents'].append({'scheme': 'Basic'}))

    def test_an_uninstalled_global_cannot_count_as_ignored(self):
        self.rejects(lambda data: observed(data, 'handler-get').update(handlerVisible=False))
        self.rejects(lambda data: observed(data, 'auth-basic-get').update(authenticatorVisible=False))

    def test_a_timing_case_must_show_the_state_it_claims_at_send_time(self):
        self.rejects(lambda data: observed(data, 'handler-cleared-after-open').update(handlerVisible=True))
        self.rejects(lambda data: observed(data, 'auth-cleared-after-open').update(authenticatorVisible=True))

    def test_a_credential_other_than_the_fixture_value_is_rejected(self):
        self.rejects(lambda data: receipts(data, 'auth-basic-get')[0].update(authorizationValue='Basic something-real'))

    def test_the_authenticator_probe_must_tell_installed_from_cleared(self):
        self.rejects(lambda data: observed(data, 'detect-authenticator-probe').update(probeAnswered=False))
        self.rejects(lambda data: observed(data, 'detect-authenticator-probe').update(probeAnsweredAfterClear=True))

    def test_the_authenticator_probe_must_send_nothing(self):
        self.rejects(lambda data: data['requests'].append(row('detect-authenticator-probe')))


class FindingTests(unittest.TestCase):
    def test_ignored_globals_are_reported_as_not_applied(self):
        findings = classify(report())
        self.assertFalse(findings['cookieHandler']['ambientSentOnGet'])
        self.assertFalse(findings['cookieManager']['seededHostCookieSent'])
        self.assertEqual(findings['authenticator']['auth-basic-get']['credentialAttempts'], 0)

    def test_applied_handler_is_a_finding_not_a_failure(self):
        data = report()
        receipts(data, 'handler-get')[0]['cookieFields'] = [SENTINEL]
        self.assertGreater(verify(data), 0)
        self.assertTrue(classify(data)['cookieHandler']['ambientSentOnGet'])

    def test_exact_fields_are_reported_when_a_handler_meets_an_attached_cookie(self):
        data = report()
        receipts(data, 'handler-attached')[0]['cookieFields'] = ['broker_selected=one', SENTINEL]
        self.assertEqual(classify(data)['cookieHandler']['attachedFields'], ['broker_selected=one', SENTINEL])

    def test_set_cookie_reaching_the_host_handler_is_reported_with_http_only(self):
        data = report()
        observed(data, 'handler-set-cookie')['handlerEvents'] = [{'op': 'put', 'setCookie': ['t28g_protected=two; Path=/; HttpOnly; Secure']}]
        found = classify(data)['cookieHandler']
        self.assertTrue(found['setCookieDelivered'])
        self.assertTrue(found['httpOnlyDelivered'])

    def test_captured_cookie_resent_later_is_reported(self):
        data = report()
        observed(data, 'manager-capture')['storeAfter'] = [{'name': 't28g_captured_protected', 'httpOnly': True}]
        receipts(data, 'manager-capture-followup')[0]['cookieFields'] = ['t28g_captured=four; t28g_captured_protected=five']
        found = classify(data)['cookieManager']
        self.assertTrue(found['httpOnlyStored'])
        self.assertTrue(found['capturedSentOnFollowup'])

    def test_credentials_sent_are_counted_from_receipts_not_from_the_client(self):
        data = report()
        data['requests'].append(row('auth-basic-get', authorization=EXPECTED_AUTHORIZATION))
        observed(data, 'auth-basic-get')['status'] = 200
        found = classify(data)['authenticator']['auth-basic-get']
        self.assertEqual((found['attempts'], found['credentialAttempts'], found['status']), (2, 1, 200))

    def test_detection_reports_that_the_probe_calls_host_code(self):
        found = classify(report())['detection']
        self.assertTrue(found['probeTellsInstalledFromCleared'])
        self.assertEqual(found['probeHostCallbacks'], 1)

    def test_per_connection_authenticator_outcome_is_reported(self):
        data = report()
        observed(data, 'opt-out-noop-authenticator').update(perConnectionResult='UnsupportedOperationException')
        self.assertEqual(classify(data)['perConnection']['result'], 'UnsupportedOperationException')

    def test_timing_cases_compare_install_moment_with_receipts(self):
        data = report()
        receipts(data, 'handler-cleared-after-open')[0]['cookieFields'] = [SENTINEL]
        found = classify(data)['timing']
        self.assertTrue(found['handlerClearedAfterOpenStillApplied'])
        self.assertFalse(found['handlerInstalledAfterOpenApplied'])


if __name__ == '__main__':
    unittest.main()
