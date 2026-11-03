"""A retained report is only evidence when its controls and witnesses are complete."""
import copy
import json
from pathlib import Path
import unittest
from verify_results import (
    classify_partition,
    classify_warmup,
    classify_writer,
    verify,
    verify_reopen,
    verify_warmup,
    verify_warmup_seed,
    warmup_rates,
)

ROOT = Path(__file__).resolve().parent
PARTITIONS = json.loads((ROOT / 'partition_cases.json').read_text())
WRITERS = json.loads((ROOT / 'writer_cases.json').read_text())
WARMUPS = json.loads((ROOT / 'warmup_cases.json').read_text())
STEPS = ['seed', 'read-same', 'read-other', 'read-first', 'read-same-deny']


def visit(loaded=True):
    return {'loaded': loaded, 'result': {'documentCookie': '', 'storeNames': []} if loaded else None}


def partition_sample(case, stored=False):
    name = 't28p_' + case['id']
    names = [name] if stored else []
    return {
        'case': case['id'], 'inventoryAfterSeed': names, 'inventoryAfterReads': names,
        'inventoryAfterDeny': names, 'inventoryFinal': names, 'policyAllowsAfterDeny': False,
        'visits': {step: visit() for step in STEPS}, 'cookies': [],
    }


def writer_sample(case):
    sample = {'case': case['id'], 'kind': case['kind']}
    if case['kind'] == 'hold':
        present = case['action'] == 'none'
        sample.update(heldObserved=True, inventoryBeforeRelease=[], responseDelivered=case['action'] != 'teardown',
                      inventoryAfterRelease=['t28w_' + case['id']] if present else [],
                      policyAllows=case['action'] != 'deny')
    elif case['kind'] == 'burst':
        name = 't28w_' + case['id'] + '_'
        sample.update(writesAtStart=3, writesAtCompletion=5, writesLater=9, stopped=True,
                      inventoryBeforePolicy=[name + '1'], inventoryAtCompletion=[name + '1', name + '2'],
                      inventoryLater=[name + '1', name + '2'], policyAllows=False)
    elif case['kind'] == 'native-unawaited':
        sample.update(seenImmediately=False, seenAfterCompletion=True)
    elif case['kind'] == 'native-under-deny':
        sample.update(inventoryAfterSet=['t28w_' + case['id']], policyAllows=False)
    else:
        sample.update(sameObject=False, firstSeesSecondPolicy=True, secondSeesFirstPolicy=True,
                      firstSeesSecondCookie=True, policyAfterRestore=True)
    return sample


def report():
    samples = []
    rows = []
    for case in PARTITIONS:
        stored = case['id'] == 'firstparty-plain'
        samples.append(partition_sample(case, stored))
        name = 't28p_' + case['id']
        for step in STEPS:
            rows.append({'case': case['id'], 'step': step, 'path': '/page', 'event': 'arrived', 'tls': True,
                         'run': 'ios-test', 'secFetchSite': 'cross-site', 'secFetchDest': 'iframe',
                         'cookie': name + '=public_' + case['id'] if stored and step != 'seed' else ''})
    writers = [writer_sample(case) for case in WRITERS]
    for case in WRITERS:
        if case['kind'] == 'hold':
            rows.append({'case': case['id'], 'step': 'hold', 'path': '/hold', 'event': 'released', 'tls': True,
                         'run': 'ios-test', 'cookie': ''})
        if case['kind'] != 'second-handle':
            present = case['kind'] == 'hold' and case['action'] == 'none'
            rows.append({'case': case['id'], 'step': 'echo', 'path': '/page', 'event': 'arrived', 'tls': True,
                         'run': 'ios-test', 'cookie': 't28w_' + case['id'] + '=public' if present else ''})
    return {'platform': 'ios', 'run': 'ios-test', 'complete': True, 'errors': [], 'samples': samples,
            'writers': writers, 'requests': rows}


def writer(r, case_id):
    return next(w for w in r['writers'] if w['case'] == case_id)


