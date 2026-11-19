import asyncio
import json
import unittest
from datetime import date, datetime
from pathlib import Path

import httpx

from frontend.auth_state import (
    AuthState,
    BARBERSHOP_TIMEZONE,
    _appointment_fits_working_hours,
    _calculate_appointment_time_slots,
    _normalize_working_hours,
    _working_hours_api_payload,
    _working_hours_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
XANO_ROOT = PROJECT_ROOT / "xano"


def weekly_hours(monday_intervals):
    return [
        {
            "day_of_week": day,
            "intervals": monday_intervals if day == 1 else [],
        }
        for day in range(1, 8)
    ]


class ContactOwnershipAndWorkingHoursTests(unittest.TestCase):
    def test_unconfigured_schedule_is_editable_and_json_encoded_schedule_loads(self):
        empty_schedules = [
            _working_hours_state(value)
            for value in (None, [], "[]")
        ]
        encoded_schedule = _working_hours_state(
            json.dumps(weekly_hours([{"start_minute": 540, "end_minute": 720}]))
        )

        for empty_schedule in empty_schedules:
            with self.subTest(schedule=empty_schedule):
                self.assertEqual(len(empty_schedule), 7)
                self.assertTrue(all(not day["intervals"] for day in empty_schedule))
        self.assertEqual(
            encoded_schedule[0]["intervals"][0]["start_minute"],
            540,
        )

    def test_closed_days_with_null_intervals_are_normalized_as_closed(self):
        raw_schedule = weekly_hours(
            [{"start_minute": 540, "end_minute": 720}]
        )
        raw_schedule[2]["intervals"] = None

        schedule = _working_hours_state(raw_schedule)
        payload = _working_hours_api_payload(schedule)

        self.assertEqual(schedule[2]["intervals"], [])
        self.assertEqual(
            payload[2],
            {"day_of_week": 3, "intervals": []},
        )

    def test_admin_can_add_an_interval_to_an_unconfigured_schedule(self):
        class WorkingHoursState:
            role = "admin"
            appointment_working_hours_editing = True
            appointment_working_hours = _working_hours_state(None)
            appointment_working_hours_form_error = ""

        state = WorkingHoursState()
        AuthState.add_working_hour_interval.fn(state, 1)

        self.assertEqual(
            state.appointment_working_hours[0]["intervals"][0]["start_minute"],
            540,
        )
        self.assertEqual(
            state.appointment_working_hours[0]["intervals"][0]["end_minute"],
            570,
        )

    def test_admin_can_add_and_adjust_a_shared_lunch_break(self):
        class WorkingHoursState:
            role = "admin"
            appointment_working_hours_editing = True
            appointment_working_hours = _working_hours_state(
                weekly_hours([{"start_minute": 540, "end_minute": 1140}])
            )
            appointment_working_hour_pause_day = 0
            appointment_working_hour_pause_start = "720"
            appointment_working_hour_pause_end = "780"
            appointment_working_hours_form_error = ""

        state = WorkingHoursState()
        AuthState.start_working_hour_pause.fn(state, 1)

        self.assertEqual(state.appointment_working_hour_pause_start, "720")
        self.assertEqual(state.appointment_working_hour_pause_end, "780")

        AuthState.set_working_hour_pause_time.fn(state, "start", "750")
        AuthState.set_working_hour_pause_time.fn(state, "end", "810")
        AuthState.apply_working_hour_pause.fn(state, 1)

        self.assertEqual(
            [
                (interval["start_minute"], interval["end_minute"])
                for interval in state.appointment_working_hours[0]["intervals"]
            ],
            [(540, 750), (810, 1140)],
        )
        self.assertEqual(state.appointment_working_hour_pause_day, 0)
        self.assertEqual(
            _working_hours_api_payload(state.appointment_working_hours)[0]["intervals"],
            [
                {"start_minute": 540, "end_minute": 750},
                {"start_minute": 810, "end_minute": 1140},
            ],
        )

    def test_lunch_pause_cannot_be_added_when_already_configured(self):
        class WorkingHoursState:
            role = "admin"
            appointment_working_hours_editing = True
            appointment_working_hours = _working_hours_state(
                weekly_hours(
                    [
                        {"start_minute": 540, "end_minute": 720},
                        {"start_minute": 780, "end_minute": 1140},
                    ]
                )
            )
            appointment_working_hour_pause_day = 0
            appointment_working_hour_pause_start = "720"
            appointment_working_hour_pause_end = "780"
            appointment_working_hours_form_error = ""

        state = WorkingHoursState()
        AuthState.start_working_hour_pause.fn(state, 1)

        self.assertEqual(state.appointment_working_hour_pause_day, 0)
        self.assertIn("já possui uma pausa", state.appointment_working_hours_form_error)

    def test_invalid_api_schedule_remains_reconfigurable(self):
        class WorkingHoursState:
            appointment_working_hours_loading = False
            appointment_working_hours_error = ""
            appointment_working_hours_form_error = ""
            appointment_working_hours = []
            error_message = ""

            async def _request(self, method, path, error_context):
                return httpx.Response(
                    200,
                    json={"weekly_hours": {"unexpected": "shape"}},
                )

        state = WorkingHoursState()
        loaded = asyncio.run(AuthState._load_appointment_working_hours(state))

        self.assertFalse(loaded)
        self.assertEqual(len(state.appointment_working_hours), 7)
        self.assertIn("A semana foi carregada fechada", state.appointment_working_hours_error)

        state.role = "admin"
        state.appointment_working_hours_editing = True
        AuthState.add_working_hour_interval.fn(state, 1)

        self.assertEqual(
            state.appointment_working_hours[0]["intervals"][0]["start_minute"],
            540,
        )

    def test_api_load_accepts_closed_days_with_null_intervals(self):
        api_schedule = weekly_hours([])
        api_schedule[0]["intervals"] = None

        class WorkingHoursState:
            appointment_working_hours_loading = False
            appointment_working_hours_error = ""
            appointment_working_hours_form_error = ""
            appointment_working_hours = []
            error_message = ""

            async def _request(self, method, path, error_context):
                return httpx.Response(
                    200,
                    json={"weekly_hours": api_schedule},
                )

        state = WorkingHoursState()
        loaded = asyncio.run(AuthState._load_appointment_working_hours(state))

        self.assertTrue(loaded)
        self.assertEqual(state.appointment_working_hours_error, "")
        self.assertEqual(state.appointment_working_hours[0]["intervals"], [])

    def test_api_load_treats_an_unconfigured_schedule_as_closed(self):
        class WorkingHoursState:
            appointment_working_hours_loading = False
            appointment_working_hours_error = ""
            appointment_working_hours_form_error = ""
            appointment_working_hours = []
            error_message = ""

            async def _request(self, method, path, error_context):
                return httpx.Response(200, json={"weekly_hours": []})

        state = WorkingHoursState()
        loaded = asyncio.run(AuthState._load_appointment_working_hours(state))

        self.assertTrue(loaded)
        self.assertEqual(state.appointment_working_hours_error, "")
        self.assertEqual(len(state.appointment_working_hours), 7)
        self.assertTrue(
            all(not day["intervals"] for day in state.appointment_working_hours)
        )

    def test_saving_valid_schedule_clears_stale_api_error(self):
        class WorkingHoursState:
            role = "admin"
            appointment_working_hours_saving = False
            appointment_working_hours_editing = True
            appointment_working_hours = _working_hours_state(
                weekly_hours([{"start_minute": 540, "end_minute": 1140}])
            )
            appointment_working_hours_form_error = ""
            appointment_working_hour_pause_day = 0
            appointment_working_hours_error = "Resposta anterior inválida."
            appointment_working_hours_success_message = ""
            appointment_error_message = "Resposta anterior inválida."
            appointment_working_hours_loading = False
            appointment_contacts = []
            appointment_professionals = []
            appointment_options_loading = False

            def __init__(self):
                self.requests = []

            async def _load_appointment_working_hours(self):
                return await AuthState._load_appointment_working_hours(self)

            async def _request(self, method, path, payload=None, error_context=""):
                self.requests.append((method, path))
                if method == "PATCH":
                    response_schedule = payload["weekly_hours"]
                else:
                    response_schedule = weekly_hours(
                        [{"start_minute": 540, "end_minute": 1140}]
                    )
                return httpx.Response(
                    200,
                    json={"weekly_hours": response_schedule},
                )

            async def _load_appointments(self):
                self.appointments_reloaded = True

        state = WorkingHoursState()

        async def save():
            return [
                event
                async for event in AuthState.save_working_hours.fn(state)
            ]

        asyncio.run(save())

        self.assertEqual(state.appointment_working_hours_error, "")
        self.assertEqual(state.appointment_error_message, "")
        self.assertEqual(
            state.appointment_working_hours_success_message,
            "Horários da barbearia salvos.",
        )
        self.assertFalse(state.appointment_working_hours_editing)
        self.assertTrue(state.appointments_reloaded)
        self.assertEqual(
            state.requests,
            [
                ("PATCH", "appointments/working-hours"),
                ("GET", "appointments/working-hours"),
            ],
        )

    def test_schedule_accepts_multiple_sorted_intervals_and_closed_days(self):
        schedule = _normalize_working_hours(
            weekly_hours(
                [
                    {"start_minute": 540, "end_minute": 720},
                    {"start_minute": 780, "end_minute": 1140},
                ]
            )
        )

        self.assertEqual(len(schedule), 7)
        self.assertEqual(schedule[0]["label"], "Segunda-feira")
        self.assertEqual(len(schedule[0]["intervals"]), 2)
        self.assertEqual(schedule[-1]["intervals"], [])

    def test_schedule_rejects_overlaps_bad_boundaries_and_duplicate_days(self):
        overlapping = weekly_hours(
            [
                {"start_minute": 540, "end_minute": 720},
                {"start_minute": 690, "end_minute": 780},
            ]
        )
        invalid_boundary = weekly_hours(
            [{"start_minute": 541, "end_minute": 720}]
        )
        duplicate_day = weekly_hours([])
        duplicate_day[1] = {
            "day_of_week": 1,
            "intervals": [],
        }

        for invalid_schedule in (overlapping, invalid_boundary, duplicate_day):
            with self.subTest(schedule=invalid_schedule):
                with self.assertRaises(ValueError):
                    _normalize_working_hours(invalid_schedule)

    def test_time_slots_follow_the_tenant_schedule_and_closed_days(self):
        schedule = _normalize_working_hours(
            weekly_hours(
                [
                    {"start_minute": 570, "end_minute": 660},
                    {"start_minute": 780, "end_minute": 840},
                ]
            )
        )
        professional = [{"id": 12, "name": "Barbeiro"}]

        monday_slots = _calculate_appointment_time_slots(
            date(2026, 1, 5),
            professional,
            30,
            [],
            [],
            schedule,
        )
        sunday_slots = _calculate_appointment_time_slots(
            date(2026, 1, 11),
            professional,
            30,
            [],
            [],
            schedule,
        )

        self.assertEqual(
            [slot["time"] for slot in monday_slots],
            ["09:30", "10:00", "10:30", "13:00", "13:30"],
        )
        self.assertEqual(sunday_slots, [])

    def test_appointment_validation_uses_configured_working_hours(self):
        schedule = _normalize_working_hours(
            weekly_hours(
                [{"start_minute": 540, "end_minute": 1140}]
            )
        )

        self.assertTrue(
            _appointment_fits_working_hours(
                datetime(2026, 1, 5, 18, 0, tzinfo=BARBERSHOP_TIMEZONE),
                20,
                schedule,
            )
        )
        self.assertFalse(
            _appointment_fits_working_hours(
                datetime(2026, 1, 5, 18, 30, tzinfo=BARBERSHOP_TIMEZONE),
                31,
                schedule,
            )
        )
        self.assertFalse(
            _appointment_fits_working_hours(
                datetime(2026, 1, 11, 9, 0, tzinfo=BARBERSHOP_TIMEZONE),
                20,
                schedule,
            )
        )

    def test_appointment_submission_uses_the_configured_schedule(self):
        class AppointmentState:
            _auth_token = "current-session"
            role = "admin"
            appointment_form_submitting = False
            appointment_form_contact_id = 1
            appointment_form_professional_id = 2
            appointment_form_service_ids = [3]
            appointment_form_date = "2026-01-05"
            appointment_form_time = "18:00"
            appointment_form_notes = ""
            appointment_form_error = ""
            appointment_selected_services = [
                {"id": 3, "name": "Corte", "duration_minutes": 20, "price": "30.00"}
            ]
            appointment_working_hours = _normalize_working_hours(
                weekly_hours([{"start_minute": 540, "end_minute": 1140}])
            )
            appointment_blocks = []
            appointment_error_message = ""
            appointment_loading = False
            appointment_editing_id = 0
            appointments = []
            appointment_contacts = [
                {"id": 1, "name": "Cliente", "phone": "(11) 91234-5678"}
            ]
            appointment_professionals = [{"id": 2, "name": "Profissional"}]
            appointment_success_details = {}
            appointment_success_message = ""
            appointment_form_open = True
            appointment_view = "form"
            appointment_date = ""
            appointment_calendar_month = ""

            def __init__(self):
                self.requests = []

            async def _request(self, method, path, payload, error_context):
                self.requests.append((method, path, payload))
                return httpx.Response(201, json={"id": 4})

            async def _load_appointments(self):
                pass

        state = AppointmentState()

        async def submit():
            return [
                event
                async for event in AuthState.save_appointment.fn(state, {})
            ]

        asyncio.run(submit())

        self.assertEqual(state.requests[0][1], "appointments")
        self.assertEqual(state.appointment_form_error, "")
        self.assertEqual(state.appointment_success_message, "Agendamento criado com sucesso.")

    def test_contact_mutations_enforce_owner_and_admin_assignment(self):
        contacts_get = (
            XANO_ROOT / "api" / "contacts" / "contacts_GET.xs"
        ).read_text(encoding="utf-8")
        contacts_post = (
            XANO_ROOT / "api" / "contacts" / "contacts_POST.xs"
        ).read_text(encoding="utf-8")
        contact_patch = (
            XANO_ROOT / "api" / "contacts" / "contact_PATCH.xs"
        ).read_text(encoding="utf-8")
        contact_status = (
            XANO_ROOT / "api" / "contacts" / "contact_status_PATCH.xs"
        ).read_text(encoding="utf-8")
        owner_resolver = (
            XANO_ROOT / "function" / "quick_start" / "resolve_contact_owner.xs"
        ).read_text(encoding="utf-8")

        self.assertIn("$role_check.role == \"admin\"", contacts_get)
        self.assertIn("$db.contact.professional_id == $auth.id", contacts_get)
        self.assertIn('"Quick Start/resolve_contact_owner"', contacts_post)
        self.assertIn("$contact_owner.professional_id", contacts_post)
        for source in (contact_patch, contact_status):
            self.assertIn("$existing_contact.professional_id == $auth.id", source)
        self.assertIn("$input.requested_professional_id == null", owner_resolver)
        self.assertIn(
            "$input.requested_professional_id != $input.existing_professional_id",
            owner_resolver,
        )
        self.assertIn("$target_professional.barbershop_id == $input.barbershop_id", owner_resolver)

    def test_appointment_contact_options_follow_the_professional_wallet(self):
        endpoint = (
            XANO_ROOT / "api" / "appointments" / "contacts_GET.xs"
        ).read_text(encoding="utf-8")
        prepare_appointment = (
            XANO_ROOT / "function" / "quick_start" / "prepare_appointment.xs"
        ).read_text(encoding="utf-8")
        appointments_post = (
            XANO_ROOT / "api" / "appointments" / "appointments_POST.xs"
        ).read_text(encoding="utf-8")
        appointment_patch = (
            XANO_ROOT / "api" / "appointments" / "appointment_PATCH.xs"
        ).read_text(encoding="utf-8")
        professional_scope = (
            XANO_ROOT
            / "function"
            / "quick_start"
            / "authorize_professional_scope.xs"
        ).read_text(encoding="utf-8")

        self.assertIn('required_role: "professional"', endpoint)
        self.assertIn("$db.contact.barbershop_id == $role_check.barbershop_id", endpoint)
        self.assertIn(
            '$role_check.role == "admin" || $db.contact.professional_id == $auth.id',
            endpoint,
        )
        self.assertIn('output = ["id", "name", "phone"]', endpoint)
        self.assertIn("role: $access_scope.role", professional_scope)
        self.assertIn('"professional_id"]', prepare_appointment)
        self.assertIn('$input.actor_role == "admin"', prepare_appointment)
        self.assertIn(
            "$contact.professional_id == $input.professional_id",
            prepare_appointment,
        )
        self.assertIn("actor_role: $scope_check.role", appointments_post)
        self.assertIn("actor_role: $target_scope_check.role", appointment_patch)

    def test_working_hours_are_tenant_scoped_and_admin_managed(self):
        hours_get = (
            XANO_ROOT / "api" / "appointments" / "working_hours_GET.xs"
        ).read_text(encoding="utf-8")
        hours_patch = (
            XANO_ROOT / "api" / "appointments" / "working_hours_PATCH.xs"
        ).read_text(encoding="utf-8")
        resolver = (
            XANO_ROOT
            / "function"
            / "quick_start"
            / "get_barbershop_working_hours.xs"
        ).read_text(encoding="utf-8")
        interval_validator = (
            XANO_ROOT
            / "function"
            / "quick_start"
            / "validate_working_interval.xs"
        ).read_text(encoding="utf-8")
        hours_validator = (
            XANO_ROOT
            / "function"
            / "quick_start"
            / "validate_working_hours.xs"
        ).read_text(encoding="utf-8")
        signup = (
            XANO_ROOT
            / "api"
            / "authentication"
            / "auth"
            / "signup_POST.xs"
        ).read_text(encoding="utf-8")

        self.assertIn('required_role: "professional"', hours_get)
        self.assertIn('required_role: "admin"', hours_patch)
        self.assertIn('"Quick Start/validate_working_hours"', hours_patch)
        self.assertIn('$barbershop.migration_key == "legacy-default"', resolver)
        self.assertIn("($weekly_hours|count) == 0", resolver)
        self.assertIn("foreach ($input.weekly_hours)", interval_validator)
        self.assertIn("$inside_working_period == true", interval_validator)
        self.assertIn("if ($day.intervals != null)", hours_validator)
        self.assertNotIn(
            "&& $day.intervals != null",
            hours_validator,
        )
        signup_hours = signup.split("weekly_hours: [", 1)[1].split(
            "\n            ]",
            1,
        )[0]
        for day_of_week in range(1, 8):
            with self.subTest(day_of_week=day_of_week):
                self.assertIn(
                    f"{{day_of_week: {day_of_week}, intervals: []}}",
                    signup_hours,
                )

    def test_contact_access_keeps_session_when_identity_check_is_unavailable(self):
        for session_invalid in (False, True):
            with self.subTest(session_invalid=session_invalid):
                class ContactAccessState:
                    _auth_token = "current-session"
                    error_message = ""
                    identity_session_invalid = session_invalid
                    service_success_message = ""

                    def _clear_registration_success_message(self):
                        pass

                    async def _load_identity(self):
                        self.error_message = (
                            "Não foi possível conectar ao serviço de acesso."
                        )
                        return None

                    def _handle_identity_failure(self):
                        return AuthState._handle_identity_failure(self)

                    def _clear_session(self):
                        self._auth_token = ""
                        self.identity_session_invalid = False

                state = ContactAccessState()

                async def load_contacts_page():
                    return [
                        event
                        async for event in AuthState.require_contact_access.fn(state)
                    ]

                events = asyncio.run(load_contacts_page())

                if session_invalid:
                    self.assertEqual(state._auth_token, "")
                    self.assertTrue(events)
                    self.assertEqual(
                        events[-1].args[0][1]._var_value,
                        "/login",
                    )
                else:
                    self.assertEqual(state._auth_token, "current-session")
                    self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
