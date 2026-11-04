"""A verifier that cannot reject bad evidence proves nothing, so these feed it altered reports."""
import copy
import json
from pathlib import Path
import unittest
from verify_results import CASES, classify, compare, measurements, verify

ROOT = Path(__file__).resolve().parent
EVENT_KINDS = {'commit', 'fence'}


def ideal_outcome(expected):
    outcome = {key: value for key, value in expected.items() if key not in {'hasHeaders', 'headerValues', 'bodyContains'}}
    outcome['headers'] = dict(expected.get('headerValues', {}))
    for name in expected.get('hasHeaders', []):
        outcome['headers'].setdefault(name, 'present')
    if 'bodyContains' in expected:
        outcome['bodyText'] = expected['bodyContains']
    return outcome


def ideal_report(platform='android'):
    """Everything the oracle asks for, built from the oracle alone. Only useful for testing the verifier."""
    run = platform + '-test'
    observations, requests = [], []
    for case in CASES:
        expect = case['expect']
        steps, events = [], []
        for step in case['steps']:
            if step['op'] in {'held', 'release', 'await', 'awaitEvent', 'startQueued'}:
                if step['op'] == 'awaitEvent':
                    events.append({'kind': step['kind'], 'label': step['label']})
                continue
            label = step['label']
            outcome = expect.get('outcomes', {}).get(label)
            found = {'label': label, 'op': step['op'], 'outcome': ideal_outcome(outcome) if outcome else {'ok': True, 'status': 200, 'headers': {}}}
            if step['op'] == 'snapshot':
                found['jar'] = expect.get('jar', {}).get(label, [])
            steps.append(found)
            if step['op'] not in {'request', 'hostRequest'}:
                continue
            receipt = expect.get('receipts', {}).get(label, {})
            if receipt.get('count') == 0:
                continue
            cookie = receipt.get('cookie', [])
            if 'cookieContains' in receipt:
                cookie = [receipt['cookieContains']]
            row = {'run': run, 'case': case['id'], 'step': label, 'event': 'arrived', 'tls': True, 'cookieFields': cookie,
                   'authorization': receipt.get('authorization'), 'path': '/s', 'method': receipt.get('method', 'GET'), 'host': 'localhost', 'listener': 'service', 'bodyLength': receipt.get('bodyLength', 0)}
            if receipt.get('authorizationSeen'):
                row['authorization'] = 'Basic bW9vbnBvb2wtZml4dHVyZS11c2VyOm5vdC1hLXNlY3JldA=='
            requests.append(row)
            if step.get('serve', {}).get('hold'):
                requests.append({**row, 'event': 'released'})
        if expect.get('commitOrder'):
            events = [{'kind': 'commit', 'label': label} for label in expect['commitOrder']]
        observations.append({'case': case['id'], 'steps': steps, 'events': events, 'timedOut': []})
    return {'platform': platform, 'run': run, 'complete': True, 'errors': [], 'observations': observations, 'requests': requests}