def reopen_report(source):
    rows = []
    entries = []
    for sample in source['samples']:
        name = 't28p_' + sample['case']
        stored = sample['inventoryFinal'] == [name]
        entries.append({'case': sample['case'], 'partition': sample['partition'], 'inventoryAtOpen': list(sample['inventoryFinal']),
                        'inventoryFinal': list(sample['inventoryFinal']), 'policyAllowsAtOpen': True,
                        'visit': visit()})
        rows.append({'case': sample['case'], 'step': 'read-same-reopen', 'path': '/page', 'event': 'arrived', 'tls': True,
                     'run': 'ios-reopen', 'cookie': name + '=public' if stored else ''})
    return {'platform': 'ios', 'run': 'ios-reopen', 'mode': 'reopen', 'complete': True, 'errors': [],
            'reopened': entries, 'requests': rows}


class PartitionClassificationTests(unittest.TestCase):
    def sample_and_rows(self, inventory, cookie_steps, case_id='xsite-header-partitioned'):
        name = 't28p_' + case_id
        case = next(c for c in PARTITIONS if c['id'] == case_id)
        sample = partition_sample(case)
        sample['inventoryAfterSeed'] = inventory
        sample['inventoryFinal'] = inventory
        rows = [{'case': case_id, 'step': s, 'path': '/page', 'event': 'arrived',
                 'cookie': name + '=public_' + case_id if s in cookie_steps else ''} for s in STEPS]
        return case, sample, rows

    def test_cookie_received_by_server_but_absent_from_inventory_is_a_false_empty(self):
        case, sample, rows = self.sample_and_rows([], ['read-same'])
        result = classify_partition(case, sample, rows)
        self.assertTrue(result['falseEmpty'])
        self.assertTrue(result['storedEvidence'])

    def test_script_visible_cookie_counts_as_stored_evidence(self):
        case, sample, rows = self.sample_and_rows([], [])
        sample['visits']['read-same']['result']['documentCookie'] = 't28p_xsite-header-partitioned=x'
        self.assertTrue(classify_partition(case, sample, rows)['falseEmpty'])

    def test_inventoried_cookie_is_not_a_false_empty(self):
        case, sample, rows = self.sample_and_rows(['t28p_xsite-header-partitioned'], ['read-same'])
        self.assertFalse(classify_partition(case, sample, rows)['falseEmpty'])

    def test_separation_requires_same_context_send_without_other_contexts(self):
        name = 't28p_xsite-header-partitioned'
        case, sample, rows = self.sample_and_rows([name], ['read-same'])
        self.assertTrue(classify_partition(case, sample, rows)['partitionSeparated'])
        case, sample, rows = self.sample_and_rows([name], ['read-same', 'read-first'])
        self.assertFalse(classify_partition(case, sample, rows)['partitionSeparated'])

    def test_a_cookie_that_was_never_stored_is_not_separation(self):
        case, sample, rows = self.sample_and_rows([], [])
        result = classify_partition(case, sample, rows)
        self.assertFalse(result['storedEvidence'])
        self.assertFalse(result['partitionSeparated'])
        self.assertFalse(result['falseEmpty'])

    def test_seed_seen_on_the_seed_request_itself_does_not_count_as_delivery(self):
        case, sample, rows = self.sample_and_rows([], ['seed'])
        self.assertFalse(classify_partition(case, sample, rows)['storedEvidence'])


class WriterClassificationTests(unittest.TestCase):
    def test_cookie_landing_after_deny_is_a_policy_leak(self):
        case = next(c for c in WRITERS if c['id'] == 'hold-navigation-deny')
        sample = writer_sample(case)
        sample['inventoryAfterRelease'] = ['t28w_hold-navigation-deny']
        result = classify_writer(case, sample, [])
        self.assertTrue(result['landedAfterEmptyCheck'])

    def test_server_witness_detects_a_landing_inventory_missed(self):
        case = next(c for c in WRITERS if c['id'] == 'hold-navigation-deny')
        rows = [{'case': case['id'], 'step': 'echo', 'cookie': 't28w_hold-navigation-deny=public'}]
        result = classify_writer(case, writer_sample(case), rows)
        self.assertTrue(result['landedAfterEmptyCheck'])
        self.assertTrue(result['inventoryMissedWitness'])

    def test_burst_names_added_after_policy_completion_are_late_writes(self):
        case = next(c for c in WRITERS if c['id'] == 'burst-document-deny')
        sample = writer_sample(case)
        name = 't28w_burst-document-deny_'
        sample['inventoryLater'] = [name + '1', name + '2', name + '7']
        result = classify_writer(case, sample, [])
        self.assertEqual(result['addedAfterCompletion'], [name + '7'])
        self.assertEqual(result['issuedAfterCompletion'], [name + '7'])

    def test_late_arrival_of_a_write_issued_before_completion_is_distinguished(self):
        case = next(c for c in WRITERS if c['id'] == 'burst-document-deny')
        sample = writer_sample(case)
        name = 't28w_burst-document-deny_'
        sample['inventoryLater'] = [name + '1', name + '2', name + '4']
        result = classify_writer(case, sample, [])
        self.assertEqual(result['addedAfterCompletion'], [name + '4'])
        self.assertEqual(result['issuedAfterCompletion'], [])


