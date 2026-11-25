from copy import deepcopy
import unittest

from check import POLICY, classify, source_fingerprints, verify_pair, verify_report


def fixture(frame_source="self", document_set="local", *, run="android-fixture"):
    samples = {}
    for mode in ("control", "guarded"):
        origin = f"https://mp-{run}-{mode}.invalid"
        policy = POLICY.replace("frame-src 'self'", f"frame-src {origin}") if frame_source == "origin" else POLICY
        frames = {}
        kinds = {"inherited": ("blank", "srcdoc"), "navigation": ("blank-navigation",)}.get(
            document_set, ("same", "blob", "data")
        )
        for name in kinds:
            entry = f"/entry/{name}"
            child_origin = "null" if name == "data" else origin
            started = {"name": name, "origin": child_origin, "messageOrigin": child_origin,
                       "protocol": ("https" if name == "same" else name) + ":"}
            if document_set in ("inherited", "navigation"):
                url = "about:blank" if name == "blank-navigation" else f"about:{name}"
                started.update(protocol="about:", url=url, secureContext=True, serviceWorkerRegistration=True)
            blocked = mode == "guarded" and name in ("blob", "data")
            worker = mode == "control" and name != "data"
            requests = [entry, "/probe.js"]
            if name == "same":
                requests.extend(["/same-frame", "/probe.js"])
            if name == "blank-navigation":
                requests.append("/before-blank")
            if worker:
                requests.append("/worker.js")
            frame_event = {"directive": "frame-src", "disposition": "enforce",
                           "scheme": None if name == "data" else name, "trusted": True}
            worker_event = {"directive": "worker-src", "disposition": "enforce",
                            "blockedURI": origin + "/worker.js", "trusted": True, "messageOrigin": origin}
            result = {"outcome": "message" if worker else "rejected", "messageOrigin": origin}
            workers = [result] if not blocked and name != "data" else []
            worker_violations = [worker_event] if workers and not worker else []
            trace = ["attach"]
            if name == "blank-navigation":
                trace.extend(["previous-document", "blank-navigation", "replacement-document"])
            trace.extend(["frame-violation"] if blocked else ["ready"])
            if workers:
                trace.append("worker-result")
            if worker_violations:
                trace.append("worker-violation")
            trace.append("detach")
            page = {
                "parentUrl": origin + entry, "trace": trace, "starts": [] if blocked else [started],
                "workers": workers, "workerViolations": worker_violations, "frameViolations": [frame_event] if blocked else [],
            }
            if name == "blank-navigation":
                page["navigation"] = {"previousUrl": origin + "/before-blank", "replacementUrl": "about:blank",
                                      "documentReplaced": True}
            frames[name] = {
                "parentUrl": origin + entry, "requests": requests, "page": page,
                "policy": policy if mode == "guarded" else "",
            }
            if name == "blank-navigation":
                frames[name]["previousDocumentPolicy"] = ""
        samples[mode] = {"profile": f"local-document-frames-{run}-{mode}", "created": True,
                         "cookieDeny": True, "frames": frames}
    return {"run": run, "provider": "fixture", "sdk": 37, "release": "17", "complete": True,
            "frameSource": frame_source, "documentSet": document_set, "samples": samples}


