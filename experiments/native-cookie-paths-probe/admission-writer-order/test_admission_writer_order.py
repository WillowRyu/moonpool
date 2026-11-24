import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check import admission_window_failures, classify

ROOT = Path(__file__).resolve().parent


class StoreOperationTests(unittest.TestCase):
    def test_owner_holds_the_current_operation_until_its_own_completion(self):
        java = Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin")
        source = ROOT / "android/app/src/main/java/org/moonpool/cookieadmission/StoreOperations.java"
        with tempfile.TemporaryDirectory() as target:
            built = subprocess.run(
                [str(java / "javac"), "-d", target, str(source), str(ROOT / "test/StoreOperationsCases.java")],
                capture_output=True, text=True, timeout=25,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            result = subprocess.run(
                [str(java / "java"), "-cp", target, "org.moonpool.cookieadmission.StoreOperationsCases"],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class AdmissionWindowTests(unittest.TestCase):
    def test_empty_inventory_alone_does_not_prove_exclusion_through_guest_execution(self):
        cookie = {"accept": False, "present": False}
        held_after_read = {"writerStarts": 0, "guestLoads": 0, "writerResult": "pending", "cookie": cookie}
        sample = {
            "heldAfterRead": held_after_read,
            "heldAtGuest": dict(held_after_read, guestLoads=1, writerStarts=1),
        }
        self.assertEqual(admission_window_failures(sample), ["admissionFirst: writer escaped before the guest observation"])
        sample["heldAtGuest"]["writerStarts"] = 0
        self.assertEqual(admission_window_failures(sample), [])


class WriterTraceTests(unittest.TestCase):
    def reviewed_sample(self):
        report = json.loads((ROOT / "results/android-admission-writer-order.json").read_text())
        admission = report["cases"]["admissionFirst"]["events"]
        admission.insert(admission.index("inspection:empty"), "inspection:start")
        writer = report["cases"]["writerFirst"]
        events = writer["events"]
        complete = events.index("writer:complete")
        events[complete:complete + 1] = ["writer:callback", "writer:readback", "inspection:start"]
        writer["afterCookie"] = writer["write"]["cookie"]
        return report

    def test_callback_receipt_must_be_distinct_from_readback(self):
        report = self.reviewed_sample()
        self.assertEqual(classify(report), [])
        events = report["cases"]["writerFirst"]["events"]
        events.remove("writer:callback")
        self.assertIn("writerFirst: operation order differs", classify(report))

    def test_cookie_presence_after_refusal_does_not_prove_marker_retention(self):
        report = self.reviewed_sample()
        self.assertEqual(classify(report), [])
        report["cases"]["writerFirst"]["afterCookie"] = "mp_admission_order=other"
        self.assertIn("writerFirst: marker readback after refusal differs", classify(report))
