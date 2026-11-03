"""A report can become visible before the native writer finishes its bytes."""
import unittest
from run_probe import parse_report, require_fixture_version


class RunnerTests(unittest.TestCase):
    def test_stale_server_case_list_fails_before_device_launch(self):
        with self.assertRaises(AssertionError): require_fixture_version({'casesSha256':'stale'})

    def test_incomplete_write_is_not_a_native_crash(self):
        for raw in (None, "", '{"run":'):
            self.assertIsNone(parse_report(raw, "android-first"))

    def test_only_current_final_report_is_collected(self):
        self.assertIsNone(parse_report('{"run":"android-old"}', "android-first"))
        self.assertEqual(parse_report('{"run":"android-first","complete":false}', "android-first"),
                         {"run":"android-first","complete":False})


if __name__ == "__main__": unittest.main()
