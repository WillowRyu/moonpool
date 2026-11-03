"""Owned loopback HTTPS fixture. Its receipts are independent of native inventory."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import ssl
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit
from vectors import cookie_name, expand

ROOT = Path(__file__).resolve().parent
STORES = {store['id']: store for store in expand()}


def page_body():
    # Static: nothing from the request or the Cookie header reaches the page.
    return b"""<!doctype html><title>Empty-store fixture</title><script>
(async () => {
  const result = { href: location.href, framed: window.top !== window, documentCookie: document.cookie };
  try {
    result.storeNames = 'cookieStore' in window ? (await cookieStore.getAll()).map((c) => c.name) : null;
  } catch (error) { result.storeError = error.name; }
  window.pageResult = JSON.stringify(result);
  if (result.framed) { parent.postMessage(result, '*'); }
})();
</script>"""


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned Empty Store Probe CA',
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

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body, cookie=None):
            self.send_response(200)
            self.send_header('Cache-Control', 'no-store')
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            if url.path == '/frame':
                self.send((ROOT / 'frame.html').read_bytes())
                return
            if url.path != '/page':
                self.send_error(404)
                return
            run, case, step, write = (query.get(key, '') for key in ['run', 'case', 'step', 'write'])
            if (not re.fullmatch('[a-z0-9-]+', run) or case not in STORES or not re.fullmatch('[a-z-]+', step)
                    or write not in ['none', 'header']):
                self.send_error(400)
                return
            row = {'run': run, 'case': case, 'step': step, 'host': self.headers.get('Host', ''),
                   'cookie': self.headers.get('Cookie', ''), 'secFetchSite': self.headers.get('Sec-Fetch-Site'),
                   'secFetchDest': self.headers.get('Sec-Fetch-Dest'), 'tls': isinstance(self.connection, ssl.SSLSocket)}
            with lock, (folder / 'requests.jsonl').open('a') as out:
                out.write(json.dumps(row) + '\n')
            store = STORES[case]
            attributes = store['cookies'].get(step) if write == 'header' else None
            self.send(page_body(), cookie=f"{cookie_name(store['kind'])}={attributes}" if attributes else None)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


def vectors_digest():
    digest = hashlib.sha256()
    for name in ['store_kinds.json', 'vectors.py', 'fixture.py', 'frame.html', 'storage.html']:
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    tls_folder = ROOT / 'local-results/tls'
    create_certificates(tls_folder)
    httpd = make_server(tls_folder, args.port)
    (ROOT / 'local-results/server.json').write_text(
        json.dumps({'port': httpd.server_port, 'vectorsSha256': vectors_digest()}) + '\n')
    print(f'Owned empty-store HTTPS fixture: https://localhost:{httpd.server_port}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
