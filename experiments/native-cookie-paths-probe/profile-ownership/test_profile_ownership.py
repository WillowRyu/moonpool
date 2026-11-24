import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from zipfile import ZipFile

import check
from check import ROOT, snapshot, source_fingerprints, write_failures


class WriterEvidenceTests(unittest.TestCase):
    def test_a_successful_callback_requires_the_owners_readback(self):
        evidence = {
            "callback": True,
            "owner": {"accept": False, "hasCookies": False, "cookie": None},
        }

        self.assertEqual(write_failures(evidence, accept=False, marker="mp_fixture=direct"), [
            "the original handle did not observe the reported write",
        ])

        evidence["owner"] = {"accept": False, "hasCookies": True, "cookie": "mp_fixture=direct"}
        self.assertEqual(write_failures(evidence, accept=False, marker="mp_fixture=direct"), [])


class RetainedOutcomeTests(unittest.TestCase):
    def test_retained_expectation_fails_for_a_consistent_refused_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report = json.loads((ROOT / "results/android-profile-ownership.json").read_text())
            report["build"]["sources"] = source_fingerprints()

            def verify(*options):
                report_path.write_text(json.dumps(report))
                return subprocess.run(
                    [sys.executable, "-OB", str(ROOT / "check.py"), str(report_path), *options],
                    capture_output=True, text=True, timeout=15,
                )

            stored = verify("--expect-direct", "stored")
            self.assertEqual(stored.returncode, 0, stored.stderr)

            report["cases"]["direct"]["write"].update(
                callback=False, owner=snapshot(False), peer=snapshot(False),
            )
            observed = verify()
            self.assertEqual(observed.returncode, 0, observed.stderr)
            self.assertIn("direct native write under deny: refused", observed.stdout)

            expected = verify("--expect-direct", "stored")
            self.assertNotEqual(expected.returncode, 0)
            self.assertIn("expected stored, observed refused", expected.stdout)


class FingerprintTests(unittest.TestCase):
    def test_fingerprints_follow_the_wrapper_and_exclude_machine_local_files(self):
        jar = "../../android-origin-probe/gradle/wrapper/gradle-wrapper.jar"
        report = json.loads((ROOT / "results/android-profile-ownership.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "experiments/native-cookie-paths-probe/profile-ownership"
            for relative in (*report["build"]["sources"], jar):
                target = (probe / relative).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)

            with mock.patch.object(check, "ROOT", probe):
                original = source_fingerprints()
                (probe / "android/local.properties").write_text("sdk.dir=/local/sdk\n")
                idea = probe / "android/.idea"
                idea.mkdir()
                (idea / "workspace.xml").write_text("<project/>")
                with_local_files = source_fingerprints()
                with self.subTest("machine-local files"):
                    self.assertEqual(with_local_files, original)

                (probe / jar).write_bytes(b"changed wrapper")
                with self.subTest("executable wrapper"):
                    self.assertNotEqual(source_fingerprints().get(jar), with_local_files.get(jar))


class ArchivedEvidenceTests(unittest.TestCase):
    def test_original_reports_can_be_verified_without_a_source_checkout(self):
        results = ROOT / "results"
        archive = results / "android-profile-ownership-original-sources.zip"
        with tempfile.TemporaryDirectory() as directory:
            verification_root = Path(directory)
            verifier = verification_root / ROOT.relative_to(ROOT.parents[2]) / "check.py"
            verifier.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / "check.py", verifier)

            def verify(name, sources):
                return subprocess.run(
                    [sys.executable, "-OB", str(verifier), str(results / name),
                     "--expect-direct", "stored", "--source-archive", str(sources)],
                    capture_output=True, text=True, timeout=15,
                )

            for name in ("android-profile-ownership.json", "android-profile-ownership-repeat.json"):
                with self.subTest(report=name):
                    result = verify(name, archive)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("0 failures, direct native write under deny: stored", result.stdout)

            modified = verification_root / "incomplete.zip"
            with ZipFile(archive) as original, ZipFile(modified, "w") as copy:
                for entry in original.infolist()[1:]:
                    copy.writestr(entry, original.read(entry))
            incomplete = verify("android-profile-ownership.json", modified)
            self.assertNotEqual(incomplete.returncode, 0)
            self.assertIn("Changed build sources", incomplete.stderr)
