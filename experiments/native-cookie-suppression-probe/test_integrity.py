"""Native binding and policy order cannot be supplied by guest result fields."""
import unittest
from integrity import check_bindings


def fixture():
    events=[{'event':'created','view':v,'profile':'a' if v in ('a1','a2') else v} for v in ('a1','a2','b','h','u')]
    events += [{'event':'policy','stage':'baseline','values':{o:True for o in ('a','b','h','u')}},
               {'event':'load','case':'baseline-a1-remote','profile':'a','policyAllows':True}]
    sample={'id':'baseline-a1-remote','stage':'baseline','view':'a1','owner':'a','profile':'a','policyAllows':True,
            'nativeUrl':'https://localhost:123/page','document':{'href':'https://localhost:123/page'}}
    return {'platform':'android','events':events,'samples':[sample]}


class IntegrityTests(unittest.TestCase):
    def test_native_binding_matches_loaded_sample(self): check_bindings(fixture())
    def test_wrong_native_partition_rejected(self):
        r=fixture(); r['samples'][0]['profile']='b'
        with self.assertRaises(AssertionError): check_bindings(r)
    def test_policy_must_precede_load(self):
        r=fixture(); r['events'][-2:]=list(reversed(r['events'][-2:]))
        with self.assertRaises(AssertionError): check_bindings(r)
    def test_same_app_views_must_share_and_host_must_differ(self):
        for index in (1,3):
            r=fixture(); r['events'][index]['profile']='b'
            with self.assertRaises(AssertionError): check_bindings(r)


if __name__=='__main__': unittest.main()
