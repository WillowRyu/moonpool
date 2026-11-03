"""Check server receipts, native inventory/verdicts, preservation and callback traces."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parent
CASES=json.loads((ROOT/'presence_cases.json').read_text())
GATES=json.loads((ROOT/'gate_cases.json').read_text())
def verify(report):
    count=0
    def require(value,message):
        nonlocal count
        assert value,message;count+=1
    require(report.get('complete') is True,'collection incomplete')
    require(report.get('errors')==[],'native load/TLS errors recorded')
    require(report['gateCases']==GATES,'native callback trace differs from oracle')
    expected=[(c['id'],p) for c in CASES for p in ['initial','reopened']]
    require([(s['case'],s['phase']) for s in report['samples']]==expected,'missing/duplicate native samples')
    expected_tokens=[s['expectedStorage'] for s in report['samples'] if s['case']=='empty']
    actual_tokens=[parse_qs(urlsplit(url).query).get('token',[''])[0] for url in report['guestResources']]
    require(sorted(actual_tokens)==sorted(expected_tokens),'unauthorized or missing native guest resource delivery')
    for c in CASES:
        selected=[s for s in report['samples'] if s['case']==c['id']]
        require(selected[0]['partition']==selected[1]['partition'],c['id']+': silently replaced partition')
        for s in selected:
            label=c['id']+'/'+s['phase']
            names=['t28a_'+c['id']] if c['present'] else []
            require(sorted(s['beforeNames'])==names,label+': seed was not observed')
            require(s['beforeCookies']==s['afterCookies'],label+': mutated cookies during admission')
            require(sorted(s['afterNames'])==names,label+': cookie lost')
            require(s['presence'] is c['present'],label+': native presence missed cookie')
            require(s['policyAllows'] is False,label+': deny policy absent')
            require(s['storage']=={'local':s['expectedStorage'],'indexed':s['expectedStorage']},label+': non-cookie data lost')
            require(s['hostPolicyAllows'] is True and s['hostCookiePresent'] is True,label+': host control damaged')
            require('t28a_host=public_host' in s['hostCookie'].split('; '),label+': host cookie value missing')
            require(s['decision']==('refused' if c['present'] else 'admitted'),label+': wrong gate decision')
            require(s['loadCalls']==(0 if c['present'] else 1),label+': unauthorized guest load')
            require(s['guestMarker']==(None if c['present'] else s['expectedStorage']),label+': guest execution')
            if c['id'] in ['httponly','offpath','unrelated']:
                require(s['visibleJsCookie']=='',label+': hidden-cookie diagnostic not established')
        rows=[r for r in report['requests'] if r['case']==c['id'] and r['path'] in ['/echo','/hidden/echo']]
        require(len(rows)==1,c['id']+': missing/duplicate server control')
        if c['present']:require('t28a_'+c['id']+'=public_'+c['id'] in rows[0]['cookie'],c['id']+': server never received seed')
        else:require(rows[0]['cookie']=='',c['id']+': empty control contains cookie')
    return count

def integrity(report):
    metadata=report['build']
    assert report['platform'] in ('android','ios'),'unknown native platform'
    paths=[ROOT/'build.py',ROOT/'storage.html',ROOT/'presence_cases.json',ROOT/'gate_cases.json',*(ROOT/report['platform']).rglob('*')]
    expected={str(path.relative_to(ROOT)) for path in paths if path.is_file() and not any(x in {'build','.gradle'} for x in path.relative_to(ROOT).parts)}
    assert set(metadata['sources'])==expected,'missing/extra runtime source fingerprints'
    for path,digest in metadata['sources'].items():
        target=(ROOT/path).resolve();assert target.is_relative_to(ROOT)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest,'changed source '+path
    key='apkSha256' if report['platform']=='android' else 'executableSha256'
    assert report['installedArtifactSha256']==metadata[key]
    artifact=ROOT/('android/app/build/outputs/apk/debug/app-debug.apk' if report['platform']=='android' else 'build/CookieAdmissionProbe.app/CookieAdmissionProbe')
    if artifact.exists():assert hashlib.sha256(artifact.read_bytes()).hexdigest()==metadata[key],'local artifact changed'
    assert all(row['tls'] and row['run']==report['run'] for row in report['requests'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reports',nargs='+',type=Path)
    for path in p.parse_args().reports:
        report=json.loads(path.read_text());integrity(report)
        print(f'{path.name}: {verify(report)} checks, 12 inventory/admission samples, 9 native callback traces')
