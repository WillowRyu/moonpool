from copy import deepcopy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from check import classify
from https_fixture import make_server


class RedirectFixtureTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self.scratch.name)
        self.server = make_server(self.folder, tls=False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.scratch.cleanup()

    def request(self, route):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            c.request("GET", route)
            response = c.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            c.close()

    def test_allowed_redirect_preserves_the_run_and_case(self):
        status, headers, _ = self.request("/static/redirect-approved?run=test&case=approved")
        self.assertEqual((status, headers["Location"]), (302, "/static/final.gif?run=test&case=approved"))

    def test_forbidden_targets_are_recorded_at_the_server(self):
        status, _, _ = self.request("/denied?run=test&case=path")
        self.assertEqual(status, 403)
        receipt = json.loads((self.folder / "receipts.jsonl").read_text())
        self.assertEqual((receipt["path"], receipt["case"]), ("/denied", "path"))

    def test_image_sets_an_engine_cookie_for_the_loader_to_discard(self):
        status, headers, body = self.request("/static/direct.gif?run=test&case=direct")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Set-Cookie"], "c09_remote=public; Secure; Path=/")
        self.assertTrue(body.startswith(b"GIF"))

    def test_fixture_keeps_http_1_1_connection_framing_across_hops(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request("GET", "/static/redirect-approved?run=test&case=approved")
            redirect = conn.getresponse()
            redirect.read()
            self.assertEqual(redirect.version, 11)
            first_socket = conn.sock
            conn.request("GET", redirect.getheader("Location"))
            final = conn.getresponse()
            self.assertEqual(final.status, 200)
            self.assertTrue(final.read().startswith(b"GIF"))
            self.assertIs(conn.sock, first_socket)
        finally:
            conn.close()


def reference_report(platform="android"):
    run = platform + "-test"
    origin = "https://mp-" + run + ".invalid" if platform == "android" else "moonpool://com.example.paths." + run
    report = {
        "platform": platform, "run": run, "complete": True, "errors": [],
        "admission": {"policyDisallowed": True, "empty": True, "afterEmpty": True},
        "guest": {"origin": origin, "cookie": "", "images": {
            "direct": "loaded", "approved": "loaded", "path": "blocked", "other": "blocked", "encoded": "blocked",
        }, "serviceWorker": platform == "android"},
        "worker": {
            "state": "retained", "registered": True, "scope": origin + "/worker/",
            "seedViewDestroyed": True, "networkBlocked": True, "retainedRegistration": True,
            "entry": "cached-worker", "loaderEntries": 0, "workerFetch": "blocked",
            "admission": "refused", "guestLoads": 0,
        } if platform == "android" else {"state": "unsupported"},
        "receipts": [],
    }
    if platform == "ios":
        report["admission"]["sources"] = {"records": False, "cookies": False}
    routes = {
        "direct": ["/static/direct.gif"],
        "approved": ["/static/redirect-approved", "/static/final.gif"],
        "path": ["/static/redirect-path"],
        "other": ["/static/redirect-other"],
        "encoded": ["/static/redirect-encoded"],
    }
    for case, paths in routes.items():
        for path in paths:
            report["receipts"].append({"run": run, "case": case, "path": path, "host": "localhost",
                                       "cookie": "", "authorization": None, "method": "GET", "tls": True})
    if platform == "android":
        report["receipts"].append({**report["receipts"][0], "case": "worker-control", "path": "/worker-network"})
    return report


class EvidenceTests(unittest.TestCase):
    def test_supported_and_unsupported_worker_platforms_are_distinguished(self):
        self.assertEqual(classify(reference_report()), [])
        self.assertEqual(classify(reference_report("ios")), [])

    def test_browser_error_cannot_hide_a_forbidden_hop(self):
        report = reference_report()
        report["receipts"].append({**report["receipts"][0], "case": "path", "path": "/denied"})
        self.assertTrue(any("path" in problem for problem in classify(report)))

    def test_approved_redirect_must_reach_its_final_resource(self):
        report = reference_report()
        report["receipts"] = [row for row in report["receipts"] if row["path"] != "/static/final.gif"]
        self.assertTrue(any("approved" in problem for problem in classify(report)))

    def test_allowed_request_cannot_have_ambient_cookies(self):
        report = reference_report()
        report["receipts"][0]["cookie"] = "c09_remote=public"
        self.assertTrue(any("credentials" in problem for problem in classify(report)))

    def test_worker_requires_a_real_retained_registration(self):
        report = reference_report()
        report["worker"]["retainedRegistration"] = False
        self.assertTrue(any("worker" in problem for problem in classify(report)))

    def test_refusal_cannot_load_a_guest(self):
        report = reference_report()
        report["worker"]["guestLoads"] = 1
        self.assertTrue(any("guest" in problem for problem in classify(report)))

    def test_ios_cannot_claim_unsupported_after_exposing_the_api(self):
        report = deepcopy(reference_report("ios"))
        report["guest"]["serviceWorker"] = True
        self.assertTrue(any("worker" in problem for problem in classify(report)))


if __name__ == "__main__":
    unittest.main()
