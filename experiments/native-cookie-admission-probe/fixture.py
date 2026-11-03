"""Owned loopback fixture; HTTPS seeding/receipt is independent from native verdicts."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re
import ssl
import subprocess
import threading
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parent
CASES={c['id']:c for c in json.loads((ROOT/'presence_cases.json').read_text())}
CASES['host']={'cookie':'t28a_host=public_host; Path=/; Secure; Max-Age=86400; SameSite=Lax'}
def create_certificates(folder):
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'server.pem').exists():return
    def run(*args):subprocess.run(['openssl',*args],cwd=folder,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    run('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.pem','-days','7','-subj','/CN=Moonpool Owned Admission Probe CA','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign')
    run('req','-newkey','rsa:2048','-nodes','-keyout','server.key','-out','server.csr','-subj','/CN=localhost')
    (folder/'server.ext').write_text('subjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
    run('x509','-req','-in','server.csr','-CA','ca.pem','-CAkey','ca.key','-CAcreateserial','-out','server.pem','-days','7','-extfile','server.ext')
    for name in ['ca.key','server.key']:(folder/name).chmod(0o600)

def make_server(folder,port,tls=True):
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            url=urlsplit(self.path);q=parse_qs(url.query);run=q.get('run',[''])[0];case=q.get('case',[''])[0]
            if url.path not in ['/seed','/echo','/hidden/echo','/visible']:
                self.send_error(404);return
            if not re.fullmatch('[a-z0-9-]+',run) or case not in CASES:
                self.send_error(400);return
            row={'run':run,'case':case,'path':url.path,'host':self.headers.get('Host',''),'cookie':self.headers.get('Cookie',''),'tls':isinstance(self.connection,ssl.SSLSocket)}
            with lock:
                with (folder/'requests.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
            self.send_response(200);self.send_header('Cache-Control','no-store')
            if url.path=='/seed' and CASES[case]['cookie']:self.send_header('Set-Cookie',CASES[case]['cookie'])
            body=b'<!doctype html><title>Admission fixture</title><p>Public setup observation</p><script>window.networkReady=location.href;</script>'
            self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    if tls:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(folder/'server.pem',folder/'server.key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
    return server

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=0);args=p.parse_args()
    folder=ROOT/'local-results/tls';create_certificates(folder);server=make_server(folder,args.port)
    (ROOT/'local-results/server.json').write_text(json.dumps({'port':server.server_port,'casesSha256':hashlib.sha256((ROOT/'presence_cases.json').read_bytes()).hexdigest()})+'\n')
    print(f'Owned admission HTTPS fixture: https://localhost:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
