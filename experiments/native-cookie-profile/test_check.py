import contextlib
import io
import sys
import tempfile
import unittest
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
        profile = check.json.loads((check.ROOT / 'vectors.json').read_text(encoding='utf-8'))
        with tempfile.NamedTemporaryFile() as psl:
            argv = ['check.py', '--subject', 'reference', '--psl', psl.name, '--case', 'P01']
            with mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(check.hashlib, 'sha256') as sha256, \
                    mock.patch.object(check, 'run_reference', side_effect=check.BehaviorFailure('self-test failed')), \
                    contextlib.redirect_stdout(io.StringIO()) as stdout:
                sha256.return_value.hexdigest.return_value = profile['psl']['sha256']
                status = check.main()
        self.assertEqual(status, 1)
        self.assertIn('FAIL self-test failed', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
