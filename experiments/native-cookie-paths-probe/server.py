"""Loopback receipts for fixed public browser-cookie probes."""

import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import ssl
import sys
import threading
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parent
TLS_DIR = ROOT / "local-results/tls"
PIXEL = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def certificates(folder):
    # Reuse the earlier probe's localhost-only CA generator against a new directory.
    sys.path.insert(0, str(ROOT.parent / "native-cookie-admission-probe"))
    from fixture import create_certificates

    create_certificates(folder)


def make_server(folder, port=0, *, tls=True):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, mime, body, headers=()):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def handle_path(self):
            url = urlsplit(self.path)
            params = {key: values[0] for key, values in parse_qs(url.query).items()}
            run, view = params.get("run", ""), params.get("view", "")
            if not re.fullmatch("[a-z0-9-]+", run) or not re.fullmatch("[A-Za-z0-9-]+", view):
                self.respond(400, "text/plain", b"Invalid test tag")
                return
            if self.headers.get("Content-Length"):
                self.rfile.read(int(self.headers["Content-Length"]))
            row = {
                "run": run, "view": view, "path": url.path, "surface": params.get("surface", ""),
                "host": self.headers.get("Host", "").split(":")[0],
                "cookie": self.headers.get("Cookie", ""), "method": self.command,
                "tls": isinstance(self.connection, ssl.SSLSocket),
            }
            with lock, (folder / "receipts.jsonl").open("a") as log:
                log.write(json.dumps(row) + "\n")

            if url.path in ("/control", "/echo"):
                self.control(url.path, view, run)
            elif url.path in ("/static/seed.gif", "/static/echo.gif"):
                headers = [("Set-Cookie", "c09_asset=1; Path=/; Secure; SameSite=None")] if "seed" in url.path else []
                self.respond(200, "image/gif", PIXEL, headers)
            elif url.path in ("/static/redirect-other", "/static/redirect-same"):
                route = url.path.rsplit("/", 1)[1]
                host = "127.0.0.1" if route == "redirect-other" else "localhost"
                query = urlencode({"run": run, "view": view, "surface": route})
                target = f"https://{host}:{self.server.server_port}/denied?{query}"
                self.respond(302, "text/plain", b"", [("Location", target)])
            else:
                self.respond(403, "text/plain", b"Denied fixture endpoint")

        def control(self, path, view, run):
            role = view.split("-", 1)[0]
            headers = []
            if path == "/control" and view.endswith("-before") and role in ("H", "U", "B"):
                marker = run if role == "H" else "public"
                headers.append(("Set-Cookie", f"c09_{role.lower()}={marker}; Path=/; Secure; SameSite=Lax"))
                if role == "B":
                    headers.append(("Set-Cookie", "c09_hidden=public; Path=/; Secure; HttpOnly; SameSite=Lax"))
            body = (b"<!doctype html><meta charset=utf-8><script>"
                    b"window.c09Control={href:location.href,cookie:document.cookie};</script>")
            self.respond(200, "text/html; charset=utf-8", body, headers)

        do_GET = do_POST = do_OPTIONS = handle_path

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / "server.pem", folder / "server.key")
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    certificates(TLS_DIR)
    with make_server(TLS_DIR, args.port) as server:
        (ROOT / "local-results/server.json").write_text(
            json.dumps({"port": server.server_port}) + "\n"
        )
        print(f"Owned C09 fixture listening on {server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
