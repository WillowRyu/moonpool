"""Public loopback origin/CORS controls; reads only the built probe fixtures."""

from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from probe_support.loopback import LoopbackFixture

fixtures = Path(__file__).resolve().parent / "build/OriginProbe.app/Fixtures"


class Fixture(LoopbackFixture):
    report_name = "t24Report"
    charset = "utf-8"

    def asset_root(self):
        return fixtures


if __name__ == "__main__":
    servers = [ThreadingHTTPServer(("127.0.0.1", port), Fixture) for port in [8877, 8878, 8879]]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        for server in servers:
            server.shutdown()
