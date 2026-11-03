"""Validate native event provenance and current source/artifact fingerprints."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def check_bindings(report):
    field='profile' if report['platform']=='android' else 'store'
    bindings={}; policies=None; stage=None; loads={}; baseline=None
    for event in report['events']:
        if event['event']=='created': bindings[event['view']]=event[field]
        elif event['event']=='policy':
            stage=event['stage']; policies=event['values']
            assert set(bindings)=={'a1','a2','b','h','u'}, 'Missing native view binding'
            assert bindings['a1']==bindings['a2'], 'Same-app views have different partitions'
            assert len({bindings[v] for v in ('a1','b','h','u')})==4, 'App/host partition collision'
            if stage=='baseline': baseline=bindings.copy()
            if stage=='recreated': assert bindings==baseline, 'Recreation changed website partition'
            if stage=='fresh-blocked':
                assert bindings['a1']!=baseline['a1'] and bindings['b']!=baseline['b'], 'Fresh case reused seeded store'
                assert bindings['h']==baseline['h'] and bindings['u']==baseline['u'], 'Host/control store replaced'
        elif event['event']=='load':
            assert policies is not None, 'Load before policy checkpoint'
            key=event['case']; assert key not in loads, 'Duplicate native load event'
            loads[key]=(event,bindings.copy(),policies.copy(),stage)
    assert set(loads)=={s['id'] for s in report['samples']}, 'Missing native load event'
    for sample in report['samples']:
        event,binding,policy,stage=loads[sample['id']]
        assert stage==sample['stage'], 'Wrong policy stage'
        assert sample[field]==binding[sample['view']]==event[field], 'Native partition mismatch'
        assert sample['policyAllows']==event['policyAllows']==policy[sample['owner']], 'Policy snapshot mismatch'
        assert sample['document']['href']==sample['nativeUrl'], 'Document/native URL mismatch'


def check_artifacts(report):
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    platform=report['platform']; metadata=report['build']
    paths=[ROOT/'page.html',ROOT/'build.py',*(ROOT/platform).rglob('*')]
    expected={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths) if p.is_file() and not any(x in {'build','.gradle'} for x in p.relative_to(ROOT).parts)}
    assert metadata['sources']==expected, 'Built source fingerprint differs from checkout'
    key='apkSha256' if platform=='android' else 'executableSha256'
    assert report['installedArtifactSha256']==metadata[key], 'Installed/built artifact mismatch'
    artifact=ROOT/('android/app/build/outputs/apk/debug/app-debug.apk' if platform=='android' else 'build/CookieSuppressionProbe.app/CookieSuppressionProbe')
    if artifact.exists(): assert sha(artifact)==metadata[key], 'Local artifact mismatch'
    config=ROOT/'build/assets/config.json'
    if config.exists(): assert sha(config)==metadata['fixtureConfigSha256'], 'Loaded fixture configuration mismatch'
    assert all(r['run']==report['run'] for r in report['requests']), 'Foreign server run included'
