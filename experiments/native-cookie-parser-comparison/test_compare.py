"""The comparison is the measurement, so it must catch every kind of difference it claims to report."""
import copy
import json
from pathlib import Path
import unittest
from compare import differences, expand, expiry_matches, http_date, load_vectors, validate

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

    def test_unreported_same_site_is_not_a_difference(self):
        vector = self.vectors['R02']
        observed = ideal(vector)
        del observed['cookie']['sameSite']
        self.assertEqual(differences(vector, observed, NOW_MS), [])

    def test_domain_case_is_not_a_difference(self):
        vector = self.vectors['D02b']
        observed = ideal(vector)
        observed['cookie']['domain'] = 'EXAMPLE.com'
        self.assertEqual(differences(vector, observed, NOW_MS), [])


if __name__ == '__main__':
    unittest.main()
