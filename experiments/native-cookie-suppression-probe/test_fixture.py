"""Exercise actual TLS requests and server receipt, without a native device."""
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from fixture import make_server, create_certificates


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        create_certificates(cls.root)
        cls.server = make_server(cls.root, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"https://localhost:{cls.server.server_port}"
        cls.context = ssl.create_default_context(cafile=str(cls.root / "ca.pem"))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()

    def get(self, path, cookie=None):
        request = urllib.request.Request(self.base + path, headers={"Cookie": cookie} if cookie else {})
        return urllib.request.urlopen(request, context=self.context, timeout=5)

    def test_https_page_sets_public_marker_and_serves_fixture(self):
        with self.get("/page?run=test&case=baseline-a1-remote") as response:
            self.assertIn("t28_server=a_baseline", response.headers["Set-Cookie"])
            self.assertIn(b"cookieProbe", response.read())

    def test_server_retains_received_cookie_without_echo_to_guest(self):
        with self.get("/observe?run=test&case=baseline-h-remote", "t28_public=sentinel") as response:
            self.assertEqual(json.load(response), {"ok": True})
        rows = [json.loads(line) for line in (self.root / "requests.jsonl").read_text().splitlines()]
        self.assertTrue(any(r["cookie"] == "t28_public=sentinel" for r in rows))

    def test_unknown_case_and_control_path_rejected(self):
        for path in ("/page?run=test&case=unknown", "/control", "/../ca.key"):
            with self.assertRaises(urllib.error.HTTPError) as result: self.get(path)
            self.assertIn(result.exception.code, (400, 404))

    def test_unknown_ca_rejected(self):
        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen(self.base + "/page?run=test&case=baseline-a1-remote", timeout=5)


if __name__ == "__main__": unittest.main()
