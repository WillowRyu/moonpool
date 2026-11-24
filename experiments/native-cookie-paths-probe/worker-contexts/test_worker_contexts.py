import unittest

from check import guard_failures


class InheritedPolicyTests(unittest.TestCase):
    def test_a_registration_error_alone_does_not_establish_csp_inheritance(self):
        origin = "https://mp-example-guarded.invalid"
        frame = {"service": {"outcome": "rejected", "error": "InvalidStateError"}, "violations": []}

        self.assertEqual(guard_failures(origin, frame, "service"), [
            "service: enforcing worker-src event missing",
        ])

        frame["violations"].append({
            "directive": "worker-src", "disposition": "enforce", "blockedURI": origin + "/service.js",
        })
        self.assertEqual(guard_failures(origin, frame, "service"), [])
