import contextlib
import io
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock

import check
from check import verify


class VerifyTests(unittest.TestCase):
    def test_case_without_assertions_raises_a_setup_error(self):
        for steps in ([], [{'op': 'receive', 'fields': ['a=1']}]):
            with self.subTest(steps=steps):
                case = {'id': 'P01', 'steps': steps}
                result = {'id': 'P01', 'observations': [None] * len(steps)}
                with self.assertRaisesRegex(ValueError, 'P01 has no assertions'):
                    verify([case], [result])


def run_main(argv):
    """Run check.main() against a temporary PSL file whose digest is made to match the corpus."""
    profile = check.json.loads((check.ROOT / 'vectors.json').read_text(encoding='utf-8'))
    with tempfile.NamedTemporaryFile() as psl, \
            mock.patch.object(sys, 'argv', ['check.py', '--psl', psl.name, *argv]), \
            mock.patch.object(check.hashlib, 'sha256') as sha256, \
            contextlib.redirect_stdout(io.StringIO()) as stdout, \
            contextlib.redirect_stderr(io.StringIO()) as stderr:
        sha256.return_value.hexdigest.return_value = profile['psl']['sha256']
        status = check.main()
    return status, stdout.getvalue(), stderr.getvalue()


def echo_runner(change=None):
    """A fake subject that returns its inputs as observations, optionally changing one."""
    def run(inputs, psl, digest):
        results = [{'id': case['id'], 'observations': [step['op'] for step in case['steps']]} for case in inputs]
        if change:
            change(results)
        return results, '0' * 64
    return run


class SubjectTests(unittest.TestCase):
    def test_subject_is_required(self):
        # Running the baseline by accident would look like a failing reference parser, and the reverse.
        with mock.patch.object(sys, 'argv', ['check.py', '--psl', 'missing.dat']), \
                contextlib.redirect_stderr(io.StringIO()) as stderr, \
                self.assertRaises(SystemExit) as stopped:
            check.main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertIn('--subject', stderr.getvalue())

    def test_reference_self_test_failure_is_a_behavior_failure(self):
        failing = mock.Mock(side_effect=check.BehaviorFailure('self-test failed'))
        with mock.patch.dict(check.RUNNERS, {'reference': failing}):
            status, stdout, _ = run_main(['--subject', 'reference', '--case', 'P01'])
        self.assertEqual(status, 1)
        self.assertIn('FAIL self-test failed', stdout)

    def test_generated_cases_need_both_ports(self):
        for subjects in (['reference'], ['swift', 'baseline']):
            with self.subTest(subjects=subjects):
                argv = [arg for subject in subjects for arg in ('--subject', subject)]
                status, _, stderr = run_main([*argv, '--generated', '5'])
                self.assertEqual(status, 2)
                self.assertIn('--generated needs', stderr)

    def test_ports_receive_generated_cases_and_the_baseline_does_not(self):
        received = {}

        def recording(subject):
            def run(inputs, psl, digest):
                received[subject] = [case['id'] for case in inputs]
                return echo_runner()(inputs, psl, digest)
            return run

        runners = {name: recording(name) for name in check.RUNNERS}
        with mock.patch.dict(check.RUNNERS, runners), mock.patch.object(check, 'verify', return_value=0):
            argv = ['--subject', 'reference', '--subject', 'swift', '--subject', 'baseline', '--generated', '3']
            status, stdout, _ = run_main([*argv, '--case', 'P01'])
        self.assertEqual(status, 0)
        self.assertEqual(received['baseline'], ['P01'])
        self.assertEqual(received['reference'], ['P01', 'G00000', 'G00001', 'G00002'])
        self.assertEqual(received['swift'], received['reference'])
        self.assertIn('1 corpus and 3 generated cases compared, 0 differences', stdout)

    def test_a_port_difference_fails_the_run(self):
        def change(results):
            results[-1]['observations'][-1] = 'different'

        runners = {'reference': echo_runner(), 'swift': echo_runner(change)}
        with mock.patch.dict(check.RUNNERS, runners), mock.patch.object(check, 'verify', return_value=0):
            status, stdout, _ = run_main(['--subject', 'reference', '--subject', 'swift', '--generated', '2'])
        self.assertEqual(status, 1)
        self.assertIn('G00001 step', stdout)
        self.assertIn('1 differences', stdout)


class CompareTests(unittest.TestCase):
    def test_identical_observations_have_no_differences(self):
        results = [{'id': 'G00000', 'observations': [None, 'a=1']}]
        self.assertEqual(check.compare({'reference': results, 'swift': results}), [])

    def test_unasserted_fields_are_compared(self):
        cookie = {'name': 'a', 'value': '1', 'domain': 'api.example.com', 'path': '/', 'hostOnly': True}
        left = [{'id': 'P01', 'observations': [[{**cookie, 'sameSite': 'default'}]]}]
        right = [{'id': 'P01', 'observations': [[{**cookie, 'sameSite': 'Lax'}]]}]
        differences = check.compare({'reference': left, 'swift': right})
        self.assertEqual(len(differences), 1)
        self.assertIn('P01 step 1', differences[0])

    def test_jar_entry_order_is_not_a_difference(self):
        a = {'name': 'a', 'value': '1', 'domain': 'api.example.com', 'path': '/', 'hostOnly': True}
        b = {**a, 'name': 'b'}
        left = [{'id': 'P02', 'observations': [[a, b]]}]
        right = [{'id': 'P02', 'observations': [[b, a]]}]
        self.assertEqual(check.compare({'reference': left, 'swift': right}), [])

    def test_header_order_is_a_difference(self):
        left = [{'id': 'O01', 'observations': ['b=2; a=1']}]
        right = [{'id': 'O01', 'observations': ['a=1; b=2']}]
        self.assertEqual(len(check.compare({'reference': left, 'swift': right})), 1)


class GeneratedTests(unittest.TestCase):
    def test_generation_is_deterministic_and_has_no_expected_values(self):
        cases = check.generated_cases(200, 7)
        self.assertEqual(cases, check.generated_cases(200, 7))
        self.assertNotEqual(cases, check.generated_cases(200, 8))
        steps = [step for case in cases for step in case['steps']]
        self.assertTrue(all('expect' not in step for step in steps))
        self.assertEqual({step['op'] for step in steps}, {'receive', 'header', 'read', 'jar', 'set'})
        # inputs_for rejects decreasing clocks, so this also checks the generated offsets.
        inputs = list(check.inputs_for(cases, datetime.fromisoformat('2026-11-11T00:00:00Z'), 'https://x/'))
        self.assertEqual(len(inputs), 200)


if __name__ == '__main__':
    unittest.main()
