import os
from typing import Any

import httpx
import reflex as rx


class AuthState(rx.State):
    _auth_token: str = ""

    display_name: str = ""
    role: str = ""
    error_message: str = ""
    temporary_password: str = ""
    is_submitting: bool = False

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> httpx.Response | None:
        base_url = os.environ.get("XANO_API_URL", "").rstrip("/")
        if not base_url:
            self.error_message = "Configure XANO_API_URL para conectar ao Xano."
            return None

        headers = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                return await client.request(
                    method,
                    f"{base_url}/{path.lstrip('/')}",
                    json=payload,
                    headers=headers,
                )
        except httpx.HTTPError:
            self.error_message = "Não foi possível conectar ao serviço de acesso."
            return None

    def _clear_session(self):
        self._auth_token = ""
        self.display_name = ""
        self.role = ""
        self.temporary_password = ""

    async def _load_identity(self) -> dict | None:
        response = await self._request("GET", "auth/me")
        if response is None or response.status_code != 200:
            self._clear_session()
            return None

        profile = response.json()
        self.display_name = profile.get("name", "")
        self.role = profile.get("role", "")
        return profile

    @rx.event
    async def login(self, form_data: dict[str, Any]):
        if self.is_submitting:
            return
        self.is_submitting = True
        self.error_message = ""
        yield
        response = await self._request(
            "POST",
            "auth/login",
            {
                "email": form_data.get("email", "").strip(),
                "password": form_data.get("password", ""),
            },
        )
        if response is None:
            self.is_submitting = False
            return
        if response.status_code != 200:
            self.error_message = "E-mail ou senha inválidos, ou conta inativa."
            self.is_submitting = False
            return

        result = response.json()
        self._auth_token = result.get("authToken", "")
        self.display_name = result.get("name", "")
        self.role = result.get("role", "")
        self.is_submitting = False
        if result.get("must_change_password", False):
            yield rx.redirect("/change-password")
            return
        yield rx.redirect("/app")

    @rx.event
    async def require_session(self):
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if profile.get("must_change_password", False):
            return rx.redirect("/change-password")

    @rx.event
    async def route_root(self):
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if profile.get("must_change_password", False):
            return rx.redirect("/change-password")
        return rx.redirect("/app")

    @rx.event
    async def require_password_change(self):
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if not profile.get("must_change_password", False):
            return rx.redirect("/app")

    @rx.event
    async def require_admin(self):
        self.temporary_password = ""
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if profile.get("must_change_password", False):
            return rx.redirect("/change-password")
        if profile.get("role") != "admin":
            return rx.redirect("/app")

    @rx.event
    async def change_temporary_password(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.is_submitting:
            return
        self.is_submitting = True
        self.error_message = ""
        yield
        response = await self._request(
            "POST",
            "auth/change-temporary-password",
            {
                "new_password": form_data.get("new_password", ""),
                "confirm_password": form_data.get("confirm_password", ""),
            },
        )
        if response is None:
            self.is_submitting = False
            return
        if response.status_code != 200:
            self.error_message = "Não foi possível alterar a senha. Confira os requisitos e tente novamente."
            self.is_submitting = False
            return
        self.is_submitting = False
        yield rx.redirect("/app")

    @rx.event
    async def create_professional(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.is_submitting:
            return
        self.is_submitting = True
        self.error_message = ""
        yield
        response = await self._request(
            "POST",
            "auth/professionals",
            {
                "name": form_data.get("name", "").strip(),
                "email": form_data.get("email", "").strip(),
                "phone": form_data.get("phone", "").strip(),
                "cpf": form_data.get("cpf", "").strip(),
            },
        )
        if response is None:
            self.is_submitting = False
            return
        if response.status_code not in (200, 201):
            self.error_message = "Não foi possível criar o profissional. Verifique o e-mail e os dados informados."
            self.is_submitting = False
            return

        self.temporary_password = response.json().get("temporary_password", "")
        if not self.temporary_password:
            self.error_message = "A conta foi criada, mas a senha temporária não foi retornada. Contate o suporte."
        self.is_submitting = False

    @rx.event
    def clear_temporary_password(self):
        self.temporary_password = ""

    @rx.event
    def logout(self):
        self._clear_session()
        return rx.redirect("/login")


def _brand() -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.el.svg(
                rx.el.path(
                    d="M21 9c-2 4-7 6-7 12a7 7 0 0 0 14 0c0-6-5-8-7-12zm0 8c2 3 4 4 4 6a4 4 0 0 1-8 0c0-2 2-4 4-6z",
                    fill="currentColor",
                ),
                view_box="0 0 42 42",
                width="25",
                height="25",
                aria_hidden="true",
            ),
            class_name="pc-brand-mark",
            aria_hidden="true",
        ),
        rx.vstack(
            rx.text("Lotus Barber", class_name="pc-brand-name"),
            rx.text("GESTÃO DA BARBEARIA", class_name="pc-brand-caption"),
            spacing="0",
            align="start",
        ),
        class_name="pc-brand",
        spacing="3",
        align="center",
    )


