import unittest

from check import verify


class VerifyTests(unittest.TestCase):
    def test_case_without_assertions_raises_a_setup_error(self):
        for steps in ([], [{'op': 'receive', 'fields': ['a=1']}]):
            with self.subTest(steps=steps):
                case = {'id': 'P01', 'steps': steps}
                result = {'id': 'P01', 'observations': [None] * len(steps)}
                with self.assertRaisesRegex(ValueError, 'P01 has no assertions'):
                    verify([case], [result])
