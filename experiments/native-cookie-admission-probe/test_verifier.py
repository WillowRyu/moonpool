import json
from pathlib import Path
import unittest
from verify_results import integrity, verify

ROOT=Path(__file__).resolve().parent
CASES=json.loads((ROOT/'presence_cases.json').read_text())
def fixture():
    samples=[]
    for c in CASES:
        for phase in ['initial','reopened']:
            names=['t28a_'+c['id']] if c['present'] else []
            samples.append({'case':c['id'],'phase':phase,'partition':c['id'],'presence':c['present'],'policyAllows':False,
                            'beforeNames':names,'afterNames':names,'beforeCookies':names,'afterCookies':names,
                            'storage':{'local':c['id'],'indexed':c['id']},'expectedStorage':c['id'],
                            'decision':'refused' if c['present'] else 'admitted','loadCalls':0 if c['present'] else 1,
                            'guestMarker':None if c['present'] else c['id'],'visibleJsCookie':'',
                            'hostPolicyAllows':True,'hostCookiePresent':True,'hostCookie':'t28a_host=public_host'})
    return {'complete':True,'errors':[],'samples':samples,'guestResources':['https://fixture.invalid/guest?token=empty']*2,'gateCases':json.loads((ROOT/'gate_cases.json').read_text()),
            'requests':[{'case':c['id'],'path':'/hidden/echo' if c['id']=='offpath' else '/echo',
                         'cookie':'t28a_'+c['id']+'=public_'+c['id'] if c['present'] else ''} for c in CASES]}

class EvidenceTests(unittest.TestCase):
    def test_native_load_error_is_not_a_clean_measurement(self):
        r=fixture();r['errors']=[{'tlsError':1}]
        with self.assertRaises(AssertionError):verify(r)
    def test_retained_report_cannot_omit_gate_source_fingerprint(self):
        r=json.loads((ROOT/'results/android-first.json').read_text())
        key=next(k for k in r['build']['sources'] if k.endswith('/AdmissionGate.java'))
        r['build']['sources'].pop(key)
        with self.assertRaises(AssertionError):integrity(r)
    def test_host_cookie_value_must_survive(self):
        r=fixture();r['samples'][0]['hostCookie']=''
        with self.assertRaises(AssertionError):verify(r)
    def test_refused_guest_resource_cannot_hide_behind_report_flags(self):
        r=fixture();r['guestResources'].append('https://fixture.invalid/guest?token=ordinary')
        with self.assertRaises(AssertionError):verify(r)
    def test_complete_observations(self):self.assertGreater(verify(fixture()),100)
    def test_missing_seed_does_not_prove_cookie_absence(self):
        r=fixture();r['samples'][2]['beforeNames']=[]
        with self.assertRaises(AssertionError):verify(r)
    def test_refused_guest_must_not_load(self):
        r=fixture();r['samples'][2]['loadCalls']=1
        with self.assertRaises(AssertionError):verify(r)
    def test_refusal_preserves_data(self):
        r=fixture();r['samples'][2]['storage']['indexed']='lost'
        with self.assertRaises(AssertionError):verify(r)
    def test_stale_callback_cannot_load(self):
        r=fixture();r['gateCases']['replacement'].append('load:old')
        with self.assertRaises(AssertionError):verify(r)
    def test_server_control_and_host_survive(self):
        r=fixture();r['requests'][1]['cookie']=''
        with self.assertRaises(AssertionError):verify(r)
        r=fixture();r['samples'][2]['hostCookiePresent']=False
        with self.assertRaises(AssertionError):verify(r)
    def test_same_partition_reopened(self):
        r=fixture();r['samples'][3]['partition']='replacement'
        with self.assertRaises(AssertionError):verify(r)

if __name__=='__main__':unittest.main()