class EvidenceTests(unittest.TestCase):
    def rejects(self, mutate, message=None):
        r = report()
        mutate(r)
        with self.assertRaises(AssertionError) as caught:
            verify(r)
        if message:
            self.assertIn(message, str(caught.exception))

    def test_complete_report_is_accepted(self):
        self.assertGreater(verify(report()), 0)

    def test_a_false_empty_is_reported_not_rejected(self):
        r = report()
        for row in r['requests']:
            if row['case'] == 'xsite-header-partitioned' and row['step'] == 'read-same':
                row['cookie'] = 't28p_xsite-header-partitioned=public_xsite-header-partitioned'
        self.assertGreater(verify(r), 0)

    def test_incomplete_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')

    def test_native_load_errors_are_rejected(self):
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_missing_partition_case_is_rejected(self):
        self.rejects(lambda r: r['samples'].pop(), 'partition')

    def test_missing_writer_case_is_rejected(self):
        self.rejects(lambda r: r['writers'].pop(), 'writer')

    def test_first_party_positive_control_must_be_stored_and_inventoried(self):
        def mutate(r):
            r['samples'][1]['inventoryAfterSeed'] = []
        self.rejects(mutate, 'positive control')

    def test_empty_control_must_stay_empty(self):
        def mutate(r):
            r['samples'][0]['inventoryAfterSeed'] = ['t28p_empty']
        self.rejects(mutate, 'empty control')

    def test_https_cross_site_context_must_be_proven_by_the_server(self):
        def mutate(r):
            for row in r['requests']:
                if row['case'] == 'xsite-header-partitioned' and row['step'] == 'seed':
                    row['secFetchSite'] = 'same-site'
        self.rejects(mutate, 'cross-site')

    def test_https_seed_must_actually_load(self):
        def mutate(r):
            r['samples'][4]['visits']['seed'] = visit(False)
        self.rejects(mutate, 'seed')

    def test_moonpool_seed_failure_is_recorded_as_unobserved_not_rejected(self):
        r = report()
        sample = next(s for s in r['samples'] if s['case'] == 'moonpool-header-partitioned')
        sample['visits']['seed'] = visit(False)
        self.assertGreater(verify(r), 0)

    def test_deny_policy_must_be_active_for_deny_reads(self):
        def mutate(r):
            r['samples'][4]['policyAllowsAfterDeny'] = True
        self.rejects(mutate, 'deny')

    def test_a_cookie_lost_during_measurement_is_rejected(self):
        def mutate(r):
            r['samples'][1]['inventoryFinal'] = []
        self.rejects(mutate, 'lost')

    def test_race_control_must_demonstrate_the_landing(self):
        def mutate(r):
            writer(r, 'hold-fetch-allow')['inventoryAfterRelease'] = []
            for row in r['requests']:
                if row['case'] == 'hold-fetch-allow':
                    row['cookie'] = ''
        self.rejects(mutate, 'race control')

    def test_hold_must_be_observed_before_the_policy_change(self):
        def mutate(r):
            writer(r, 'hold-navigation-deny')['heldObserved'] = False
        self.rejects(mutate, 'held')

    def test_hold_must_start_from_an_empty_check(self):
        def mutate(r):
            writer(r, 'hold-navigation-deny')['inventoryBeforeRelease'] = ['t28w_x']
        self.rejects(mutate, 'empty check')

    def test_hold_release_must_be_recorded_by_the_server(self):
        def mutate(r):
            r['requests'] = [row for row in r['requests']
                             if not (row['case'] == 'hold-navigation-deny' and row['event'] == 'released')]
        self.rejects(mutate, 'released')

    def test_burst_writer_must_be_active_before_the_policy_change(self):
        def mutate(r):
            writer(r, 'burst-document-deny')['inventoryBeforePolicy'] = []
        self.rejects(mutate, 'active')

    def test_burst_writer_must_be_stopped_before_final_witness(self):
        def mutate(r):
            writer(r, 'burst-document-deny')['stopped'] = False
        self.rejects(mutate, 'stopped')

    def test_non_tls_or_foreign_run_rows_are_rejected(self):
        def mutate(r):
            r['requests'][0]['tls'] = False
        self.rejects(mutate, 'TLS')

    def test_a_deny_negative_without_proof_of_delivery_is_rejected(self):
        def mutate(r):
            writer(r, 'hold-fetch-deny')['responseDelivered'] = False
        self.rejects(mutate, 'delivered')

    def test_teardown_negative_does_not_need_delivery_proof(self):
        r = report()
        self.assertFalse(writer(r, 'hold-navigation-teardown')['responseDelivered'])
        self.assertGreater(verify(r), 0)

    def test_report_is_not_mutated_by_verification(self):
        r = report()
        before = copy.deepcopy(r)
        verify(r)
        self.assertEqual(r, before)


