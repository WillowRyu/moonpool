"""iOS reports what HTTPCookie parsed and what a per-app cookie storage kept; the view must not hide either."""
import unittest
from compare import SESSION_SENTINEL, ios_view

NOW_MS = 1_800_000_000_000


def cookie(**fields):
    base = {'name': 'a', 'value': '1', 'domain': 'api.example.com', 'path': '/', 'secure': False, 'httpOnly': False,
            'sessionOnly': True, 'expiresMs': None, 'sameSite': None}
    base.update(fields)
    return base


class View(unittest.TestCase):
    def test_nothing_parsed_is_not_accepted(self):
        self.assertEqual(ios_view({'id': 'X', 'parsed': [], 'stored': [], 'sends': []}, NOW_MS), {'id': 'X', 'accepted': False, 'count': 0})

    def test_a_host_only_session_cookie(self):
        view = ios_view({'id': 'X', 'parsed': [cookie()], 'stored': [cookie()], 'sends': [True]}, NOW_MS)
        self.assertTrue(view['accepted'])
        self.assertEqual(view['cookie']['domain'], 'api.example.com')
        self.assertTrue(view['cookie']['hostOnly'])
        self.assertFalse(view['cookie']['persistent'])
        self.assertEqual(view['cookie']['expiresAt'], SESSION_SENTINEL)
        self.assertEqual(view['sends'], [True])
        self.assertEqual(view['count'], 1)

    def test_a_leading_dot_marks_a_domain_cookie_and_is_removed(self):
        dotted = cookie(domain='.example.com')
        view = ios_view({'id': 'X', 'parsed': [dotted], 'stored': [dotted], 'sends': []}, NOW_MS)
        self.assertEqual(view['cookie']['domain'], 'example.com')
        self.assertFalse(view['cookie']['hostOnly'])

    def test_the_stored_cookie_wins_so_a_storage_cap_shows(self):
        parsed = cookie(sessionOnly=False, expiresMs=NOW_MS + 730 * 86400000)
        stored = cookie(sessionOnly=False, expiresMs=NOW_MS + 400 * 86400000)
        view = ios_view({'id': 'X', 'parsed': [parsed], 'stored': [stored], 'sends': []}, NOW_MS)
        self.assertEqual(view['cookie']['expiresAt'], NOW_MS + 400 * 86400000)
        self.assertEqual(view['parsedExpiresAt'], NOW_MS + 730 * 86400000)

    def test_an_expired_cookie_is_a_deletion_even_though_storage_keeps_nothing(self):
        expired = cookie(sessionOnly=False, expiresMs=NOW_MS - 1000)
        view = ios_view({'id': 'X', 'parsed': [expired], 'stored': [], 'sends': []}, NOW_MS)
        self.assertTrue(view['accepted'])
        self.assertEqual(view['cookie']['expiresAt'], NOW_MS - 1000)

    def test_parsed_but_refused_by_storage_is_not_accepted(self):
        view = ios_view({'id': 'X', 'parsed': [cookie()], 'stored': [], 'sends': []}, NOW_MS)
        self.assertFalse(view['accepted'])
        self.assertEqual(view['refusedBy'], 'storage')

    def test_several_parsed_cookies_are_counted(self):
        view = ios_view({'id': 'X', 'parsed': [cookie(), cookie(name='b')], 'stored': [cookie(), cookie(name='b')], 'sends': []}, NOW_MS)
        self.assertEqual(view['count'], 2)
        self.assertEqual(view['cookie']['name'], 'a')

    def test_same_site_is_lowercased_when_reported(self):
        view = ios_view({'id': 'X', 'parsed': [cookie(sameSite='lax')], 'stored': [cookie(sameSite='lax')], 'sends': []}, NOW_MS)
        self.assertEqual(view['cookie']['sameSite'], 'lax')
        view = ios_view({'id': 'X', 'parsed': [cookie()], 'stored': [cookie()], 'sends': []}, NOW_MS)
        self.assertNotIn('sameSite', view['cookie'])

    def test_an_expiry_at_the_parsing_clock_is_a_deletion(self):
        """iOS sets Max-Age=0 to the moment it parses, which is at or before the clock the app records first."""
        now = cookie(sessionOnly=False, expiresMs=NOW_MS)
        view = ios_view({'id': 'X', 'parsed': [now], 'stored': [], 'sends': []}, NOW_MS)
        self.assertTrue(view['accepted'])
        self.assertNotIn('refusedBy', view)


if __name__ == '__main__':
    unittest.main()
