"""The fixture's receipts and raw header fields are independent of any native client."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from fixture import make_servers


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.main, self.control = make_servers(self.folder, 0, 0, tls=False)
        self.threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (self.main, self.control)]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        for server in (self.main, self.control):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        self.tmp.cleanup()

    def get(self, path, headers=None, server=None, method='GET'):
        client = http.client.HTTPConnection('127.0.0.1', (server or self.main).server_port, timeout=5)
        client.request(method, path, headers=headers or {})
        response = client.getresponse()
        body = response.read()
        client.close()
        return response, body

    def rows(self):
        return [json.loads(line) for line in (self.folder / 'requests.jsonl').read_text().splitlines()]

    def test_each_set_cookie_is_sent_as_its_own_field_in_order(self):
        response, _ = self.get('/serve?run=test&case=multi')
        fields = response.headers.get_all('Set-Cookie')
        self.assertEqual(len(fields), 5)
        self.assertTrue(fields[0].startswith('t28h_plain=one'))
        self.assertIn('Expires=Wed, 21 Oct 2037', fields[2])

    def test_lowercase_case_really_sends_lowercase_header_names(self):
        response, _ = self.get('/serve?run=test&case=lowercase-names')
        self.assertIn('set-cookie', [name for name, _ in response.getheaders()])

    def test_redirect_returns_the_status_location_and_cookie_without_counting_a_target_hit(self):
        response, _ = self.get('/serve?run=test&case=redirect-302')
        self.assertEqual(response.status, 302)
        self.assertIn('/target?run=test&case=redirect-302', response.headers['Location'])
        self.assertIsNotNone(response.headers['Set-Cookie'])
        self.assertEqual([r for r in self.rows() if r['path'] == '/target'], [])

    def test_following_the_location_is_visible_as_a_target_hit(self):
        response, _ = self.get('/serve?run=test&case=redirect-302')
        self.get(response.headers['Location'])
        self.assertEqual(len([r for r in self.rows() if r['path'] == '/target' and r['case'] == 'redirect-302']), 1)

    def test_error_statuses_keep_their_cookie_and_body(self):
        response, body = self.get('/serve?run=test&case=status-404')
        self.assertEqual(response.status, 404)
        self.assertIsNotNone(response.headers['Set-Cookie'])
        self.assertIn(b'status-404', body)

    def test_challenge_asks_for_basic_credentials(self):
        response, _ = self.get('/serve?run=test&case=challenge-401')
        self.assertEqual(response.status, 401)
        self.assertIn('Basic', response.headers['WWW-Authenticate'])

    def test_challenge_scheme_is_selected_by_the_case(self):
        bearer, _ = self.get('/serve?run=test&case=challenge-bearer')
        self.assertIn('Bearer', bearer.headers['WWW-Authenticate'])
        plain, _ = self.get('/serve?run=test&case=challenge-plain')
        self.assertEqual(plain.status, 401)
        self.assertIsNone(plain.headers['WWW-Authenticate'])

    def test_cache_pair_is_one_url_with_a_cacheable_response(self):
        response, _ = self.get('/serve?run=test&case=cache-pair')
        self.assertIn('max-age', response.headers['Cache-Control'])

    def test_receipt_keeps_every_raw_cookie_field_and_does_not_echo_them(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.putrequest('GET', '/echo?run=test&case=attach-cookie')
        client.putheader('Cookie', 'a=sentinel')
        client.putheader('Cookie', 'b=sentinel')
        client.endheaders()
        body = client.getresponse().read()
        client.close()
        self.assertEqual(self.rows()[0]['cookieFields'], ['a=sentinel', 'b=sentinel'])
        self.assertNotIn(b'sentinel', body)

    def test_receipt_records_method_body_length_and_authorization_presence(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.request('POST', '/echo?run=test&case=attach-post', body=b'{"ok":true}', headers={'Authorization': 'Basic secret'})
        client.getresponse().read()
        client.close()
        row = self.rows()[0]
        self.assertEqual(row['method'], 'POST')
        self.assertEqual(row['bodyLength'], 11)
        self.assertIs(row['authorization'], True)
        self.assertNotIn('secret', json.dumps(row))

    def test_unknown_case_or_malformed_run_is_rejected_and_unrecorded(self):
        self.assertEqual(self.get('/serve?run=test&case=nope')[0].status, 400)
        self.assertEqual(self.get('/serve?run=BAD!&case=multi')[0].status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())

    def wait_held(self, case):
        for _ in range(200):
            _, status = self.get(f'/held?run=test&case={case}', server=self.control)
            if json.loads(status)['held']:
                return True
            time.sleep(0.01)
        return False

    def test_hold_headers_sends_nothing_until_release(self):
        result = {}

        def request():
            result['response'], _ = self.get('/serve?run=test&case=hold-headers')

        thread = threading.Thread(target=request)
        thread.start()
        self.assertTrue(self.wait_held('hold-headers'))
        self.assertNotIn('response', result)
        self.get('/release?run=test&case=hold-headers', server=self.control)
        thread.join(5)
        self.assertEqual(result['response'].status, 200)
        self.assertEqual([r['event'] for r in self.rows()], ['arrived', 'released'])

    def test_hold_body_sends_headers_first_then_the_body_after_release(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.request('GET', '/serve?run=test&case=hold-body')
        response = client.getresponse()
        self.assertIsNotNone(response.headers['Set-Cookie'])
        self.assertTrue(self.wait_held('hold-body'))
        self.get('/release?run=test&case=hold-body', server=self.control)
        self.assertIn(b'hold-body', response.read())
        client.close()

    def test_hold_body_can_send_some_body_bytes_before_holding(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.request('GET', '/serve?run=test&case=hold-body-first-kilobyte')
        response = client.getresponse()
        self.assertEqual(len(response.read(1024)), 1024)
        self.assertTrue(self.wait_held('hold-body-first-kilobyte'))
        self.get('/release?run=test&case=hold-body-first-kilobyte', server=self.control)
        self.assertIn(b'hold-body-first-kilobyte', response.read())
        client.close()

    def test_nosniff_variant_sends_the_header(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.request('GET', '/serve?run=test&case=hold-body-nosniff')
        response = client.getresponse()
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertTrue(self.wait_held('hold-body-nosniff'))
        self.get('/release?run=test&case=hold-body-nosniff', server=self.control)
        response.read()
        client.close()

    def test_control_endpoints_are_not_reachable_on_the_service_listener(self):
        self.assertEqual(self.get('/release?run=test&case=hold-headers')[0].status, 404)
        self.assertEqual(self.get('/held?run=test&case=hold-headers')[0].status, 404)


if __name__ == '__main__':
    unittest.main()
