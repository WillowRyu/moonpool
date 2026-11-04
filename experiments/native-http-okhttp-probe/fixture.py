"""Owned loopback HTTPS service. Its receipts are independent of any native client's report.

Hold controls live on a separate listener, so they are not part of the service surface a client
under test talks to. Credentials here are public fixture values.
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
BY_CASE = {case.get('requestCase', case['id']): case for case in CASES}
EXPECTED_AUTHORIZATION = 'Basic ' + base64.b64encode(b'moonpool-fixture-user:not-a-secret').decode()


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned OkHttp Probe CA',
        '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    run('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'server.key', '-out', 'server.csr', '-subj', '/CN=localhost')
    (folder / 'server.ext').write_text(
        'subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\n'
        'keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
    run('x509', '-req', '-in', 'server.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial',
        '-out', 'server.pem', '-days', '7', '-extfile', 'server.ext')
    for name in ['ca.key', 'server.key']:
        (folder / name).chmod(0o600)


def make_servers(folder, port, control_port, tls=True):
    lock = threading.Lock()
    holds = {}

    def hold_for(key):
        with lock:
            return holds.setdefault(key, {'held': False, 'release': threading.Event()})

    def valid(query):
        return re.fullmatch('[a-z0-9-]+', query.get('run', '')) and query.get('case') in BY_CASE

    class Service(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def record(self, url, run, case, event, body_length):
            row = {'run': run, 'case': case, 'path': url.path, 'event': event, 'method': self.command,
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
            case = BY_CASE[name]
            self.record(url, run, name, 'arrived', length)
            serving = url.path == '/serve'
            if serving and case.get('closeWithoutResponse'):
                self.close_connection = True
                return
            kind = case.get('kind') if serving else None
            entry = hold_for((run, name))
            if kind == 'hold-headers':
                self.hold(entry, url, run, name, length)
            early = case.get('earlyBytes', 0) if kind == 'hold-body' else 0
            # Leading spaces are valid JSON, so early bytes can be sent before the hold.
            body = b' ' * early + json.dumps({'case': name, 'ok': True}).encode()
            self.send_head(case if serving else {}, run, name, len(body))
            if kind == 'hold-body':
                self.wfile.write(body[:early])
                self.wfile.flush()
                body = body[early:]
                self.hold(entry, url, run, name, length)
            self.wfile.write(body)

        def hold(self, entry, url, run, name, length):
            with lock:
                entry['held'] = True
            entry['release'].wait(30)
            self.record(url, run, name, 'released', length)

        def send_head(self, case, run, name, length):
            accepted = case.get('acceptCredentials') and self.headers.get('Authorization') == EXPECTED_AUTHORIZATION
            self.send_response(200 if accepted else case.get('status', 200))
            header = 'set-cookie' if case.get('lowerNames') else 'Set-Cookie'
            for value in case.get('acceptedSetCookie', []) if accepted else case.get('setCookie', []):
                self.send_header(header, value)
            if case.get('redirect'):
                self.send_header('Location', f'/target?run={run}&case={name}')
            scheme = case.get('challengeScheme', 'Basic')
            if case.get('challenge') and scheme and not accepted:
                self.send_header('WWW-Authenticate', f'{scheme} realm="t28"')
            if case.get('retryAfter'):
                self.send_header('Retry-After', case['retryAfter'])
            self.send_header('Cache-Control', case.get('cacheControl', 'no-store'))
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(length))
            self.end_headers()

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

    class Control(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            if url.path not in ['/held', '/release'] or not valid(query):
                self.send_error(404)
                return
            entry = hold_for((query['run'], query['case']))
            if url.path == '/release':
                entry['release'].set()
            body = json.dumps({'held': entry['held']}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    servers = ThreadingHTTPServer(('127.0.0.1', port), Service), ThreadingHTTPServer(('127.0.0.1', control_port), Control)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        for server in servers:
            server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return servers


def vectors_digest():
    digest = hashlib.sha256()
    for name in ['cases.json', 'fixture.py']:
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


if __name__ == '__main__':
    tls_folder = ROOT / 'local-results/tls'
    create_certificates(tls_folder)
    service, control = make_servers(tls_folder, 0, 0)
    (ROOT / 'local-results/server.json').write_text(json.dumps(
        {'port': service.server_port, 'controlPort': control.server_port, 'vectorsSha256': vectors_digest()}) + '\n')
    print(f'Owned OkHttp fixture: {service.server_port} / control {control.server_port}', flush=True)
    threading.Thread(target=control.serve_forever, daemon=True).start()
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.server_close()
        control.server_close()
