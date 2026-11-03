"""The fixture observes cookies independently of anything the native app reports."""
import http.client
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
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

    def test_header_write_sets_only_the_case_cookie_and_records_context(self):
        response, _ = self.get(
            '/page?run=test&case=xsite-header-partitioned&step=seed&write=header',
            {'Cookie': 't28p_public=sentinel', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Dest': 'iframe'},
        )
        cookie = response.headers['Set-Cookie']
        self.assertIn('t28p_xsite-header-partitioned=public_xsite-header-partitioned', cookie)
        self.assertIn('Partitioned', cookie)
        self.assertIn('Secure', cookie)
        row = self.rows()[0]
        self.assertEqual(row['cookie'], 't28p_public=sentinel')
        self.assertEqual(row['secFetchSite'], 'cross-site')
        self.assertEqual(row['secFetchDest'], 'iframe')
        self.assertEqual(row['step'], 'seed')

    def test_read_step_never_sets_a_cookie(self):
        response, _ = self.get('/page?run=test&case=xsite-header-partitioned&step=read-same&write=none')
        self.assertIsNone(response.headers['Set-Cookie'])

    def test_script_page_carries_the_writer_but_header_does_not(self):
        response, body = self.get('/page?run=test&case=xsite-script-partitioned&step=seed&write=script')
        self.assertIsNone(response.headers['Set-Cookie'])
        self.assertIn(b't28p_xsite-script-partitioned', body)

    def test_received_cookie_is_not_echoed_into_the_page(self):
        _, body = self.get('/page?run=test&case=empty&step=read-same&write=none', {'Cookie': 'a=sentinel'})
        self.assertNotIn(b'sentinel', body)

    def test_unknown_case_or_malformed_run_is_rejected_and_unrecorded(self):
        self.assertEqual(self.get('/page?run=test&case=nope&step=seed&write=none')[0].status, 400)
        self.assertEqual(self.get('/page?run=BAD!&case=empty&step=seed&write=none')[0].status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())

    def test_frame_page_is_static_and_served_without_cookie_side_effects(self):
        response, body = self.get('/frame?target=https%3A%2F%2Fexample.invalid%2F')
        self.assertEqual(response.status, 200)
        self.assertIsNone(response.headers['Set-Cookie'])
        self.assertNotIn(b'example.invalid', body)

    def test_held_response_waits_for_release_then_sets_the_cookie(self):
        result = {}

        def request():
            result['response'], _ = self.get('/hold?run=test&case=hold-navigation-deny&step=hold')

        thread = threading.Thread(target=request)
        thread.start()
        for _ in range(100):
            _, status = self.get('/held?run=test&case=hold-navigation-deny')
            if json.loads(status)['held']:
                break
            threading.Event().wait(0.01)
        self.assertTrue(json.loads(status)['held'])
        self.assertNotIn('response', result)
        self.assertEqual(json.loads(self.get('/release?run=test&case=hold-navigation-deny')[1])['released'], True)
        thread.join(5)
        self.assertIn('t28w_hold-navigation-deny=public', result['response'].headers['Set-Cookie'])
        events = [r['event'] for r in self.rows() if r['path'] == '/hold']
        self.assertEqual(events, ['arrived', 'released'])

    def test_release_records_whether_the_client_already_closed(self):
        client = socket.create_connection(('127.0.0.1', self.server.server_port), timeout=5)
        client.sendall(b'GET /hold?run=test&case=hold-navigation-teardown&step=hold HTTP/1.0\r\n\r\n')
        for _ in range(100):
            if json.loads(self.get('/held?run=test&case=hold-navigation-teardown')[1])['held']:
                break
            time.sleep(0.01)
        client.close()
        time.sleep(0.05)
        self.get('/release?run=test&case=hold-navigation-teardown')
        for _ in range(100):
            released = [r for r in self.rows() if r['event'] == 'released']
            if released:
                break
            time.sleep(0.01)
        self.assertTrue(released[0]['clientClosed'])

    def test_release_of_a_connected_client_is_not_reported_closed(self):
        thread = threading.Thread(target=lambda: self.get('/hold?run=test&case=hold-fetch-deny&step=hold'))
        thread.start()
        for _ in range(100):
            if json.loads(self.get('/held?run=test&case=hold-fetch-deny')[1])['held']:
                break
            time.sleep(0.01)
        self.get('/release?run=test&case=hold-fetch-deny')
        thread.join(5)
        self.assertFalse(next(r for r in self.rows() if r['event'] == 'released')['clientClosed'])

    def test_warmup_seed_steps_set_one_first_party_and_one_partitioned_cookie(self):
        first, _ = self.get('/page?run=test&case=warmup-none-1&step=seed-first&write=header')
        partitioned, _ = self.get('/page?run=test&case=warmup-none-1&step=seed-xsite&write=header')
        self.assertIn('t28u_warmup-none-1_first=public', first.headers['Set-Cookie'])
        self.assertNotIn('Partitioned', first.headers['Set-Cookie'])
        self.assertIn('t28u_warmup-none-1_partitioned=public', partitioned.headers['Set-Cookie'])
        self.assertIn('Partitioned', partitioned.headers['Set-Cookie'])

    def test_warmup_witness_steps_never_set_a_cookie(self):
        response, _ = self.get('/page?run=test&case=warmup-none-1&step=witness-first&write=none')
        self.assertIsNone(response.headers['Set-Cookie'])

    def test_held_status_is_false_before_a_request_arrives(self):
        self.assertFalse(json.loads(self.get('/held?run=test&case=hold-fetch-deny')[1])['held'])

    def test_burst_writer_page_names_each_write_uniquely(self):
        _, body = self.get('/writer?run=test&case=burst-document-deny&step=burst&api=document')
        self.assertIn(b't28w_burst-document-deny_', body)
        self.assertIn(b'window.writes', body)


if __name__ == '__main__':
    unittest.main()
