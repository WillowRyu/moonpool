import unittest

from check import POLICY, frame_failures, frame_refusal, worker_evidence


class FrameRefusalTests(unittest.TestCase):
    def test_silent_data_frame_does_not_prove_a_policy_refusal(self):
        page = {"starts": [], "workers": [], "workerViolations": [], "frameViolations": [],
                "trace": ["attach", "detach"]}
        self.assertFalse(frame_refusal(page, "data"))

        event = {"directive": "frame-src", "disposition": "enforce", "trusted": True, "scheme": "data"}
        page.update(frameViolations=[event], trace=["attach", "frame-violation", "detach"])
        self.assertTrue(frame_refusal(page, "data"))

        page["starts"] = [{"name": "data", "protocol": "data:", "messageOrigin": "null"}]
        self.assertFalse(frame_refusal(page, "data"))

    def test_retained_data_refusal_requires_the_reported_scheme(self):
        event = {"directive": "frame-src", "disposition": "enforce", "trusted": True, "scheme": None}
        page = {"starts": [], "workers": [], "workerViolations": [], "frameViolations": [event],
                "trace": ["attach", "frame-violation", "detach"]}
        self.assertFalse(frame_refusal(page, "data"))

    def test_worker_marker_requires_a_loader_receipt(self):
        origin = "moonpool://com.example.localframes.ios-test.control"
        message = {"outcome": "message", "messageOrigin": origin}
        self.assertFalse(worker_evidence(message, [], origin, "control", receipts=0))
        self.assertTrue(worker_evidence(message, [], origin, "control", receipts=1))

        rejected = dict(message, outcome="rejected")
        self.assertFalse(worker_evidence(rejected, [], origin, "control", receipts=0))
        self.assertFalse(worker_evidence(rejected, [], origin, "guarded", receipts=0))

    def test_frame_refusal_requires_each_parent_and_store_binding(self):
        origin = "moonpool://com.example.localframes.ios-test.guarded"
        event = {"directive": "frame-src", "disposition": "enforce", "trusted": True, "scheme": "data"}
        page = {"parentUrl": origin + "/entry/data", "starts": [], "workers": [], "workerViolations": [],
                "frameViolations": [event], "trace": ["attach", "frame-violation", "detach"]}
        frame = {"parentUrl": page["parentUrl"], "store": "selected", "policies": {"/entry/data": POLICY},
                 "requests": ["/entry/data", "/probe.js"], "page": page}
        self.assertEqual(frame_failures(frame, origin, "guarded", "data", "selected"), [])

        other_url = origin + "/entry/blob"
        mismatches = {
            "native URL": dict(frame, parentUrl=other_url),
            "page URL": dict(frame, page=dict(page, parentUrl=other_url)),
            "store": dict(frame, store="different"),
        }
        for reason, changed in mismatches.items():
            with self.subTest(reason=reason):
                self.assertEqual(frame_failures(changed, origin, "guarded", "data", "selected"),
                                 ["parent document or store binding differs"])

    def test_guarded_blob_requires_a_child_start_and_a_worker_refusal(self):
        origin = "moonpool://com.example.localframes.ios-test.guarded"
        entry = "/entry/blob"
        worker_event = {"directive": "worker-src", "disposition": "enforce", "trusted": True,
                        "blockedURI": origin + "/worker.js", "messageOrigin": origin}
        page = {
            "parentUrl": origin + entry,
            "starts": [{"name": "blob", "protocol": "blob:", "origin": origin, "messageOrigin": origin}],
            "workers": [{"outcome": "rejected", "messageOrigin": origin}], "workerViolations": [worker_event],
            "frameViolations": [], "trace": ["attach", "ready", "worker-result", "worker-violation", "detach"],
        }
        frame = {"parentUrl": origin + entry, "store": "selected", "policies": {entry: POLICY},
                 "requests": [entry, "/probe.js"], "page": page}
        self.assertEqual(frame_failures(frame, origin, "guarded", "blob", "selected"), [])

        violation_first = dict(frame, page=dict(page, trace=["attach", "ready", "worker-violation", "worker-result", "detach"]))
        self.assertEqual(frame_failures(violation_first, origin, "guarded", "blob", "selected"), [])

        no_start = dict(frame, page=dict(page, starts=[]))
        self.assertIn("the frame start, document origin or enforcing events differ",
                      frame_failures(no_start, origin, "guarded", "blob", "selected"))

        no_worker = dict(frame, page=dict(page, workers=[]))
        self.assertIn("the worker outcome lacks matching evidence",
                      frame_failures(no_worker, origin, "guarded", "blob", "selected"))

        no_violation = dict(frame, page=dict(page, workerViolations=[]))
        self.assertIn("the worker outcome lacks matching evidence",
                      frame_failures(no_violation, origin, "guarded", "blob", "selected"))
