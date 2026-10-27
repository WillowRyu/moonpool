"""Exercise public HTTP responses without a simulator or fixed listening port."""

from contextlib import contextmanager, redirect_stdout
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import json
import unittest

EXPERIMENTS = Path(__file__).resolve().parents[1]


def load_fixture(platform):
    spec = spec_from_file_location(f"{platform}_fixture", EXPERIMENTS / f"{platform}-origin-probe/fixture_server.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def running(module, logical_port):
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Fixture)
    port = server.server_address[1]
    # Keep the fixture's port-based A/B role while binding a free test socket.
    server.server_port = logical_port
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def get(port, path, host="localhost:8878", origin=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=3)
    headers = {"Host": host}
    if origin is not None:
        headers["Origin"] = origin
    with redirect_stdout(StringIO()):
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


class LoopbackControls(unittest.TestCase):
    def test_both_platforms_reflect_only_the_explicit_cors_control(self):
        for platform in ["android", "ios"]:
            with self.subTest(platform=platform), running(load_fixture(platform), 8877) as port:
                status, headers, body = get(port, "/cors", origin="moonpool://")
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("Cache-Control"), "no-store")
                self.assertEqual(int(headers["Content-Length"]), len(body))
                self.assertEqual(headers.get("Access-Control-Allow-Origin"), "moonpool://")
                self.assertEqual(json.loads(body)["originHeader"], "moonpool://")
                self.assertNotIn("Access-Control-Allow-Origin", get(port, "/no-cors", origin="null")[1])

    def test_absent_and_opaque_origin_remain_distinct(self):
        for platform in ["android", "ios"]:
            with self.subTest(platform=platform), running(load_fixture(platform), 8877) as port:
                self.assertEqual(json.loads(get(port, "/cors")[2])["originHeader"], None)
                self.assertEqual(get(port, "/cors")[1].get("Access-Control-Allow-Origin"), "*")
                self.assertEqual(get(port, "/cors", origin="null")[1].get("Access-Control-Allow-Origin"), "null")

    def test_external_control_uses_the_correct_platform_report_name(self):
        for platform, name in [("android", "t23Report"), ("ios", "t24Report")]:
            with self.subTest(platform=platform), running(load_fixture(platform), 8877) as port:
                status, headers, body = get(port, "/external")
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["Content-Type"])
                self.assertIn(f"window.{name}=".encode(), body)


class IOSBundledResources(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixtures = self.root / "fixtures"
        for group in ["apps/a", "apps/b", "common"]:
            (self.fixtures / group).mkdir(parents=True)
        (self.fixtures / "apps/a/data.json").write_text('{"publicMarker":"a"}')
        (self.fixtures / "apps/b/data.json").write_text('{"publicMarker":"b"}')
        (self.fixtures / "common/probe.js").write_text("window.publicMarker = true;")
        self.secret = self.root / "outside.json"
        self.secret.write_text('{"privateMarker":"must-not-be-served"}')
        self.module = load_fixture("ios")
        self.module.fixtures = self.fixtures

    def test_a_b_and_shared_resources_load_with_their_declared_mime(self):
        for logical_port, host, app in [(8878, "localhost:8878", "a"), (8879, "127.0.0.1:8879", "b")]:
            with self.subTest(app=app), running(self.module, logical_port) as port:
                status, headers, body = get(port, "/assets/data.json?seed=true", host)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["publicMarker"], app)
                self.assertIn("application/json", headers["Content-Type"])
                self.assertIn("text/javascript", get(port, "/assets/probe.js", host)[1]["Content-Type"])

    def test_missing_wrong_host_and_parent_paths_fail_without_private_bytes(self):
        with running(self.module, 8878) as port:
            for path, host in [("/assets/missing.json", "localhost:8878"), ("/assets/../outside.json", "localhost:8878"),
                               ("/assets/%2e%2e/outside.json", "localhost:8878"), ("/assets/data.json", "wrong.test:8878")]:
                with self.subTest(path=path, host=host):
                    status, _, body = get(port, path, host)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b"privateMarker", body)

    def test_absolute_and_encoded_absolute_resource_paths_cannot_escape(self):
        with running(self.module, 8878) as port:
            for path in ["/assets/" + str(self.secret), "/assets/%2f" + str(self.secret).lstrip("/")]:
                with self.subTest(path=path):
                    status, _, body = get(port, path)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b"privateMarker", body)

    def test_app_symlink_cannot_read_another_app_or_outside_the_fixture(self):
        for name, target in [("outside-link.json", self.secret), ("other-app.json", self.fixtures / "apps/b/data.json")]:
            (self.fixtures / "apps/a" / name).symlink_to(target)
        with running(self.module, 8878) as port:
            for name in ["outside-link.json", "other-app.json"]:
                with self.subTest(name=name):
                    status, _, body = get(port, "/assets/" + name)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b"privateMarker", body)

    def test_symlink_inside_the_same_app_root_remains_a_valid_asset(self):
        (self.fixtures / "apps/a/alias.json").symlink_to(self.fixtures / "apps/a/data.json")
        with running(self.module, 8878) as port:
            status, _, body = get(port, "/assets/alias.json")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["publicMarker"], "a")

    def test_shared_resource_symlink_cannot_escape_its_own_root(self):
        script = self.fixtures / "common/probe.js"
        script.unlink()
        script.symlink_to(self.secret)
        with running(self.module, 8878) as port:
            status, _, body = get(port, "/assets/probe.js")
            self.assertEqual(status, 404)
            self.assertNotIn(b"privateMarker", body)


if __name__ == "__main__":
    unittest.main()