def _message() -> rx.Component:
    return rx.cond(
        AuthState.error_message != "",
        rx.text(AuthState.error_message, role="alert", class_name="pc-alert"),
        rx.fragment(),
    )


def _auth_intro() -> rx.Component:
    return rx.vstack(
        rx.text("ACESSO PROFISSIONAL", class_name="pc-eyebrow"),
        rx.heading("Seu talento", class_name="pc-auth-title"),
        rx.heading("em primeiro lugar.", class_name="pc-auth-title pc-auth-title-second"),
        rx.text(
            "Organize sua rotina e deixe a gestão mais simples para focar no que você faz melhor.",
            class_name="pc-auth-description",
        ),
        rx.box(class_name="pc-accent-rule", aria_hidden="true"),
        rx.text("Agenda · equipe · atendimento", class_name="pc-auth-meta"),
        class_name="pc-auth-intro",
        spacing="3",
        align="start",
    )


def _auth_shell(card: rx.Component) -> rx.Component:
    return rx.el.main(
        _brand(),
        rx.box(
            _auth_intro(),
            card,
            class_name="pc-auth-layout",
        ),
        class_name="pc-auth-page",
    )


def _auth_card(title: str, description: str, form: rx.Component) -> rx.Component:
    return rx.el.section(
        rx.box(class_name="pc-stripe", aria_hidden="true"),
        rx.vstack(
            rx.heading(title, class_name="pc-card-title"),
            rx.text(description, class_name="pc-card-description"),
            form,
            rx.text(
                "Acesso exclusivo para a equipe da barbearia.",
                class_name="pc-card-note",
            ),
            rx.text("LOTUS BARBER · PAINEL INTERNO", class_name="pc-card-footer"),
            class_name="pc-auth-card-content",
            spacing="0",
            align="stretch",
        ),
        class_name="pc-auth-card",
        aria_label=title,
    )