class ReopenTests(unittest.TestCase):
    def source(self):
        r = report()
        for sample in r['samples']:
            sample['partition'] = 'uuid-' + sample['case']
        return r

    def rejects(self, mutate, message):
        source = self.source()
        reopened = reopen_report(source)
        mutate(reopened)
        with self.assertRaises(AssertionError) as caught:
            verify_reopen(reopened, source)
        self.assertIn(message, str(caught.exception))

    def test_complete_reopen_is_accepted(self):
        source = self.source()
        self.assertGreater(verify_reopen(reopen_report(source), source), 0)

    def test_a_different_partition_is_not_a_reopening(self):
        self.rejects(lambda r: r['reopened'][1].update(partition='other'), 'partition')

    def test_positive_control_must_be_retained_and_eventually_listed(self):
        self.rejects(lambda r: r['reopened'][1].update(inventoryFinal=[]), 'positive control')
        def drop_receipt(r):
            r['requests'][1]['cookie'] = ''
        self.rejects(drop_receipt, 'positive control')

    def test_positive_control_missing_at_open_is_a_finding(self):
        source = self.source()
        reopened = reopen_report(source)
        reopened['reopened'][1]['inventoryAtOpen'] = []
        self.assertGreater(verify_reopen(reopened, source), 0)

    def test_empty_control_must_stay_empty(self):
        self.rejects(lambda r: r['reopened'][0].update(inventoryAtOpen=['t28p_empty']), 'empty control')

    def test_incomplete_or_failed_collection_is_rejected(self):
        self.rejects(lambda r: r.update(complete=False), 'incomplete')
        self.rejects(lambda r: r.update(errors=[{'code': 1}]), 'errors')

    def test_a_cold_false_empty_is_reported_not_rejected(self):
        source = self.source()
        reopened = reopen_report(source)
        entry = reopened['reopened'][4]
        entry['inventoryAtOpen'] = []
        reopened['requests'][4]['cookie'] = 't28p_xsite-header-partitioned=public'
        self.assertGreater(verify_reopen(reopened, source), 0)


def both(case_id):
    return ['t28u_' + case_id + '_first', 't28u_' + case_id + '_partitioned']


warmup_names_for = both


def seed_report():
    return {'platform': 'ios', 'run': 'ios-seed', 'mode': 'warmup-seed', 'complete': True, 'errors': [], 'requests': [],
            'seeded': [{'case': c['id'], 'partition': 'uuid-' + c['id'], 'inventoryAfterSeed': both(c['id'])} for c in WARMUPS]}


def warmup_report():
    entries = []
    rows = []
    for case in WARMUPS:
        listed = both(case['id']) if case['action'] == 'network' else []
        entries.append({'case': case['id'], 'partition': 'uuid-' + case['id'], 'action': case['action'],
                        'timeline': [{'at': 0, 'names': listed, 'records': []}, {'at': 2, 'names': listed, 'records': []}],
                        'witnessFirstLoaded': True, 'witnessXsiteLoaded': True, 'inventoryFinal': both(case['id'])})
        rows.append({'case': case['id'], 'step': 'witness-first', 'tls': True, 'run': 'ios-warmup',
                     'cookie': 't28u_' + case['id'] + '_first=public'})
        rows.append({'case': case['id'], 'step': 'witness-xsite', 'tls': True, 'run': 'ios-warmup',
                     'cookie': 't28u_' + case['id'] + '_partitioned=public'})
    return {'platform': 'ios', 'run': 'ios-warmup', 'mode': 'warmup', 'complete': True, 'errors': [],
            'warmups': entries, 'requests': rows}


