"""hasCookies answers are compared with server receipts; a report needs its controls and witnesses."""
import copy
import unittest
from vectors import cookie_name, expand
from verify_results import classify, first_call_outcomes, outcome, outcomes, outcomes_by_order, verify_check, verify_first_call, verify_seed

STORES = expand()
RUN = 'android-check-test'


def by_kind(kind):
    return next(store for store in STORES if store['kind'] == kind)


def present(store):
    return store['group'] == 'cookie'


def seed_report():
    seeded = []
    for store in STORES:
        if store['brandNew']:
            continue
        seeded.append({'case': store['id'], 'kind': store['kind'], 'profile': 'restart-t-' + store['id'],
                       'visitsLoaded': [True for _ in store['steps']], 'hasCookies': present(store),
                       'storageReady': True if store['storage'] else None})
    return {'platform': 'android', 'run': 'android-seed-test', 'mode': 'seed', 'complete': True, 'errors': [],
            'seeded': seeded, 'requests': []}


def check_entry(store):
    answer = present(store)
    return {'case': store['id'], 'kind': store['kind'], 'order': store['order'], 'profile': 'restart-t-' + store['id'],
            'first': answer, 'firstMs': 1, 'acceptAfterFirst': True, 'afterPolicy': answer, 'later': answer,
            'acceptAtRule': False, 'acceptDuringWitness': True, 'witnessFirstLoaded': True,
            'witnessXsiteLoaded': True, 'finalHasCookies': answer,
            'storage': {'local': store['id'], 'indexed': store['id']} if store['storage'] else None}


def check_report():
    rows = []
    for store in STORES:
        cookie = cookie_name(store['kind']) + '=public' if present(store) else ''
        for step in ['witness-first', 'witness-xsite']:
            rows.append({'run': RUN, 'case': store['id'], 'step': step, 'tls': True, 'cookie': cookie})
    return {'platform': 'android', 'run': RUN, 'mode': 'check', 'complete': True, 'errors': [],
            'checks': [check_entry(store) for store in STORES], 'requests': rows}


def entry_of(report, kind, order='bare'):
    return next(e for e in report['checks'] if e['kind'] == kind and e['order'] == order)


class OutcomeTests(unittest.TestCase):
    def test_empty_answer_with_a_witness_is_a_false_admit(self):
        self.assertEqual(outcome(False, True), 'false-admit')

    def test_empty_answer_without_a_witness_admits_correctly(self):
        self.assertEqual(outcome(False, False), 'correct-admit')

    def test_present_answer_with_a_witness_refuses_correctly(self):
        self.assertEqual(outcome(True, True), 'correct-refuse')

    def test_present_answer_without_a_witness_is_an_over_refusal(self):
        self.assertEqual(outcome(True, False), 'over-refuse')


class ClassificationTests(unittest.TestCase):
    def classify(self, kind, cookie='', **answers):
        store = by_kind(kind)
        entry = {**check_entry(store), **answers}
        return classify(store, entry, [{'case': store['id'], 'step': 'witness-first', 'cookie': cookie}])

    def test_first_call_and_baseline_order_are_classified_separately(self):
        result = self.classify('cookie-denied', 't28r_cookie-denied=public', first=False, afterPolicy=True)
        self.assertEqual(result['firstOutcome'], 'false-admit')
        self.assertEqual(result['ruleOutcome'], 'correct-refuse')

    def test_another_kinds_cookie_is_not_a_witness(self):
        result = self.classify('local-data', 't28r_cookie-denied=public')
        self.assertFalse(result['witnessed'])
        self.assertEqual(result['ruleOutcome'], 'correct-admit')


class OutcomeTableTests(unittest.TestCase):
    def test_counts_both_outcomes_per_kind_across_reports(self):
        table = outcomes([check_report(), check_report()])
        self.assertEqual(table['local-data']['rule'], {'correct-admit': 12})
        self.assertEqual(table['cookie-denied']['first'], {'correct-refuse': 12})

    def test_first_call_outcomes_are_grouped_by_what_ran_before_it(self):
        report = check_report()
        entry_of(report, 'cookie-denied', 'bare')['first'] = False
        table = outcomes_by_order([report])
        self.assertEqual(table['bare']['false-admit'], 1)
        self.assertNotIn('false-admit', table['policy'])


class SeedEvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message):
        report = seed_report()
        mutate(report)
        with self.assertRaises(AssertionError) as caught:
            verify_seed(report)
        self.assertIn(message, str(caught.exception))

    def seeded(self, report, kind):
        return next(e for e in report['seeded'] if e['kind'] == kind)

    def test_complete_seed_is_accepted(self):
        self.assertGreater(verify_seed(seed_report()), 0)

    def test_late_stores_may_be_seeded_after_the_others(self):
        report = seed_report()
        report['seeded'].reverse()
        self.assertGreater(verify_seed(report), 0)

    def test_incomplete_or_failed_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_a_missing_or_duplicate_store_is_rejected(self):
        self.rejects(lambda r: r['seeded'].pop(), 'stores')
        self.rejects(lambda r: r['seeded'].__setitem__(0, r['seeded'][1]), 'stores')

    def test_a_cookie_kind_must_hold_its_cookie_while_the_writer_lives(self):
        self.rejects(lambda r: self.seeded(r, 'cookie-denied').update(hasCookies=False), 'not present')

    def test_a_cookie_free_kind_must_be_free_while_the_writer_lives(self):
        self.rejects(lambda r: self.seeded(r, 'local-data').update(hasCookies=True), 'contains a cookie')

    def test_local_data_must_have_been_written(self):
        self.rejects(lambda r: self.seeded(r, 'local-data').update(storageReady=None), 'local data')

    def test_a_seed_visit_must_load(self):
        self.rejects(lambda r: self.seeded(r, 'cookie-denied').update(visitsLoaded=[False]), 'did not load')


class CheckEvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message):
        report = check_report()
        mutate(report)
        with self.assertRaises(AssertionError) as caught:
            verify_check(report, seed_report())
        self.assertIn(message, str(caught.exception))

    def test_complete_check_is_accepted(self):
        self.assertGreater(verify_check(check_report(), seed_report()), 0)

    def test_a_false_admit_is_a_finding_not_a_rejection(self):
        report = check_report()
        entry_of(report, 'cookie-denied').update(first=False)
        self.assertGreater(verify_check(report, seed_report()), 0)

    def test_an_over_refusal_is_a_finding_not_a_rejection(self):
        report = check_report()
        entry_of(report, 'local-data').update(afterPolicy=True)
        self.assertGreater(verify_check(report, seed_report()), 0)

    def test_incomplete_or_failed_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_a_different_profile_is_not_a_reopening(self):
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(profile='other'), 'profile')

    def test_baseline_answer_requires_the_deny_policy(self):
        self.rejects(lambda r: entry_of(r, 'local-data').update(acceptAtRule=True), 'deny')

    def test_witness_under_deny_cannot_see_a_retained_cookie_so_it_is_rejected(self):
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(acceptDuringWitness=False), 'allow')

    def test_witness_contexts_must_load(self):
        self.rejects(lambda r: entry_of(r, 'local-data').update(witnessFirstLoaded=False), 'witness')
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(witnessXsiteLoaded=False), 'witness')

    def test_cookie_kinds_need_a_server_witness(self):
        def mutate(r):
            for row in r['requests']:
                if row['case'].startswith('cookie-denied'):
                    row['cookie'] = ''
        self.rejects(mutate, 'positive control')

    def test_cookie_free_kinds_must_have_no_server_witness(self):
        def mutate(r):
            for row in r['requests']:
                if row['case'].startswith('local-data-b1'):
                    row['cookie'] = 't28r_local-data=public'
        self.rejects(mutate, 'free control')

    def test_local_data_must_survive_the_check(self):
        self.rejects(lambda r: entry_of(r, 'local-data').update(storage={'local': None, 'indexed': None}), 'local data')

    def test_a_cookie_must_not_be_lost_during_the_check(self):
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(finalHasCookies=False), 'lost')

    def test_non_tls_or_foreign_rows_are_rejected(self):
        def mutate(r):
            r['requests'][0]['tls'] = False
        self.rejects(mutate, 'TLS')

    def test_verification_does_not_mutate_the_report(self):
        report = check_report()
        before = copy.deepcopy(report)
        verify_check(report, seed_report())
        self.assertEqual(report, before)


def first_call_report(kind='cookie-denied', order='bare', answer=True, cookie=True):
    store = next(s for s in STORES if s['kind'] == kind and s['order'] == order)
    entry = {**check_entry(store), 'first': answer, 'afterPolicy': answer, 'later': answer, 'finalHasCookies': answer}
    value = cookie_name(store['kind']) + '=public' if cookie else ''
    rows = [{'run': 'android-first-x', 'case': store['id'], 'step': 'witness-first', 'tls': True, 'cookie': value}]
    return {'platform': 'android', 'run': 'android-first-x', 'mode': 'check', 'only': store['id'], 'complete': True,
            'errors': [], 'checks': [entry], 'requests': rows}


class FirstCallTests(unittest.TestCase):
    def rejects(self, mutate, message):
        report = first_call_report()
        mutate(report)
        with self.assertRaises(AssertionError) as caught:
            verify_first_call(report, seed_report())
        self.assertIn(message, str(caught.exception))

    def test_complete_first_call_is_accepted(self):
        self.assertGreater(verify_first_call(first_call_report(), seed_report()), 0)

    def test_a_false_empty_on_the_first_call_is_a_finding(self):
        report = first_call_report(answer=False)
        self.assertGreater(verify_first_call(report, seed_report()), 0)
        self.assertEqual(first_call_outcomes([report]), {'false-admit': 1})

    def test_the_process_must_have_checked_exactly_the_named_store(self):
        self.rejects(lambda r: r['checks'].append(dict(r['checks'][0])), 'exactly')
        self.rejects(lambda r: r.update(only='local-data-b1'), 'exactly')

    def test_only_a_bare_store_answers_for_the_first_call_question(self):
        report = first_call_report(order='policy')
        with self.assertRaises(AssertionError) as caught:
            verify_first_call(report, seed_report())
        self.assertIn('bare', str(caught.exception))

    def test_the_store_must_be_the_one_seeded_earlier(self):
        self.rejects(lambda r: r['checks'][0].update(profile='other'), 'profile')

    def test_failed_collection_and_foreign_rows_are_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')
        self.rejects(lambda r: r['requests'][0].update(tls=False), 'TLS')

    def test_witness_must_run_under_allow_and_load(self):
        self.rejects(lambda r: r['checks'][0].update(acceptDuringWitness=False), 'allow')
        self.rejects(lambda r: r['checks'][0].update(witnessFirstLoaded=False), 'witness')

    def test_a_cookie_kind_needs_its_server_witness(self):
        self.rejects(lambda r: r['requests'][0].update(cookie=''), 'positive control')


if __name__ == '__main__':
    unittest.main()
