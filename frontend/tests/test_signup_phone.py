import asyncio
import unittest

import httpx

from frontend.auth_state import (
    AuthState,
    _contact_phone_validation_error,
    _format_contact_phone,
    _form_value_or_state,
    _phone_for_api,
)


class SignupPhoneTests(unittest.TestCase):
    def test_signup_phone_accepts_supported_formats(self):
        accepted = (
            "(11) 91234-5678",
            "(11) 92039-8470",
            "(11) 92099-9470",
            "11912345678",
            "(11) 3123-4567",
            "1131234567",
            "+55 11 91234-5678",
            "5511912345678",
            "  (11) 91234-5678  ",
        )
        for value in accepted:
            with self.subTest(value=value):
                normalized = _phone_for_api(value)
                self.assertIn(len(normalized), (10, 11))
                self.assertEqual(_contact_phone_validation_error(value), "")

    def test_signup_submission_sends_the_phone_from_the_screen_normalized(self):
        class SignupState:
            signup_is_submitting = False
            signup_owner_phone = "(11) 92039-8470"
            signup_error_message = ""
            registration_success_message = ""
            error_message = ""
            payload = None

            async def _request(self, method, path, payload, error_context):
                self.payload = payload
                return httpx.Response(409, json={"message": "test sentinel"})

        state = SignupState()
        form_data = {
            "barbershop_name": "Barbearia teste",
            "owner_name": "Proprietário teste",
            "owner_email": "teste@example.com",
            "owner_phone": "(11) 92039-8470",
            "owner_password": "Gabriel123",
        }

        async def submit():
            async for _ in AuthState.signup_barbershop.fn(state, form_data):
                pass

        asyncio.run(submit())

        self.assertEqual(state.payload["owner_phone"], "11920398470")
        self.assertEqual(state.signup_error_message, "test sentinel")

    def test_signup_phone_rejects_non_phone_content_and_invalid_ddd(self):
        rejected = (
            "abcdefghijk",
            "(11) 91234-56@8",
            "(00) 91234-5678",
            "(01) 91234-5678",
            "(10) 91234-5678",
            "119123456",
            "119123456789",
            "",
        )
        for value in rejected:
            with self.subTest(value=value):
                self.assertNotEqual(_contact_phone_validation_error(value), "")

    def test_masked_mobile_phone_normalizes_to_eleven_digits(self):
        for digits, masked in (
            ("11983748939", "(11) 98374-8939"),
            ("11920398470", "(11) 92039-8470"),
            ("11938383838", "(11) 93838-3838"),
        ):
            with self.subTest(digits=digits):
                masked_phone = _format_contact_phone(digits)

                self.assertEqual(masked_phone, masked)
                self.assertEqual(_phone_for_api(masked_phone), digits)
                self.assertEqual(_contact_phone_validation_error(masked_phone), "")

    def test_blank_form_phone_uses_controlled_state_value(self):
        state_phone = "(11) 93838-3838"

        for form_data in ({"owner_phone": ""}, {}):
            with self.subTest(form_data=form_data):
                phone = _form_value_or_state(
                    form_data, "owner_phone", state_phone
                )

                self.assertEqual(_phone_for_api(phone), "11938383838")
                self.assertEqual(_contact_phone_validation_error(phone), "")

    def test_masked_landline_phone_normalizes_to_ten_digits(self):
        masked_phone = _format_contact_phone("1138383838")

        self.assertEqual(masked_phone, "(11) 3838-3838")
        self.assertEqual(_contact_phone_validation_error(masked_phone), "")

    def test_invalid_length_and_area_code_are_rejected(self):
        self.assertEqual(
            _contact_phone_validation_error("(11) 9837-489"),
            "Informe um telefone com DDD e 10 ou 11 dígitos.",
        )
        self.assertEqual(
            _contact_phone_validation_error("(00) 98374-8939"),
            "Informe um DDD válido.",
        )


if __name__ == "__main__":
    unittest.main()
