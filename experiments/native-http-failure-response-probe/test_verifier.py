"""A verifier that cannot reject bad evidence proves nothing, so these feed it altered reports."""
import unittest
from verify_results import CASES, classify_case, compare, finding, folded, verify

RUN = 'ios-test'


def ideal_report(carries=True):
    """A report where the resend happens as the transport evidence measured. Only useful for testing the verifier."""
    observations, requests = [], []
    for case in CASES:
        attempts = case['setCookieByAttempt']
        basic = case.get('challenge') == 'Basic'
        arrivals = 2 if basic else 1
        for arrival in range(1, arrivals + 1):
            requests.append({'run': RUN, 'case': case['id'], 'arrival': arrival, 'tls': True, 'method': case.get('method', 'GET'),
                             'bodyLength': len(case.get('body', '')), 'authorization': case.get('headers', {}).get('Authorization'),
                             'cookieFields': [], 'served': attempts[min(arrival, len(attempts)) - 1]})
        challenges = []
        if basic:
            first = folded(attempts[0]) if carries else None
            challenges.append({'method': 'NSURLAuthenticationMethodHTTPBasic', 'previousFailureCount': 0, 'hasFailureResponse': carries,
                               'status': 401 if carries else None, 'setCookie': first})
        final = attempts[min(arrivals, len(attempts)) - 1]
        observations.append({'case': case['id'], 'challenges': challenges, 'responses': [{'status': case['status'], 'setCookie': folded(final)}],
                             'status': case['status'], 'error': None, 'bodyText': '{}'})
    return {'platform': 'ios', 'run': RUN, 'release': '26.4.1', 'complete': True, 'errors': [], 'observations': observations, 'requests': requests}


def item(report, case):
    return next(found for found in report['observations'] if found['case'] == case)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.report = ideal_report()

    def test_ideal_report_passes(self):
        self.assertGreater(verify(self.report), 30)

    def test_incomplete_collection_is_rejected(self):
        self.report['complete'] = False
        with self.assertRaisesRegex(AssertionError, 'incomplete'):
            verify(self.report)

    def test_native_errors_are_rejected(self):
        self.report['errors'] = [{'error': 'x'}]
        with self.assertRaisesRegex(AssertionError, 'native errors'):
            verify(self.report)

    def test_missing_case_is_rejected(self):
        self.report['observations'].pop()
        with self.assertRaisesRegex(AssertionError, 'missing/extra'):
            verify(self.report)

    def test_non_tls_or_foreign_receipt_is_rejected(self):
        self.report['requests'][0]['tls'] = False
        with self.assertRaisesRegex(AssertionError, 'non-TLS'):
            verify(self.report)

    def test_a_control_with_a_challenge_is_rejected(self):
        item(self.report, 'control-bearer')['challenges'] = [{'setCookie': None}]
        with self.assertRaisesRegex(AssertionError, 'control-bearer'):
            verify(self.report)

    def test_a_control_with_the_wrong_cookie_is_rejected(self):
        item(self.report, 'control-plain')['responses'][0]['setCookie'] = 'other=1'
        with self.assertRaisesRegex(AssertionError, 'control-plain'):
            verify(self.report)

    def test_a_basic_case_without_its_401_is_rejected(self):
        item(self.report, 'basic-post')['status'] = None
        with self.assertRaisesRegex(AssertionError, 'basic-post'):
            verify(self.report)

    def test_a_case_that_never_reached_the_server_is_rejected(self):
        self.report['requests'] = [row for row in self.report['requests'] if row['case'] != 'basic-post']
        with self.assertRaisesRegex(AssertionError, 'basic-post'):
            verify(self.report)

    def test_a_missing_failure_response_is_a_finding_not_a_rejection(self):
        report = ideal_report(carries=False)
        self.assertGreater(verify(report), 30)
        self.assertFalse(finding([report])['usable'])

    def test_all_cases_carrying_the_first_cookie_make_it_usable(self):
        self.assertTrue(finding([self.report])['usable'])

    def test_one_case_with_another_attempts_cookie_is_not_usable(self):
        item(self.report, 'basic-cookie-per-attempt')['challenges'][0]['setCookie'] = 'attempt=2; Path=/; Secure'
        result = finding([self.report])
        self.assertFalse(result['usable'])
        self.assertIn('basic-cookie-per-attempt', result['notCarried'])

    def test_a_case_with_no_challenge_callback_is_not_usable(self):
        item(self.report, 'basic-post')['challenges'] = []
        self.assertIn('basic-post', finding([self.report])['notCarried'])

    def test_a_case_with_no_first_cookie_must_report_none(self):
        item(self.report, 'basic-no-cookie')['challenges'][0]['setCookie'] = 'invented=1'
        self.assertIn('basic-no-cookie', finding([self.report])['notCarried'])

    def test_a_case_without_a_resend_is_reported_with_its_arrivals(self):
        self.report['requests'] = [row for row in self.report['requests'] if not (row['case'] == 'basic-post' and row['arrival'] == 2)]
        self.assertEqual(classify_case(self.report, next(c for c in CASES if c['id'] == 'basic-post'))['arrivals'], 1)

    def test_runs_with_the_same_measurements_compare_equal(self):
        self.assertEqual(compare(self.report, ideal_report()), [])

    def test_runs_that_differ_are_reported(self):
        other = ideal_report()
        item(other, 'basic-post')['challenges'][0]['setCookie'] = None
        self.assertEqual(compare(self.report, other), ['basic-post'])


if __name__ == '__main__':
    unittest.main()