def login_page() -> rx.Component:
    login_form = rx.form(
        rx.vstack(
            rx.vstack(
                rx.el.label("E-mail", html_for="login-email", class_name="pc-field-label"),
                rx.input(
                    id="login-email",
                    name="email",
                    type="email",
                    placeholder="nome@barbearia.com",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("Senha", html_for="login-password", class_name="pc-field-label"),
                rx.input(
                    id="login-password",
                    name="password",
                    type="password",
                    placeholder="Digite sua senha",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            _message(),
            rx.button(
                rx.cond(AuthState.is_submitting, "Entrando...", "Entrar na plataforma"),
                rx.cond(
                    AuthState.is_submitting,
                    rx.fragment(),
                    rx.text("→", class_name="pc-button-arrow", aria_hidden="true"),
                ),
                type="submit",
                disabled=AuthState.is_submitting,
                class_name="pc-button pc-button-primary",
                width="100%",
            ),
            rx.cond(
                AuthState.is_submitting,
                rx.text("Validando seu acesso...", role="status", class_name="pc-submit-status"),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        on_submit=AuthState.login,
        reset_on_submit=False,
        width="100%",
        class_name="pc-form",
    )
    return _auth_shell(
        _auth_card(
            "Bem-vindo de volta",
            "Acesse sua conta da equipe.",
            login_form,
        )
    )


def change_password_page() -> rx.Component:
    password_form = rx.form(
        rx.vstack(
            rx.vstack(
                rx.el.label("Nova senha", html_for="new-password", class_name="pc-field-label"),
                rx.input(
                    id="new-password",
                    name="new_password",
                    type="password",
                    placeholder="Mínimo de 8 caracteres",
                    min_length=8,
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("Confirme a nova senha", html_for="confirm-password", class_name="pc-field-label"),
                rx.input(
                    id="confirm-password",
                    name="confirm_password",
                    type="password",
                    placeholder="Digite novamente a nova senha",
                    min_length=8,
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            _message(),
            rx.button(
                rx.cond(AuthState.is_submitting, "Salvando...", "Salvar senha"),
                rx.cond(
                    AuthState.is_submitting,
                    rx.fragment(),
                    rx.text("→", class_name="pc-button-arrow", aria_hidden="true"),
                ),
                type="submit",
                disabled=AuthState.is_submitting,
                class_name="pc-button pc-button-primary",
                width="100%",
            ),
            rx.cond(
                AuthState.is_submitting,
                rx.text("Atualizando sua senha...", role="status", class_name="pc-submit-status"),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        on_submit=AuthState.change_temporary_password,
        reset_on_submit=False,
        width="100%",
        class_name="pc-form",
    )
    return _auth_shell(
        _auth_card(
            "Defina sua senha",
            "Para continuar, substitua a senha temporária.",
            password_form,
        )
    )


def _app_sidebar(active_route: str) -> rx.Component:
    return rx.el.aside(
        rx.box(class_name="pc-sidebar-stripe", aria_hidden="true"),
        _brand(),
        rx.text("MENU PRINCIPAL", class_name="pc-sidebar-label"),
        rx.vstack(
            rx.link(
                rx.text("Visão geral"),
                href="/app",
                tab_index=0,
                aria_current="page" if active_route == "/app" else None,
                class_name=(
                    "pc-nav-link pc-nav-link-active"
                    if active_route == "/app"
                    else "pc-nav-link"
                ),
            ),
            rx.cond(
                AuthState.role == "admin",
                rx.link(
                    rx.text("Equipe"),
                    href="/team/new",
                    tab_index=0,
                    aria_current="page" if active_route == "/team/new" else None,
                    class_name=(
                        "pc-nav-link pc-nav-link-active"
                        if active_route == "/team/new"
                        else "pc-nav-link"
                    ),
                ),
                rx.fragment(),
            ),
            width="100%",
            spacing="2",
            class_name="pc-nav",
        ),
        rx.vstack(
            rx.text(AuthState.display_name, class_name="pc-sidebar-user"),
            rx.text(
                rx.cond(AuthState.role == "admin", "Administradora", "Profissional"),
                class_name="pc-sidebar-role",
            ),
            class_name="pc-sidebar-profile",
            align="start",
            spacing="1",
        ),
        class_name="pc-sidebar",
    )


def _app_shell(content: rx.Component, active_route: str) -> rx.Component:
    return rx.el.main(
        rx.link(
            "Pular para o conteúdo principal",
            href="#pc-main-content",
            class_name="pc-skip-link",
            tab_index=0,
            on_click=rx.call_script(
                "document.getElementById('pc-main-content').focus()"
            ),
        ),
        _app_sidebar(active_route),
        rx.box(
            rx.el.header(
                rx.hstack(
                    rx.text("Lotus Barber", class_name="pc-breadcrumb"),
                    rx.text("/", class_name="pc-breadcrumb-divider"),
                    rx.text(
                        "Visão geral" if active_route == "/app" else "Equipe",
                        class_name="pc-breadcrumb-current",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Sair",
                        on_click=AuthState.logout,
                        class_name="pc-button pc-button-secondary pc-logout",
                    ),
                    width="100%",
                    align="center",
                ),
                class_name="pc-topbar",
            ),
            rx.box(
                content,
                id="pc-main-content",
                tab_index=-1,
                class_name="pc-main-content",
            ),
            class_name="pc-app-main",
        ),
        class_name="pc-app-shell",
    )


def app_page() -> rx.Component:
    content = rx.vstack(
        rx.text("ESPAÇO DE TRABALHO", class_name="pc-eyebrow"),
        rx.heading("Bem-vindo(a), ", AuthState.display_name, class_name="pc-page-title"),
        rx.text(
            "Organize a rotina da sua barbearia em um só lugar.",
            class_name="pc-page-description",
        ),
        rx.el.section(
            rx.vstack(
                rx.box(class_name="pc-panel-accent", aria_hidden="true"),
                rx.text("SUA OPERAÇÃO, COM MAIS CLAREZA", class_name="pc-eyebrow"),
                rx.heading(
                    "Tudo pronto para começar",
                    class_name="pc-panel-title",
                ),
                rx.text(
                    "O acesso da equipe está configurado. As próximas áreas de gestão serão adicionadas em etapas próprias.",
                    class_name="pc-panel-description",
                ),
                rx.cond(
                    AuthState.role == "admin",
                    rx.link(
                        "Cadastrar profissional",
                        href="/team/new",
                        tab_index=0,
                        class_name="pc-button pc-button-primary pc-action-link",
                    ),
                    rx.fragment(),
                ),
                align="start",
                spacing="4",
                width="100%",
            ),
            class_name="pc-welcome-panel",
        ),
        width="100%",
        align="stretch",
        spacing="4",
        class_name="pc-dashboard-content",
    )
    return _app_shell(content, "/app")


def create_professional_page() -> rx.Component:
    professional_form = rx.form(
        rx.vstack(
            rx.vstack(
                rx.el.label("Nome completo", html_for="professional-name", class_name="pc-field-label"),
                rx.input(
                    id="professional-name",
                    name="name",
                    placeholder="Nome do profissional",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("E-mail", html_for="professional-email", class_name="pc-field-label"),
                rx.input(
                    id="professional-email",
                    name="email",
                    type="email",
                    placeholder="nome@barbearia.com",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("Telefone", html_for="professional-phone", class_name="pc-field-label"),
                rx.input(
                    id="professional-phone",
                    name="phone",
                    type="tel",
                    placeholder="(00) 00000-0000",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("CPF", html_for="professional-cpf", class_name="pc-field-label"),
                rx.input(
                    id="professional-cpf",
                    name="cpf",
                    placeholder="000.000.000-00",
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            _message(),
            rx.button(
                rx.cond(AuthState.is_submitting, "Criando conta...", "Criar conta"),
                rx.cond(
                    AuthState.is_submitting,
                    rx.fragment(),
                    rx.text("→", class_name="pc-button-arrow", aria_hidden="true"),
                ),
                type="submit",
                disabled=AuthState.is_submitting,
                class_name="pc-button pc-button-primary",
            ),
            rx.cond(
                AuthState.is_submitting,
                rx.text("Criando o acesso do profissional...", role="status", class_name="pc-submit-status"),
                rx.fragment(),
            ),
            width="100%",
            spacing="4",
        ),
        on_submit=AuthState.create_professional,
        reset_on_submit=True,
        width="100%",
        class_name="pc-form",
    )
    content = rx.vstack(
        rx.text("GESTÃO DA EQUIPE", class_name="pc-eyebrow"),
        rx.heading("Cadastrar profissional", class_name="pc-page-title"),
        rx.text(
            "Todos os campos são obrigatórios. A senha temporária será exibida uma única vez.",
            class_name="pc-page-description",
        ),
        rx.el.section(
            professional_form,
            rx.cond(
                AuthState.temporary_password != "",
                rx.vstack(
                    rx.text("Acesso inicial", class_name="pc-secret-title"),
                    rx.text(
                        "Copie e entregue esta senha ao profissional por um canal seguro.",
                        class_name="pc-secret-description",
                    ),
                    rx.code(AuthState.temporary_password, class_name="pc-secret-code"),
                    rx.button(
                        "Ocultar senha",
                        on_click=AuthState.clear_temporary_password,
                        class_name="pc-button pc-button-secondary",
                    ),
                    align="start",
                    spacing="3",
                    width="100%",
                    class_name="pc-secret-panel",
                ),
                rx.fragment(),
            ),
            class_name="pc-form-panel",
        ),
        width="100%",
        align="stretch",
        spacing="4",
        class_name="pc-team-content",
    )
    return _app_shell(content, "/team/new")


def register_pages(app: rx.App):
    app.add_page(login_page, route="/login", title="Entrar | Lotus Barber")
    app.add_page(
        change_password_page,
        route="/change-password",
        title="Definir senha | Lotus Barber",
        on_load=AuthState.require_password_change,
    )
    app.add_page(
        app_page,
        route="/app",
        title="Barbearia | Lotus Barber",
        on_load=AuthState.require_session,
    )
    app.add_page(
        create_professional_page,
        route="/team/new",
        title="Cadastrar profissional | Lotus Barber",
        on_load=AuthState.require_admin,
    )
    app.add_page(login_page, route="/", title="Entrar | Lotus Barber")