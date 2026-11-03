"""The verdict follows the accepted iOS rule; a retained report needs its controls and witnesses."""
import copy
import unittest
from vectors import cookie_name, expand
from verify_results import classify, outcomes, verdict, verify_check, verify_seed

STORES = expand()
CYCLE = 'ios-check-test'


def by_kind(kind):
    return next(store for store in STORES if store['kind'] == kind)


def expected_present(store):
    return store['group'] == 'cookie'


def seed_report():
    seeded = []
    for store in STORES:
        if store['brandNew']:
            continue
        names = [cookie_name(store['kind'])] if expected_present(store) else []
        seeded.append({'case': store['id'], 'kind': store['kind'], 'partition': 'uuid-' + store['id'],
                       'visitsLoaded': [True for _ in store['steps']], 'inventoryAfterSeed': names,
                       'storageReady': True if store['storage'] else None})
    return {'platform': 'ios', 'run': 'ios-seed-test', 'mode': 'seed', 'complete': True, 'errors': [],
            'seeded': seeded, 'requests': []}


def check_entry(store):
    present = expected_present(store)
    name = cookie_name(store['kind'])
    names = [name] if present else []
    records = ['127.0.0.1'] if present else []
    entry = {'case': store['id'], 'kind': store['kind'], 'order': store['order'],
             'partition': 'new-uuid' if store['brandNew'] else 'uuid-' + store['id'],
             'policyAllowsAfterRule': False, 'first': {'names': names, 'records': records},
             'later': {'names': names, 'records': records}, 'witnessFirstLoaded': True, 'witnessXsiteLoaded': True,
             'storage': {'local': store['id'], 'indexed': store['id']} if store['storage'] else None,
             'inventoryFinal': names}
    if store['hazard']:
        entry['namesBeforePolicy'] = []
    return entry


def check_report():
    rows = []
    for store in STORES:
        cookie = cookie_name(store['kind']) + '=public' if expected_present(store) else ''
        for step in ['witness-first', 'witness-xsite']:
            rows.append({'run': CYCLE, 'case': store['id'], 'step': step, 'tls': True, 'cookie': cookie})
    return {'platform': 'ios', 'run': CYCLE, 'mode': 'check', 'complete': True, 'errors': [],
            'checks': [check_entry(store) for store in STORES], 'requests': rows}


def entry_of(report, kind):
    return next(entry for entry in report['checks'] if entry['kind'] == kind)


class RuleVerdictTests(unittest.TestCase):
    def test_both_sources_empty_is_empty(self):
        self.assertEqual(verdict({'names': [], 'records': []}), 'empty')

    def test_both_sources_reporting_cookies_is_present(self):
        self.assertEqual(verdict({'names': ['a'], 'records': ['host']}), 'present')

    def test_disagreement_is_unknown_in_either_direction(self):
        self.assertEqual(verdict({'names': ['a'], 'records': []}), 'unknown')
        self.assertEqual(verdict({'names': [], 'records': ['host']}), 'unknown')


class ClassificationTests(unittest.TestCase):
    def classify(self, kind, first, cookie=''):
        store = by_kind(kind)
        entry = check_entry(store)
        entry['first'] = first
        rows = [{'case': store['id'], 'step': 'witness-first', 'cookie': cookie}]
        return classify(store, entry, rows)

    def test_empty_verdict_with_a_server_witness_is_a_false_admit(self):
        result = self.classify('cookie-denied', {'names': [], 'records': []}, 't28e_cookie-denied=public')
        self.assertEqual(result['outcome'], 'false-admit')

    def test_empty_verdict_without_a_witness_admits_correctly(self):
        self.assertEqual(self.classify('local-data', {'names': [], 'records': []})['outcome'], 'correct-admit')

    def test_present_verdict_with_a_witness_refuses_correctly(self):
        result = self.classify('cookie-denied', {'names': ['a'], 'records': ['h']}, 't28e_cookie-denied=public')
        self.assertEqual(result['outcome'], 'correct-refuse')

    def test_any_refusal_of_a_store_without_a_witness_is_an_over_refusal(self):
        self.assertEqual(self.classify('short-lived', {'names': ['a'], 'records': ['h']})['outcome'], 'over-refuse')
        self.assertEqual(self.classify('local-data', {'names': [], 'records': ['h']})['outcome'], 'over-refuse')

    def test_disagreement_on_a_witnessed_cookie_still_refuses_safely(self):
        result = self.classify('partitioned-denied', {'names': ['a'], 'records': []}, 't28e_partitioned-denied=public')
        self.assertEqual(result['outcome'], 'safe-refuse')

    def test_another_kinds_cookie_is_not_a_witness(self):
        result = self.classify('local-data', {'names': [], 'records': []}, 't28e_cookie-denied=public')
        self.assertFalse(result['witnessed'])


