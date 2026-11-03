"""The fixture observes cookies independently of anything the native app reports."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from fixture import make_server


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.server = make_server(self.folder, 0, tls=False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def get(self, path, headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        client.request('GET', path, headers=headers or {})
        response = client.getresponse()
        body = response.read()
        client.close()
        return response, body

    def rows(self):
        return [json.loads(line) for line in (self.folder / 'requests.jsonl').read_text().splitlines()]

    def test_seed_step_sets_the_kind_cookie_under_its_own_name(self):
        response, _ = self.get('/page?run=test&case=httponly-denied-r1&step=seed&write=header')
        cookie = response.headers['Set-Cookie']
        self.assertTrue(cookie.startswith('t28e_httponly-denied=public;'))
        self.assertIn('HttpOnly', cookie)

    def test_expire_step_removes_with_max_age_zero(self):
        response, _ = self.get('/page?run=test&case=server-expired-n2&step=expire&write=header')
        self.assertIn('t28e_server-expired=gone', response.headers['Set-Cookie'])
        self.assertIn('Max-Age=0', response.headers['Set-Cookie'])

    def test_witness_steps_never_set_a_cookie(self):
        response, _ = self.get('/page?run=test&case=cookie-denied-r1&step=witness-first&write=none')
        self.assertIsNone(response.headers['Set-Cookie'])

    def test_a_kind_without_a_cookie_sets_nothing_even_when_asked(self):
        response, _ = self.get('/page?run=test&case=network-visit-r1&step=seed&write=header')
        self.assertIsNone(response.headers['Set-Cookie'])

    def test_receipt_records_cookie_and_context_without_echoing_it(self):
        _, body = self.get('/page?run=test&case=cookie-denied-r1&step=witness-xsite&write=none',
                           {'Cookie': 't28e_cookie-denied=sentinel', 'Sec-Fetch-Site': 'cross-site'})
        row = self.rows()[0]
        self.assertEqual(row['cookie'], 't28e_cookie-denied=sentinel')
        self.assertEqual(row['secFetchSite'], 'cross-site')
        self.assertEqual(row['case'], 'cookie-denied-r1')
        self.assertNotIn(b'sentinel', body)

    def test_unknown_store_or_malformed_run_is_rejected_and_unrecorded(self):
        self.assertEqual(self.get('/page?run=test&case=nope-r1&step=seed&write=none')[0].status, 400)
        self.assertEqual(self.get('/page?run=BAD!&case=cookie-denied-r1&step=seed&write=none')[0].status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())

    def test_frame_page_is_static_and_sets_nothing(self):
        response, body = self.get('/frame?target=https%3A%2F%2Fexample.invalid%2F')
        self.assertEqual(response.status, 200)
        self.assertIsNone(response.headers['Set-Cookie'])
        self.assertNotIn(b'example.invalid', body)


if __name__ == '__main__':
    unittest.main()
