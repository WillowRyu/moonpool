import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from zipfile import ZipFile

import run_probe
from check import ROOT, admission_failures, policy_failures, source_fingerprints


class RegistrationEvidenceTests(unittest.TestCase):
    def test_a_generic_registration_error_does_not_prove_enforcing_csp(self):
        origin = "https://mp-example-managed.invalid"
        page = {
            "attempts": {
                "main": {"origin": origin, "outcome": "rejected", "error": "SecurityError"},
                "frame": {"origin": origin, "outcome": "rejected", "error": "SecurityError"},
            },
            "scopes": [],
        }

        self.assertEqual(policy_failures(origin, page, guarded=True), [
            "main: enforcing worker-src violation missing",
            "frame: enforcing worker-src violation missing",
        ])


class ColdAdmissionTests(unittest.TestCase):
    def test_refusal_preserves_data_in_the_bound_profile(self):
        check = {
            "profile": "worker-prevention-android-example-unknown",
            "profilePresent": True,
            "cookieDeny": True,
            "cookiePresent": False,
            "provenance": False,
            "verdict": "unknown",
            "events": ["policy", "decision", "refuse"],
            "guestLoads": 0,
            "guest": None,
            "marker": None,
            "markerOrigin": "https://mp-android-example-unknown.invalid",
            "documentPolicies": {},
            "workerRequests": [],
        }

        self.assertEqual(admission_failures("android-example", "unknown", check), [
            "stored marker did not survive",
        ])

        check["marker"] = "android-example-unknown"
        self.assertEqual(admission_failures("android-example", "unknown", check), [])


class CollectorGuardTests(unittest.TestCase):
    def test_wrong_emulator_is_refused_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            apk = local / "fixture.apk"
            apk.write_bytes(b"fixture")
            owner = local / "owner.json"
            owner.write_text(json.dumps({"avd": "Expected", "serial": "fixture-serial"}))
            (local / "android-build.json").write_text(json.dumps({
                "sources": run_probe.source_fingerprints(),
                "artifactSha256": run_probe.sha(apk),
            }))

            def command(parts, **options):
                self.assertEqual(parts[3:], ["emu", "avd", "name"])
                return SimpleNamespace(stdout="Different\nOK\n")

            with mock.patch.multiple(run_probe, LOCAL=local, APK=apk, command=command):
                with self.assertRaisesRegex(RuntimeError, "Wrong emulator"):
                    run_probe.collect("test", owner)


class ReportGuardTests(unittest.TestCase):
    def test_optimized_verifier_rejects_source_and_artifact_mismatches(self):
        original = (ROOT / "results/android-worker-prevention.json").read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            for mismatch, reason in (
                ("sources", "Changed build sources"),
                ("artifact", "Installed APK differs"),
            ):
                with self.subTest(mismatch=mismatch):
                    report = json.loads(original)
                    report["build"]["sources"] = source_fingerprints()
                    if mismatch == "sources":
                        report["build"]["sources"] = {}
                    else:
                        report["installedArtifactSha256"] = "0" * 64
                    path.write_text(json.dumps(report))

                    result = subprocess.run(
                        [sys.executable, "-OB", str(ROOT / "check.py"), str(path)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(reason, result.stderr)


class InitialReportTests(unittest.TestCase):
    def test_initial_reports_replay_from_the_shared_source_archive(self):
        results = ROOT / "results"
        archive = results / "android-worker-prevention-initial-sources.zip"
        with tempfile.TemporaryDirectory() as temporary:
            with ZipFile(archive) as sources:
                sources.extractall(temporary)
            checker = Path(temporary) / "experiments/native-cookie-paths-probe/worker-prevention/check.py"
            for name in ("android-worker-prevention.json", "android-worker-prevention-repeat.json"):
                with self.subTest(report=name):
                    result = subprocess.run(
                        [sys.executable, "-IB", str(checker), str(results / name)],
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("0 failures", result.stdout)

            asset = checker.parent / "register.js"
            asset.write_bytes(asset.read_bytes() + b"\n")
            changed = subprocess.run(
                [sys.executable, "-IB", str(checker), str(results / "android-worker-prevention.json")],
                capture_output=True, text=True, timeout=15,
            )
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("Changed build sources", changed.stderr)