class OutcomeTableTests(unittest.TestCase):
    def test_counts_outcomes_per_kind_across_reports(self):
        table = outcomes([check_report(), check_report()])
        self.assertEqual(table['local-data'], {'correct-admit': 8})
        self.assertEqual(table['partitioned-denied'], {'correct-refuse': 8})


class SeedEvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message):
        report = seed_report()
        mutate(report)
        with self.assertRaises(AssertionError) as caught:
            verify_seed(report)
        self.assertIn(message, str(caught.exception))

    def test_complete_seed_is_accepted(self):
        self.assertGreater(verify_seed(seed_report()), 0)

    def test_incomplete_or_failed_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_a_missing_store_is_rejected(self):
        self.rejects(lambda r: r['seeded'].pop(), 'stores')

    def test_late_stores_may_be_seeded_after_the_others(self):
        report = seed_report()
        report['seeded'].reverse()
        self.assertGreater(verify_seed(report), 0)

    def test_a_duplicate_store_is_rejected(self):
        self.rejects(lambda r: r['seeded'].__setitem__(0, r['seeded'][1]), 'stores')

    def test_partitioned_control_must_be_written_before_it_can_test_the_rule(self):
        def mutate(r):
            next(e for e in r['seeded'] if e['kind'] == 'partitioned-denied')['inventoryAfterSeed'] = []
        self.rejects(mutate, 'not inventoried')

    def test_a_cookie_kind_must_hold_its_cookie_while_the_writer_lives(self):
        def mutate(r):
            next(e for e in r['seeded'] if e['kind'] == 'cookie-denied')['inventoryAfterSeed'] = []
        self.rejects(mutate, 'not inventoried')

    def test_a_cookie_free_kind_must_be_free_while_the_writer_lives(self):
        def mutate(r):
            next(e for e in r['seeded'] if e['kind'] == 'local-data')['inventoryAfterSeed'] = ['x']
        self.rejects(mutate, 'contains a cookie')

    def test_local_data_must_have_been_written(self):
        def mutate(r):
            next(e for e in r['seeded'] if e['kind'] == 'local-data')['storageReady'] = None
        self.rejects(mutate, 'local data')

    def test_a_seed_visit_must_load(self):
        def mutate(r):
            next(e for e in r['seeded'] if e['kind'] == 'cookie-denied')['visitsLoaded'] = [False]
        self.rejects(mutate, 'did not load')


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
        entry_of(report, 'partitioned-denied').update(first={'names': [], 'records': []})
        self.assertGreater(verify_check(report, seed_report()), 0)

    def test_an_over_refusal_is_a_finding_not_a_rejection(self):
        report = check_report()
        entry_of(report, 'local-data').update(first={'names': [], 'records': ['moonpool']})
        self.assertGreater(verify_check(report, seed_report()), 0)

    def test_incomplete_or_failed_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_a_different_partition_is_not_a_reopening(self):
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(partition='other'), 'partition')

    def test_rule_requires_the_policy_to_be_active(self):
        self.rejects(lambda r: entry_of(r, 'local-data').update(policyAllowsAfterRule=True), 'deny')

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
                if row['case'].startswith('local-data-r1'):
                    row['cookie'] = 't28e_local-data=public'
        self.rejects(mutate, 'free control')

    def test_local_data_must_survive_the_check(self):
        self.rejects(lambda r: entry_of(r, 'local-data').update(storage={'local': None, 'indexed': None}), 'local data')

    def test_a_cookie_must_not_be_lost_during_the_check(self):
        self.rejects(lambda r: entry_of(r, 'cookie-denied').update(inventoryFinal=[]), 'lost')

    def test_hazard_control_must_reproduce_the_false_empty_before_policy(self):
        self.rejects(lambda r: entry_of(r, 'hazard-control').update(namesBeforePolicy=['t28e_hazard-control']), 'hazard')

    def test_hazard_control_must_be_detected_after_policy(self):
        self.rejects(lambda r: entry_of(r, 'hazard-control').update(first={'names': [], 'records': []}), 'hazard')

    def test_non_tls_or_foreign_rows_are_rejected(self):
        def mutate(r):
            r['requests'][0]['tls'] = False
        self.rejects(mutate, 'TLS')

    def test_verification_does_not_mutate_the_report(self):
        report = check_report()
        before = copy.deepcopy(report)
        verify_check(report, seed_report())
        self.assertEqual(report, before)


if __name__ == '__main__':
    unittest.main()
