from copy import deepcopy
import unittest
from uuid import uuid4

from check import KINDS, MODES, POLICY, source_fingerprints, verify_pair, verify_report


def frame_fixture(origin, kind, mode, store, frame_source="self"):
    entry = f"/entry/{kind}"
    policy = POLICY.replace("frame-src 'self'", f"frame-src {origin}") if frame_source == "origin" else POLICY
    policies = {entry: policy if mode == "guarded" else ""}
    if kind == "same":
        policies["/same-frame"] = policies[entry]
    requests = [path for document in policies for path in (document, "/probe.js")]
    page = {"parentUrl": origin + entry, "trace": ["attach"], "starts": [], "workers": [],
            "frameViolations": [], "workerViolations": []}
    if kind == "blank-navigation":
        policies["/before-blank"] = ""
        requests.append("/before-blank")
        page["navigation"] = {"previousUrl": origin + "/before-blank", "replacementUrl": "about:blank",
                              "documentReplaced": True}
        page["trace"].extend(["previous-document", "blank-navigation", "replacement-document"])
    refused = kind == "data" or (kind == "blob" and frame_source == "origin")
    if refused and mode == "guarded":
        page["frameViolations"].append({"directive": "frame-src", "disposition": "enforce", "trusted": True, "scheme": kind})
        page["trace"].append("frame-violation")
    else:
        child_origin = "null" if kind == "data" else origin
        protocol = "moonpool:" if kind == "same" else f"{kind}:"
        start = {"name": kind, "protocol": protocol, "origin": child_origin, "messageOrigin": child_origin}
        if kind in ("blank", "srcdoc", "blank-navigation"):
            url = "about:blank" if kind == "blank-navigation" else f"about:{kind}"
            start.update(protocol="about:", url=url, secureContext=True, serviceWorkerRegistration=False)
        page["starts"].append(start)
        page["trace"].append("ready")
        if kind != "data":
            outcome = "message" if mode == "control" else "rejected"
            page["workers"].append({"outcome": outcome, "messageOrigin": origin})
            page["trace"].append("worker-result")
            if mode == "control":
                requests.append("/worker.js")
            else:
                page["workerViolations"].append({"directive": "worker-src", "disposition": "enforce", "trusted": True,
                                                "blockedURI": origin + "/worker.js", "messageOrigin": origin})
                page["trace"].append("worker-violation")
    page["trace"].append("detach")
    return {"parentUrl": origin + entry, "store": store, "requests": requests, "policies": policies, "page": page}


def report_fixture(run, pid, frame_source="self", document_set="local"):
    samples = {}
    kinds = {"inherited": ("blank", "srcdoc"), "navigation": ("blank-navigation",)}.get(document_set, KINDS)
    for mode in MODES:
        store = str(uuid4())
        origin = f"moonpool://com.example.localframes.{run}.{mode}"
        samples[mode] = {
            "store": store, "persistent": True, "cookies": {"policyDisallowed": True, "records": False, "cookies": False},
            "frames": {kind: frame_fixture(origin, kind, mode, store, frame_source) for kind in kinds},
        }
    return {
        "run": run, "pid": pid, "complete": True, "platform": "ios", "release": "26.4.1", "initializedWebKit": True,
        "build": {"sources": source_fingerprints(), "artifactSha256": "a" * 64, "sdk": "26.4", "xcode": "Xcode 26.4.1"},
        "installedArtifactSha256": "a" * 64,
        "simulator": {"runtime": "com.apple.CoreSimulator.SimRuntime.iOS-26-4",
                      "deviceType": "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"},
        "frameSource": frame_source, "documentSet": document_set, "samples": samples,
    }


