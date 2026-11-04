"""Owned loopback HTTPS service. Its receipts are independent of what the broker reports.

Hold controls live on a separate listener, so they are not part of the service surface the broker talks to.
Every cookie and credential here is a public fixture value.
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
EXPECTED_AUTHORIZATION = 'Basic ' + base64.b64encode(b'moonpool-fixture-user:not-a-secret').decode()
SERVED_PATHS = ['/s', '/deep/s']


def steps_by_label():
    found = {}
    for case in CASES:
        for step in case['steps']:
            if step['op'] in ('request', 'hostRequest'):
                found[(case['id'], step['label'])] = step.get('serve', {})
                if step.get('serve', {}).get('location'):
                    found[(case['id'], 'target')] = {}
    return found


STEPS = steps_by_label()


def serve_for(case, step):
    return STEPS[(case, step)]


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned Broker Probe CA',
        '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    run('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'server.key', '-out', 'server.csr', '-subj', '/CN=localhost')
    (folder / 'server.ext').write_text(
        'subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\n'
        'keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
    run('x509', '-req', '-in', 'server.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial',
        '-out', 'server.pem', '-days', '7', '-extfile', 'server.ext')
    for name in ['ca.key', 'server.key']:
        (folder / name).chmod(0o600)


def make_servers(folder, port, second_port, control_port, tls=True):
    lock = threading.Lock()
    holds, attempts = {}, {}

    def hold_for(key):
        with lock:
            return holds.setdefault(key, {'held': False, 'release': threading.Event()})

    def parsed(handler):
        url = urlsplit(handler.path)
        query = {key: values[0] for key, values in parse_qs(url.query).items()}
        known = re.fullmatch('[a-z0-9-]+', query.get('run', '')) and (query.get('case'), query.get('step')) in STEPS
        return url, query, known

    def make_service(listener):
        class Service(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def record(self, url, query, event, body_length):
                row = {'run': query['run'], 'case': query['case'], 'step': query['step'], 'path': url.path, 'event': event, 'listener': listener,
                       'host': self.headers.get('Host', '').rsplit(':', 1)[0], 'method': self.command, 'tls': isinstance(self.connection, ssl.SSLSocket),
                       'bodyLength': body_length, 'cookieFields': self.headers.get_all('Cookie') or [], 'authorization': self.headers.get('Authorization')}
                with lock, (folder / 'requests.jsonl').open('a') as out:
                    out.write(json.dumps(row) + '\n')

            def handle_request(self):
                url, query, known = parsed(self)
                length = int(self.headers.get('Content-Length') or 0)
                if length:
                    self.rfile.read(length)
                if url.path not in SERVED_PATHS or not known:
                    self.send_error(404 if url.path not in SERVED_PATHS else 400)
                    return
                self.record(url, query, 'arrived', length)
                serve = serve_for(query['case'], query['step'])
                key = (query['run'], query['case'], query['step'])
                with lock:
                    attempts[key] = attempts.get(key, 0) + 1
                    attempt = attempts[key]
                if serve.get('hold') == 'headers':
                    self.hold(key, url, query, length)
                early = serve.get('earlyBytes', 0) if serve.get('hold') == 'body' else serve.get('abortAfterBytes', 0)
                # Leading spaces are valid JSON, so early bytes can be sent before a hold or a failure.
                body = b'' if serve.get('noBody') else b' ' * early + json.dumps({'step': query['step'], 'ok': True}).encode()
                self.send_head(serve, query, attempt, len(body))
                if serve.get('abortAfterBytes'):
                    self.wfile.write(body[:early])
                    self.wfile.flush()
                    self.close_connection = True
                    return
                if serve.get('hold') == 'body':
                    self.wfile.write(body[:early])
                    self.wfile.flush()
                    body = body[early:]
                    self.hold(key, url, query, length)
                self.wfile.write(body)

            def hold(self, key, url, query, length):
                entry = hold_for(key)
                with lock:
                    entry['held'] = True
                entry['release'].wait(30)
                self.record(url, query, 'released', length)

            def send_head(self, serve, query, attempt, length):
                accepted = serve.get('acceptCredentials') and self.headers.get('Authorization') == EXPECTED_AUTHORIZATION
                self.send_response(200 if accepted else serve.get('status', 200))
                fields = serve.get('setCookie', [])
                if serve.get('setCookieByAttempt'):
                    fields = serve['setCookieByAttempt'][min(attempt, len(serve['setCookieByAttempt'])) - 1]
                for value in fields:
                    self.send_header('set-cookie' if serve.get('lowerNames') else 'Set-Cookie', value)
                if serve.get('location'):
                    host = 'localhost' if serve['location'] == 'approved' else '127.0.0.1'
                    self.send_header('Location', f"https://{host}:{self.server.server_address[1]}/s?run={query['run']}&case={query['case']}&step=target")
                if serve.get('challenge') and not accepted:
                    self.send_header('WWW-Authenticate', f"{serve['challenge']} realm=\"t28\"")
                if serve.get('retryAfter'):
                    self.send_header('Retry-After', serve['retryAfter'])
                self.send_header('Cache-Control', 'no-store')
                if not serve.get('noBody'):
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(length + (64 if serve.get('abortAfterBytes') else 0)))
                self.end_headers()

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

        return Service

    class Control(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_GET(self):
            url, query, known = parsed(self)
            if url.path not in ['/held', '/release'] or not known:
                self.send_error(404)
                return
            entry = hold_for((query['run'], query['case'], query['step']))
            if url.path == '/release':
                entry['release'].set()
            body = json.dumps({'held': entry['held']}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    servers = (ThreadingHTTPServer(('127.0.0.1', port), make_service('service')),
               ThreadingHTTPServer(('127.0.0.1', second_port), make_service('service2')),
               ThreadingHTTPServer(('127.0.0.1', control_port), Control))
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
    service, second, control = make_servers(tls_folder, 0, 0, 0)
    (ROOT / 'local-results/server.json').write_text(json.dumps(
        {'port': service.server_port, 'secondPort': second.server_port, 'controlPort': control.server_port, 'vectorsSha256': vectors_digest()}) + '\n')
    print(f'Owned broker fixture: {service.server_port} / {second.server_port} / control {control.server_port}', flush=True)
    for server in (second, control):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for server in (service, second, control):
            server.server_close()
