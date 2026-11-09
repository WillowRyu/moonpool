"""The comparison is the measurement, so it must catch every kind of difference it claims to report."""
import copy
import json
from pathlib import Path
import unittest
from compare import differences, expand, expiry_matches, http_date, load_vectors, platform_differences, validate

ROOT = Path(__file__).resolve().parent
NOW_MS = 1_800_000_000_000


def ideal(vector):
    """An observation that matches the draft exactly, built from the draft alone."""
    draft = vector['draft']
    if not draft['accept']:
        return {'id': vector['id'], 'accepted': False}
    expiry = draft['expiry']
    if expiry == 'session':
        persistent, expires = False, 253402300799999
    elif expiry == 'expired':
        persistent, expires = True, NOW_MS - 1000
    else:
        seconds = expiry.get('seconds', 0) + expiry.get('days', 0) * 86400
        persistent, expires = True, NOW_MS + seconds * 1000
    cookie = {key: draft[key] for key in ('name', 'value', 'domain', 'path', 'hostOnly', 'httpOnly', 'secure')}
    cookie.update(persistent=persistent, expiresAt=expires)
    if 'sameSite' in draft:
        cookie['sameSite'] = draft['sameSite']
    return {'id': vector['id'], 'accepted': True, 'cookie': cookie, 'sends': list(draft.get('sends', []))}


class VectorFile(unittest.TestCase):
    def test_the_retained_vectors_are_valid(self):
        self.assertEqual(validate(json.loads((ROOT / 'vectors.json').read_text())), [])

    def test_duplicate_ids_and_mismatched_sends_are_caught(self):
        doc = json.loads((ROOT / 'vectors.json').read_text())
        broken = copy.deepcopy(doc)
        broken['vectors'].append(copy.deepcopy(broken['vectors'][0]))
        self.assertTrue(any('duplicate' in problem for problem in validate(broken)))
        broken = copy.deepcopy(doc)
        first = next(v for v in broken['vectors'] if v['checks'])
        first['draft']['sends'] = first['draft']['sends'][:-1]
        self.assertTrue(any(first['id'] in problem for problem in validate(broken)))

    def test_every_templated_field_is_checked(self):
        """Review finding: validate expanded only the line, so a bad token elsewhere surfaced only at run time."""
        doc = json.loads((ROOT / 'vectors.json').read_text())
        for field in ('url', 'value', 'check'):
            broken = copy.deepcopy(doc)
            vector = next(v for v in broken['vectors'] if v['id'] == 'P01')
            if field == 'url':
                vector['url'] += '{dat:+1d}'
            elif field == 'value':
                vector['draft']['value'] = '{repeat:vv:2}'
            else:
                vector['checks'][0] += '{when:x}'
            with self.subTest(field):
                self.assertTrue(any('P01' in problem for problem in validate(broken)))

    def test_every_vector_says_whether_it_is_well_formed(self):
        broken = json.loads((ROOT / 'vectors.json').read_text())
        del broken['vectors'][0]['wellFormed']
        self.assertTrue(validate(broken))


class Expansion(unittest.TestCase):
    def test_http_dates_use_the_imf_fixdate_form(self):
        self.assertEqual(http_date(0), 'Thu, 01 Jan 1970 00:00:00 GMT')
        self.assertEqual(http_date(784111777), 'Sun, 06 Nov 1994 08:49:37 GMT')

    def test_tokens_expand_relative_to_the_run_clock(self):
        self.assertEqual(expand('x; Expires={date:+1d}', 0), 'x; Expires=Fri, 02 Jan 1970 00:00:00 GMT')
        self.assertEqual(expand('{date:+2h}', 0), 'Thu, 01 Jan 1970 02:00:00 GMT')
        self.assertEqual(expand('{date:+30m}', 0), 'Thu, 01 Jan 1970 00:30:00 GMT')
        self.assertEqual(expand('{date:-1d}', 86400), 'Thu, 01 Jan 1970 00:00:00 GMT')
        self.assertEqual(expand('a={repeat:v:3}', 0), 'a=vvv')

    def test_an_unknown_token_is_an_error_not_literal_text(self):
        with self.assertRaises(ValueError):
            expand('{when:+1d}', 0)

    def test_loading_expands_lines_and_draft_values(self):
        vectors = {v['id']: v for v in load_vectors(NOW_MS)}
        self.assertEqual(len(vectors['P07a']['draft']['value']), 4095)
        self.assertNotIn('{', vectors['R02']['line'])


class Expiry(unittest.TestCase):
    def test_session_cookies_are_not_persistent(self):
        self.assertTrue(expiry_matches('session', {'persistent': False, 'expiresAt': 0}, NOW_MS))
        self.assertFalse(expiry_matches('session', {'persistent': True, 'expiresAt': NOW_MS + 60000}, NOW_MS))

    def test_expired_means_at_or_before_the_run_clock(self):
        self.assertTrue(expiry_matches('expired', {'persistent': True, 'expiresAt': NOW_MS}, NOW_MS))
        self.assertTrue(expiry_matches('expired', {'persistent': True, 'expiresAt': -2**63}, NOW_MS))
        self.assertFalse(expiry_matches('expired', {'persistent': True, 'expiresAt': NOW_MS + 60000}, NOW_MS))

    def test_relative_expiry_allows_only_clock_skew(self):
        sixty = {'seconds': 60}
        self.assertTrue(expiry_matches(sixty, {'persistent': True, 'expiresAt': NOW_MS + 61000}, NOW_MS))
        self.assertFalse(expiry_matches(sixty, {'persistent': True, 'expiresAt': NOW_MS + 600000}, NOW_MS))
        self.assertFalse(expiry_matches({'days': 400}, {'persistent': True, 'expiresAt': NOW_MS + 730 * 86400000}, NOW_MS))

    def test_a_short_lifetime_is_not_hidden_by_the_skew(self):
        """Review finding: a 120 s skew let Max-Age=60 match a cookie that expired at once, or one that lived 170 s."""
        sixty = {'seconds': 60}
        for wrong in (NOW_MS, NOW_MS + 170_000, NOW_MS - 50_000):
            with self.subTest(wrong - NOW_MS):
                self.assertFalse(expiry_matches(sixty, {'persistent': True, 'expiresAt': wrong}, NOW_MS))


