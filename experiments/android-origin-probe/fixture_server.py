"""Loopback-only public CORS/navigation controls for T23. No credentials."""

from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from probe_support.loopback import LoopbackFixture


class Fixture(LoopbackFixture):
    report_name = "t23Report"


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8877), Fixture).serve_forever()
