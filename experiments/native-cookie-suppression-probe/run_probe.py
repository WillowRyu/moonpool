"""Collect from explicit owned devices; an unexpected process exit ends the run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from verify import expected_cases

ROOT=Path(__file__).resolve().parent
ADB=Path.home()/'Library/Android/sdk/platform-tools/adb'
PACKAGES={'android':'org.moonpool.cookiesuppression','ios':'org.moonpool.ioscookiesuppressionprobe'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def command(parts, check=True, binary=False):
    return subprocess.run(parts,capture_output=True,text=not binary,check=check,timeout=30)

def parse_report(raw, tag):
    if not raw: return None
    try: report=json.loads(raw)
    except json.JSONDecodeError: return None
    return report if isinstance(report,dict) and report.get('run')==tag else None

def require_fixture_version(server):
    digest=hashlib.sha256(json.dumps(expected_cases(),sort_keys=True).encode()).hexdigest()
    assert server.get('casesSha256')==digest, 'Restart the fixture: running server has a different case list'


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('platform',choices=['android','ios']); parser.add_argument('--run',required=True); parser.add_argument('--install',action='store_true')
    args=parser.parse_args(); platform=args.platform; tag=platform+'-'+args.run
    if not re.fullmatch(r'[a-z0-9-]+',tag): raise ValueError('Invalid public run tag')
    owner=json.loads((ROOT/'local-results'/f'{platform}-owner.json').read_text())
    metadata=json.loads((ROOT/'local-results'/f'{platform}-build.json').read_text())
    for path,digest in metadata['sources'].items(): assert sha(ROOT/path)==digest, 'Changed built source: '+path
    assert sha(ROOT/'build/assets/config.json')==metadata['fixtureConfigSha256']
    assert sha(ROOT/'local-results/tls/ca.pem')==metadata['caSha256']
    server=json.loads((ROOT/'local-results/server.json').read_text()); require_fixture_version(server)
    port=server['port']; base=f'https://localhost:{port}'
    package=PACKAGES[platform]
    if platform=='android':
        serial=owner['serial']
        def adb(*parts,**kwargs): return command([str(ADB),'-s',serial,*parts],**kwargs)
        assert adb('emu','avd','name').stdout.splitlines()[0]==owner['avd']
        adb('reverse',f'tcp:{port}',f'tcp:{port}')
        if args.install: adb('install','-r',str(ROOT/'android/app/build/outputs/apk/debug/app-debug.apk'))
        path=adb('shell','pm','path',package).stdout.strip().removeprefix('package:')
        installed=hashlib.sha256(adb('exec-out','cat',path,binary=True).stdout).hexdigest()
        assert installed==metadata['apkSha256']
        adb('shell','am','force-stop',package)
        adb('shell','run-as',package,'rm','-f','files/report.json')
        launch=adb('shell','am','start','-n',package+'/.ProbeActivity','--es','run',tag,'--es','base',base)
        assert 'Error' not in launch.stdout, launch.stdout
        def read_report():
            result=adb('exec-out','run-as',package,'cat','files/report.json',check=False)
            return result.stdout if result.returncode==0 else None
        def alive(): return bool(adb('shell','pidof',package,check=False).stdout.strip())
    else:
        device=owner['owned']; assert device not in owner['protected']
        def sim(*parts,**kwargs): return command(['xcrun','simctl',*parts],**kwargs)
        devices=json.loads(sim('list','devices','available','-j').stdout)['devices']
        current=next(d for group in devices.values() for d in group if d['udid']==device)
        assert current['name']==owner['name'] and current['state']=='Booted'
        if args.install: sim('install',device,str(ROOT/'build/CookieSuppressionProbe.app'))
        app=Path(sim('get_app_container',device,package,'app').stdout.strip())
        installed=sha(app/'CookieSuppressionProbe'); assert installed==metadata['executableSha256']
        assert sha(app/'_CodeSignature/CodeResources')==metadata['signatureSha256']
        command(['codesign','--verify','--deep','--strict',str(app)])
        sim('terminate',device,package,check=False)
        container=Path(sim('get_app_container',device,package,'data').stdout.strip())
        output=container/'Documents/report.json'; output.unlink(missing_ok=True)
        launched=sim('launch',device,package,'--run',tag,'--base',base).stdout.strip()
        pid=int(launched.rsplit(':',1)[1].strip())
        def read_report(): return output.read_text() if output.exists() else None
        def alive():
            try: os.kill(pid,0); return True
            except ProcessLookupError: return False
    started=time.monotonic()
    while time.monotonic()-started<180:
        report=parse_report(read_report(),tag)
        if report is not None: break
        if time.monotonic()-started>5 and not alive():
            raise RuntimeError('Probe process exited unexpectedly; stopped without retry. Inspect owned local evidence.')
        time.sleep(0.5)
    else: raise TimeoutError('No final report; stopped without retry')
    report['build']=metadata; report['installedArtifactSha256']=installed
    report['requests']=[json.loads(line) for line in (ROOT/'local-results/tls/requests.jsonl').read_text().splitlines() if json.loads(line)['run']==tag]
    report['capturedUtc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    results=ROOT/'results'; results.mkdir(exist_ok=True)
    (results/(tag+'.json')).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f'{tag}: complete={report.get("complete")}, samples={len(report.get("samples",[]))}, server requests={len(report["requests"])}')
    if not report.get('complete'): print({k:report[k] for k in ['unsupported','failedCase','error','lastDocument'] if k in report})


if __name__=='__main__': main()
