import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check import admission_window_failures, classify

ROOT = Path(__file__).resolve().parent


class SwiftStoreOperationTests(unittest.TestCase):
    def test_owner_waits_for_its_own_completion_and_drops_requests_on_close(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "store-operations-tests"
            built = subprocess.run(
                ["xcrun", "swiftc", "-swift-version", "5", "-parse-as-library", str(ROOT / "StoreOperations.swift"),
                 str(ROOT / "StoreOperationsCases.swift"), "-o", str(executable)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)


class AdmissionWindowTests(unittest.TestCase):
    def test_both_cookie_sources_are_required_at_the_guest_observation(self):
        empty = {"policyDisallowed": True, "records": False, "cookies": False, "fixturePresent": False}
        held = {"writerStarts": 0, "guestLoads": 0, "writerResult": "pending", "cookie": empty}
        sample = {
            "heldAfterRead": held,
            "heldAtGuest": dict(held, guestLoads=1, cookie=dict(empty, records=True)),
        }
        self.assertEqual(admission_window_failures(sample), ["admissionFirst: guest observation lacks exclusion evidence"])
        sample["heldAtGuest"]["cookie"] = empty
        self.assertEqual(admission_window_failures(sample), [])

    def test_inspection_start_cannot_overlap_the_writer_readback(self):
        report = json.loads((ROOT / "results/ios-admission-writer-order.json").read_text())
        admission = report["cases"]["admissionFirst"]["events"]
        admission.insert(admission.index("inspection:empty"), "inspection:start")
        events = report["cases"]["writerFirst"]["events"]
        complete = events.index("writer:complete")
        events[complete:complete + 1] = ["writer:callback", "writer:readback", "inspection:start"]
        self.assertEqual(classify(report), [])

        events.remove("inspection:start")
        events.insert(events.index("writer:readback"), "inspection:start")
        self.assertIn("writerFirst: operation order differs", classify(report))
