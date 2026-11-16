import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from server import make_server
from verify import classify


class FixtureTest(unittest.TestCase):
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

    def request(self, path, *, method="GET", cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request(method, path, headers={"Cookie": cookie} if cookie else {})
            response = conn.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            conn.close()

    def test_server_witnesses_forbidden_attempts_even_when_they_fail(self):
        target = "/denied?run=test&view=initial&surface=beacon"
        status, _, _ = self.request(target, method="POST", cookie="unexpected=1")
        self.assertEqual(status, 403)
        row = json.loads((self.folder / "receipts.jsonl").read_text())
        self.assertEqual((row["path"], row["surface"], row["cookie"], row["method"]),
                         ("/denied", "beacon", "unexpected=1", "POST"))

    def test_allowed_image_sets_an_engine_cookie_for_the_browser_to_reject(self):
        status, headers, body = self.request("/static/seed.gif?run=test&view=initial")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"GIF"))
        self.assertIn(("Set-Cookie", "c09_asset=1; Path=/; Secure; SameSite=None"), headers)

    def test_redirects_reach_independently_witnessed_denied_targets(self):
        for path, host in (("redirect-other", "127.0.0.1"), ("redirect-same", "localhost")):
            status, headers, _ = self.request(f"/static/{path}?run=test&view=initial")
            self.assertEqual(status, 302)
            self.assertEqual(
                dict(headers)["Location"],
                f"https://{host}:{self.server.server_port}/denied?run=test&view=initial&surface={path}",
            )


def reference_report():
    run = "android-example"
    report = {
        "platform": "android", "run": run, "complete": True, "errors": [],
        "partitions": {"A": "store-A", "B": "store-B", "H": "store-H", "U": "store-U"},
        "controls": [], "samples": [], "receipts": [],
    }

    def receipt(path, view, cookie="", **extra):
        report["receipts"].append({
            "run": run, "path": path, "view": view, "surface": "", "host": "localhost",
            "cookie": cookie, "tls": True, **extra,
        })

    for stage, roles in (("before", "HUB"), ("after-A", "HUB"), ("after-B", "HU")):
        for role in roles:
            view = f"{role}-{stage}"
            cookie = f"c09_{role.lower()}=" + (run if role == "H" else "public")
            report["controls"].append({"view": view, "cookie": cookie, "policyAllows": True})
            network_cookie = cookie + ("; c09_hidden=public" if role == "B" else "")
            receipt("/control", view, "" if stage == "before" else network_cookie)
            if stage == "before":
                receipt("/echo", view, network_cookie)

    for view in ("initial", "reload", "recreated"):
        report["samples"].append({
            "view": view, "partition": "store-A", "events": ["policyComplete", "policyRead", "presence", "load", "script"],
            "policyAllows": False, "presence": "empty", "loadCalls": 1, "guestResources": 1,
            "afterPresent": False, "popupDenials": 0,
            "guest": {
                "view": view, "origin": f"https://mp-{run}-a.invalid",
                "first": {"direct": "", "prototype": ""},
                "afterWrite": {"direct": "", "prototype": ""}, "last": {"direct": "", "prototype": ""},
                "frame": {"direct": "", "prototype": ""},
                "storage": {"local": run, "indexed": run, "previousLocal": None if view == "initial" else run,
                            "previousIndexed": None if view == "initial" else run},
                "resources": {"local": "loaded", "seed": "loaded", "echo": "loaded"},
                "attempts": {"fetch": "rejected", "xhr": "rejected", "beacon": "queued",
                             "socket": "rejected", "events": "rejected", "form": "attempted",
                             "frame": "attempted", "popup": "blocked", "worker": "rejected",
                             "redirect-other": "rejected", "redirect-same": "rejected"},
                "violations": ["connect-src", "form-action", "frame-src", "worker-src", "img-src"],
                "serviceWorker": "unsupported",
            },
        })
        for path in ("seed.gif", "echo.gif", "redirect-other", "redirect-same"):
            receipt("/static/" + path, view)
    report["samples"].append({
        "view": "present", "partition": "store-B", "events": ["policyComplete", "policyRead", "presence", "refuse"],
        "policyAllows": False, "presence": "present", "loadCalls": 0, "guestResources": 0,
        "guest": None, "afterPresent": True, "beforeCookies": ["c09_b=public", "c09_hidden=public"],
        "afterCookies": ["c09_b=public", "c09_hidden=public"],
    })
    report["samples"].append({
        "view": "unknown", "partition": "store-A",
        "events": ["policyComplete", "policyRead", "presence", "refuse"],
        "policyAllows": False, "presence": "unknown", "source": "injected",
        "loadCalls": 0, "guestResources": 0, "guest": None,
    })
    return report


class EvidenceTest(unittest.TestCase):
    def test_reference_evidence(self):
        self.assertEqual(classify(reference_report()), [])

    def test_load_before_policy_fails(self):
        report = reference_report()
        report["samples"][0]["events"] = ["load", "policyComplete", "policyRead", "presence", "script"]
        self.assertTrue(any("order" in problem for problem in classify(report)))

    def test_http_only_store_must_never_reach_the_guest_loader(self):
        report = reference_report()
        report["samples"][-2]["guestResources"] = 1
        self.assertTrue(any("present" in problem for problem in classify(report)))

    def test_cookie_policy_isolation_needs_the_host_send_control(self):
        report = reference_report()
        next(row for row in report["receipts"] if row["view"] == "H-after-B")["cookie"] = ""
        self.assertTrue(any("H-after-B" in problem for problem in classify(report)))

    def test_a_browser_error_does_not_hide_a_request_at_the_server(self):
        report = reference_report()
        report["receipts"].append({
            **copy.copy(report["receipts"][0]), "path": "/denied", "view": "reload", "surface": "fetch",
        })
        self.assertTrue(any("fetch" in problem for problem in classify(report)))

    def test_missing_allowed_receipt_is_a_failure(self):
        report = reference_report()
        report["receipts"] = [row for row in report["receipts"] if row["path"] != "/static/echo.gif"]
        self.assertTrue(any("echo.gif" in problem for problem in classify(report)))

    def test_recreated_view_preserves_indexeddb(self):
        report = reference_report()
        report["samples"][2]["guest"]["storage"]["previousIndexed"] = None
        self.assertTrue(any("recreated" in problem for problem in classify(report)))

    def test_recreated_view_must_use_the_same_origin(self):
        report = reference_report()
        report["samples"][2]["guest"]["origin"] = "https://mp-other-a.invalid"
        self.assertTrue(any("origin" in problem for problem in classify(report)))

    def test_window_proxy_requires_a_witness_that_the_host_refused_the_popup(self):
        report = reference_report()
        report["samples"][0]["guest"]["attempts"]["popup"] = "opened"
        self.assertTrue(any("popup" in problem for problem in classify(report)))
        report["samples"][0]["popupDenials"] = 1
        self.assertEqual(classify(report), [])


if __name__ == "__main__":
    unittest.main()
