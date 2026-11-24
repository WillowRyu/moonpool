from copy import deepcopy
import unittest

from check import CASES, classify, origin, partition


def reference_report(run="android-sample"):
    seed = []
    for case in ("used", "root", "offpath"):
        url = origin(run, case)
        marker = {"origin": url, "data": run, "scope": None}
        if case in ("root", "offpath"):
            marker["scope"] = url + ("/" if case == "root" else "/outside/")
        seed.append({"case": case, "profile": partition(run, case), "seed": marker})
    checks = []
    for index, case in enumerate(CASES, 1):
        key = "used" if case == "opaque" else case
        url = origin(run, key)
        worker = case in ("root", "offpath")
        probe = {
            "source": "host", "origin": "null" if case == "opaque" else url,
            "api": case != "opaque", "controller": None,
            "scopes": [url + ("/" if case == "root" else "/outside/")] if worker else [],
            "data": run if key != "fresh" and case != "opaque" else None,
            "contextOrigin": "null" if case == "opaque" else url,
        }
        check = {
            "run": run, "case": case, "profile": partition(run, key),
            "pid": index + 100, "phase": "check", "complete": True,
            "profilePresent": key != "fresh", "policy": {"cookieDeny": True, "workerNetworkBlocked": True,
                                                        "browserNetworkBlocked": True},
            "cookiePresent": False, "proof": probe, "nonceMatches": True, "inspectionRequests": [],
            "events": ["policy", "inspect", "verdict", "refuse" if worker or case == "opaque" else "guest"],
            "verdict": "present" if worker else ("unknown" if case == "opaque" else "empty"),
            "guestLoads": 0 if worker or case == "opaque" else 1,
            "guest": None if worker or case == "opaque" else {"marker": "guest", "origin": url},
            "diagnostic": {"title": "c09-worker", "pageScriptsEnabled": False} if worker else None,
        }
        checks.append(check)
    return {"run": run, "seed": {"run": run, "phase": "seed", "pid": 90, "complete": True, "profiles": seed},
            "checks": checks}


class EvidenceTests(unittest.TestCase):
    def test_distinguishes_both_worker_scopes_and_clean_stores(self):
        self.assertEqual(classify(reference_report()), [])

    def test_a_profile_opened_by_a_previous_process_is_required(self):
        report = reference_report()
        root = next(row for row in report["checks"] if row["case"] == "root")
        root["profilePresent"] = False
        root["pid"] = report["seed"]["pid"]
        errors = classify(report)
        self.assertTrue(any("process" in error for error in errors))
        self.assertTrue(any("profile" in error for error in errors))

    def test_a_page_without_a_controller_can_still_have_a_worker(self):
        report = reference_report()
        row = next(item for item in report["checks"] if item["case"] == "offpath")
        self.assertIsNone(row["proof"]["controller"])
        row["proof"]["scopes"] = []
        row["verdict"] = "empty"
        self.assertTrue(any("offpath" in error for error in classify(report)))

    def test_a_claim_from_a_worker_response_is_not_native_evidence(self):
        report = reference_report()
        root = next(row for row in report["checks"] if row["case"] == "root")
        root["proof"] = deepcopy(root["diagnostic"])
        root["nonceMatches"] = False
        root["verdict"] = "empty"
        self.assertTrue(any("root" in error for error in classify(report)))

    def test_an_unknown_origin_cannot_start_a_guest(self):
        report = reference_report()
        opaque = next(item for item in report["checks"] if item["case"] == "opaque")
        opaque["guestLoads"] = 1
        self.assertTrue(any("opaque" in error and "guest" in error for error in classify(report)))

    def test_a_request_for_the_inspection_document_is_detected(self):
        report = reference_report()
        report["checks"][0]["inspectionRequests"] = ["/entry"]
        self.assertTrue(any("inspection" in error for error in classify(report)))

    def test_the_policy_has_to_precede_the_inspection(self):
        report = reference_report()
        report["checks"][0]["events"] = ["inspect", "policy", "verdict", "refuse"]
        self.assertTrue(any("order" in error for error in classify(report)))

    def test_storage_marker_is_verified_in_existing_clean_profile(self):
        report = reference_report()
        next(row for row in report["checks"] if row["case"] == "used")["proof"]["data"] = None
        self.assertTrue(any("used" in error and "data" in error for error in classify(report)))

    def test_inherited_context_has_to_report_the_exact_origin(self):
        report = reference_report()
        used = next(row for row in report["checks"] if row["case"] == "used")
        used["proof"]["contextOrigin"] = "null"
        self.assertTrue(any("used" in error and "origin" in error for error in classify(report)))

    def test_unavailable_inventory_can_be_measured_without_granting_admission(self):
        report = reference_report()
        for row in report["checks"]:
            row.update(verdict="unknown", guestLoads=0, guest=None, events=["policy", "inspect", "verdict", "refuse"])
            if row["case"] != "opaque":
                proof = row["proof"]
                proof["inline"] = {
                    "contextOrigin": proof["origin"], "api": True,
                    "error": "InvalidStateError: The document is in an invalid state.", "scopes": [],
                }
                proof["frame"] = deepcopy(proof["inline"])
                proof.update(error=proof["inline"]["error"], scopes=[])
        self.assertEqual(classify(report, expect_unavailable=True), [])
        self.assertNotEqual(classify(report), [])
        report["checks"][0]["guestLoads"] = 1
        self.assertTrue(any("guest" in error for error in classify(report, expect_unavailable=True)))


if __name__ == "__main__":
    unittest.main()
