"""Each store is the first a new process asks about; the verdict follows the accepted iOS rule."""
import copy
import unittest
from vectors import cookie_name, expand
from verify_results import classify, outcomes, verdict, verify_first, verify_seed

STORES = expand()


def present(store):
    return store['group'] == 'cookie'


def seed_report():
    seeded = [{'case': s['id'], 'kind': s['kind'], 'partition': 'uuid-' + s['id'], 'visitsLoaded': [True for _ in s['steps']],
               'inventoryAfterSeed': [cookie_name(s['kind'])] if present(s) else [],
               'storageReady': True if s['storage'] else None} for s in STORES]
    return {'platform': 'ios', 'run': 'ios-seed', 'mode': 'seed', 'complete': True, 'errors': [], 'seeded': seeded, 'requests': []}


def launch(store, index):
    run = f'ios-first-{index}'
    names = [cookie_name(store['kind'])] if present(store) else []
    records = ['127.0.0.1'] if present(store) else []
    entry = {'case': store['id'], 'kind': store['kind'], 'order': store['order'], 'partition': 'uuid-' + store['id'],
             'first': {'names': names, 'records': records}, 'later': {'names': names, 'records': records},
             'policyAllowsAfterRule': False, 'witnessFirstLoaded': True, 'witnessXsiteLoaded': True, 'inventoryFinal': names,
             'storage': {'local': store['id'], 'indexed': store['id']} if store['storage'] else None}
    if store['hazard']:
        entry['namesBeforePolicy'] = []
    cookie = cookie_name(store['kind']) + '=public' if present(store) else ''
    rows = [{'run': run, 'case': store['id'], 'step': step, 'tls': True, 'cookie': cookie} for step in ['witness-first', 'witness-xsite']]
    return {'run': run, 'only': store['id'], 'complete': True, 'errors': [], 'checks': [entry], 'requests': rows}


def first_report():
    return {'platform': 'ios', 'run': 'ios-first', 'mode': 'first', 'launches': [launch(s, i + 1) for i, s in enumerate(STORES)]}


def launch_of(report, kind):
    return next(item for item in report['launches'] if item['checks'][0]['kind'] == kind)


class RuleTests(unittest.TestCase):
    def test_verdict_follows_the_accepted_rule(self):
        self.assertEqual(verdict({'names': [], 'records': []}), 'empty')
        self.assertEqual(verdict({'names': ['a'], 'records': ['h']}), 'present')
        self.assertEqual(verdict({'names': ['a'], 'records': []}), 'unknown')
        self.assertEqual(verdict({'names': [], 'records': ['h']}), 'unknown')

    def classify(self, kind, first, cookie=''):
        store = next(s for s in STORES if s['kind'] == kind)
        entry = {**launch(store, 1)['checks'][0], 'first': first}
        return classify(store, entry, [{'case': store['id'], 'cookie': cookie}])['outcome']

    def test_outcomes(self):
        empty = {'names': [], 'records': []}
        both = {'names': ['a'], 'records': ['h']}
        self.assertEqual(self.classify('cookie-denied', empty, 't28f_cookie-denied=public'), 'false-admit')
        self.assertEqual(self.classify('local-data-denied', empty), 'correct-admit')
        self.assertEqual(self.classify('cookie-denied', both, 't28f_cookie-denied=public'), 'correct-refuse')
        self.assertEqual(self.classify('local-data-denied', both), 'over-refuse')
        self.assertEqual(self.classify('cookie-denied', {'names': ['a'], 'records': []}, 't28f_cookie-denied=public'), 'safe-refuse')

    def test_table_counts_every_store_of_a_kind(self):
        self.assertEqual(outcomes(first_report())['local-data-denied'], {'correct-admit': 4})


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

    def test_failed_or_partial_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')
        self.rejects(lambda r: r['seeded'].pop(), 'stores')

    def test_cookie_and_free_controls_are_required(self):
        self.rejects(lambda r: self.seeded(r, 'partitioned-denied').update(inventoryAfterSeed=[]), 'not inventoried')
        self.rejects(lambda r: self.seeded(r, 'local-data-denied').update(inventoryAfterSeed=['x']), 'contains a cookie')
        self.rejects(lambda r: self.seeded(r, 'local-data-denied').update(storageReady=None), 'local data')
        self.rejects(lambda r: self.seeded(r, 'cookie-denied').update(visitsLoaded=[False]), 'did not load')


class FirstEvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message):
        report = first_report()
        mutate(report)
        with self.assertRaises(AssertionError) as caught:
            verify_first(report, seed_report())
        self.assertIn(message, str(caught.exception))

    def test_complete_report_is_accepted(self):
        self.assertGreater(verify_first(first_report(), seed_report()), 0)

    def test_a_false_admit_or_over_refusal_is_a_finding(self):
        report = first_report()
        launch_of(report, 'cookie-denied')['checks'][0]['first'] = {'names': [], 'records': []}
        launch_of(report, 'local-data-denied')['checks'][0]['first'] = {'names': [], 'records': ['h']}
        self.assertGreater(verify_first(report, seed_report()), 0)

    def test_every_store_needs_its_own_launch(self):
        self.rejects(lambda r: r['launches'].pop(), 'launch')

    def test_a_process_must_check_exactly_its_store(self):
        self.rejects(lambda r: r['launches'][0]['checks'].append(dict(r['launches'][0]['checks'][0])), 'exactly')
        self.rejects(lambda r: r['launches'][0].update(only='other'), 'launch')

    def test_a_launch_must_succeed(self):
        self.rejects(lambda r: r['launches'][0].update(complete=False), 'incomplete')
        self.rejects(lambda r: r['launches'][0].update(errors=[{'code': 1}]), 'errors')

    def test_receipts_must_be_tls_and_from_this_launch(self):
        self.rejects(lambda r: r['launches'][0]['requests'][0].update(tls=False), 'TLS')
        self.rejects(lambda r: r['launches'][0]['requests'][0].update(run='ios-first-99'), 'TLS')

    def test_a_different_partition_is_not_a_reopening(self):
        self.rejects(lambda r: launch_of(r, 'cookie-denied')['checks'][0].update(partition='other'), 'partition')

    def test_rule_needs_deny_active_and_witnesses_loaded(self):
        self.rejects(lambda r: launch_of(r, 'cookie-denied')['checks'][0].update(policyAllowsAfterRule=True), 'deny')
        self.rejects(lambda r: launch_of(r, 'cookie-denied')['checks'][0].update(witnessFirstLoaded=False), 'witness')

    def test_positive_and_free_controls_are_required(self):
        def no_witness(r):
            for row in launch_of(r, 'cookie-denied')['requests']:
                row['cookie'] = ''
        def witness(r):
            for row in launch_of(r, 'local-data-denied')['requests']:
                row['cookie'] = 't28f_local-data-denied=public'
        self.rejects(no_witness, 'positive control')
        self.rejects(witness, 'free control')

    def test_local_data_and_cookies_must_survive(self):
        self.rejects(lambda r: launch_of(r, 'local-data-denied')['checks'][0].update(storage=None), 'local data')
        self.rejects(lambda r: launch_of(r, 'cookie-denied')['checks'][0].update(inventoryFinal=[]), 'lost')

    def test_hazard_control_must_show_the_blocker_then_the_correct_verdict(self):
        self.rejects(lambda r: launch_of(r, 'hazard-control')['checks'][0].update(namesBeforePolicy=['x']), 'hazard')
        self.rejects(lambda r: launch_of(r, 'hazard-control')['checks'][0].update(first={'names': [], 'records': []}), 'hazard')

    def test_verification_does_not_mutate_the_report(self):
        report = first_report()
        before = copy.deepcopy(report)
        verify_first(report, seed_report())
        self.assertEqual(report, before)


if __name__ == '__main__':
    unittest.main()
