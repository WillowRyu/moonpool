"""Test the evidence oracle before collecting native observations."""
import copy
import unittest

from verify import assess, verify, expected_cases


def fixture(platform="android"):
    samples, requests = [], []
    for case in expected_cases():
        blocked = case["blocked"]
        visible = not blocked and (case["kind"] == "remote" or platform == "android")
        marker = case["owner"] + "_" + case["stage"]
        names = ("js", "proto", "frame", "server", "resource", "frameHeader") if case["kind"] == "remote" else ("js", "proto", "frame")
        cookie = "; ".join(f"t28_{name}={marker}" for name in names) if visible else ""
        sample = {**case, "policyAllows": not blocked, "actualPartition": case["owner"],
                  "document": {"case": case["id"], "cookie": cookie, "prototypeRead": cookie,
                               "frameRead": cookie, "frameLoaded": True, "complete": True,
                               "remoteObserved": case["kind"] == "remote", "secureContext": case["kind"] == "remote" or platform == "android"},
                  "nativeCookieValues": [marker] if visible else ([] if case['stage']=='fresh-blocked' else [case["owner"] + "_baseline"]),
                  "policyBeforeLoad": True, "loadErrors": []}
        samples.append(sample)
        if case["kind"] == "remote":
            for path in ("/page", "/frame", "/resource", "/observe"):
                requests.append({"case": case["id"], "path": path,
                                 "cookie": cookie if path != "/page" else "",
                                 "tls": True})
    return {"platform": platform, "complete": True, "samples": samples, "requests": requests}


class EvidenceTests(unittest.TestCase):
    def test_valid_evidence_can_report_contract_failure(self):
        report=fixture('ios')
        sample=next(s for s in report['samples'] if s['id']=='a-blocked-a1-remote')
        sample['document']['cookie']='t28_js=a_baseline'
        result=assess(report)
        self.assertFalse(result['contractPass'])
        self.assertIn('a-blocked-a1-remote: raw cookie access cookie',result['violations'])
        with self.assertRaises(AssertionError): verify(report)

    def test_fresh_disallowed_stores_have_paired_controls(self):
        fresh = [c for c in expected_cases() if c["stage"] == "fresh-blocked"]
        self.assertEqual({c["view"] for c in fresh}, {"a1", "a2", "b", "h", "u"})
        self.assertEqual(len(fresh), 10)

    def test_complete_paired_controls(self):
        for platform in ("android", "ios"):
            self.assertGreater(verify(fixture(platform)), 100)

    def test_missing_host_control_is_not_isolation(self):
        report = fixture()
        report["samples"] = [s for s in report["samples"] if s["owner"] != "h"]
        with self.assertRaises(AssertionError): verify(report)

    def test_global_cookie_switch_fails_control(self):
        report = fixture()
        sample = next(s for s in report["samples"] if s["id"] == "a-blocked-h-remote")
        sample["policyAllows"] = False
        with self.assertRaises(AssertionError): verify(report)

    def test_empty_js_does_not_hide_outgoing_cookie(self):
        report = fixture()
        row = next(r for r in report["requests"] if r["case"] == "a-blocked-a1-remote")
        row["cookie"] = "t28_server=a_baseline"
        with self.assertRaises(AssertionError): verify(report)

    def test_native_mutation_is_not_hidden_by_empty_js(self):
        report = fixture()
        sample = next(s for s in report["samples"] if s["id"] == "a-blocked-a2-remote")
        sample["nativeCookieValues"].append("a_a-blocked")
        with self.assertRaises(AssertionError): verify(report)

    def test_unloaded_frame_does_not_pass(self):
        report = fixture("ios")
        report["samples"][0]["document"]["frameLoaded"] = False
        with self.assertRaises(AssertionError): verify(report)

    def test_server_positive_control_required(self):
        report = fixture()
        row = next(r for r in report["requests"] if r["case"] == "baseline-h-remote" and r["path"] == "/observe")
        row["cookie"] = ""
        with self.assertRaises(AssertionError): verify(report)

    def test_partition_and_case_correspondence(self):
        report = fixture()
        report["samples"][0]["actualPartition"] = "b"
        with self.assertRaises(AssertionError): verify(report)
        report = fixture()
        report["samples"].append(copy.deepcopy(report["samples"][0]))
        with self.assertRaises(AssertionError): verify(report)


if __name__ == "__main__": unittest.main()
