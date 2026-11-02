"""Negative verifier controls: malformed/copy-pasted raw evidence must fail."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import verify_results

ROOT = Path(__file__).resolve().parent

class EvidenceVerifierTest(unittest.TestCase):
    def test_retained_raw_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_results.verify(ROOT / "results")

    def rejects(self, mutate):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for file in (ROOT / "results").glob("*.json"):
                (directory / file.name).write_bytes(file.read_bytes())
            target = directory / "first-seed.json"
            value = json.loads(target.read_text())
            mutate(value)
            target.write_text(json.dumps(value))
            with self.assertRaises(AssertionError), contextlib.redirect_stdout(io.StringIO()):
                verify_results.verify(directory)

    def test_copied_a_cookie_sample_cannot_impersonate_b(self):
        def mutate(data):
            samples = data["samples"]
            a = copy.deepcopy(next(s for s in samples if s["label"] == "https-initial-a"))
            a["label"] = "https-initial-b"
            index = next(i for i, s in enumerate(samples) if s["label"] == "https-initial-b")
            samples[index] = a
        self.rejects(mutate)

    def test_missing_source_hash_is_not_accepted(self):
        self.rejects(lambda data: data["buildMetadata"]["sources"].pop("Admission.swift"))

    def test_default_store_metadata_cannot_pass(self):
        self.rejects(lambda data: data["samples"][0].update(storeIdentifier="nil"))

    def test_old_document_cannot_impersonate_reload(self):
        def mutate(data):
            first = next(s for s in data["samples"] if s["label"] == "initial-a")
            reload = next(s for s in data["samples"] if s["label"] == "reload-a")
            reload["observation"] = copy.deepcopy(first["observation"])
            reload["freshNativeMessage"] = copy.deepcopy(first["freshNativeMessage"])
        self.rejects(mutate)

    def test_unloaded_frame_does_not_prove_dom_isolation(self):
        self.rejects(lambda data: data["samples"][0]["observation"]["cross"].pop("loaded"))

if __name__ == "__main__":
    unittest.main()