class WarmupTests(unittest.TestCase):
    def rejects(self, mutate, message):
        r = warmup_report()
        mutate(r)
        with self.assertRaises(AssertionError) as caught:
            verify_warmup(r, seed_report())
        self.assertIn(message, str(caught.exception))

    def test_complete_reports_are_accepted(self):
        self.assertGreater(verify_warmup_seed(seed_report()), 0)
        self.assertGreater(verify_warmup(warmup_report(), seed_report()), 0)

    def test_seed_must_be_inventoried_while_the_writing_process_lives(self):
        r = seed_report()
        r['seeded'][0]['inventoryAfterSeed'] = []
        with self.assertRaises(AssertionError) as caught:
            verify_warmup_seed(r)
        self.assertIn('seed', str(caught.exception))

    def test_false_empty_at_first_enumeration_is_a_finding(self):
        case = WARMUPS[0]
        entry = warmup_report()['warmups'][0]
        rows = warmup_report()['requests']
        result = classify_warmup(case, entry, rows)
        self.assertTrue(result['falseEmptyAtFirstEnumeration'])
        self.assertFalse(result['listedByTimeline'])

    def test_partial_listing_is_still_a_false_empty_for_the_missing_cookie(self):
        case = WARMUPS[0]
        entry = warmup_report()['warmups'][0]
        entry['timeline'][0]['names'] = both(case['id'])[:1]
        result = classify_warmup(case, entry, warmup_report()['requests'])
        self.assertTrue(result['falseEmptyAtFirstEnumeration'])

    def test_listing_is_reported_with_the_first_time_it_was_complete(self):
        index = next(i for i, c in enumerate(WARMUPS) if c['action'] == 'wait')
        case = WARMUPS[index]
        entry = warmup_report()['warmups'][index]
        entry['timeline'][1]['names'] = both(case['id'])
        result = classify_warmup(case, entry, warmup_report()['requests'])
        self.assertTrue(result['falseEmptyAtFirstEnumeration'])
        self.assertTrue(result['listedByTimeline'])
        self.assertEqual(result['firstCompleteAt'], 2)

    def test_data_records_are_reported_separately_from_cookie_names(self):
        index = next(i for i, c in enumerate(WARMUPS) if c['action'] == 'records')
        case = WARMUPS[index]
        entry = warmup_report()['warmups'][index]
        entry['timeline'][0]['records'] = ['127.0.0.1']
        self.assertTrue(classify_warmup(case, entry, warmup_report()['requests'])['dataRecordsAtFirstEnumeration'])

    def test_each_strategy_needs_its_own_retained_cookies_as_witness(self):
        def mutate(r):
            r['requests'][0]['cookie'] = ''
        self.rejects(mutate, 'witness')

    def test_a_different_partition_is_rejected(self):
        self.rejects(lambda r: r['warmups'][0].update(partition='other'), 'partition')

    def test_network_control_must_produce_a_complete_listing(self):
        def mutate(r):
            entry = next(e for e in r['warmups'] if e['action'] == 'network')
            for step in entry['timeline']:
                step['names'] = []
        self.rejects(mutate, 'network control')

    def test_rates_count_false_empties_per_strategy_across_reports(self):
        first = warmup_report()
        second = warmup_report()
        for entry in second['warmups']:
            if entry['action'] == 'policy':
                entry['timeline'][0]['names'] = warmup_names_for(entry['case'])
                break
        rates = warmup_rates([first, second])
        total = sum(1 for c in WARMUPS if c['action'] == 'policy') * 2
        self.assertEqual(rates['policy'], {'stores': total, 'falseEmptyAtFirstEnumeration': total - 1})
        self.assertEqual(rates['network'], {'stores': 2, 'falseEmptyAtFirstEnumeration': 0})

    def test_final_inventory_must_list_both_cookies(self):
        self.rejects(lambda r: r['warmups'][0].update(inventoryFinal=[]), 'final')


if __name__ == '__main__':
    unittest.main()
