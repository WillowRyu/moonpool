"""The fixture's receipts are the witness for what actually left the client."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from fixture import EXPECTED_AUTHORIZATION, make_servers


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

    def test_receipt_keeps_exact_cookie_and_authorization_values(self):
        self.get('/echo?run=test&case=handler-attached', {'Cookie': 'broker_selected=one', 'Authorization': 'Bearer x'})
        self.assertEqual(self.rows()[0]['cookieFields'], ['broker_selected=one'])
        self.assertEqual(self.rows()[0]['authorizationValue'], 'Bearer x')

    def test_each_set_cookie_is_its_own_field_in_order(self):
        response, _ = self.get('/serve?run=test&case=multi')
        fields = response.headers.get_all('Set-Cookie')
        self.assertEqual(len(fields), 5)
        self.assertIn('Expires=Wed, 21 Oct 2037', fields[2])

    def test_lowercase_case_really_sends_lowercase_names(self):
        response, _ = self.get('/serve?run=test&case=lowercase-names')
        self.assertIn('set-cookie', [name for name, _ in response.getheaders()])

    def test_only_the_fixture_credential_is_accepted(self):
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-get')[0].status, 401)
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-get', {'Authorization': EXPECTED_AUTHORIZATION})[0].status, 200)

    def test_challenge_uses_the_case_scheme_or_no_header(self):
        self.assertEqual(self.get('/serve?run=test&case=auth-digest')[0].getheader('WWW-Authenticate'), 'Digest realm="t28"')
        self.assertIsNone(self.get('/serve?run=test&case=auth-no-scheme')[0].getheader('WWW-Authenticate'))

    def test_redirect_points_at_a_counted_target(self):
        response, _ = self.get('/serve?run=test&case=redirect-307')
        self.assertEqual(response.status, 307)
        self.get(response.getheader('Location'))
        self.assertEqual([row['path'] for row in self.rows()], ['/serve', '/target'])

    def test_retry_after_is_sent_exactly_as_the_case_says(self):
        self.assertEqual(self.get('/serve?run=test&case=resend-503-zero-get')[0].getheader('Retry-After'), '0')
        self.assertEqual(self.get('/serve?run=test&case=resend-503-delayed')[0].getheader('Retry-After'), '5')
        self.assertIsNone(self.get('/serve?run=test&case=resend-408')[0].getheader('Retry-After'))

    def test_closed_connection_case_records_the_request_and_sends_no_response(self):
        with self.assertRaises(http.client.RemoteDisconnected):
            self.get('/serve?run=test&case=resend-closed-connection')
        self.assertEqual(len(self.rows()), 1)

    def test_paired_cache_case_counts_both_requests_under_one_name(self):
        self.get('/serve?run=test&case=cache-pair')
        self.get('/serve?run=test&case=cache-pair')
        self.assertEqual([row['case'] for row in self.rows()], ['cache-pair', 'cache-pair'])

    def test_hold_body_sends_headers_first_and_records_the_release(self):
        client = http.client.HTTPConnection('127.0.0.1', self.main.server_port, timeout=5)
        client.request('GET', '/serve?run=test&case=hold-body')
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        for _ in range(50):
            if json.loads(self.get('/held?run=test&case=hold-body', server=self.control)[1])['held']:
                break
            time.sleep(0.02)
        self.get('/release?run=test&case=hold-body', server=self.control)
        response.read()
        client.close()
        self.assertEqual([row['event'] for row in self.rows()], ['arrived', 'released'])

    def test_unknown_case_is_refused_without_a_receipt(self):
        self.assertEqual(self.get('/echo?run=test&case=nope')[0].status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
