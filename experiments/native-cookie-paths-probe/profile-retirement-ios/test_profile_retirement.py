import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from check import ROOT, cookie_verdict, retirement_failures, source_fingerprints


class WebKitRetirementTests(unittest.TestCase):
    def test_both_admitted_views_must_be_detached_and_released(self):
        released = {
            "live": False, "loads": 1, "retireCalls": 1, "released": True,
            "attached": False, "groupInactiveAtRelease": True,
        }
        refused = {
            "live": False, "loads": 0, "retireCalls": 1, "released": False,
            "attached": False, "groupInactiveAtRelease": False,
        }
        states = {
            "a1": dict(released),
            "a2": dict(released, released=False, attached=True),
            "a3": dict(refused),
            "a4": dict(refused),
        }

        self.assertEqual(retirement_failures(states), ["a2: admitted WebView retirement differs"])
        states["a2"] = dict(released)
        self.assertEqual(retirement_failures(states), [])

    def test_two_cookie_sources_must_agree_under_verified_deny(self):
        sample = {"policyDisallowed": True, "records": False, "cookies": False}
        self.assertEqual(cookie_verdict(sample), "empty")
        self.assertEqual(cookie_verdict(dict(sample, cookies=True)), "unknown")
        self.assertEqual(cookie_verdict(dict(sample, records=True, cookies=True)), "present")
        self.assertEqual(cookie_verdict(dict(sample, policyDisallowed=False)), "unknown")


class RetainedReleaseTests(unittest.TestCase):
    def test_retained_report_requires_both_weak_references_to_clear(self):
        report = json.loads((ROOT / "results/ios-profile-retirement.json").read_text())
        report["build"]["sources"] = source_fingerprints()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"

            def verify(*options):
                path.write_text(json.dumps(report))
                return subprocess.run(
                    [sys.executable, "-OB", str(ROOT / "check.py"), str(path), *options],
                    capture_output=True, text=True, timeout=15,
                )

            passing = verify("--expect-cleared-weak-references")
            self.assertEqual(passing.returncode, 0, passing.stderr)

            report["weakReferencesCleared"]["a2"] = False
            observation = verify()
            self.assertEqual(observation.returncode, 0, observation.stderr)
            retained = verify("--expect-cleared-weak-references")
            self.assertNotEqual(retained.returncode, 0)
            self.assertIn("both weak references must clear", retained.stdout)


class SwiftCookiePresenceTests(unittest.TestCase):
    def test_swift_gate_input_handles_disagreement_and_missing_sources(self):
        gate = ROOT.parent.parent / "native-cookie-admission-probe/ios/AdmissionGate.swift"
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "cookie-presence-tests"
            compile_result = subprocess.run(
                ["xcrun", "swiftc", "-swift-version", "5", "-parse-as-library", str(gate),
                 str(ROOT / "CookiePresence.swift"), str(ROOT / "CookiePresenceTests.swift"), "-o", str(executable)],
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
