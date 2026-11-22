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

    def test_new_login_token_clears_previous_tenant_finance_options(self):
        class TenantState:
            _auth_token = "previous-token"
            finance_kpis = [{"value": "R$ 200,00"}]
            finance_dashboard_loaded = True
            finance_kpis_loading = True
            finance_kpis_error = "Erro antigo"
            finance_cashflow = {"6m": [{"month": "Nov"}]}
            finance_period = "year"
            finance_chart_points = [{"month": "Nov"}]
            finance_chart_y_ticks = [{"value": 200}]
            finance_chart_inflow_path = "old-path"
            finance_chart_outflow_path = "old-path"
            finance_chart_inflow_area = "old-area"
            finance_chart_outflow_area = "old-area"
            finance_chart_loading = True
            finance_chart_error = "Erro antigo"
            finance_chart_active_index = 0
            finance_summary = {"income": "200"}
            finance_summary_empty = False
            finance_summary_loading = True
            finance_summary_error = "Erro antigo"
            finance_transactions = [{"id": 26}]
            finance_transactions_loading = True
            finance_transactions_error = "Erro antigo"
            finance_transactions_total = 1
            finance_transactions_page = 2
            finance_has_cancelled_transactions = True
            finance_show_cancelled_transactions = True
            finance_api_available = True
            finance_mock_mode = False
            finance_contacts = [{"id": 26, "name": "Cliente anterior"}]
            finance_services = [{"id": 10, "name": "Serviço anterior"}]
            finance_appointment_options = [{"id": 42}]
            finance_appointment_options_loading = True
            finance_form_options_loading = True
            finance_form_options_loaded = True
            finance_form_options_error = "Erro antigo"
            finance_form_open = True
            finance_form_type = "income"
            finance_form_mode = "edit"
            finance_form_transaction_id = 26
            finance_form_title = "Movimentação anterior"
            finance_form_detail = "Detalhe anterior"
            finance_form_amount = "200.00"
            finance_form_occurred_at = "2026-11-21T20:00"
            finance_form_contact_id = 26
            finance_form_contact_option = "Cliente anterior #26"
            finance_form_service_option = "Serviço anterior #10"
            finance_form_service_ids = [10]
            finance_form_appointment_id = 42
            finance_form_appointment_option = "Agendamento anterior #42"
            finance_form_confirming = True
            finance_form_error = "Erro antigo"
            finance_form_success_message = "Sucesso antigo"
            finance_form_submitting = True
            finance_cancel_transaction_id = 26
            finance_cancel_reason = "Motivo anterior"
            finance_cancel_error = "Erro antigo"
            finance_cancel_submitting = True
            display_name = ""
            role = ""

            def _clear_finance_state(self):
                AuthState._clear_finance_state(self)

        state = TenantState()
        profile = AuthState._apply_login_response(
            state,
            {
                "authToken": "new-tenant-token",
                "user": {"id": 7, "name": "Nova conta", "role": "admin"},
            },
        )

        self.assertEqual(profile["id"], 7)
        self.assertEqual(state.finance_contacts, [])
        self.assertEqual(state.finance_services, [])
        self.assertEqual(state.finance_transactions, [])
        self.assertFalse(state.finance_form_options_loaded)
        self.assertFalse(state.finance_dashboard_loaded)
        self.assertFalse(state.finance_form_open)
        self.assertEqual(state.finance_form_contact_id, 0)
        self.assertEqual(state.finance_form_service_ids, [])
        self.assertEqual(state.finance_appointment_options, [])

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

    def test_future_movement_is_sent_to_api_and_displays_api_error(self):
        error_message = "A data da movimentação não pode estar no futuro."

        class MovementState:
            finance_form_submitting = False
            finance_api_available = True
            finance_form_mode = "create"
            finance_form_type = "expense"
            finance_form_title = ""
            finance_form_detail = ""
            finance_form_amount = ""
            finance_form_occurred_at = ""
            finance_form_contact_id = 0
            finance_form_service_ids = []
            finance_form_appointment_id = 0
            finance_form_confirming = False
            finance_form_transaction_id = 0
            finance_form_error = ""
            finance_form_success_message = ""

            def __init__(self):
                self.requests = []

            async def _request(self, method, path, payload, error_context):
                self.requests.append((method, path, payload))
                return httpx.Response(400, json={"message": error_message})

        state = MovementState()

        async def submit():
            async for _ in AuthState.save_finance_transaction.fn(
                state,
                {
                    "type": "expense",
                    "title": "Pagamento",
                    "amount": "200",
                    "occurred_at": "2099-11-21T21:03",
                },
            ):
                pass

        asyncio.run(submit())

        self.assertEqual(len(state.requests), 1)
        self.assertEqual(state.requests[0][0:2], ("POST", "finance/transactions"))
        self.assertEqual(state.finance_form_error, error_message)
        self.assertFalse(state.finance_form_submitting)
