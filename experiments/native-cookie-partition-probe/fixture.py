"""Owned loopback HTTPS fixture. Its receipts are independent of native inventory."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import select
import ssl
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
PARTITIONS = {c['id']: c for c in json.loads((ROOT / 'partition_cases.json').read_text())}
WRITERS = {c['id']: c for c in json.loads((ROOT / 'writer_cases.json').read_text())}
WARMUPS = {c['id']: c for c in json.loads((ROOT / 'warmup_cases.json').read_text())}
HOLD_LIMIT_SECONDS = 30


def partition_cookie(case):
    return f"t28p_{case['id']}=public_{case['id']}; Path=/; Secure; Max-Age=86400; {case['attributes']}"


def writer_cookie(case):
    return f"t28w_{case['id']}=public; Path=/; Secure; Max-Age=600; SameSite=Lax"


def warmup_cookie(case_id, step):
    if step == 'seed-first':
        return f't28u_{case_id}_first=public; Path=/; Secure; Max-Age=86400; SameSite=None'
    if step == 'seed-xsite':
        return f't28u_{case_id}_partitioned=public; Path=/; Secure; Max-Age=86400; SameSite=None; Partitioned'
    return None


def page_body(spec):
    # JSON is built from checked-in vectors only; request input never reaches the page.
    return """<!doctype html><title>Partition fixture</title><script>
(async () => {
  const spec = %s;
  const result = { href: location.href, framed: window.top !== window,
    cookieStoreAvailable: 'cookieStore' in window, writeError: null, storeError: null };
  try {
    if (spec.write === 'script') { document.cookie = spec.cookie; }
    if (spec.write === 'cookiestore') {
      await cookieStore.set({ ...spec.store, expires: Date.now() + 86400000 });
    }
  } catch (error) { result.writeError = error.name; }
  result.documentCookie = document.cookie;
  try {
    result.storeNames = 'cookieStore' in window
      ? (await cookieStore.getAll()).map((c) => ({ name: c.name, partitioned: c.partitioned ?? null }))
      : null;
  } catch (error) { result.storeError = error.name; }
  window.pageResult = JSON.stringify(result);
  if (result.framed) { parent.postMessage(result, '*'); }
})();
</script>""" % json.dumps(spec)


def writer_body(case_id, api):
    return """<!doctype html><title>Writer fixture</title><script>
window.writes = 0;
window.writeError = null;
const prefix = %s;
const api = %s;
const timer = setInterval(() => {
  if (window.writes >= 300) { clearInterval(timer); return; }
  // The counter advances before the write, so an index names when it was issued.
  const name = prefix + (++window.writes);
  if (api === 'document') {
    document.cookie = name + '=x; Path=/; Secure; Max-Age=600; SameSite=Lax';
  } else {
    cookieStore.set({ name, value: 'x', path: '/', sameSite: 'lax', expires: Date.now() + 600000 })
      .catch((error) => { window.writeError = error.name; });
  }
}, 10);
window.stopWriter = () => { clearInterval(timer); return 'stopped'; };
</script>""" % (json.dumps(f't28w_{case_id}_'), json.dumps(api))


def create_certificates(folder):
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'server.pem').exists():
        return

    def run(*args):
        subprocess.run(['openssl', *args], cwd=folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '7',
        '-subj', '/CN=Moonpool Owned Partition Probe CA',
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
    holds = {}

    def hold_for(key):
        with lock:
            return holds.setdefault(key, {'arrived': False, 'release': threading.Event()})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def client_closed(self):
            # Nothing more is expected on this connection, so readable means it closed.
            try:
                return bool(select.select([self.connection], [], [], 0)[0])
            except (OSError, ValueError):
                return True

        def record(self, url, run, case, step, event, **extra):
            row = {**extra,
                'run': run, 'case': case, 'step': step, 'path': url.path, 'event': event,
                'host': self.headers.get('Host', ''), 'cookie': self.headers.get('Cookie', ''),
                'secFetchSite': self.headers.get('Sec-Fetch-Site'), 'secFetchDest': self.headers.get('Sec-Fetch-Dest'),
                'tls': isinstance(self.connection, ssl.SSLSocket),
            }
            with lock, (folder / 'requests.jsonl').open('a') as out:
                out.write(json.dumps(row) + '\n')

        def send(self, body, content_type='text/html', cookie=None):
            self.send_response(200)
            self.send_header('Cache-Control', 'no-store')
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(url.query).items()}
            if url.path == '/frame':
                self.send((ROOT / 'frame.html').read_bytes())
                return
            run, case, step = query.get('run', ''), query.get('case', ''), query.get('step', '')
            if not re.fullmatch('[a-z0-9-]+', run) or case not in {**PARTITIONS, **WRITERS, **WARMUPS}:
                self.send_error(400)
                return
            if url.path == '/held':
                self.send(json.dumps({'held': hold_for((run, case))['arrived']}).encode(), 'application/json')
            elif url.path == '/release':
                hold_for((run, case))['release'].set()
                self.send(json.dumps({'released': True}).encode(), 'application/json')
            elif not re.fullmatch('[a-z-]+', step):
                self.send_error(400)
            elif url.path == '/page':
                self.page(url, run, case, step, query.get('write', 'none'))
            elif url.path == '/hold' and case in WRITERS:
                self.hold(url, run, case, step)
            elif url.path == '/writer' and case in WRITERS and query.get('api') in ['document', 'cookiestore']:
                self.record(url, run, case, step, 'arrived')
                self.send(writer_body(case, query['api']).encode())
            else:
                self.send_error(404)

        def page(self, url, run, case, step, write):
            if write not in ['none', 'header', 'script', 'cookiestore']:
                self.send_error(400)
                return
            self.record(url, run, case, step, 'arrived')
            spec = {'write': write}
            cookie = None
            if case in PARTITIONS and write != 'none':
                partition = PARTITIONS[case]
                if write == 'header':
                    cookie = partition_cookie(partition)
                elif write == 'script':
                    spec['cookie'] = partition_cookie(partition)
                else:
                    spec['store'] = {'name': f't28p_{case}', 'value': f'public_{case}', 'path': '/',
                                     'sameSite': 'none', 'partitioned': True}
            if case in WARMUPS and write == 'header':
                cookie = warmup_cookie(case, step)
            self.send(page_body(spec).encode(), cookie=cookie)

        def hold(self, url, run, case, step):
            entry = hold_for((run, case))
            self.record(url, run, case, step, 'arrived')
            with lock:
                entry['arrived'] = True
            released = entry['release'].wait(HOLD_LIMIT_SECONDS)
            self.record(url, run, case, step, 'released' if released else 'timeout', clientClosed=self.client_closed())
            body = b'<!doctype html><title>Held</title><script>window.networkReady=location.href;</script>'
            try:
                self.send(body, cookie=writer_cookie(WRITERS[case]))
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                pass  # The client may have torn down; a write here cannot prove delivery either way.

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        # Handshake per connection thread so a parked or stalled client cannot block accept.
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server


def vectors_digest():
    digest = hashlib.sha256()
    for name in ['partition_cases.json', 'writer_cases.json', 'warmup_cases.json', 'fixture.py', 'frame.html']:
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
    print(f'Owned partition HTTPS fixture: https://localhost:{httpd.server_port}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
