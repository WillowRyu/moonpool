"""The fixture's receipts are the witness for what actually left the client."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from fixture import EXPECTED_AUTHORIZATION, make_server


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

    def get(self, path, headers=None, method='GET'):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        client.request(method, path, headers=headers or {})
        response = client.getresponse()
        response.read()
        client.close()
        return response

    def rows(self):
        return [json.loads(line) for line in (self.folder / 'requests.jsonl').read_text().splitlines()]

    def test_receipt_keeps_the_exact_cookie_fields(self):
        self.get('/echo?run=test&case=handler-attached', {'Cookie': 'broker_selected=one'})
        self.assertEqual(self.rows()[0]['cookieFields'], ['broker_selected=one'])

    def test_receipt_keeps_the_exact_authorization_value(self):
        self.get('/serve?run=test&case=auth-basic-get', {'Authorization': 'Basic abc'})
        self.assertEqual(self.rows()[0]['authorizationValue'], 'Basic abc')

    def test_receipt_shows_no_authorization_when_none_was_sent(self):
        self.get('/echo?run=test&case=control-plain')
        self.assertIsNone(self.rows()[0]['authorizationValue'])

    def test_challenge_names_the_scheme_the_case_asks_for(self):
        self.assertEqual(self.get('/serve?run=test&case=auth-bearer').getheader('WWW-Authenticate'), 'Bearer realm="t28"')

    def test_challenge_can_omit_the_header_entirely(self):
        response = self.get('/serve?run=test&case=auth-no-scheme')
        self.assertEqual(response.status, 401)
        self.assertIsNone(response.getheader('WWW-Authenticate'))

    def test_only_the_host_fixture_credentials_are_accepted(self):
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-get').status, 401)
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-get', {'Authorization': 'Basic wrong'}).status, 401)
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-get', {'Authorization': EXPECTED_AUTHORIZATION}).status, 200)

    def test_a_rejecting_case_stays_401_even_with_the_right_credentials(self):
        self.assertEqual(self.get('/serve?run=test&case=auth-basic-always-401', {'Authorization': EXPECTED_AUTHORIZATION}).status, 401)

    def test_challenge_and_accepted_responses_set_different_cookies(self):
        challenge = self.get('/serve?run=test&case=combined-basic-cookie')
        accepted = self.get('/serve?run=test&case=combined-basic-cookie', {'Authorization': EXPECTED_AUTHORIZATION})
        self.assertIn('t28g_challenge', challenge.getheader('Set-Cookie'))
        self.assertIn('t28g_accepted', accepted.getheader('Set-Cookie'))

    def test_redirect_points_at_a_counted_target(self):
        response = self.get('/serve?run=test&case=handler-redirect')
        self.assertEqual(response.status, 302)
        self.get(response.getheader('Location'))
        self.assertEqual([row['path'] for row in self.rows()], ['/serve', '/target'])

    def test_request_body_length_is_recorded_for_every_attempt(self):
        self.get('/serve?run=test&case=auth-basic-post', {'Content-Length': '0'}, method='POST')
        self.assertEqual(self.rows()[0]['method'], 'POST')
        self.assertEqual(self.rows()[0]['bodyLength'], 0)

    def test_unknown_case_is_refused_and_leaves_no_receipt(self):
        self.assertEqual(self.get('/echo?run=test&case=nope').status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