def find_step(report, case, label):
    item = next(i for i in report['observations'] if i['case'] == case)
    return next(s for s in item['steps'] if s['label'] == label)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.report = ideal_report()

    def states(self, report=None):
        return classify(report or self.report)

    def test_ideal_report_passes(self):
        self.assertGreater(verify(self.report), 100)
        self.assertEqual({name: item['problems'] for name, item in self.states().items() if item['state'] != 'pass'}, {})

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

    def test_missing_step_outcome_is_rejected(self):
        self.report['observations'][0]['steps'] = []
        with self.assertRaisesRegex(AssertionError, 'missing step'):
            verify(self.report)

    def test_barrier_timeout_is_rejected(self):
        self.report['observations'][0]['timedOut'] = ['held:x']
        with self.assertRaisesRegex(AssertionError, 'barrier'):
            verify(self.report)

    def test_failed_positive_control_is_rejected(self):
        find_step(self.report, 'c00-plain', 'plain')['outcome'] = {'ok': False, 'code': -32007}
        with self.assertRaisesRegex(AssertionError, 'control'):
            verify(self.report)

    def test_host_control_that_never_reached_the_server_is_rejected(self):
        self.report['requests'] = [row for row in self.report['requests'] if not (row['case'] == 'c00-host-positive' and row['step'] == 'hostCookie')]
        with self.assertRaisesRegex(AssertionError, 'control'):
            verify(self.report)

    def test_tls_negative_that_reached_the_server_is_rejected(self):
        row = {**self.report['requests'][0], 'case': 'c00-tls-negative', 'step': 'refused'}
        self.report['requests'].append(row)
        with self.assertRaisesRegex(AssertionError, 'control'):
            verify(self.report)

    def test_non_tls_or_foreign_row_is_rejected(self):
        self.report['requests'][0]['tls'] = False
        with self.assertRaisesRegex(AssertionError, 'non-TLS'):
            verify(self.report)

    def test_unreleased_hold_is_rejected(self):
        index = next(i for i, row in enumerate(self.report['requests']) if row['event'] == 'released')
        del self.report['requests'][index]
        with self.assertRaisesRegex(AssertionError, 'released'):
            verify(self.report)

    def test_cross_app_marker_fails_the_case(self):
        next(row for row in self.report['requests'] if row['case'] == 'c01-ownership' and row['step'] == 'meB')['cookieFields'] = ['sid=value-a']
        self.assertEqual(self.states()['c01-ownership']['state'], 'fail')

    def test_redirect_hit_fails_the_case(self):
        moved = next(row for row in self.report['requests'] if row['case'] == 'c06-redirect-302')
        self.report['requests'].append({**moved, 'step': 'target'})
        self.assertEqual(self.states()['c06-redirect-302']['state'], 'fail')

    def test_stale_post_reset_commit_fails_the_case(self):
        find_step(self.report, 'c08-reset-before-headers', 'jar')['jar'] = ['sid=stale']
        self.assertEqual(self.states()['c08-reset-before-headers']['state'], 'fail')

    def test_missing_fence_event_fails_the_case(self):
        item = next(i for i in self.report['observations'] if i['case'] == 'c08-reset-before-headers')
        item['events'] = []
        self.assertEqual(self.states()['c08-reset-before-headers']['state'], 'fail')

    def test_commit_order_fails_the_case(self):
        item = next(i for i in self.report['observations'] if i['case'] == 'c07-header-order')
        item['events'].reverse()
        self.assertEqual(self.states()['c07-header-order']['state'], 'fail')

    def test_protected_value_in_guest_outcome_fails_the_case(self):
        find_step(self.report, 'c03-httponly', 'read')['outcome']['cookies'] = [{'name': 'prot', 'path': '/', 'value': 'protected-marker'}]
        problems = self.states()['c03-httponly']['problems']
        self.assertTrue(any('protected-marker' in problem for problem in problems))

    def test_protected_value_in_error_text_fails_the_case(self):
        find_step(self.report, 'c03-httponly', 'overwrite')['outcome']['message'] = 'bad protected-marker'
        self.assertEqual(self.states()['c03-httponly']['state'], 'fail')

    def test_set_cookie_in_guest_headers_fails_the_case(self):
        find_step(self.report, 'c02-login-default-include', 'login')['outcome']['headers']['set-cookie'] = 'x'
        self.assertEqual(self.states()['c02-login-default-include']['state'], 'fail')

    def test_host_cookie_at_a_broker_step_fails_the_case(self):
        next(row for row in self.report['requests'] if row['case'] == 'c00-host-positive' and row['step'] == 'broker')['cookieFields'] = ['host_ambient=sentinel']
        self.assertEqual(self.states()['c00-host-positive']['state'], 'fail')

    def test_host_credential_at_a_broker_step_fails_the_case(self):
        next(row for row in self.report['requests'] if row['case'] == 'c00-host-positive' and row['step'] == 'brokerAuth')['authorization'] = 'Basic x'
        self.assertEqual(self.states()['c00-host-positive']['state'], 'fail')

    def test_rejected_request_that_reached_the_server_fails_the_case(self):
        row = {**self.report['requests'][0], 'case': 'c02-forbidden-headers', 'step': 'h0'}
        self.report['requests'].append(row)
        self.assertEqual(self.states()['c02-forbidden-headers']['state'], 'fail')

    def test_a_failed_case_does_not_fail_verification(self):
        find_step(self.report, 'c08-reset-before-headers', 'jar')['jar'] = ['sid=stale']
        self.assertGreater(verify(self.report), 100)

    def test_comparison_reports_a_platform_difference(self):
        other = ideal_report('ios')
        self.assertEqual(compare(self.report, other), [])
        find_step(other, 'c02-omit-outgoing', 'jar')['jar'] = ['other=1']
        self.assertEqual([item['case'] for item in compare(self.report, other)], ['c02-omit-outgoing'])

    def test_comparison_ignores_declared_measurements(self):
        other = ideal_report('ios')
        find_step(other, 'c03-comma-value-attribute-loss', 'jar')['jar'] = ['other=1']
        self.assertEqual(compare(self.report, other), [])

    def test_the_second_attempts_cookie_fails_a_basic_case(self):
        find_step(self.report, 'c06-basic-401-cookies', 'jar')['jar'] = ['attempt=2']
        self.assertEqual(self.states()['c06-basic-401-cookies']['state'], 'fail')

    def test_committing_twice_fails_a_basic_case(self):
        item = next(i for i in self.report['observations'] if i['case'] == 'c06-basic-401-cookies')
        item['events'] = [{'kind': 'commit', 'label': 'challenged'}, {'kind': 'commit', 'label': 'challenged'}]
        self.assertEqual(self.states()['c06-basic-401-cookies']['state'], 'fail')

    def test_a_jar_difference_after_a_basic_resend_is_now_reported(self):
        other = ideal_report('ios')
        find_step(other, 'c06-basic-401-cookies', 'jar')['jar'] = ['attempt=2']
        self.assertEqual([item['case'] for item in compare(self.report, other)], ['c06-basic-401-cookies'])

    def test_comparison_reports_a_guest_visible_header_difference(self):
        other = ideal_report('ios')
        find_step(other, 'c06-retry-after-zero', 'busy')['outcome']['headers']['retry-after'] = '5'
        self.assertEqual([item['case'] for item in compare(self.report, other)], ['c06-retry-after-zero'])

    def test_comparison_ignores_the_date_and_the_run_and_port_in_a_location(self):
        other = ideal_report('ios')
        find_step(self.report, 'c00-plain', 'plain')['outcome']['headers']['date'] = 'Wed'
        find_step(other, 'c00-plain', 'plain')['outcome']['headers']['date'] = 'Thu'
        find_step(self.report, 'c06-redirect-302', 'moved')['outcome']['headers']['location'] = 'https://localhost:1/s?run=android-a&case=c&step=target'
        find_step(other, 'c06-redirect-302', 'moved')['outcome']['headers']['location'] = 'https://localhost:2/s?run=ios-b&case=c&step=target'
        self.assertEqual(compare(self.report, other), [])

    def test_comparison_still_reports_a_location_on_another_host(self):
        other = ideal_report('ios')
        find_step(self.report, 'c06-redirect-302', 'moved')['outcome']['headers']['location'] = 'https://localhost:1/s?run=android-a'
        find_step(other, 'c06-redirect-302', 'moved')['outcome']['headers']['location'] = 'https://127.0.0.1:1/s?run=ios-b'
        self.assertEqual([item['case'] for item in compare(self.report, other)], ['c06-redirect-302'])

    def test_wrong_method_at_the_server_fails_the_case(self):
        next(row for row in self.report['requests'] if row['case'] == 'c06-methods' and row['step'] == 'mPOST')['method'] = 'GET'
        self.assertEqual(self.states()['c06-methods']['state'], 'fail')

    def test_wrong_body_length_at_the_server_fails_the_case(self):
        next(row for row in self.report['requests'] if row['case'] == 'c06-methods' and row['step'] == 'putBody')['bodyLength'] = 0
        self.assertEqual(self.states()['c06-methods']['state'], 'fail')

    def test_hold_timeout_does_not_count_as_a_release(self):
        row = next(row for row in self.report['requests'] if row['event'] == 'released')
        row['event'] = 'holdTimedOut'
        with self.assertRaisesRegex(AssertionError, 'released'):
            verify(self.report)

    def test_measurements_record_what_a_guest_could_read(self):
        find_step(self.report, 'c03-comma-value-attribute-loss', 'read')['outcome']['cookies'] = [{'name': 'sid', 'path': '/', 'value': 'abc'}]
        found = measurements(self.report)['c03-comma-value-attribute-loss/read']
        self.assertEqual(found['cookies'], [{'name': 'sid', 'path': '/', 'value': 'abc'}])

    def test_cases_cover_the_declared_contract_groups(self):
        self.assertEqual({case['contract'] for case in CASES}, {'control', 'C01', 'C02', 'C03', 'C05', 'C06', 'C07', 'C08'})
        self.assertEqual(json.loads((ROOT / 'cases.json').read_text()), copy.deepcopy(CASES))


if __name__ == '__main__':
    unittest.main()
