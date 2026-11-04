"""Owned loopback HTTPS service. Its receipts are independent of any native client's report.

Credentials here are public fixture values. They stand in for what a host app's global handlers
would hold, so a leak can be shown without any real secret.
"""
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

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / 'cases.json').read_text())
BY_CASE = {case['id']: case for case in CASES}
EXPECTED_AUTHORIZATION = 'Basic ' + base64.b64encode(b'moonpool-fixture-user:not-a-secret').decode()


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned HTTP Globals Probe CA',
        '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    run('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'server.key', '-out', 'server.csr', '-subj', '/CN=localhost')
    (folder / 'server.ext').write_text(
        'subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\n'
        'keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
    run('x509', '-req', '-in', 'server.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial',
        '-out', 'server.pem', '-days', '7', '-extfile', 'server.ext')
    for name in ['ca.key', 'server.key']:
        (folder / name).chmod(0o600)


def make_server(folder, port, tls=True):
    lock = threading.Lock()

    def valid(query):
        return re.fullmatch('[a-z0-9-]+', query.get('run', '')) and query.get('case') in BY_CASE

    class Service(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def record(self, url, run, case, body_length):
            row = {'run': run, 'case': case, 'path': url.path, 'event': 'arrived', 'method': self.command,
                   'tls': isinstance(self.connection, ssl.SSLSocket), 'bodyLength': body_length,
                   'cookieFields': self.headers.get_all('Cookie') or [],
                   'authorizationValue': self.headers.get('Authorization')}
            with lock, (folder / 'requests.jsonl').open('a') as out:
                out.write(json.dumps(row) + '\n')

        def handle_request(self):
            url = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            length = int(self.headers.get('Content-Length') or 0)
            if length:
                self.rfile.read(length)
            if url.path not in ['/echo', '/serve', '/target'] or not valid(query):
                self.send_error(404 if url.path not in ['/echo', '/serve', '/target'] else 400)
                return
            run, name = query['run'], query['case']
            self.record(url, run, name, length)
            self.respond(BY_CASE[name] if url.path == '/serve' else {}, run, name)

        def respond(self, case, run, name):
            accepted = case.get('acceptCredentials') and self.headers.get('Authorization') == EXPECTED_AUTHORIZATION
            self.send_response(200 if accepted else case.get('status', 200))
            for value in case.get('acceptedSetCookie', []) if accepted else case.get('setCookie', []):
                self.send_header('Set-Cookie', value)
            if case.get('redirect'):
                self.send_header('Location', f'/target?run={run}&case={name}')
            scheme = case.get('challengeScheme', 'Basic')
            if case.get('challenge') and scheme and not accepted:
                self.send_header('WWW-Authenticate', f'{scheme} realm="t28"')
            body = json.dumps({'case': name, 'ok': True}).encode()
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

    server = ThreadingHTTPServer(('127.0.0.1', port), Service)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


def vectors_digest():
    digest = hashlib.sha256()
    for name in ['cases.json', 'fixture.py']:
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


if __name__ == '__main__':
    tls_folder = ROOT / 'local-results/tls'
    create_certificates(tls_folder)
    service = make_server(tls_folder, 0)
    (ROOT / 'local-results/server.json').write_text(json.dumps({'port': service.server_port, 'vectorsSha256': vectors_digest()}) + '\n')
    print(f'Owned HTTP globals fixture: {service.server_port}', flush=True)
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.server_close()