class Differences(unittest.TestCase):
    def setUp(self):
        self.vectors = {v['id']: v for v in load_vectors(NOW_MS)}

    def test_an_observation_built_from_the_draft_has_no_difference(self):
        for vector in self.vectors.values():
            if vector['draft'].get('split'):
                continue
            with self.subTest(vector['id']):
                self.assertEqual(differences(vector, ideal(vector), NOW_MS), [])

    def test_each_field_is_reported_by_name(self):
        vector = self.vectors['R02']
        for field, value in [('value', 'other'), ('domain', 'example.com'), ('path', '/x'), ('hostOnly', False),
                             ('httpOnly', False), ('secure', False), ('sameSite', 'strict')]:
            observed = ideal(vector)
            observed['cookie'][field] = value
            with self.subTest(field):
                self.assertEqual(differences(vector, observed, NOW_MS), [field])
        observed = ideal(vector)
        observed['cookie']['expiresAt'] += 400 * 86400000
        self.assertEqual(differences(vector, observed, NOW_MS), ['expiry'])
        observed = ideal(vector)
        observed['sends'] = [False]
        self.assertEqual(differences(vector, observed, NOW_MS), ['sends'])

    def test_acceptance_differences_hide_field_noise(self):
        self.assertEqual(differences(self.vectors['P06'], ideal(self.vectors['R02']) | {'id': 'P06'}, NOW_MS), ['accept'])
        self.assertEqual(differences(self.vectors['R02'], {'id': 'R02', 'accepted': False}, NOW_MS), ['accept'])

    def test_unreported_same_site_is_marked_unobserved(self):
        """Review finding: iOS cannot express SameSite=None, and treating silence as agreement hid it."""
        vector = self.vectors['R02']
        observed = ideal(vector)
        del observed['cookie']['sameSite']
        self.assertEqual(differences(vector, observed, NOW_MS), ['sameSite(unobserved)'])

    def test_an_error_row_is_reported_as_an_error(self):
        """Review finding: a probe error has no 'accepted' key and used to look like an acceptance difference."""
        self.assertEqual(differences(self.vectors['R02'], {'id': 'R02', 'error': 'boom'}, NOW_MS), ['error'])

    def test_domain_case_is_not_a_difference(self):
        vector = self.vectors['D02b']
        observed = ideal(vector)
        observed['cookie']['domain'] = 'EXAMPLE.com'
        self.assertEqual(differences(vector, observed, NOW_MS), [])


class BetweenPlatforms(unittest.TestCase):
    """W's real cost is where the two platforms disagree with each other, whatever the draft says."""

    def setUp(self):
        self.vectors = {v['id']: v for v in load_vectors(NOW_MS)}

    def pair(self, vector_id):
        observed = ideal(self.vectors[vector_id])
        return observed, copy.deepcopy(observed)

    def test_identical_observations_do_not_differ(self):
        for vector_id in ('R02', 'P06', 'E05', 'D01'):
            a, b = self.pair(vector_id)
            with self.subTest(vector_id):
                self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), [])

    def test_acceptance_hides_field_noise(self):
        a, _ = self.pair('R02')
        self.assertEqual(platform_differences(a, NOW_MS, {'id': 'R02', 'accepted': False}, NOW_MS), ['accept'])

    def test_expiry_is_compared_relative_to_each_run_clock(self):
        a, b = self.pair('R12')
        later = NOW_MS + 3_600_000
        b['cookie']['expiresAt'] += 3_600_000
        self.assertEqual(platform_differences(a, NOW_MS, b, later), [])
        b['cookie']['expiresAt'] -= 330 * 86400000
        self.assertEqual(platform_differences(a, NOW_MS, b, later), ['expiry'])

    def test_two_expired_cookies_agree_even_with_different_past_times(self):
        a, b = self.pair('E05')
        b['cookie']['expiresAt'] = -2**63
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), [])

    def test_fields_sends_and_count_are_reported(self):
        a, b = self.pair('R05')
        b['cookie']['hostOnly'] = True
        b['sends'] = [False]
        b['count'] = 2
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), ['hostOnly', 'sends', 'count'])

    def test_same_site_reported_on_one_side_only_is_unobserved(self):
        a, b = self.pair('R02')
        b['cookie']['sameSite'] = 'Lax'
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), [])
        b['cookie']['sameSite'] = 'strict'
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), ['sameSite'])
        del b['cookie']['sameSite']
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), ['sameSite(unobserved)'])
        del a['cookie']['sameSite']
        self.assertEqual(platform_differences(a, NOW_MS, b, NOW_MS), [])

    def test_an_error_on_either_side_is_reported_as_an_error(self):
        a, _ = self.pair('R02')
        self.assertEqual(platform_differences(a, NOW_MS, {'id': 'R02', 'error': 'boom'}, NOW_MS), ['error'])
        self.assertEqual(platform_differences({'id': 'R02', 'error': 'boom'}, NOW_MS, a, NOW_MS), ['error'])


if __name__ == '__main__':
    unittest.main()
