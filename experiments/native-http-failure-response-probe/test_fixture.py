"""The fixture's receipts are the witness for what each attempt was actually served."""
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

    def get(self, case, run='ios-test', path='/s', method='GET', body=None, headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        client.request(method, f'{path}?run={run}&case={case}', body=body, headers=headers or {})
        response = client.getresponse()
        text = response.read()
        client.close()
        return response, text

    def rows(self):
        return [json.loads(line) for line in (self.folder / 'requests.jsonl').read_text().splitlines()]

    def test_each_arrival_gets_its_own_cookie_and_is_recorded(self):
        first, _ = self.get('basic-cookie-per-attempt')
        second, _ = self.get('basic-cookie-per-attempt')
        self.assertEqual(first.headers['Set-Cookie'], 'attempt=1; Path=/; Secure')
        self.assertEqual(second.headers['Set-Cookie'], 'attempt=2; Path=/; Secure')
        self.assertEqual([(row['arrival'], row['served']) for row in self.rows()],
                         [(1, ['attempt=1; Path=/; Secure']), (2, ['attempt=2; Path=/; Secure'])])

    def test_attempts_are_counted_per_run(self):
        self.get('basic-cookie-per-attempt', run='ios-first')
        response, _ = self.get('basic-cookie-per-attempt', run='ios-repeat')
        self.assertEqual(response.headers['Set-Cookie'], 'attempt=1; Path=/; Secure')

    def test_an_attempt_can_serve_no_cookie(self):
        self.get('basic-first-attempt-only')
        response, _ = self.get('basic-first-attempt-only')
        self.assertIsNone(response.headers['Set-Cookie'])
        self.assertEqual(self.rows()[1]['served'], [])

    def test_two_fields_stay_separate(self):
        response, _ = self.get('basic-two-fields')
        self.assertEqual(response.headers.get_all('Set-Cookie'), ['a=1; Path=/; Secure', 'b=2; Path=/; Secure; HttpOnly'])

    def test_challenge_header_follows_the_scheme(self):
        response, _ = self.get('basic-no-cookie')
        self.assertEqual((response.status, response.headers['WWW-Authenticate']), (401, 'Basic realm="t28"'))
        response, _ = self.get('control-bearer')
        self.assertEqual((response.status, response.headers['WWW-Authenticate']), (401, 'Bearer realm="t28"'))
        response, _ = self.get('control-no-challenge')
        self.assertEqual((response.status, response.headers['WWW-Authenticate']), (401, None))

    def test_body_names_the_arrival_it_came_from(self):
        self.get('basic-no-cookie')
        _, body = self.get('basic-no-cookie')
        self.assertEqual(json.loads(body), {'case': 'basic-no-cookie', 'arrival': 2})

    def test_receipt_keeps_method_body_length_and_authorization(self):
        self.get('basic-post', method='POST', body='{}', headers={'Authorization': 'Bearer guest-owned'})
        row = self.rows()[0]
        self.assertEqual((row['method'], row['bodyLength'], row['authorization']), ('POST', 2, 'Bearer guest-owned'))

    def test_unknown_case_or_path_is_refused_without_a_receipt(self):
        self.assertEqual(self.get('nothing')[0].status, 404)
        self.assertEqual(self.get('control-plain', path='/other')[0].status, 404)
        self.assertEqual(self.get('control-plain', run='BAD')[0].status, 404)
        self.assertFalse((self.folder / 'requests.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
