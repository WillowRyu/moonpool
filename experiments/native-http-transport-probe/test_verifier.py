"""Transport observations become findings; missing controls or witnesses reject the report."""
import copy
import json
from pathlib import Path
import unittest
from verify_results import canonical_cookie_lines, canonical_differences, classify, compare, split_folded, verify

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())
RUN = 'android-test'


def observation(case, folded=False):
    expected = case.get('setCookie')
    item = {'case': case['id'], 'status': case.get('status', 200), 'error': None, 'location': None,
            'bodyText': case['id'], 'setCookieFields': None, 'setCookieFolded': None}
    if expected:
        if folded:
            item['setCookieFolded'] = ', '.join(expected)
        else:
            item['setCookieFields'] = list(expected)
    if case.get('redirect'):
        item['location'] = '/target?run=x&case=' + case['id']
    if case.get('kind') == 'hold-headers':
        item['respondedBeforeRelease'] = False
    if case.get('kind') == 'hold-body':
        item['headersBeforeRelease'] = True
        item['bodyBeforeRelease'] = False
    if case.get('kind') == 'tls-negative':
        item.update(status=None, error='untrusted', bodyText=None)
    return item


def row(case_id, path='/echo', event='arrived', cookies=None):
    return {'run': RUN, 'case': case_id, 'path': path, 'event': event, 'method': 'GET', 'tls': True,
            'cookieFields': cookies or [], 'authorization': False, 'bodyLength': 0}


def report(folded=False):
    rows = []
    for case in CASES:
        if case.get('kind') == 'tls-negative':
            continue
        request_case = case.get('requestCase', case['id'])
        cookies = [case['attachCookie']] if case.get('attachCookie') else []
        rows.append(row(request_case, case['path'], 'arrived', cookies))
        if case.get('kind', '').startswith('hold'):
            rows.append(row(request_case, case['path'], 'released'))
    return {'platform': 'ios' if folded else 'android', 'run': RUN, 'complete': True, 'errors': [],
            'observations': [observation(case, folded) for case in CASES], 'requests': rows}


def obs(r, case_id):
    return next(item for item in r['observations'] if item['case'] == case_id)


class SplitTests(unittest.TestCase):
    def test_comma_inside_expires_does_not_split(self):
        value = 'a=1; Expires=Wed, 21 Oct 2037 07:28:00 GMT, b=2; Path=/'
        self.assertEqual(split_folded(value), ['a=1; Expires=Wed, 21 Oct 2037 07:28:00 GMT', 'b=2; Path=/'])

    def test_a_comma_in_a_value_that_looks_like_a_cookie_is_split_wrongly(self):
        self.assertEqual(len(split_folded('t28h_comma=a, t28h_fake=b; Path=/, t28h_real=c; Path=/')), 3)


class ClassifyTests(unittest.TestCase):
    def test_separate_fields_in_order(self):
        self.assertEqual(classify(report())['setCookie']['multi']['shape'], 'separate-ordered')

    def test_reordered_fields_are_reported(self):
        r = report()
        obs(r, 'multi')['setCookieFields'].reverse()
        self.assertEqual(classify(r)['setCookie']['multi']['shape'], 'separate-reordered')

    def test_folded_value_is_reported_with_whether_splitting_recovers_it(self):
        result = classify(report(folded=True))['setCookie']
        self.assertEqual(result['multi']['shape'], 'folded')
        self.assertTrue(result['multi']['splitRecovers'])
        self.assertFalse(result['tricky']['splitRecovers'])

    def test_missing_or_altered_values_are_reported(self):
        r = report()
        obs(r, 'multi')['setCookieFields'] = None
        obs(r, 'tricky')['setCookieFields'] = ['other=1']
        result = classify(r)['setCookie']
        self.assertEqual(result['multi']['shape'], 'missing')
        self.assertEqual(result['tricky']['shape'], 'altered')

    def test_an_ambient_cookie_is_seen_by_the_server(self):
        r = report()
        next(x for x in r['requests'] if x['case'] == 'after-multi-echo')['cookieFields'] = ['t28h_plain=one']
        self.assertTrue(classify(r)['ambientCookieSent'])

    def test_attached_cookie_must_arrive_exactly_once_and_unchanged(self):
        self.assertTrue(classify(report())['attachedCookieExact'])
        r = report()
        next(x for x in r['requests'] if x['case'] == 'attach-cookie')['cookieFields'] = ['t28h_b=2; t28h_a=1']
        self.assertFalse(classify(r)['attachedCookieExact'])

    def test_followed_redirect_is_counted_from_server_receipts(self):
        r = report()
        r['requests'].append(row('redirect-307', '/target'))
        result = classify(r)['redirects']
        self.assertEqual(result['redirect-307']['targetHits'], 1)
        self.assertEqual(result['redirect-301']['targetHits'], 0)

    def test_redirect_reports_status_location_and_cookie_visibility(self):
        result = classify(report())['redirects']['redirect-302']
        self.assertEqual(result['status'], 302)
        self.assertTrue(result['locationVisible'])
        self.assertTrue(result['cookieVisible'])

    def test_error_statuses_report_body_and_cookie_visibility(self):
        result = classify(report())['errorStatuses']['status-500']
        self.assertEqual(result, {'status': 500, 'bodyVisible': True, 'cookieVisible': True})

    def test_challenge_reports_attempts_and_authorization(self):
        self.assertEqual(classify(report())['challenges']['challenge-401'],
                         {'status': 401, 'attempts': 1, 'authorizationSent': False, 'error': None})

    def test_a_replayed_request_after_a_challenge_is_counted_from_receipts(self):
        r = report()
        r['requests'].append(row('challenge-post-reject', '/serve'))
        self.assertEqual(classify(r)['challenges']['challenge-post-reject']['attempts'], 2)

    def test_a_cancelled_challenge_reports_its_error_and_no_status(self):
        r = report()
        obs(r, 'challenge-cancel').update(status=None, error='NSURLErrorDomain:-999')
        self.assertEqual(classify(r)['challenges']['challenge-cancel']['error'], 'NSURLErrorDomain:-999')

    def test_each_hold_body_variant_reports_header_visibility(self):
        r = report()
        obs(r, 'hold-body-first-byte')['headersBeforeRelease'] = False
        variants = classify(r)['holdBodyVariants']
        self.assertFalse(variants['hold-body-first-byte'])
        self.assertTrue(variants['hold-body-first-kilobyte'])

    def test_second_cache_request_reaching_the_server_means_no_shared_cache(self):
        self.assertEqual(classify(report())['cacheServerHits'], 2)
        r = report()
        pair = [x for x in r['requests'] if x['case'] == 'cache-pair']
        r['requests'].remove(pair[1])
        self.assertEqual(classify(r)['cacheServerHits'], 1)

    def test_hold_results_are_reported(self):
        result = classify(report())['holds']
        self.assertFalse(result['respondedBeforeHeaderRelease'])
        self.assertTrue(result['headersBeforeBodyRelease'])
        self.assertFalse(result['bodyBeforeBodyRelease'])


