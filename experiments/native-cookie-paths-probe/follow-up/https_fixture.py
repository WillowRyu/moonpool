"""Owned HTTPS receipts for the C09 static-resource and retained-worker checks."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import ssl
import sys
import threading
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parent
TLS_DIR = ROOT / "local-results/tls"
sys.path.insert(0, str(ROOT.parent))
from server import PIXEL, certificates


def make_server(folder, *, tls=True):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def respond(self, status, mime, body=b"", **headers):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            for key, value in headers.items():
                self.send_header(key.replace("_", "-"), value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            run = query.get("run", [""])[0]
            case = query.get("case", [""])[0]
            if not re.fullmatch("[a-z0-9-]+", run) or not re.fullmatch("[a-z0-9-]+", case):
                self.respond(400, "text/plain")
                return
            receipt = {
                "run": run, "case": case, "path": url.path, "method": self.command,
                "host": self.headers.get("Host", "").split(":")[0],
                "cookie": self.headers.get("Cookie", ""), "authorization": self.headers.get("Authorization"),
                "tls": isinstance(self.connection, ssl.SSLSocket),
            }
            with lock, (folder / "receipts.jsonl").open("a") as file:
                file.write(json.dumps(receipt) + "\n")
            tags = urlencode({"run": run, "case": case})
            redirects = {
                "/static/redirect-approved": "/static/final.gif",
                "/static/redirect-path": "/denied",
                "/static/redirect-other": f"https://127.0.0.1:{self.server.server_port}/static/final.gif",
                "/static/redirect-encoded": "/static/%66inal.gif",
            }
            if target := redirects.get(url.path):
                self.respond(302, "text/plain", Location=f"{target}?{tags}",
                             Set_Cookie="c09_hop=public; Secure; Path=/")
            elif url.path in ("/static/direct.gif", "/static/final.gif"):
                self.respond(200, "image/gif", PIXEL, Set_Cookie="c09_remote=public; Secure; Path=/")
            elif url.path == "/worker-network":
                self.respond(200, "text/plain", b"Public worker witness")
            else:
                self.respond(403, "text/plain")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / "server.pem", folder / "server.key")
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


def main():
    certificates(TLS_DIR)
    with make_server(TLS_DIR) as server:
        (ROOT / "local-results/server.json").write_text(json.dumps({"port": server.server_port}) + "\n")
        print(f"Owned C09 follow-up fixture listening on {server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
