"""Mutation controls show that raw observations, not success labels, drive verification."""
import copy
import json
from pathlib import Path
import unittest
from verify_results import verify_report

ROOT = Path(__file__).resolve().parent

class VerifierMutationTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "results/t28-first-restart.json").read_text())
        verify_report(self.report)

    def reject(self, change):
        changed = copy.deepcopy(self.report)
        change(changed)
        with self.assertRaises((AssertionError, KeyError)):
            verify_report(changed)

    def test_missing_positive_sample_rejected(self):
        self.reject(lambda r: r["samples"].pop())

    def test_remote_before_write_bleed_rejected(self):
        self.reject(lambda r: next(s for s in r["samples"] if s["name"] == "remote-b")["before"].update(before="t28_remote=t28-first-a"))

    def test_remote_wrong_profile_rejected(self):
        self.reject(lambda r: next(s for s in r["samples"] if s["name"] == "remote-b").update(profile=r["a"]["profile"]))

    def test_unloaded_foreign_frame_rejected(self):
        self.reject(lambda r: r["samples"][0]["document"]["crossFrame"]["ready"].update(origin="null"))

    def test_lost_restart_indexeddb_rejected(self):
        self.reject(lambda r: r["samples"][0]["document"]["before"].update(indexedDB=None))

    def test_missing_native_early_use_negative_rejected(self):
        self.reject(lambda r: r.update(events=[e for e in r["events"] if e["kind"] != "early-getProfile"]))

    def test_changed_asset_digest_rejected(self):
        self.reject(lambda r: r["build"]["sources"].update({"app/src/main/assets/probe.js": "0" * 64}))

if __name__ == "__main__":
    unittest.main()
