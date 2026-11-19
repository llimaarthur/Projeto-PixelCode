import asyncio
import unittest
from datetime import datetime, timezone

import httpx

from frontend.auth_state import (
    AuthState,
    _appointment_professionals_from_response,
    _appointment_payment_status_from_response,
    _appointment_status_from_response,
    _completed_appointment_income_payload,
)


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

    def test_completion_income_payload_links_appointment_and_contact(self):
        payload = _completed_appointment_income_payload(
            {
                "id": 18,
                "contact_id": 42,
                "contact_name": "Ana Souza",
                "total_price": "75.00",
            },
            datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["type"], "income")
        self.assertEqual(payload["amount"], "75.00")
        self.assertEqual(payload["contact_id"], 42)
        self.assertEqual(payload["appointment_id"], 18)

    def test_zero_value_completion_does_not_create_financial_movement(self):
        payload = _completed_appointment_income_payload(
            {"id": 18, "contact_id": 42, "total_price": "0"},
            datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        )

        self.assertIsNone(payload)

    def test_financial_completion_requires_matching_appointment_response(self):
        self.assertEqual(
            _appointment_payment_status_from_response(
                {
                    "data": {
                        "appointment_id": 18,
                        "appointment_status": "completed",
                    }
                },
                18,
            ),
            "completed",
        )
        with self.assertRaises(ValueError):
            _appointment_payment_status_from_response(
                {"appointment_id": 19, "appointment_status": "completed"},
                18,
            )

    def test_completing_appointment_creates_income_and_refreshes_overview(self):
        class CompletionState:
            _auth_token = "token"
            appointments = [
                {
                    "id": 18,
                    "contact_id": 42,
                    "contact_name": "Ana Souza",
                    "total_price": "75.00",
                }
            ]
            appointment_success_message = ""
            appointment_error_message = ""
            appointment_selected_detail = {}
            error_message = ""

            def __init__(self):
                self.requests = []
                self.overview_refreshed = False

            async def _request(self, method, path, payload, error_context):
                self.requests.append((method, path, payload))
                return httpx.Response(
                    200,
                    json={
                        "appointment_id": 18,
                        "appointment_status": "completed",
                    },
                )

            def _update_loaded_appointment_status(self, appointment_id, status):
                return AuthState._update_loaded_appointment_status(
                    self,
                    appointment_id,
                    status,
                )

            async def _load_appointments(self):
                return None

            async def _load_overview_appointments(self):
                self.overview_refreshed = True

        state = CompletionState()
        asyncio.run(
            AuthState.set_appointment_status.fn(state, 18, "completed")
        )

        self.assertEqual(state.requests[0][0:2], ("POST", "finance/transactions"))
        self.assertEqual(state.requests[0][2]["appointment_id"], 18)
        self.assertEqual(state.requests[0][2]["amount"], "75.00")
        self.assertEqual(
            state.appointment_success_message,
            "Atendimento concluído e registrado no financeiro.",
        )
        self.assertTrue(state.overview_refreshed)

    def test_clearing_menu_messages_clears_working_hours_success(self):
        class MessagesState:
            service_success_message = "Serviço salvo."
            contact_success_message = "Cliente salvo."
            appointment_success_message = "Agendamento salvo."
            appointment_working_hours_success_message = "Horários salvos."
            profile_form_success_message = "Perfil salvo."
            profile_photo_success_message = "Foto salva."
            professional_success_message = "Profissional salvo."

        state = MessagesState()
        AuthState.clear_menu_success_messages.fn(state)

        self.assertEqual(state.appointment_working_hours_success_message, "")

    def test_professional_response_accepts_supported_envelopes(self):
        self.assertEqual(
            _appointment_professionals_from_response(
                {"items": [{"id": 7, "name": "João Silva"}]}
            ),
            [{"id": 7, "name": "João Silva"}],
        )
        self.assertEqual(
            _appointment_professionals_from_response(
                {"data": {"items": [{"id": 7, "name": "João Silva"}]}}
            ),
            [{"id": 7, "name": "João Silva"}],
        )
        self.assertEqual(
            _appointment_professionals_from_response({"items": []}),
            [],
        )

    def test_appointment_options_use_the_team_endpoint_and_load_remaining_data(self):
        class OptionsState:
            role = "professional"
            user_id = 7
            appointment_error_message = "Erro antigo."
            appointment_professionals = []
            appointment_contacts = []
            appointment_professional_id = 7
            appointment_options_loading = True
            service_error_message = ""

            def __init__(self):
                self.requested_paths = []
                self.services_loaded = False

            async def _load_appointment_working_hours(self):
                return True

            async def _request(self, method, path, *args, **kwargs):
                self.requested_paths.append(path)
                if path == "auth/professionals":
                    return httpx.Response(
                        200,
                        json=[
                            {"id": 7, "name": "Profissional atual"},
                            {"id": 8, "name": "Outro profissional"},
                        ],
                    )
                if path == "appointments/contacts":
                    return httpx.Response(
                        200,
                        json={
                            "items": [
                                {
                                    "id": 24,
                                    "name": "Ana Souza",
                                    "phone": "11912345678",
                                }
                            ],
                            "total": 1,
                        },
                    )
                self.fail(f"Endpoint inesperado: {path}")

            async def _load_services(self):
                self.services_loaded = True

        state = OptionsState()
        asyncio.run(AuthState._load_appointment_options(state))

        self.assertEqual(
            state.appointment_professionals,
            [{"id": 7, "name": "Profissional atual"}],
        )
        self.assertEqual(state.appointment_contacts[0]["name"], "Ana Souza")
        self.assertTrue(state.services_loaded)
        self.assertEqual(
            state.requested_paths,
            ["auth/professionals", "appointments/contacts"],
        )
        self.assertEqual(state.appointment_error_message, "")
        self.assertFalse(state.appointment_options_loading)

    def test_failed_professional_reload_does_not_keep_previous_options(self):
        class OptionsState:
            appointment_error_message = "Erro antigo."
            appointment_professionals = [{"id": 7, "name": "João Silva"}]
            appointment_contacts = [{"id": 9, "name": "Ana Souza"}]
            appointment_options_loading = True
            appointment_professional_id = 0

            async def _load_appointment_working_hours(self):
                return True

            async def _request(self, method, path, error_context):
                return httpx.Response(500, json={"message": "Falha temporária."})

        state = OptionsState()
        asyncio.run(AuthState._load_appointment_options(state))

        self.assertEqual(state.appointment_professionals, [])
        self.assertEqual(state.appointment_contacts, [])
        self.assertIn("Falha temporária.", state.appointment_error_message)
        self.assertFalse(state.appointment_options_loading)
