"""Loopback-only HTTPS cookie fixture. Private keys and raw logs stay ignored."""
import argparse
import base64
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import ssl
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit

from verify import expected_cases

ROOT = Path(__file__).resolve().parent
CASES = {case["id"]: case for case in expected_cases()}
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "server.pem").exists(): return
    def openssl(*args):
        subprocess.run(["openssl", *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "7",
            "-subj", "/CN=Moonpool Owned Cookie Probe CA", "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "server.key", "-out", "server.csr", "-subj", "/CN=localhost")
    (folder / "server.ext").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n")
    openssl("x509", "-req", "-in", "server.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial", "-out", "server.pem", "-days", "7", "-extfile", "server.ext")
    for name in ("ca.key", "server.key"): (folder / name).chmod(0o600)


def make_server(folder, port):
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            parsed = urlsplit(self.path); query = parse_qs(parsed.query)
            if parsed.path not in ("/page", "/frame", "/resource", "/observe"):
                self.send_error(404); return
            run = query.get("run", [""])[0]; key = query.get("case", [""])[0]
            if not re.fullmatch(r"[a-z0-9-]+", run) or key not in CASES:
                self.send_error(400); return
            case = CASES[key]; marker = case["owner"] + "_" + case["stage"]
            entry = {"run": run, "case": key, "path": parsed.path, "cookie": self.headers.get("Cookie", ""), "tls": isinstance(self.connection, ssl.SSLSocket)}
            with lock:
                with (folder / "requests.jsonl").open("a") as out: out.write(json.dumps(entry) + "\n")
            self.send_response(200); self.send_header("Cache-Control", "no-store")
            names = {"/page": "server", "/frame": "frameHeader", "/resource": "resource"}
            if parsed.path in names:
                self.send_header("Set-Cookie", f"t28_{names[parsed.path]}={marker}; Path=/; Secure; Max-Age=86400; SameSite=Lax")
            if parsed.path == "/page": body=(ROOT / "page.html").read_bytes(); mime="text/html"
            elif parsed.path == "/frame": body=b"<!doctype html><p>cookie-frame-ready</p>"; mime="text/html"
            elif parsed.path == "/resource": body=GIF; mime="image/gif"
            else: body=b'{"ok":true}'; mime="application/json"
            self.send_header("Content-Type", mime); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(folder / "server.pem", folder / "server.key")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(); folder=ROOT / "local-results/tls"
    create_certificates(folder); server=make_server(folder,args.port)
    digest=hashlib.sha256(json.dumps(expected_cases(),sort_keys=True).encode()).hexdigest()
    (ROOT / "local-results/server.json").write_text(json.dumps({"port": server.server_port,"casesSha256":digest}) + "\n")
    print(f"Owned HTTPS fixture: https://localhost:{server.server_port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
