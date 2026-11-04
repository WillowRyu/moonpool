"""The fixture's receipts are the witness for what actually left the broker."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import urlsplit
from fixture import EXPECTED_AUTHORIZATION, make_servers, serve_for


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.service, self.second, self.control = self.servers = make_servers(self.folder, 0, 0, 0, tls=False)
        self.threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in self.servers]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        self.tmp.cleanup()

    def get(self, case, step, headers=None, server=None, path='/s', method='GET'):
        target = f'{path}?run=fixture-test&case={case}&step={step}'
        client = http.client.HTTPConnection('127.0.0.1', (server or self.service).server_port, timeout=5)
        client.request(method, target, headers=headers or {})
        response = client.getresponse()
        body = response.read()
        client.close()
        return response, body

    def rows(self):
        return [json.loads(line) for line in (self.folder / 'requests.jsonl').read_text().splitlines()]

    def in_background(self, case, step):
        found = {}

        def work():
            found['response'], found['body'] = self.get(case, step)

        thread = threading.Thread(target=work)
        thread.start()
        return thread, found

    def control_ask(self, path, case, step):
        return self.get(case, step, server=self.control, path=path)

    def wait_held(self, case, step):
        for _ in range(100):
            _, body = self.control_ask('/held', case, step)
            if json.loads(body)['held']:
                return True
            threading.Event().wait(0.02)
        return False

    def test_unknown_step_is_refused_without_a_receipt(self):
        response, _ = self.get('c00-plain', 'nothing')
        self.assertEqual(response.status, 400)
        self.assertFalse((self.folder / 'requests.jsonl').exists())

    def test_receipt_keeps_exact_cookie_and_authorization_and_listener(self):
        self.get('c00-plain', 'plain', {'Cookie': 'a=1; b=2', 'Authorization': 'Bearer x'}, server=self.second)
        row = self.rows()[0]
        self.assertEqual(row['cookieFields'], ['a=1; b=2'])
        self.assertEqual(row['authorization'], 'Bearer x')
        self.assertEqual(row['listener'], 'service2')
        self.assertEqual((row['case'], row['step'], row['event']), ('c00-plain', 'plain', 'arrived'))

    def test_set_cookie_fields_stay_separate_and_never_reach_the_body(self):
        response, body = self.get('c03-httponly', 'login')
        self.assertEqual(response.headers.get_all('Set-Cookie'), serve_for('c03-httponly', 'login')['setCookie'])
        self.assertNotIn(b'protected-marker', body)

    def test_lowercase_header_name(self):
        response, _ = self.get('c03-one-pipeline', 'lower')
        self.assertIn('set-cookie', [name for name, _ in response.getheaders()])

    def test_redirect_location_names_the_target_step_on_the_chosen_host(self):
        response, _ = self.get('c06-redirect-302', 'moved')
        self.assertEqual(response.status, 302)
        url = urlsplit(response.headers['Location'])
        self.assertEqual(url.path, '/s')
        self.assertIn('step=target', url.query)
        response, _ = self.get('c06-redirect-forbidden-then-explicit', 'moved')
        self.assertTrue(response.headers['Location'].startswith('https://127.0.0.1:'))

    def test_redirect_target_counts_as_a_receipt(self):
        self.get('c06-redirect-302', 'target')
        self.assertEqual(self.rows()[0]['step'], 'target')

    def test_cookies_can_differ_per_attempt(self):
        first, _ = self.get('c06-basic-401-cookies', 'challenged')
        second, _ = self.get('c06-basic-401-cookies', 'challenged')
        self.assertEqual(first.headers['Set-Cookie'], 'attempt=1; Path=/; Secure')
        self.assertEqual(second.headers['Set-Cookie'], 'attempt=2; Path=/; Secure')

    def test_challenge_accepts_only_the_public_fixture_credential(self):
        response, _ = self.get('c00-host-positive', 'hostAuth')
        self.assertEqual((response.status, response.headers['WWW-Authenticate']), (401, 'Basic realm="t28"'))
        response, _ = self.get('c00-host-positive', 'hostAuth', {'Authorization': EXPECTED_AUTHORIZATION})
        self.assertEqual(response.status, 200)

    def test_hold_headers_answers_nothing_until_released(self):
        thread, found = self.in_background('c07-header-order', 'first')
        self.assertTrue(self.wait_held('c07-header-order', 'first'))
        self.assertNotIn('response', found)
        self.control_ask('/release', 'c07-header-order', 'first')
        thread.join(5)
        self.assertEqual(found['response'].status, 200)
        self.assertEqual([row['event'] for row in self.rows()], ['arrived', 'released'])

    def test_hold_body_delivers_headers_and_one_byte_first(self):
        client = http.client.HTTPConnection('127.0.0.1', self.service.server_port, timeout=5)
        client.request('GET', '/s?run=fixture-test&case=c08-reset-after-headers&step=old')
        response = client.getresponse()
        self.assertEqual(response.headers['Set-Cookie'], 'sid=committed; Path=/; Secure')
        self.assertEqual(response.read(1), b' ')
        self.assertTrue(self.wait_held('c08-reset-after-headers', 'old'))
        self.control_ask('/release', 'c08-reset-after-headers', 'old')
        self.assertEqual(json.loads(response.read())['ok'], True)
        client.close()

    def test_abort_closes_inside_the_declared_body(self):
        client = http.client.HTTPConnection('127.0.0.1', self.service.server_port, timeout=5)
        client.request('GET', '/s?run=fixture-test&case=c06-body-failure-keeps-cookie&step=broken')
        response = client.getresponse()
        with self.assertRaises(http.client.IncompleteRead):
            response.read()
        client.close()

    def test_empty_response_has_no_body(self):
        response, body = self.get('c06-empty-204', 'empty', method='POST')
        self.assertEqual((response.status, body), (204, b''))

    def test_retry_after_is_sent_as_declared(self):
        response, _ = self.get('c06-retry-after-zero', 'busy', method='POST')
        self.assertEqual((response.status, response.headers['Retry-After']), (503, '0'))

    def test_deep_path_is_served_and_recorded(self):
        self.get('c03-same-name-paths', 'deep', path='/deep/s')
        self.assertEqual(self.rows()[0]['path'], '/deep/s')

    def test_hold_that_times_out_is_not_recorded_as_released(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            service, second, control = make_servers(folder, 0, 0, 0, tls=False, hold_seconds=0.05)
            thread = threading.Thread(target=service.serve_forever, daemon=True)
            thread.start()
            try:
                self.get('c07-header-order', 'first', server=service)
            finally:
                service.shutdown()
                thread.join()
                for server in (service, second, control):
                    server.server_close()
            events = [json.loads(line)['event'] for line in (folder / 'requests.jsonl').read_text().splitlines()]
        self.assertEqual(events, ['arrived', 'holdTimedOut'])

    def test_delay_waits_before_answering(self):
        with mock.patch('fixture.time.sleep') as sleep:
            response, _ = self.get('c06-slow-response', 'slow')
        self.assertEqual(response.status, 200)
        sleep.assert_called_once_with(12)

    def test_every_supported_method_is_served_and_recorded(self):
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            response, _ = self.get('c06-methods', 'm' + method, method=method)
            self.assertEqual(response.status, 200)
        self.assertEqual([row['method'] for row in self.rows()], ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])

    def test_head_declares_a_length_and_sends_no_body(self):
        response, body = self.get('c06-methods', 'mHEAD', method='HEAD')
        self.assertEqual((response.status, body), (200, b''))
        self.assertGreater(int(response.headers['Content-Length']), 0)

    def test_control_is_not_on_the_service_listener(self):
        response, _ = self.get('c07-header-order', 'first', path='/release')
        self.assertEqual(response.status, 404)
        response, _ = self.get('c07-header-order', 'first', server=self.control, path='/s')
        self.assertEqual(response.status, 404)


if __name__ == '__main__':
    unittest.main()
