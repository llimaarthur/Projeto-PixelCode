import unittest

from frontend.auth_state import _appointment_status_from_response


class FinanceStateTests(unittest.TestCase):
    def test_appointment_status_requires_matching_persisted_response(self):
        self.assertEqual(
            _appointment_status_from_response(
                {"data": {"id": 18, "status": "confirmed"}},
                18,
            ),
            "confirmed",
        )
        for payload in (
            None,
            {"id": 19, "status": "confirmed"},
            {"id": 18, "status": "invalid"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    _appointment_status_from_response(payload, 18)
