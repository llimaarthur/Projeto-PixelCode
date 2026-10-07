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
        self.error_message = ""
        response = await self._request(
            "POST",
            "auth/login",
            {
                "email": form_data.get("email", "").strip(),
                "password": form_data.get("password", ""),
            },
        )
        if response is None:
            return
        if response.status_code != 200:
            self.error_message = "E-mail ou senha inválidos, ou conta inativa."
            return

        result = response.json()
        self._auth_token = result.get("authToken", "")
        self.display_name = result.get("name", "")
        self.role = result.get("role", "")
        if result.get("must_change_password", False):
            return rx.redirect("/change-password")
        return rx.redirect("/app")

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
            return rx.redirect("/login")
        self.error_message = ""
        response = await self._request(
            "POST",
            "auth/change-temporary-password",
            {
                "new_password": form_data.get("new_password", ""),
                "confirm_password": form_data.get("confirm_password", ""),
            },
        )
        if response is None:
            return
        if response.status_code != 200:
            self.error_message = "Não foi possível alterar a senha. Confira os requisitos e tente novamente."
            return
        return rx.redirect("/app")

    @rx.event
    async def create_professional(self, form_data: dict[str, Any]):
        if not self._auth_token:
            return rx.redirect("/login")
        self.error_message = ""
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
            return
        if response.status_code not in (200, 201):
            self.error_message = "Não foi possível criar o profissional. Verifique o e-mail e os dados informados."
            return

        self.temporary_password = response.json().get("temporary_password", "")
        if not self.temporary_password:
            self.error_message = "A conta foi criada, mas a senha temporária não foi retornada. Contate o suporte."

    @rx.event
    def clear_temporary_password(self):
        self.temporary_password = ""

    @rx.event
    def logout(self):
        self._clear_session()
        return rx.redirect("/login")


def _message():
    return rx.cond(
        AuthState.error_message != "",
        rx.text(AuthState.error_message, color="tomato", role="alert"),
        rx.fragment(),
    )


def login_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("PixelCode", size="7"),
            rx.text("Acesso da equipe da barbearia", color_scheme="gray"),
            rx.form(
                rx.vstack(
                    rx.input(
                        name="email",
                        type="email",
                        placeholder="E-mail",
                        required=True,
                        width="100%",
                    ),
                    rx.input(
                        name="password",
                        type="password",
                        placeholder="Senha",
                        required=True,
                        width="100%",
                    ),
                    _message(),
                    rx.button("Entrar", type="submit", width="100%"),
                    width="100%",
                    spacing="4",
                ),
                on_submit=AuthState.login,
                reset_on_submit=False,
                width="100%",
            ),
            width="100%",
            max_width="24rem",
            spacing="5",
            align="stretch",
            padding_y="12",
            margin_x="auto",
        ),
    )


def change_password_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Defina sua senha", size="6"),
            rx.text("Para continuar, substitua a senha temporária."),
            rx.form(
                rx.vstack(
                    rx.input(
                        name="new_password",
                        type="password",
                        placeholder="Nova senha (mínimo 8 caracteres)",
                        min_length=8,
                        required=True,
                        width="100%",
                    ),
                    rx.input(
                        name="confirm_password",
                        type="password",
                        placeholder="Confirme a nova senha",
                        min_length=8,
                        required=True,
                        width="100%",
                    ),
                    _message(),
                    rx.button("Salvar senha", type="submit", width="100%"),
                    width="100%",
                    spacing="4",
                ),
                on_submit=AuthState.change_temporary_password,
                reset_on_submit=False,
                width="100%",
            ),
            max_width="28rem",
            spacing="4",
            align="stretch",
            padding_y="12",
            margin_x="auto",
            width="100%",
        ),
    )


def app_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Área da barbearia", size="6"),
                    rx.text("Bem-vindo(a), ", AuthState.display_name),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.button("Sair", on_click=AuthState.logout, variant="soft"),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                AuthState.role == "admin",
                rx.vstack(
                    rx.heading("Equipe", size="4"),
                    rx.text("Cadastre os profissionais que terão acesso ao sistema."),
                    rx.link(rx.button("Cadastrar profissional"), href="/team/new"),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.text(
                "Acesso configurado. As áreas de clientes, serviços, agenda e pagamentos serão adicionadas em etapas próprias.",
                color_scheme="gray",
            ),
            width="100%",
            max_width="52rem",
            spacing="6",
            align="stretch",
            padding_y="8",
            margin_x="auto",
        ),
    )


def create_professional_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.hstack(
                rx.heading("Cadastrar profissional", size="6"),
                rx.spacer(),
                rx.link("Voltar", href="/app"),
                width="100%",
            ),
            rx.text("Todos os campos são obrigatórios. A senha temporária será exibida uma única vez."),
            rx.form(
                rx.vstack(
                    rx.input(name="name", placeholder="Nome completo", required=True, width="100%"),
                    rx.input(name="email", type="email", placeholder="E-mail", required=True, width="100%"),
                    rx.input(name="phone", type="tel", placeholder="Telefone", required=True, width="100%"),
                    rx.input(name="cpf", placeholder="CPF", required=True, width="100%"),
                    _message(),
                    rx.button("Criar conta", type="submit"),
                    width="100%",
                    spacing="4",
                ),
                on_submit=AuthState.create_professional,
                reset_on_submit=True,
                width="100%",
            ),
            rx.cond(
                AuthState.temporary_password != "",
                rx.vstack(
                    rx.text("Copie e entregue esta senha ao profissional por um canal seguro."),
                    rx.code(AuthState.temporary_password),
                    rx.button("Ocultar senha", on_click=AuthState.clear_temporary_password, variant="soft"),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                rx.fragment(),
            ),
            max_width="34rem",
            width="100%",
            spacing="5",
            align="stretch",
            padding_y="8",
            margin_x="auto",
        ),
    )


def register_pages(app: rx.App):
    app.add_page(login_page, route="/login", title="Entrar | PixelCode")
    app.add_page(
        change_password_page,
        route="/change-password",
        title="Definir senha | PixelCode",
        on_load=AuthState.require_password_change,
    )
    app.add_page(
        app_page,
        route="/app",
        title="Barbearia | PixelCode",
        on_load=AuthState.require_session,
    )
    app.add_page(
        create_professional_page,
        route="/team/new",
        title="Cadastrar profissional | PixelCode",
        on_load=AuthState.require_admin,
    )
    app.add_page(login_page, route="/", title="Entrar | PixelCode")