import unittest

from check import cleanup_failures, continuity_failures


class WebViewRetirementTests(unittest.TestCase):
    def test_logical_invalidation_does_not_substitute_for_destroying_both_views(self):
        destroyed = {
            "live": False, "loads": 1, "retireCalls": 1, "destroyed": True,
            "attached": False, "groupInactiveAtDestroy": True,
        }
        refused = {
            "live": False, "loads": 0, "retireCalls": 1, "destroyed": False,
            "attached": False, "groupInactiveAtDestroy": False,
        }
        states = {
            "a1": dict(destroyed),
            "a2": dict(destroyed, destroyed=False, attached=True),
            "a3": dict(refused),
            "a4": dict(refused),
        }

        self.assertEqual(cleanup_failures(states), ["a2: admitted WebView teardown differs"])
        states["a2"] = dict(destroyed)
        self.assertEqual(cleanup_failures(states), [])

    def test_a_replacement_document_is_not_continuity_for_b(self):
        before = {
            "name": "b1", "origin": "https://mp-example-b.invalid", "marker": "example-b",
            "instance": "first-document", "cookie": "", "pulse": 1,
        }
        after = dict(before, instance="replacement-document", pulse=2)
        self.assertEqual(continuity_failures(before, after), ["b1: original document did not continue"])
        self.assertEqual(continuity_failures(before, dict(before, pulse=2)), [])
