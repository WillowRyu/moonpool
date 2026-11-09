"""Waiting for the app's report must neither lose a finished report nor retry a failed one."""
from pathlib import Path
import tempfile
import unittest
from run_ios import wait_for_report


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Waiting(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'report.json'
        self.clock = Clock()

    def tearDown(self):
        self.dir.cleanup()

    def wait(self, alive):
        return wait_for_report(self.path, alive, deadline_seconds=5, monotonic=self.clock.monotonic, sleep=self.clock.sleep)

    def test_a_report_written_before_the_app_exits_is_returned(self):
        def alive():
            self.path.write_text('{"ok": true}')
            return True
        self.assertEqual(self.wait(alive), {'ok': True})

    def test_a_report_written_just_before_exit_is_not_lost(self):
        """Review finding: an exit between the existence check and the liveness check used to fail a complete run."""
        def alive():
            self.path.write_text('{"ok": true}')
            return False
        self.assertEqual(self.wait(alive), {'ok': True})

    def test_an_exit_without_a_report_fails_without_retry(self):
        calls = []
        def alive():
            calls.append(1)
            return False
        with self.assertRaises(RuntimeError):
            self.wait(alive)
        self.assertEqual(len(calls), 1)

    def test_no_report_by_the_deadline_fails(self):
        with self.assertRaises(TimeoutError):
            self.wait(lambda: True)


if __name__ == '__main__':
    unittest.main()