class RetainedReportTests(unittest.TestCase):
    def setUp(self):
        self.first = report_fixture("ios-fixture-a", 100)
        self.repeat = report_fixture("ios-fixture-b", 101)

    def test_pair_accepts_independent_runs_on_the_same_app_and_environment(self):
        self.assertEqual(verify_pair(self.first, self.repeat), [])

    def test_later_blank_requires_worker_receipt_after_the_previous_document(self):
        first = report_fixture("ios-navigation-a", 100, "origin", "navigation")
        repeat = report_fixture("ios-navigation-b", 101, "origin", "navigation")
        self.assertEqual(verify_pair(first, repeat, expect_retained_outcomes=True), [])
        requests = repeat["samples"]["control"]["frames"]["blank-navigation"]["requests"]
        requests.remove("/worker.js")
        requests.insert(requests.index("/before-blank"), "/worker.js")
        self.assertIn("repeat: control/blank-navigation: worker receipt precedes the previous document",
                      verify_pair(first, repeat, expect_retained_outcomes=True))

    def test_later_blank_requires_the_previous_response_and_a_new_document(self):
        report = report_fixture("ios-navigation-a", 100, "origin", "navigation")
        self.assertEqual(verify_report(report, expect_retained_outcomes=True), [])
        guarded = report["samples"]["guarded"]["frames"]["blank-navigation"]
        for value in (False, 1):
            with self.subTest(value=value):
                guarded["page"]["navigation"]["documentReplaced"] = value
                self.assertIn("guarded/blank-navigation: replacement document evidence differs",
                              verify_report(report, expect_retained_outcomes=True))
        guarded["page"]["navigation"]["documentReplaced"] = True
        guarded["policies"]["/before-blank"] = POLICY
        self.assertIn("guarded/blank-navigation: document response policies differ", verify_report(report))

    def test_inherited_frame_results_require_child_execution_and_worker_csp(self):
        report = report_fixture("ios-inherited-a", 100, "origin", "inherited")
        self.assertEqual(verify_report(report), [])
        child = report["samples"]["guarded"]["frames"]["srcdoc"]["page"]
        for change, failure in (
            ({"starts": []}, "the frame start, document origin or enforcing events differ"),
            ({"workerViolations": []}, "the worker outcome lacks matching evidence"),
            ({"starts": [dict(child["starts"][0], url="about:blank")]},
             "the frame start, document origin or enforcing events differ"),
            ({"starts": [dict(child["starts"][0], serviceWorkerRegistration=1)]},
             "the frame start, document origin or enforcing events differ"),
        ):
            with self.subTest(change=change):
                changed = deepcopy(report)
                changed["samples"]["guarded"]["frames"]["srcdoc"]["page"].update(change)
                self.assertIn(f"guarded/srcdoc: {failure}", verify_report(changed))

    def test_pair_requires_the_same_document_set(self):
        inherited = report_fixture("ios-inherited-b", 101, "self", "inherited")
        self.assertEqual(verify_report(inherited), [])
        self.assertIn("document sets differ across runs", verify_pair(self.first, inherited))

    def test_retained_pair_requires_the_measured_inherited_capabilities(self):
        first = report_fixture("ios-inherited-a", 100, "origin", "inherited")
        repeat = report_fixture("ios-inherited-b", 101, "origin", "inherited")
        self.assertEqual(verify_pair(first, repeat, expect_retained_outcomes=True), [])
        for mode, kind in (("control", "blank"), ("guarded", "srcdoc")):
            for field in ("secureContext", "serviceWorkerRegistration"):
                with self.subTest(mode=mode, kind=kind, field=field):
                    changed = deepcopy(repeat)
                    start = changed["samples"][mode]["frames"][kind]["page"]["starts"][0]
                    start[field] = not start[field]
                    self.assertEqual(verify_report(changed), [])
                    self.assertIn(f"repeat: {mode}/{kind}: inherited capability observations differ",
                                  verify_pair(first, changed, expect_retained_outcomes=True))

    def test_explicit_origin_requires_frame_refusal_even_if_the_blob_worker_is_blocked(self):
        report = report_fixture("ios-explicit-a", 100, "origin")
        self.assertEqual(verify_report(report), [])
        guarded = report["samples"]["guarded"]
        blob = guarded["frames"]["blob"]
        origin = "moonpool://com.example.localframes.ios-explicit-a.guarded"
        blob["page"] = frame_fixture(origin, "blob", "guarded", guarded["store"])["page"]
        self.assertIn("guarded/blob: no attributable enforcing frame refusal", verify_report(report))

    def test_pair_requires_the_same_frame_source(self):
        explicit = report_fixture("ios-explicit-b", 101, "origin")
        self.assertEqual(verify_report(explicit), [])
        self.assertIn("frame sources differ across runs", verify_pair(self.first, explicit))

    def test_pair_rejects_a_repeated_run_tag_even_with_fresh_stores(self):
        repeated_tag = report_fixture(self.first["run"], 101)
        self.assertIn("run tags are identical", verify_pair(self.first, repeated_tag))

    def test_pair_rejects_a_reused_store_even_when_view_bindings_match(self):
        sample = self.repeat["samples"]["guarded"]
        sample["store"] = self.first["samples"]["control"]["store"].upper()
        for frame in sample["frames"].values():
            frame["store"] = sample["store"]
        self.assertEqual(verify_report(self.repeat), [])
        self.assertIn("store identifiers were reused across runs", verify_pair(self.first, self.repeat))

    def test_pair_requires_the_same_installed_app(self):
        self.repeat["installedArtifactSha256"] = self.repeat["build"]["artifactSha256"] = "b" * 64
        self.assertEqual(verify_report(self.repeat), [])
        self.assertIn("installed app digests differ across runs", verify_pair(self.first, self.repeat))

    def test_pair_requires_the_same_execution_environment(self):
        differences = ((None, "release", "26.5"), ("build", "sdk", "26.5"), ("build", "xcode", "Xcode 26.5"),
                       ("simulator", "runtime", "com.apple.CoreSimulator.SimRuntime.iOS-26-5"),
                       ("simulator", "deviceType", "com.apple.CoreSimulator.SimDeviceType.iPhone-17"))
        for section, field, value in differences:
            with self.subTest(field=field):
                changed = deepcopy(self.repeat)
                target = changed if section is None else changed[section]
                target[field] = value
                self.assertEqual(verify_report(changed), [])
                self.assertIn("execution environments differ across runs", verify_pair(self.first, changed))

    def test_report_rejects_an_empty_digest_even_when_the_fields_match(self):
        self.repeat["installedArtifactSha256"] = self.repeat["build"]["artifactSha256"] = ""
        self.assertIn("installed app digest is missing or differs from the build", verify_report(self.repeat))

    def test_report_requires_sdk_and_simulator_metadata(self):
        for section, field in (("build", "sdk"), ("simulator", "runtime"), ("simulator", "deviceType")):
            with self.subTest(field=field):
                changed = deepcopy(self.repeat)
                del changed[section][field]
                self.assertIn("missing simulator or build environment", verify_report(changed))

    def test_report_requires_a_native_process_identifier(self):
        del self.repeat["pid"]
        self.assertIn("missing native process identifier", verify_report(self.repeat))