class FramePolicyTests(unittest.TestCase):
    def test_later_blank_requires_worker_receipt_after_the_previous_document(self):
        report = fixture("origin", "navigation")
        self.assertEqual(classify(report, expect_retained_outcomes=True), [])
        requests = report["samples"]["control"]["frames"]["blank-navigation"]["requests"]
        requests.remove("/worker.js")
        requests.insert(requests.index("/before-blank"), "/worker.js")
        self.assertIn("control/blank-navigation: worker receipt precedes the previous document",
                      classify(report, expect_retained_outcomes=True))

    def test_later_blank_requires_the_previous_response_and_a_new_document(self):
        report = fixture("origin", "navigation")
        self.assertEqual(classify(report, expect_retained_outcomes=True), [])
        guarded = report["samples"]["guarded"]["frames"]["blank-navigation"]
        for value in (False, 1):
            with self.subTest(value=value):
                guarded["page"]["navigation"]["documentReplaced"] = value
                self.assertIn("guarded/blank-navigation: replacement document evidence differs",
                              classify(report, expect_retained_outcomes=True))
        guarded["page"]["navigation"]["documentReplaced"] = True
        guarded["previousDocumentPolicy"] = POLICY
        self.assertIn("guarded/blank-navigation: previous document response policy differs", classify(report))
        guarded["previousDocumentPolicy"] = ""
        guarded["requests"].remove("/before-blank")
        self.assertIn("guarded/blank-navigation: loader requests differ", classify(report, expect_retained_outcomes=True))

    def test_inherited_frames_require_the_child_url_and_parent_message_origin(self):
        self.assertEqual(classify(fixture("origin", "inherited"), expect_retained_outcomes=True), [])
        for field, value in (("url", "about:blank"), ("messageOrigin", "null"), ("secureContext", 1)):
            with self.subTest(field=field):
                report = fixture("origin", "inherited")
                report["samples"]["guarded"]["frames"]["srcdoc"]["page"]["starts"][0][field] = value
                self.assertIn("guarded/srcdoc: the executed document's URL scheme or origin differs",
                              classify(report, expect_retained_outcomes=True))

    def test_each_inherited_worker_control_requires_its_own_loader_receipt(self):
        report = fixture("origin", "inherited")
        report["samples"]["control"]["frames"]["blank"]["requests"].remove("/worker.js")
        self.assertIn("control: retained worker receipt counts differ", classify(report, expect_retained_outcomes=True))

    def test_explicit_origin_requires_the_guarded_document_origin_in_the_header(self):
        report = fixture("origin")
        self.assertEqual(classify(report, expect_retained_outcomes=True), [])
        report["samples"]["guarded"]["frames"]["same"]["policy"] = POLICY
        self.assertIn("guarded/same: parent response policy differs", classify(report))

    def test_retained_violations_require_a_boolean_trust_flag(self):
        cases = (
            ("data", "frameViolations", "guarded/data: an enforcing frame-src event was not observed"),
            ("same", "workerViolations", "guarded/same: the executed document's worker result or violation differs"),
        )
        for kind, field, expected in cases:
            with self.subTest(field=field):
                report = fixture()
                self.assertEqual(classify(report, expect_retained_outcomes=True), [])
                page = report["samples"]["guarded"]["frames"][kind]["page"]
                page[field][0]["trusted"] = 1
                self.assertIn(expected, classify(report, expect_retained_outcomes=True))

    def test_redacted_data_event_requires_its_own_parent_document(self):
        report = fixture()
        self.assertEqual(classify(report), [])
        guarded = report["samples"]["guarded"]["frames"]
        guarded["data"]["parentUrl"] = guarded["blob"]["parentUrl"]
        self.assertIn("guarded/data: the separate parent document differs", classify(report))

    def test_absence_of_a_child_requires_an_enforcing_frame_event(self):
        report = fixture()
        data = report["samples"]["guarded"]["frames"]["data"]["page"]
        data["frameViolations"] = []
        self.assertIn("guarded/data: an enforcing frame-src event was not observed", classify(report))

    def test_a_child_start_is_evidence_even_without_a_worker_result(self):
        report = fixture()
        blob = report["samples"]["guarded"]["frames"]["blob"]["page"]
        start = report["samples"]["guarded"]["frames"]["same"]["page"]["starts"][0]
        blob["starts"] = [dict(start, name="blob", protocol="blob:")]
        self.assertIn("guarded/blob: the executed document also reports a frame refusal", classify(report))

    def test_retained_verification_requires_the_observed_blob_refusal(self):
        for frame_source in ("self", "origin"):
            with self.subTest(frame_source=frame_source):
                report = fixture(frame_source)
                guarded = report["samples"]["guarded"]["frames"]
                same = guarded["same"]["page"]
                blob = guarded["blob"]["page"]
                blob.update(starts=[dict(same["starts"][0], name="blob", protocol="blob:")],
                            workers=same["workers"], workerViolations=same["workerViolations"],
                            frameViolations=[], trace=same["trace"])
                self.assertEqual(classify(report), [])
                self.assertIn("guarded/blob: retained frame refusal differs", classify(report, expect_retained_outcomes=True))

    def test_retained_verification_requires_each_control_worker_receipt(self):
        report = fixture()
        report["samples"]["control"]["frames"]["blob"]["requests"].remove("/worker.js")
        self.assertEqual(classify(report), [])
        self.assertIn("control: retained worker receipt counts differ", classify(report, expect_retained_outcomes=True))


