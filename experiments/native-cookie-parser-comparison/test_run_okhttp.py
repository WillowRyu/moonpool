"""The probe receives vectors through base64 fields, so no byte of a line can be lost or reinterpreted on the way."""
import base64
import unittest
from run_okhttp import encode_rows

NOW_MS = 1_800_000_000_000


class Encoding(unittest.TestCase):
    def test_every_field_round_trips_including_control_and_non_ascii_bytes(self):
        vectors = [{'id': 'X', 'url': 'https://a.example/', 'line': 'a=é\u0001\t;', 'checks': ['https://a.example/', 'https://b.example/']}]
        (row,) = encode_rows(vectors)
        identifier, url, line, checks = row.split('\t')
        decode = lambda text: base64.b64decode(text).decode('utf-8')
        self.assertEqual(identifier, 'X')
        self.assertEqual(decode(url), 'https://a.example/')
        self.assertEqual(decode(line), 'a=é\u0001\t;')
        self.assertEqual(decode(checks).split('\n'), ['https://a.example/', 'https://b.example/'])

    def test_no_checks_is_an_empty_field(self):
        (row,) = encode_rows([{'id': 'Y', 'url': 'https://a.example/', 'line': 'a=1', 'checks': []}])
        self.assertEqual(row.split('\t')[3], '')


if __name__ == '__main__':
    unittest.main()
