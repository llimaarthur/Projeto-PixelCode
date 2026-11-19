import asyncio
import re
import unittest
from pathlib import Path

from frontend.auth_state import AuthState, create_professional_page


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SOURCE_PATH = PROJECT_ROOT / "frontend" / "frontend" / "auth_state.py"
STYLES_PATH = PROJECT_ROOT / "frontend" / "assets" / "styles.css"
TEAM_GET_PATH = (
    PROJECT_ROOT
    / "xano"
    / "api"
    / "authentication"
    / "auth"
    / "professionals_GET.xs"
)
TEAM_CREATE_PATH = (
    PROJECT_ROOT
    / "xano"
    / "api"
    / "authentication"
    / "auth"
    / "create_professional_POST.xs"
)
TEAM_REPAIR_PATH = (
    PROJECT_ROOT
    / "xano"
    / "api"
    / "authentication"
    / "auth"
    / "professionals_repair_POST.xs"
)


class TeamAccessAndBrandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frontend = FRONTEND_SOURCE_PATH.read_text(encoding="utf-8")
        cls.styles = STYLES_PATH.read_text(encoding="utf-8")

    def test_professionals_can_read_only_their_own_team(self):
        team_get = TEAM_GET_PATH.read_text(encoding="utf-8")
        self.assertIn('required_role: "professional"', team_get)
        self.assertIn(
            "$db.user.barbershop_id == $role_check.barbershop_id",
            team_get,
        )
        self.assertIn(
            "$role_check.include_legacy_rows == true && $db.user.barbershop_id == null",
            team_get,
        )

        team_guard = self.frontend.split(
            "async def require_team_access", 1
        )[1].split("async def load_professionals", 1)[0]
        self.assertIn('self.role not in ("admin", "professional")', team_guard)

    def test_team_mutations_remain_admin_only(self):
        for endpoint in (TEAM_CREATE_PATH, TEAM_REPAIR_PATH):
            with self.subTest(endpoint=endpoint.name):
                source = endpoint.read_text(encoding="utf-8")
                self.assertIn('required_role: "admin"', source)

    def test_professional_creation_confirms_a_saved_record_after_request_timeout(self):
        class ProfessionalState:
            _auth_token = "current-session"
            is_submitting = False
            professional_phone = ""
            professional_cpf = ""
            professional_email = ""
            professional_password_visible = False
            professional_success_message = ""
            error_message = ""
            professionals = [{"id": 1, "email": "admin@example.com"}]

            async def _request(self, method, path, payload):
                self.error_message = "Não foi possível conectar ao serviço de acesso."
                return None

            async def load_professionals(self):
                self.professionals = [
                    {"id": 1, "email": "admin@example.com"},
                    {"id": 2, "email": "barbeiro@example.com"},
                ]

        state = ProfessionalState()
        form_data = {
            "name": "Barbeiro",
            "email": "barbeiro@example.com",
            "phone": "(11) 91234-5678",
            "cpf": "283.764.283-32",
            "password": "barbeiro123",
        }

        async def submit():
            return [
                event
                async for event in AuthState.create_professional.fn(
                    state, form_data
                )
            ]

        events = asyncio.run(submit())

        self.assertEqual(
            state.professional_success_message,
            "Profissional cadastrado com sucesso.",
        )
        self.assertEqual(state.error_message, "")
        self.assertEqual(state.professionals[-1]["email"], form_data["email"])
        self.assertEqual(state.is_submitting, False)
        self.assertTrue(events)

    def test_failed_team_reload_does_not_keep_the_previous_account_list(self):
        class TeamState:
            professionals_loading = False
            professionals_error = ""
            professionals = [{"id": 1, "email": "previous@example.com"}]
            professional_page = 1
            professional_page_count = 1
            error_message = "Falha temporária."

            async def _request(self, method, path, error_context):
                return None

        state = TeamState()
        asyncio.run(AuthState.load_professionals.fn(state))

        self.assertEqual(state.professionals, [])
        self.assertTrue(state.professionals_error)
        self.assertFalse(state.professionals_loading)

    def test_professional_sees_list_without_admin_form(self):
        self.assertIn("AuthState.can_view_team", self.frontend)
        team_page = self.frontend.split(
            "def create_professional_page()", 1
        )[1].split("def _service_row", 1)[0]
        self.assertRegex(
            team_page,
            re.compile(
                r'rx\.cond\(\s*AuthState\.role == "admin",\s*'
                r"rx\.el\.section\(\s*professional_form",
                re.DOTALL,
            ),
        )
        self.assertIn("AuthState.professional_page_items", team_page)
        self.assertIn("on_load=AuthState.require_team_access", self.frontend)
        self.assertIsNotNone(create_professional_page())

    def test_professional_password_uses_accessible_shared_visibility_control(self):
        self.assertIn("professional_password_visible: bool = False", self.frontend)
        toggle = self.frontend.split(
            "def toggle_password_visibility", 1
        )[1].split("def set_profile_name", 1)[0]
        self.assertRegex(
            toggle,
            r'field == "professional":\s*'
            r"self\.professional_password_visible = "
            r"not self\.professional_password_visible",
        )
        self.assertRegex(
            self.frontend,
            re.compile(
                r'_password_input\(\s*field_id="professional-password",\s*'
                r'name="password",\s*visibility_key="professional",\s*'
                r'visible=AuthState\.professional_password_visible',
                re.DOTALL,
            ),
        )
        self.assertIn('aria_label=rx.cond(visible, "Ocultar senha", "Mostrar senha")', self.frontend)
        self.assertIn('rx.icon("eye-off"', self.frontend)

    def test_registration_flash_clears_on_navigation_away_from_login(self):
        clear_signup = self.frontend.split(
            "def clear_signup_messages", 1
        )[1].split("def set_signup_owner_phone", 1)[0]
        self.assertIn("_clear_registration_success_message()", clear_signup)
        clear_registration = self.frontend.split(
            "def _clear_registration_success_message", 1
        )[1].split("def _tenant_title_script", 1)[0]
        self.assertIn('self.registration_success_message = ""', clear_registration)

        for method in (
            "require_overview_access",
            "require_finance_access",
            "require_team_access",
            "require_service_access",
            "require_contact_access",
            "require_appointment_access",
            "require_password_change",
        ):
            with self.subTest(method=method):
                body = self.frontend.split(f"async def {method}", 1)[1].split(
                    "\n    @rx.", 1
                )[0]
                self.assertIn("_clear_registration_success_message()", body)

        self.assertIn("on_load=AuthState.clear_navigation_success_messages", self.frontend)
        login_page = self.frontend.split('route="/login"', 1)[1].split("app.add_page", 1)[0]
        self.assertIn("on_load=AuthState.clear_menu_success_messages", login_page)

    def test_login_clears_success_messages_from_the_previous_account(self):
        class LoginState:
            is_submitting = False
            error_message = ""
            service_success_message = "Serviço salvo."
            contact_success_message = "Cliente salvo."
            appointment_success_message = "Agendamento salvo."
            appointment_view = "success"
            appointment_success_details = {
                "contact_name": "Cliente da barbearia anterior",
                "contact_phone": "(11) 99999-9999",
                "date_display": "18/11/2026",
                "time_display": "13:30",
                "service_summary": "Corte",
                "total_display": "R$ 30,00",
                "professional_name": "Profissional anterior",
            }
            appointment_working_hours_success_message = "Horários salvos."
            profile_form_success_message = "Perfil salvo."
            profile_photo_success_message = "Foto salva."
            professional_success_message = "Profissional salvo."
            profile_editor_open = True

            def clear_menu_success_messages(self):
                return AuthState.clear_menu_success_messages.fn(self)

            async def _request(self, method, path, payload):
                return None

        state = LoginState()

        async def submit_login():
            return [
                event
                async for event in AuthState.login.fn(
                    state,
                    {"email": "outro-profissional@example.com", "password": "senha"},
                )
            ]

        asyncio.run(submit_login())

        for field in (
            "service_success_message",
            "contact_success_message",
            "appointment_success_message",
            "appointment_working_hours_success_message",
            "profile_form_success_message",
            "profile_photo_success_message",
            "professional_success_message",
        ):
            with self.subTest(field=field):
                self.assertEqual(getattr(state, field), "")
        self.assertEqual(state.appointment_view, "calendar")
        self.assertEqual(
            state.appointment_success_details,
            {
                "contact_name": "",
                "contact_phone": "",
                "date_display": "",
                "time_display": "",
                "service_summary": "",
                "total_display": "",
                "professional_name": "",
            },
        )
        self.assertFalse(state.profile_editor_open)

    def test_tenant_name_is_loaded_and_used_in_shell_and_page_title(self):
        identity_loader = self.frontend.split(
            "async def _load_identity", 1
        )[1].split("async def login", 1)[0]
        self.assertIn(
            '_first_matching_value(profile, "barbershop_name")',
            identity_loader,
        )
        self.assertIn("_brand(tenant_name=AuthState.barbershop_name)", self.frontend)
        self.assertRegex(
            self.frontend,
            re.compile(
                r'rx\.text\(\s*_tenant_display_name\(\),\s*'
                r'class_name="pc-breadcrumb"',
                re.DOTALL,
            ),
        )
        self.assertIn("def _tenant_title_script", self.frontend)
        self.assertIn("json.dumps", self.frontend)
        self.assertIn("text-overflow: ellipsis;", self.styles)
        self.assertIn('title="Equipe"', self.frontend)


if __name__ == "__main__":
    unittest.main()