def retained_report(run, frame_source="origin", document_set="inherited"):
    report = fixture(frame_source, document_set, run=run)
    digest = "a" * 64
    report.update(build={"sources": source_fingerprints(), "artifactSha256": digest}, installedArtifactSha256=digest)
    return report


class RetainedReportTests(unittest.TestCase):
    def setUp(self):
        self.first = retained_report("android-fixture-a")
        self.repeat = retained_report("android-fixture-b")

    def test_pair_accepts_independent_runs_and_rejects_a_duplicate_report(self):
        self.assertEqual(verify_pair(self.first, self.repeat, expect_retained_outcomes=True), [])
        duplicate = verify_pair(self.first, deepcopy(self.first), expect_retained_outcomes=True)
        self.assertIn("run tags are identical", duplicate)
        self.assertIn("profile names were reused across runs", duplicate)

    def test_retained_pair_requires_the_measured_inherited_capabilities(self):
        for mode, kind in (("control", "blank"), ("guarded", "srcdoc")):
            for field in ("secureContext", "serviceWorkerRegistration"):
                with self.subTest(mode=mode, kind=kind, field=field):
                    changed = deepcopy(self.repeat)
                    start = changed["samples"][mode]["frames"][kind]["page"]["starts"][0]
                    start[field] = not start[field]
                    self.assertEqual(verify_report(changed), [])
                    self.assertIn(f"repeat: {mode}/{kind}: inherited capability observations differ",
                                  verify_pair(self.first, changed, expect_retained_outcomes=True))

    def test_pair_rejects_a_reused_profile_with_a_different_run_tag(self):
        self.repeat["samples"]["control"]["profile"] = self.first["samples"]["control"]["profile"]
        self.assertIn("repeat: control: selected profile or cookie deny differs", verify_pair(self.first, self.repeat))

    def test_report_requires_a_valid_installed_apk_digest(self):
        for installed, built in (("", ""), ("g" * 64, "g" * 64), ("a" * 64, "b" * 64)):
            with self.subTest(installed=installed, built=built):
                report = deepcopy(self.repeat)
                report["installedArtifactSha256"] = installed
                report["build"]["artifactSha256"] = built
                self.assertIn("installed APK digest is missing or differs from the build", verify_report(report))

    def test_pair_requires_the_same_apk(self):
        self.repeat["installedArtifactSha256"] = self.repeat["build"]["artifactSha256"] = "b" * 64
        self.assertEqual(verify_report(self.repeat), [])
        self.assertIn("installed APK digests differ across runs", verify_pair(self.first, self.repeat))

    def test_pair_requires_the_same_execution_environment(self):
        for field, value in (("sdk", 38), ("release", "18"), ("provider", "146.0.0.0")):
            with self.subTest(field=field):
                changed = deepcopy(self.repeat)
                changed[field] = value
                self.assertEqual(verify_report(changed), [])
                self.assertIn("execution environments differ across runs", verify_pair(self.first, changed))

    def test_report_requires_sdk_os_and_webview_metadata(self):
        for field, value in (("sdk", True), ("release", " "), ("provider", None)):
            with self.subTest(field=field):
                changed = deepcopy(self.repeat)
                changed[field] = value
                self.assertIn("missing Android execution environment", verify_report(changed))

    def test_pair_requires_the_same_document_set_and_frame_source(self):
        local = retained_report("android-fixture-b", document_set="local")
        self_source = retained_report("android-fixture-b", frame_source="self")
        self.assertEqual(verify_report(local), [])
        self.assertEqual(verify_report(self_source), [])
        self.assertIn("document sets differ across runs", verify_pair(self.first, local))
        self.assertIn("frame sources differ across runs", verify_pair(self.first, self_source))
