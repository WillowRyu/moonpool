"""Owned loopback HTTPS service. It serves a different response per arrival and records what each arrival was served."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import ssl
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
CASES = {case['id']: case for case in json.loads((ROOT / 'cases.json').read_text())}


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned Failure Response Probe CA',
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
    attempts = {}

    class Service(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def handle_request(self):
            url = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            length = int(self.headers.get('Content-Length') or 0)
            if length:
                self.rfile.read(length)
            case = CASES.get(query.get('case'))
            if url.path != '/s' or case is None or not re.fullmatch('[a-z0-9-]+', query.get('run', '')):
                self.send_error(404)
                return
            with lock:
                key = (query['run'], case['id'])
                attempts[key] = attempts.get(key, 0) + 1
                arrival = attempts[key]
                fields = case['setCookieByAttempt'][min(arrival, len(case['setCookieByAttempt'])) - 1]
                row = {'run': query['run'], 'case': case['id'], 'arrival': arrival, 'tls': isinstance(self.connection, ssl.SSLSocket), 'method': self.command,
                       'bodyLength': length, 'authorization': self.headers.get('Authorization'), 'cookieFields': self.headers.get_all('Cookie') or [], 'served': fields}
                with (folder / 'requests.jsonl').open('a') as out:
                    out.write(json.dumps(row) + '\n')
            body = json.dumps({'case': case['id'], 'arrival': arrival}).encode()
            self.send_response(case['status'])
            for value in fields:
                self.send_header('Set-Cookie', value)
            if case.get('challenge'):
                self.send_header('WWW-Authenticate', f"{case['challenge']} realm=\"t28\"")
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = handle_request

    server = ThreadingHTTPServer(('127.0.0.1', port), Service)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


if __name__ == '__main__':
    tls_folder = ROOT / 'local-results/tls'
    create_certificates(tls_folder)
    service = make_server(tls_folder, 0)
    (ROOT / 'local-results/server.json').write_text(json.dumps({'port': service.server_port}) + '\n')
    print(f'Owned failure response fixture: {service.server_port}', flush=True)
    try:
        service.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.server_close()
