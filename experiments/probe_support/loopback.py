"""Public loopback controls and confined assets, exercised through HTTP tests."""

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json


@dataclass
class Response:
    body: bytes
    mime: str = "application/json"
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


def control_response(path, origin, report_name):
    if path == "/external":
        body = f'''<!doctype html><h1>Public external-origin control</h1>
<script>window.{report_name}={{external:true,origin:location.origin,href:location.href}};</script>'''
        return Response(body.encode(), "text/html")
    headers = {"Access-Control-Allow-Origin": origin or "*"} if path == "/cors" else {}
    return Response(
        json.dumps({"publicMarker": "loopback-control", "originHeader": origin}).encode(),
        headers=headers,
    )


def bundled_response(fixtures: Path, port: int, host: str, path: str):
    role = {8878: ("a", "localhost:8878"), 8879: ("b", "127.0.0.1:8879")}.get(port)
    if role is None:
        return Response(b"Unknown app or outside package", status=404)
    app, expected_host = role
    relative = path.removeprefix("/assets/")
    if (
        host != expected_host
        or not path.startswith("/assets/")
        or relative.startswith("/")
        or ".." in relative
        or "\\" in relative
    ):
        return Response(b"Unknown app or outside package", status=404)
    resource = "index.html" if relative == "second.html" else relative
    group = "common" if resource in {"probe.js", "style.css", "marker.svg"} else f"apps/{app}"
    try:
        package_root = (fixtures / group).resolve(strict=True)
        source = (package_root / resource).resolve(strict=True)
        # Resolve links first: textual prefixes alone do not confine filesystem reads.
        if not source.is_relative_to(package_root) or not source.is_file():
            return Response(b"Unknown app or outside package", status=404)
        body = source.read_bytes()
    except (OSError, RuntimeError, ValueError):
        return Response(b"Missing bundled resource", status=404)
    mime = {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".svg": "image/svg+xml",
    }.get(Path(resource).suffix, "application/json")
    return Response(body, mime)


class LoopbackFixture(BaseHTTPRequestHandler):
    report_name = "t23Report"
    charset = None

    def asset_root(self):
        return None

    def do_GET(self):
        root = self.asset_root()
        path = self.path if root is None else unquote(urlsplit(self.path).path)
        origin = self.headers.get("Origin")
        print(
            json.dumps({"port": self.server.server_port, "path": path, "origin": origin}),
            flush=True,
        )
        if root is None or self.server.server_port == 8877:
            response = control_response(path, origin, self.report_name)
        else:
            response = bundled_response(
                root, self.server.server_port, self.headers.get("Host"), path
            )
        self.send_response(response.status)
        content_type = (
            response.mime
            if self.charset is None
            else f"{response.mime}; charset={self.charset}"
        )
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(response.body)))
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(response.body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_):
        pass