class CanonicalTests(unittest.TestCase):
    def test_separate_fields_and_folded_value_reach_the_same_lines(self):
        case = next(c for c in CASES if c['id'] == 'multi')
        separate = canonical_cookie_lines({'setCookieFields': case['setCookie'], 'setCookieFolded': None})
        folded = canonical_cookie_lines({'setCookieFields': None, 'setCookieFolded': ', '.join(case['setCookie'])})
        self.assertEqual(separate, folded)
        self.assertEqual(separate, case['setCookie'])

    def test_the_same_pipeline_gives_both_platforms_the_same_lines_for_a_comma_value(self):
        self.assertEqual(canonical_differences(report(), report(folded=True)), [])

    def test_a_platform_altering_a_field_is_a_difference(self):
        r = report()
        obs(r, 'multi')['setCookieFields'] = ['other=1']
        self.assertEqual(canonical_differences(r, report(folded=True)), ['multi'])


class CompareTests(unittest.TestCase):
    def test_folding_is_a_platform_difference(self):
        differences = compare(classify(report()), classify(report(folded=True)))
        self.assertIn('setCookie.multi.shape', differences)

    def test_identical_results_have_no_differences(self):
        self.assertEqual(compare(classify(report()), classify(report())), {})


class EvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message):
        r = report()
        mutate(r)
        with self.assertRaises(AssertionError) as caught:
            verify(r)
        self.assertIn(message, str(caught.exception))

    def test_complete_report_is_accepted(self):
        self.assertGreater(verify(report()), 0)

    def test_a_folded_report_is_a_finding_not_a_rejection(self):
        self.assertGreater(verify(report(folded=True)), 0)

    def test_a_followed_redirect_is_a_finding_not_a_rejection(self):
        r = report()
        r['requests'].append(row('redirect-301', '/target'))
        self.assertGreater(verify(r), 0)

    def test_failed_or_partial_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')
        self.rejects(lambda r: r['observations'].pop(), 'cases')

    def test_receipts_must_be_tls_and_from_this_run(self):
        self.rejects(lambda r: r['requests'][0].update(tls=False), 'TLS')
        self.rejects(lambda r: r['requests'][0].update(run='other'), 'TLS')

    def test_every_request_needs_a_server_receipt(self):
        self.rejects(lambda r: r.update(requests=[x for x in r['requests'] if x['case'] != 'multi']), 'receipt')

    def test_positive_controls_must_succeed(self):
        self.rejects(lambda r: obs(r, 'control-echo').update(status=500), 'control')
        self.rejects(lambda r: obs(r, 'target-control').update(status=500), 'control')

    def test_normal_tls_validation_must_be_proven_by_the_negative(self):
        self.rejects(lambda r: obs(r, 'tls-negative').update(status=200, error=None), 'TLS negative')

    def test_the_tls_negative_must_not_reach_the_server(self):
        self.rejects(lambda r: r['requests'].append(row('tls-negative')), 'TLS negative')

    def test_held_requests_must_have_been_released_by_the_server(self):
        self.rejects(lambda r: r.update(requests=[x for x in r['requests'] if x['event'] != 'released']), 'released')

    def test_verification_does_not_mutate_the_report(self):
        r = report()
        before = copy.deepcopy(r)
        verify(r)
        self.assertEqual(r, before)


if __name__ == '__main__':
    unittest.main()
