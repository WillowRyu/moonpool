"""The runner must not launch the wrong artifact, reuse a run's evidence, or leave a device mapped."""
import json
from pathlib import Path
import tempfile
import unittest
from build import ios_artifact_digest
from run_probe import assert_fresh_run, collect

TAG = 'android-test'


class FakeDevice:
    def __init__(self, installed='good', reports=(), alive=True):
        self.calls, self.installed, self.reports, self.is_alive = [], installed, list(reports), alive

    def prepare(self):
        self.calls.append('prepare')
        return self.installed

    def launch(self):
        self.calls.append('launch')

    def read_report(self):
        return self.reports.pop(0) if self.reports else None

    def alive(self):
        return self.is_alive

    def stop(self):
        self.calls.append('stop')


class CollectTests(unittest.TestCase):
    def test_returns_the_final_report_and_stops_the_device(self):
        device = FakeDevice(reports=[None, 'not json', json.dumps({'run': 'other'}), json.dumps({'run': TAG, 'complete': True})])
        report, installed = collect(device, TAG, 'good', poll_seconds=0)
        self.assertEqual((report['complete'], installed), (True, 'good'))
        self.assertEqual(device.calls, ['prepare', 'launch', 'stop'])

    def test_a_different_artifact_is_never_launched(self):
        device = FakeDevice(installed='bad')
        with self.assertRaisesRegex(AssertionError, 'artifact'):
            collect(device, TAG, 'good', poll_seconds=0)
        self.assertEqual(device.calls, ['prepare', 'stop'])

    def test_a_failed_prepare_still_stops_the_device(self):
        device = FakeDevice()
        device.prepare = lambda: (_ for _ in ()).throw(OSError('install failed'))
        with self.assertRaises(OSError):
            collect(device, TAG, 'good', poll_seconds=0)
        self.assertEqual(device.calls, ['stop'])

    def test_a_deadline_stops_the_device(self):
        device = FakeDevice()
        with self.assertRaises(TimeoutError):
            collect(device, TAG, 'good', deadline_seconds=0, poll_seconds=0)
        self.assertEqual(device.calls, ['prepare', 'launch', 'stop'])

    def test_a_process_exit_stops_the_device_without_retry(self):
        device = FakeDevice(alive=False)
        with self.assertRaisesRegex(RuntimeError, 'without retry'):
            collect(device, TAG, 'good', startup_seconds=0, poll_seconds=0)
        self.assertEqual(device.calls, ['prepare', 'launch', 'stop'])


class FreshRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rows = Path(self.tmp.name) / 'requests.jsonl'

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_receipts_yet_is_fresh(self):
        assert_fresh_run(self.rows, TAG)

    def test_receipts_from_another_run_are_fine(self):
        self.rows.write_text(json.dumps({'run': 'ios-test'}) + '\n')
        assert_fresh_run(self.rows, TAG)

    def test_a_reused_run_tag_is_refused(self):
        self.rows.write_text(json.dumps({'run': TAG}) + '\n')
        with self.assertRaisesRegex(ValueError, TAG):
            assert_fresh_run(self.rows, TAG)


class IosArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Path(self.tmp.name)
        (self.app / 'Fixtures').mkdir()
        (self.app / 'HttpBrokerProbe').write_bytes(b'binary')
        (self.app / 'Fixtures/cases.json').write_text('[]')
        (self.app / 'Fixtures/ca.der').write_bytes(b'ca')
        self.digest = ios_artifact_digest(self.app)

    def tearDown(self):
        self.tmp.cleanup()

    def test_changed_cases_change_the_digest(self):
        (self.app / 'Fixtures/cases.json').write_text('[{}]')
        self.assertNotEqual(ios_artifact_digest(self.app), self.digest)

    def test_changed_ca_changes_the_digest(self):
        (self.app / 'Fixtures/ca.der').write_bytes(b'other')
        self.assertNotEqual(ios_artifact_digest(self.app), self.digest)

    def test_changed_executable_changes_the_digest(self):
        (self.app / 'HttpBrokerProbe').write_bytes(b'other')
        self.assertNotEqual(ios_artifact_digest(self.app), self.digest)

    def test_files_the_installer_may_add_do_not_change_the_digest(self):
        (self.app / 'PkgInfo').write_text('APPL')
        self.assertEqual(ios_artifact_digest(self.app), self.digest)


if __name__ == '__main__':
    unittest.main()
