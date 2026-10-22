import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from math import ceil, isfinite
from pathlib import Path
from typing import Any

import httpx
import reflex as rx


CONTACT_SOURCE_LABELS = {
    "whatsapp": "WhatsApp",
    "indicacao": "Indicação",
    "instagram": "Instagram",
    "ligacao": "Ligação",
    "outra": "Outra",
}
CONTACT_SOURCE_VALUES = {
    label: value for value, label in CONTACT_SOURCE_LABELS.items()
}
BRAZIL_AREA_CODES = frozenset(
    {
        "11", "12", "13", "14", "15", "16", "17", "18", "19",
        "21", "22", "24", "27", "28",
        "31", "32", "33", "34", "35", "37", "38",
        "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "51", "53", "54", "55",
        "61", "62", "63", "64", "65", "66", "67", "68", "69",
        "71", "73", "74", "75", "77", "79",
        "81", "82", "83", "84", "85", "86", "87", "88", "89",
        "91", "93", "94", "95", "96", "97", "98", "99",
    }
)


def _format_service_price(price: Decimal) -> str:
    formatted = f"{price:,.2f}"
    return "R$ " + formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _format_service_duration(duration_minutes: int) -> str:
    hours, minutes = divmod(duration_minutes, 60)
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


def _format_contact_date(value: Any) -> str:
    iso_date = _contact_date_iso_value(value)
    if not iso_date:
        return str(value or "—")
    parsed_date = date.fromisoformat(iso_date)
    return parsed_date.strftime("%d/%m/%Y")


def _contact_date_iso_value(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        timestamp = value / 1000 if abs(value) >= 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return ""

    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass

    try:
        timestamp = float(text)
    except ValueError:
        return ""
    if abs(timestamp) >= 10_000_000_000:
        timestamp /= 1000
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return ""


def _normalize_contact_phone(value: str) -> str:
    digits = "".join(character for character in value if "0" <= character <= "9")
    if len(digits) in (12, 13) and digits.startswith("55"):
        return digits[2:]
    return digits


def _format_contact_phone(value: str) -> str:
    digits = "".join(character for character in value if "0" <= character <= "9")
    country_prefix = ""
    explicit_country_prefix = value.lstrip().startswith("+55")
    if len(digits) > 11 and digits.startswith("55") and (
        explicit_country_prefix or len(digits) == 13
    ):
        digits = digits[2:]
        country_prefix = "+55 "
    digits = digits[:11]
    if len(digits) <= 2:
        return country_prefix + digits

    area_code = digits[:2]
    subscriber = digits[2:]
    if subscriber.startswith("9"):
        subscriber = subscriber[:9]
        if len(subscriber) > 5:
            subscriber = subscriber[:5] + "-" + subscriber[5:]
    else:
        subscriber = subscriber[:8]
        if len(subscriber) > 4:
            subscriber = subscriber[:4] + "-" + subscriber[4:]
    return f"{country_prefix}({area_code}) {subscriber}"


def _format_cpf(value: str) -> str:
    digits = "".join(character for character in value if "0" <= character <= "9")[:11]
    if len(digits) > 9:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) > 6:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
    if len(digits) > 3:
        return f"{digits[:3]}.{digits[3:]}"
    return digits


def _cpf_validation_error(value: str) -> str:
    digits = "".join(character for character in value if "0" <= character <= "9")
    if len(digits) != 11:
        return "Informe um CPF com 11 dígitos."
    return ""


def _contact_phone_validation_error(value: str) -> str:
    digits = _normalize_contact_phone(value)
    if len(digits) not in (10, 11):
        return "Informe um telefone com DDD e 10 ou 11 dígitos."
    if digits[:2] not in BRAZIL_AREA_CODES:
        return "Informe um DDD válido."
    if len(digits) == 10 and digits[2] not in "23456789":
        return "Informe um telefone fixo ou celular válido."
    if len(digits) == 11 and digits[2] != "9":
        return "Celulares devem ter 9 dígitos após o DDD."
    return ""


def _api_error_message(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        if response.status_code in (401, 403):
            return "Sua sessão expirou ou não tem permissão para esta operação."
        return fallback
    if not isinstance(body, dict):
        if response.status_code in (401, 403):
            return "Sua sessão expirou ou não tem permissão para esta operação."
        return fallback
    for key in ("message", "error", "detail"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested_message = value.get("message")
            if isinstance(nested_message, str) and nested_message.strip():
                return nested_message.strip()
    if response.status_code in (401, 403):
        return "Sua sessão expirou ou não tem permissão para esta operação."
    return fallback


def _configured_api_url(variable_name: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if value:
        return value.rstrip("/")

    env_file = Path(__file__).resolve().parents[1] / ".env"
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, configured_value = line.partition("=")
            if separator and key.strip() == variable_name:
                return configured_value.strip().strip("\"'").rstrip("/")
    except OSError:
        return ""
    return ""


class AuthState(rx.State):
    _auth_token: str = ""

    display_name: str = ""
    role: str = ""
    error_message: str = ""
    temporary_password: str = ""
    is_submitting: bool = False
    professional_phone: str = ""
    professional_cpf: str = ""
    services: list[dict[str, Any]] = []
    service_loading: bool = False
    service_error_message: str = ""
    service_success_message: str = ""
    service_form_error: str = ""
    service_form_open: bool = False
    service_form_name: str = ""
    service_form_description: str = ""
    service_form_price: str = ""
    service_form_duration: str = ""
    service_editing_id: int = 0
    service_search: str = ""
    service_status_filter: str = "Todos os status"
    service_page: int = 1
    service_page_size: int = 5
    contacts: list[dict[str, Any]] = []
    contact_loading: bool = False
    contact_error_message: str = ""
    contact_success_message: str = ""
    contact_form_error: str = ""
    contact_form_open: bool = False
    contact_form_name: str = ""
    contact_form_phone: str = ""
    contact_form_source: str = "WhatsApp"
    contact_form_notes: str = ""
    contact_form_first_contact_at: str = ""
    contact_editing_id: int = 0
    contact_search: str = ""
    contact_status_filter: str = "Ativos"
    contact_source_filter: str = "Todas as origens"
    contact_page: int = 1
    contact_page_size: int = 10
    contact_total_count: int = 0
    contact_confirming_id: int = 0
    contact_confirming_status: str = ""

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        error_context: str = "serviço de acesso",
        query_params: dict[str, Any] | None = None,
    ) -> httpx.Response | None:
        endpoint_path = path.lstrip("/")
        api_group_variable = (
            "XANO_SERVICES_API_URL"
            if endpoint_path == "services" or endpoint_path.startswith("services/")
            else "XANO_CONTACTS_API_URL"
            if endpoint_path == "contacts" or endpoint_path.startswith("contacts/")
            else "XANO_API_URL"
        )
        base_url = _configured_api_url(api_group_variable)
        if not base_url:
            self.error_message = f"Configure {api_group_variable} para conectar ao Xano."
            return None

        headers = {}
        if self._auth_token:
            headers["Authorization"] = "Bearer " + self._auth_token

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                return await client.request(
                    method,
                    f"{base_url}/{endpoint_path}",
                    json=payload,
                    params=query_params,
                    headers=headers,
                )
        except httpx.HTTPError:
            self.error_message = f"Não foi possível conectar ao {error_context}."
            return None

    def _clear_session(self):
        self._auth_token = ""
        self.display_name = ""
        self.role = ""
        self.temporary_password = ""

    @rx.event
    def clear_menu_success_messages(self):
        self.service_success_message = ""
        self.contact_success_message = ""

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
        self.clear_menu_success_messages()
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
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if profile.get("must_change_password", False):
            return rx.redirect("/change-password")

    @rx.event
    async def route_root(self):
        self.clear_menu_success_messages()
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
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            return rx.redirect("/login")
        if not profile.get("must_change_password", False):
            return rx.redirect("/app")

    @rx.event
    async def require_admin(self):
        self.clear_menu_success_messages()
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
        phone = _format_contact_phone(str(form_data.get("phone", "")).strip())
        cpf = _format_cpf(str(form_data.get("cpf", "")).strip())
        phone_error = _contact_phone_validation_error(phone)
        cpf_error = _cpf_validation_error(cpf)
        if phone_error:
            self.error_message = phone_error
            return
        if cpf_error:
            self.error_message = cpf_error
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
                "phone": phone,
                "cpf": cpf,
            },
        )
        if response is None:
            self.is_submitting = False
            return
        if response.status_code not in (200, 201):
            self.error_message = _api_error_message(
                response,
                "Não foi possível criar o profissional. Verifique o e-mail e os dados informados.",
            )
            self.is_submitting = False
            return

        self.temporary_password = response.json().get("temporary_password", "")
        if not self.temporary_password:
            self.error_message = "A conta foi criada, mas a senha temporária não foi retornada. Contate o suporte."
        self.professional_phone = ""
        self.professional_cpf = ""
        self.is_submitting = False

    @rx.event
    def set_professional_phone(self, value: str):
        self.professional_phone = _format_contact_phone(value)

    @rx.event
    def set_professional_cpf(self, value: str):
        self.professional_cpf = _format_cpf(value)

    @rx.event
    def clear_temporary_password(self):
        self.temporary_password = ""

    @rx.event
    def logout(self):
        self.clear_menu_success_messages()
        self._clear_session()
        return rx.redirect("/login")

    @rx.var
    def filtered_services(self) -> list[dict[str, Any]]:
        search = self.service_search.strip().casefold()
        status_filter = self.service_status_filter
        return [
            service
            for service in self.services
            if (
                not search
                or search in service["name"].casefold()
                or search in service["description"].casefold()
            )
            and (
                status_filter == "Todos os status"
                or (status_filter == "Ativos" and service["status"] == "active")
                or (status_filter == "Inativos" and service["status"] == "inactive")
            )
        ]

    @rx.var
    def paginated_services(self) -> list[dict[str, Any]]:
        start = (self.service_page - 1) * self.service_page_size
        return self.filtered_services[start : start + self.service_page_size]

    @rx.var
    def active_service_count(self) -> int:
        return sum(service["status"] == "active" for service in self.services)

    @rx.var
    def inactive_service_count(self) -> int:
        return sum(service["status"] == "inactive" for service in self.services)

    @rx.var
    def service_count(self) -> int:
        return len(self.services)

    @rx.var
    def service_page_count(self) -> int:
        return max(1, ceil(len(self.filtered_services) / self.service_page_size))

    @rx.var
    def service_results_summary(self) -> str:
        count = len(self.filtered_services)
        if count == 0:
            return "Nenhum serviço encontrado"
        first = (self.service_page - 1) * self.service_page_size + 1
        last = min(first + self.service_page_size - 1, count)
        return f"Mostrando {first}–{last} de {count} serviços"

    @rx.event
    def set_service_search(self, value: str):
        self.service_search = value
        self.service_page = 1

    @rx.event
    def set_service_status_filter(self, value: str):
        self.service_status_filter = value
        self.service_page = 1

    @rx.event
    def previous_service_page(self):
        if self.service_page > 1:
            self.service_page -= 1

    @rx.event
    def next_service_page(self):
        if self.service_page < self.service_page_count:
            self.service_page += 1

    async def _load_services(self):
        if self.role not in ("admin", "professional"):
            self.service_loading = False
            self.service_error_message = "Sua sessão não permite consultar o catálogo."
            return

        self.service_loading = True
        self.service_error_message = ""
        path = "services/admin" if self.role == "admin" else "services"
        response = await self._request(
            "GET",
            path,
            error_context="catálogo de serviços",
        )
        if response is None:
            self.service_error_message = self.error_message
            self.service_loading = False
            return
        if response.status_code != 200:
            self.service_error_message = _api_error_message(
                response,
                "Não foi possível carregar o catálogo de serviços. "
                "Verifique seu acesso e tente novamente.",
            )
            self.service_loading = False
            return

        try:
            result = response.json()
            if not isinstance(result, list):
                raise ValueError("A resposta do catálogo não contém uma lista.")

            services = []
            for item in result:
                price = Decimal(str(item["price"]))
                duration_minutes = int(item["duration_minutes"])
                if item["status"] not in ("active", "inactive"):
                    raise ValueError("O catálogo retornou um status de serviço inválido.")
                if (
                    not price.is_finite()
                    or price < 0
                    or duration_minutes < 1
                    or not str(item["name"]).strip()
                ):
                    raise ValueError("O catálogo retornou valores de serviço inválidos.")
                services.append(
                    {
                        "id": int(item["id"]),
                        "name": str(item["name"]),
                        "description": str(item.get("description") or ""),
                        "price": str(price),
                        "price_display": _format_service_price(price),
                        "duration_minutes": duration_minutes,
                        "duration_display": _format_service_duration(duration_minutes),
                        "status": item["status"],
                    }
                )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            self.service_error_message = (
                "O catálogo retornou dados inválidos. Atualize a página ou contate o suporte."
            )
            self.service_loading = False
            return

        self.services = sorted(services, key=lambda service: service["name"].casefold())
        self.service_page = min(self.service_page, self.service_page_count)
        self.service_loading = False

    @rx.event
    async def require_service_access(self):
        self.contact_success_message = ""
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        profile = await self._load_identity()
        if profile is None:
            yield rx.redirect("/login")
            return
        if profile.get("must_change_password", False):
            yield rx.redirect("/change-password")
            return
        self.service_status_filter = (
            "Todos os status"
            if profile.get("role") == "admin"
            else "Ativos"
        )
        self.service_loading = True
        yield
        await self._load_services()

    @rx.var
    def contact_page_count(self) -> int:
        return max(1, ceil(self.contact_total_count / self.contact_page_size))

    @rx.var
    def contact_results_summary(self) -> str:
        if not self.contacts:
            return "Nenhum contato encontrado"
        first = (self.contact_page - 1) * self.contact_page_size + 1
        last = first + len(self.contacts) - 1
        return f"Mostrando {first} – {last} de {self.contact_total_count} contatos"

    @rx.event
    def set_contact_search(self, value: str):
        self.contact_search = value
        self.contact_page = 1

    @rx.event
    async def set_contact_status_filter(self, value: str):
        self.contact_status_filter = value
        self.contact_page = 1
        await self._load_contacts()

    @rx.event
    async def set_contact_source_filter(self, value: str):
        self.contact_source_filter = value
        self.contact_page = 1
        await self._load_contacts()

    @rx.event
    async def previous_contact_page(self):
        if self.contact_page > 1:
            self.contact_page -= 1
            await self._load_contacts()

    @rx.event
    async def next_contact_page(self):
        if self.contact_page < self.contact_page_count:
            self.contact_page += 1
            await self._load_contacts()

    async def _load_contacts(self):
        self.contact_loading = True
        self.contact_error_message = ""
        payload: dict[str, Any] = {
            "page": self.contact_page,
            "page_size": self.contact_page_size,
        }
        if self.contact_search.strip():
            payload["search"] = self.contact_search.strip()
        if self.contact_status_filter != "Todos os status":
            payload["status"] = "active" if self.contact_status_filter == "Ativos" else "inactive"
        if self.contact_source_filter != "Todas as origens":
            payload["source"] = CONTACT_SOURCE_VALUES.get(
                self.contact_source_filter,
                self.contact_source_filter,
            )

        response = await self._request(
            "GET",
            "contacts",
            error_context="cadastro de contatos",
            query_params=payload,
        )
        if response is None:
            self.contact_error_message = self.error_message
            self.contact_loading = False
            return
        if response.status_code != 200:
            self.contact_error_message = _api_error_message(
                response,
                "Não foi possível carregar os contatos. Tente novamente.",
            )
            self.contact_loading = False
            return
        try:
            result = response.json()
            if isinstance(result, list):
                raw_contacts = result
                total_count = len(result)
            elif isinstance(result, dict) and isinstance(result.get("items"), list):
                raw_contacts = result["items"]
                total_value = result.get(
                    "total",
                    result.get("itemsTotal", len(raw_contacts)),
                )
                total_count = int(
                    len(raw_contacts) if total_value is None else total_value
                )
            else:
                raise ValueError("A resposta de contatos não contém uma lista.")
            if total_count < 0:
                raise ValueError("A resposta de contatos contém uma contagem inválida.")
            contacts = []
            for item in raw_contacts:
                if not isinstance(item, dict):
                    raise ValueError("Um contato retornado possui formato inválido.")
                if item.get("status") not in ("active", "inactive"):
                    raise ValueError("Status de contato inválido.")
                first_contact_at = _contact_date_iso_value(item["first_contact_at"])
                if not first_contact_at:
                    raise ValueError("Data do primeiro contato inválida.")
                contacts.append(
                    {
                        "id": int(item["id"]),
                        "name": str(item["name"]).strip(),
                        "phone": _format_contact_phone(str(item["phone"]).strip()),
                        "source": str(item["source"]),
                        "source_display": CONTACT_SOURCE_LABELS.get(
                            str(item["source"]),
                            str(item["source"]),
                        ),
                        "notes": str(item.get("notes") or ""),
                        "status": str(item["status"]),
                        "first_contact_at": first_contact_at,
                        "first_contact_display": _format_contact_date(first_contact_at),
                    }
                )
        except (KeyError, TypeError, ValueError):
            self.contact_error_message = (
                "O cadastro retornou dados inválidos. Atualize a página ou contate o suporte."
            )
            self.contact_loading = False
            return

        self.contacts = contacts
        self.contact_total_count = total_count
        last_page = max(1, ceil(total_count / self.contact_page_size))
        if self.contact_page > last_page:
            self.contact_page = last_page
            await self._load_contacts()
            return
        self.contact_loading = False

    @rx.event
    async def require_contact_access(self):
        self.service_success_message = ""
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        profile = await self._load_identity()
        if profile is None:
            yield rx.redirect("/login")
            return
        if profile.get("must_change_password", False):
            yield rx.redirect("/change-password")
            return
        if profile.get("role") not in ("admin", "professional"):
            yield rx.redirect("/app")
            return
        self.contact_status_filter = "Todos os status" if profile.get("role") == "admin" else "Ativos"
        self.contact_loading = True
        yield
        await self._load_contacts()

    @rx.event
    async def refresh_contacts(self):
        await self._load_contacts()

    @rx.event
    def start_new_contact(self):
        self.contact_editing_id = 0
        self.contact_form_name = ""
        self.contact_form_phone = ""
        self.contact_form_source = "WhatsApp"
        self.contact_form_notes = ""
        self.contact_form_first_contact_at = ""
        self.contact_form_error = ""
        self.contact_form_open = True

    @rx.event
    def start_edit_contact(self, contact_id: int):
        contact = next((item for item in self.contacts if item["id"] == contact_id), None)
        if contact is None:
            self.contact_error_message = "O contato selecionado não está mais disponível."
            return
        self.contact_editing_id = contact_id
        self.contact_form_name = contact["name"]
        self.contact_form_phone = _format_contact_phone(contact["phone"])
        self.contact_form_source = CONTACT_SOURCE_LABELS.get(
            contact["source"],
            contact["source"],
        )
        self.contact_form_notes = contact["notes"]
        self.contact_form_first_contact_at = contact["first_contact_at"][:10]
        self.contact_form_error = ""
        self.contact_form_open = True

    @rx.event
    def cancel_contact_form(self):
        self.contact_form_open = False
        self.contact_form_error = ""

    @rx.event
    def set_contact_form_name(self, value: str):
        self.contact_form_name = value

    @rx.event
    def set_contact_form_phone(self, value: str):
        self.contact_form_phone = _format_contact_phone(value)

    @rx.event
    def set_contact_form_source(self, value: str):
        self.contact_form_source = value

    @rx.event
    def set_contact_form_notes(self, value: str):
        self.contact_form_notes = value

    @rx.event
    def set_contact_form_first_contact_at(self, value: str):
        self.contact_form_first_contact_at = value

    @rx.event
    def request_contact_status(self, contact_id: int, status: str):
        self.contact_confirming_id = contact_id
        self.contact_confirming_status = status

    @rx.event
    def cancel_contact_status(self):
        self.contact_confirming_id = 0
        self.contact_confirming_status = ""

    @rx.event
    async def confirm_contact_status(self):
        if not self.contact_confirming_id:
            return
        contact_id = self.contact_confirming_id
        status = self.contact_confirming_status
        self.contact_confirming_id = 0
        self.contact_confirming_status = ""
        await self.set_contact_status(contact_id, status)

    @rx.event
    async def save_contact(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.is_submitting:
            return
        self.is_submitting = True
        self.contact_form_error = ""
        name = str(form_data.get("name", "")).strip()
        phone = str(form_data.get("phone", "")).strip()
        notes = str(form_data.get("notes", "")).strip()
        first_contact_at = str(form_data.get("first_contact_at", "")).strip()
        source_label = str(form_data.get("source", ""))
        source = CONTACT_SOURCE_VALUES.get(source_label)
        phone_error = _contact_phone_validation_error(phone)
        if not name:
            self.contact_form_error = "Informe o nome do cliente."
        elif len(name) > 120:
            self.contact_form_error = "O nome deve ter no máximo 120 caracteres."
        elif not phone:
            self.contact_form_error = "Informe o telefone do cliente."
        elif phone_error:
            self.contact_form_error = phone_error
        elif source is None:
            self.contact_form_error = "Selecione uma origem válida."
        elif not first_contact_at:
            self.contact_form_error = "Informe a data do primeiro contato."
        elif len(notes) > 1000:
            self.contact_form_error = "As observações devem ter no máximo 1000 caracteres."
        if self.contact_form_error:
            self.is_submitting = False
            return
        payload = {
            "name": name,
            "phone": _normalize_contact_phone(phone),
            "source": source,
            "notes": notes,
            "first_contact_at": first_contact_at,
        }
        path = (
            f"contacts/{self.contact_editing_id}"
            if self.contact_editing_id
            else "contacts"
        )
        response = await self._request(
            "PATCH" if self.contact_editing_id else "POST",
            path,
            payload,
            "cadastro de contatos",
        )
        if response is None or response.status_code not in (200, 201):
            self.contact_form_error = (
                self.error_message
                if response is None
                else _api_error_message(response, "Não foi possível salvar o contato.")
            )
            self.is_submitting = False
            return
        self.contact_form_open = False
        self.contact_success_message = (
            "Contato atualizado com sucesso."
            if self.contact_editing_id
            else "Contato cadastrado com sucesso."
        )
        self.is_submitting = False
        await self._load_contacts()

    @rx.event
    async def set_contact_status(self, contact_id: int, status: str):
        if not self._auth_token:
            return rx.redirect("/login")
        response = await self._request(
            "PATCH",
            f"contacts/{contact_id}/status",
            {"status": status},
            "cadastro de contatos",
        )
        if response is None or response.status_code != 200:
            self.contact_error_message = (
                self.error_message
                if response is None
                else _api_error_message(response, "Não foi possível alterar o status.")
            )
            return
        self.contact_success_message = (
            "Contato ativado com sucesso."
            if status == "active"
            else "Contato desativado com sucesso."
        )
        await self._load_contacts()

    @rx.event
    async def refresh_services(self):
        self.service_loading = True
        yield
        await self._load_services()

    @rx.event
    def start_new_service(self):
        if self.role != "admin":
            return
        self.service_editing_id = 0
        self.service_form_name = ""
        self.service_form_description = ""
        self.service_form_price = ""
        self.service_form_duration = ""
        self.service_form_error = ""
        self.service_form_open = True

    @rx.event
    def start_edit_service(self, service_id: int):
        if self.role != "admin":
            return
        service = next(
            (item for item in self.services if item["id"] == service_id),
            None,
        )
        if service is None:
            self.service_error_message = "O serviço selecionado não está mais disponível."
            return
        self.service_editing_id = service_id
        self.service_form_name = service["name"]
        self.service_form_description = service["description"]
        self.service_form_price = service["price"]
        self.service_form_duration = str(service["duration_minutes"])
        self.service_form_error = ""
        self.service_form_open = True

    @rx.event
    def cancel_service_form(self):
        self.service_form_open = False
        self.service_form_error = ""

    @rx.event
    async def save_service(self, form_data: dict[str, Any]):
        if self.role != "admin":
            self.service_form_error = "Somente a administração pode alterar serviços."
            return
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.is_submitting:
            return

        name = str(form_data.get("name", "")).strip()
        description = str(form_data.get("description", "")).strip()
        try:
            price = Decimal(str(form_data.get("price", "")).strip())
            duration_minutes = int(str(form_data.get("duration_minutes", "")).strip())
        except (InvalidOperation, ValueError):
            self.service_form_error = "Informe um preço e uma duração válidos."
            return
        if not name:
            self.service_form_error = "Informe o nome do serviço."
            return
        if not price.is_finite() or price < 0:
            self.service_form_error = "O preço deve ser positivo ou zero e ter até duas casas decimais."
            return
        try:
            has_invalid_precision = price != price.quantize(Decimal("0.01"))
            api_price = float(price)
        except (InvalidOperation, OverflowError, ValueError):
            self.service_form_error = "Informe um preço válido com até duas casas decimais."
            return
        if has_invalid_precision or not isfinite(api_price):
            self.service_form_error = "O preço deve ser positivo ou zero e ter até duas casas decimais."
            return
        if duration_minutes < 1:
            self.service_form_error = "A duração deve ser de pelo menos um minuto."
            return

        payload = {
            "name": name,
            "description": description,
            "price": api_price,
            "duration_minutes": duration_minutes,
        }
        self.is_submitting = True
        self.service_form_error = ""
        self.service_error_message = ""
        yield
        is_editing = self.service_editing_id > 0
        method = "PATCH" if is_editing else "POST"
        path = (
            f"services/{self.service_editing_id}"
            if is_editing
            else "services"
        )
        response = await self._request(
            method,
            path,
            payload,
            error_context="catálogo de serviços",
        )
        self.is_submitting = False
        if response is None:
            self.service_form_error = self.error_message
            return
        if response.status_code not in (200, 201):
            self.service_form_error = _api_error_message(
                response,
                "Não foi possível salvar o serviço. Confira os dados e tente novamente."
            )
            return

        self.service_form_open = False
        self.service_success_message = (
            "Serviço atualizado com sucesso."
            if is_editing
            else "Serviço cadastrado com sucesso."
        )
        await self._load_services()

    @rx.event
    async def set_service_status(self, service_id: int, status: str):
        if self.role != "admin":
            self.service_error_message = "Somente a administração pode alterar serviços."
            return
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if status not in ("active", "inactive"):
            self.service_error_message = "Status de serviço inválido."
            return
        if self.is_submitting:
            return

        self.is_submitting = True
        self.service_error_message = ""
        yield
        response = await self._request(
            "PATCH",
            f"services/{service_id}/status",
            {"status": status},
            error_context="catálogo de serviços",
        )
        self.is_submitting = False
        if response is None:
            self.service_error_message = self.error_message
            return
        if response.status_code != 200:
            self.service_error_message = _api_error_message(
                response,
                "Não foi possível alterar o status do serviço. Tente novamente."
            )
            return
        self.service_success_message = (
            "Serviço ativado com sucesso."
            if status == "active"
            else "Serviço desativado com sucesso."
        )
        await self._load_services()


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


def _nav_icon(name: str) -> rx.Component:
    return rx.icon(
        name,
        size=16,
        stroke_width=1.8,
        aria_hidden="true",
        class_name="pc-nav-icon",
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
                _nav_icon("layout-dashboard"),
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
            rx.link(
                _nav_icon("scissors"),
                rx.text("Serviços"),
                href="/services",
                tab_index=0,
                aria_current="page" if active_route == "/services" else None,
                class_name=(
                    "pc-nav-link pc-nav-link-active"
                    if active_route == "/services"
                    else "pc-nav-link"
                ),
            ),
            rx.link(
                _nav_icon("contact-round"),
                rx.text("Clientes"),
                href="/contacts",
                tab_index=0,
                aria_current="page" if active_route == "/contacts" else None,
                class_name=(
                    "pc-nav-link pc-nav-link-active"
                    if active_route == "/contacts"
                    else "pc-nav-link"
                ),
            ),
            rx.cond(
                AuthState.role == "admin",
                rx.link(
                    _nav_icon("users-round"),
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
            rx.hstack(
                rx.icon(
                    "circle-user-round",
                    size=20,
                    stroke_width=1.7,
                    aria_hidden="true",
                    class_name="pc-profile-icon",
                ),
                rx.vstack(
                    rx.text(AuthState.display_name, class_name="pc-sidebar-user"),
                    rx.text(
                        rx.cond(AuthState.role == "admin", "Administradora", "Profissional"),
                        class_name="pc-sidebar-role",
                    ),
                    spacing="1",
                    align="start",
                ),
                class_name="pc-sidebar-profile-identity",
                align="center",
            ),
            class_name="pc-sidebar-profile",
            align="start",
            spacing="0",
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
                        (
                            "Visão geral"
                            if active_route == "/app"
                            else "Serviços"
                            if active_route == "/services"
                            else "Clientes e contatos"
                            if active_route == "/contacts"
                            else "Equipe"
                        ),
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
                    value=AuthState.professional_phone,
                    on_change=AuthState.set_professional_phone,
                    placeholder="(00) 00000-0000",
                    required=True,
                    max_length=20,
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
                    value=AuthState.professional_cpf,
                    on_change=AuthState.set_professional_cpf,
                    placeholder="000.000.000-00",
                    required=True,
                    max_length=14,
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


def _service_row(service: Any) -> rx.Component:
    return rx.el.article(
        rx.vstack(
            rx.text(service["name"], class_name="pc-service-name"),
            rx.text(
                rx.cond(service["description"] != "", service["description"], "Sem descrição"),
                class_name="pc-service-description",
            ),
            spacing="1",
            align="start",
            class_name="pc-service-primary",
        ),
        rx.text(
            service["price_display"],
            class_name="pc-service-column pc-service-price",
            data_label="Preço",
        ),
        rx.text(
            service["duration_display"],
            class_name="pc-service-column pc-service-duration",
            data_label="Duração",
        ),
        rx.cond(
            service["status"] == "active",
            rx.text(
                "Ativo",
                class_name="pc-service-status pc-service-status-active",
            ),
            rx.text(
                "Inativo",
                class_name="pc-service-status pc-service-status-inactive",
            ),
        ),
        rx.cond(
            AuthState.role == "admin",
            rx.hstack(
                rx.button(
                    "Editar",
                    type="button",
                    on_click=AuthState.start_edit_service(service["id"]),
                    class_name="pc-service-action pc-service-edit",
                ),
                rx.button(
                    rx.cond(service["status"] == "active", "Desativar", "Ativar"),
                    type="button",
                    disabled=AuthState.is_submitting,
                    on_click=AuthState.set_service_status(
                        service["id"],
                        rx.cond(
                            service["status"] == "active",
                            "inactive",
                            "active",
                        ),
                    ),
                    class_name="pc-service-action pc-service-toggle",
                ),
                class_name="pc-service-actions",
                spacing="3",
            ),
            rx.text("Somente leitura", class_name="pc-service-readonly"),
        ),
        class_name="pc-service-row",
    )


def _service_form() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.heading(
                rx.cond(
                    AuthState.service_editing_id > 0,
                    "Editar serviço",
                    "Cadastrar serviço",
                ),
                class_name="pc-service-form-title",
            ),
            rx.text(
                "Preencha os dados do serviço. Novos serviços começam ativos.",
                class_name="pc-service-form-description",
            ),
            rx.form(
                rx.vstack(
                    rx.vstack(
                        rx.el.label(
                            "Nome do serviço",
                            html_for="service-name",
                            class_name="pc-field-label",
                        ),
                        rx.input(
                            id="service-name",
                            name="name",
                            placeholder="Ex.: Corte tradicional",
                            default_value=AuthState.service_form_name,
                            required=True,
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                    ),
                    rx.vstack(
                        rx.el.label(
                            "Descrição",
                            html_for="service-description",
                            class_name="pc-field-label",
                        ),
                        rx.input(
                            id="service-description",
                            name="description",
                            placeholder="Detalhes opcionais do serviço",
                            default_value=AuthState.service_form_description,
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.el.label(
                                "Preço (R$)",
                                html_for="service-price",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="service-price",
                                name="price",
                                type="number",
                                placeholder="0,00",
                                min="0",
                                step="0.01",
                                default_value=AuthState.service_form_price,
                                required=True,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.el.label(
                                "Duração (minutos)",
                                html_for="service-duration",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="service-duration",
                                name="duration_minutes",
                                type="number",
                                placeholder="Ex.: 45",
                                min="1",
                                step="1",
                                default_value=AuthState.service_form_duration,
                                required=True,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        class_name="pc-service-form-numbers",
                        width="100%",
                        spacing="4",
                        align="start",
                    ),
                    rx.cond(
                        AuthState.service_form_error != "",
                        rx.text(
                            AuthState.service_form_error,
                            role="alert",
                            class_name="pc-alert",
                        ),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                AuthState.is_submitting,
                                "Salvando...",
                                rx.cond(
                                    AuthState.service_editing_id > 0,
                                    "Salvar alterações",
                                    "Cadastrar serviço",
                                ),
                            ),
                            type="submit",
                            disabled=AuthState.is_submitting,
                            class_name="pc-button pc-button-primary",
                        ),
                        rx.button(
                            "Cancelar",
                            type="button",
                            disabled=AuthState.is_submitting,
                            on_click=AuthState.cancel_service_form,
                            class_name="pc-button pc-button-secondary",
                        ),
                        class_name="pc-service-form-actions",
                        spacing="3",
                    ),
                    rx.cond(
                        AuthState.is_submitting,
                        rx.text(
                            "Salvando o serviço...",
                            role="status",
                            class_name="pc-submit-status",
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="4",
                    align="stretch",
                ),
                on_submit=AuthState.save_service,
                reset_on_submit=False,
                width="100%",
                class_name="pc-form",
            ),
            width="100%",
            align="start",
            spacing="3",
        ),
        class_name="pc-service-form-panel",
    )


def service_catalog_page() -> rx.Component:
    content = rx.vstack(
        rx.box(
            rx.vstack(
                rx.text("GESTÃO DA BARBEARIA", class_name="pc-eyebrow"),
                rx.heading("Serviços", class_name="pc-page-title"),
                rx.text(
                    "Gerencie os serviços oferecidos pela sua barbearia.",
                    class_name="pc-page-description",
                ),
                align="start",
                spacing="2",
            ),
            rx.cond(
                AuthState.role == "admin",
                rx.button(
                    rx.text("+", aria_hidden="true"),
                    "Novo serviço",
                    type="button",
                    on_click=AuthState.start_new_service,
                    class_name="pc-button pc-button-primary pc-new-service-button",
                ),
                rx.fragment(),
            ),
            class_name="pc-catalog-header",
        ),
        rx.hstack(
            rx.el.section(
                rx.text("Serviços ativos", class_name="pc-stat-label"),
                rx.text(AuthState.active_service_count, class_name="pc-stat-value"),
                rx.text("disponíveis no catálogo", class_name="pc-stat-note"),
                class_name="pc-stat-card",
            ),
            rx.cond(
                AuthState.role == "admin",
                rx.el.section(
                    rx.text("Serviços inativos", class_name="pc-stat-label"),
                    rx.text(AuthState.inactive_service_count, class_name="pc-stat-value"),
                    rx.text("arquivados temporariamente", class_name="pc-stat-note"),
                    class_name="pc-stat-card",
                ),
                rx.fragment(),
            ),
            rx.el.section(
                rx.text("Catálogo", class_name="pc-stat-label"),
                rx.text("Uma barbearia", class_name="pc-stat-value pc-stat-value-text"),
                rx.text("compartilhado pela equipe", class_name="pc-stat-note"),
                class_name="pc-stat-card",
            ),
            class_name="pc-service-stats",
            spacing="4",
            width="100%",
        ),
        rx.cond(
            AuthState.service_form_open,
            _service_form(),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.service_success_message != "",
            rx.text(
                AuthState.service_success_message,
                role="status",
                class_name="pc-service-success",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.service_error_message != "",
            rx.hstack(
                rx.text(
                    AuthState.service_error_message,
                    role="alert",
                    class_name="pc-service-error-text",
                ),
                rx.button(
                    "Tentar novamente",
                    type="button",
                    on_click=AuthState.refresh_services,
                    class_name="pc-service-action pc-service-edit",
                ),
                class_name="pc-service-error",
                align="center",
                justify="between",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.el.section(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            "Catálogo de serviços",
                            class_name="pc-catalog-title",
                        ),
                        rx.text(
                            rx.cond(
                                AuthState.role == "admin",
                                "Os serviços ativos podem ser consultados pela equipe.",
                                "Consulte os serviços ativos oferecidos pela barbearia.",
                            ),
                            class_name="pc-catalog-description",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.input(
                        type="search",
                        aria_label="Buscar serviço por nome ou descrição",
                        placeholder="Buscar serviço...",
                        value=AuthState.service_search,
                        on_change=AuthState.set_service_search,
                        class_name="pc-service-search",
                    ),
                    rx.select(
                        rx.cond(
                            AuthState.role == "admin",
                            ["Todos os status", "Ativos", "Inativos"],
                            ["Ativos"],
                        ),
                        value=AuthState.service_status_filter,
                        on_change=AuthState.set_service_status_filter,
                        class_name="pc-service-filter",
                    ),
                    class_name="pc-catalog-tools",
                    align="center",
                    spacing="3",
                    width="100%",
                ),
                rx.box(
                    rx.text("SERVIÇO", class_name="pc-service-table-heading"),
                    rx.text("PREÇO", class_name="pc-service-table-heading"),
                    rx.text("DURAÇÃO", class_name="pc-service-table-heading"),
                    rx.text("STATUS", class_name="pc-service-table-heading"),
                    rx.text(
                        rx.cond(
                            AuthState.role == "admin",
                            "AÇÕES",
                            "ACESSO",
                        ),
                        class_name="pc-service-table-heading",
                    ),
                    class_name="pc-service-table-head",
                ),
                rx.cond(
                    AuthState.service_loading,
                    rx.text(
                        "Carregando serviços...",
                        role="status",
                        class_name="pc-service-empty",
                    ),
                    rx.cond(
                        AuthState.service_count == 0,
                        rx.vstack(
                            rx.text(
                                rx.cond(
                                    AuthState.role == "admin",
                                    "Ainda não há serviços cadastrados.",
                                    "Não há serviços ativos disponíveis no momento.",
                                ),
                                class_name="pc-service-empty-title",
                            ),
                            rx.cond(
                                AuthState.role == "admin",
                                rx.button(
                                    "Cadastrar o primeiro serviço",
                                    type="button",
                                    on_click=AuthState.start_new_service,
                                    class_name="pc-button pc-button-primary",
                                ),
                                rx.fragment(),
                            ),
                            class_name="pc-service-empty",
                            align="center",
                            spacing="3",
                        ),
                        rx.cond(
                            AuthState.filtered_services.length() == 0,
                            rx.text(
                                "Nenhum serviço corresponde à busca ou ao filtro.",
                                class_name="pc-service-empty",
                            ),
                            rx.foreach(
                                AuthState.paginated_services,
                                _service_row,
                            ),
                        ),
                    ),
                ),
                rx.hstack(
                    rx.text(
                        AuthState.service_results_summary,
                        class_name="pc-service-results",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Anterior",
                        type="button",
                        disabled=AuthState.service_page <= 1,
                        on_click=AuthState.previous_service_page,
                        class_name="pc-button pc-button-secondary pc-page-button",
                    ),
                    rx.text(
                        "Página ",
                        AuthState.service_page,
                        " de ",
                        AuthState.service_page_count,
                        class_name="pc-service-page-indicator",
                    ),
                    rx.button(
                        "Próxima",
                        type="button",
                        disabled=AuthState.service_page >= AuthState.service_page_count,
                        on_click=AuthState.next_service_page,
                        class_name="pc-button pc-button-secondary pc-page-button",
                    ),
                    class_name="pc-service-pagination",
                    align="center",
                    width="100%",
                ),
                width="100%",
                align="stretch",
                spacing="0",
            ),
            class_name="pc-service-catalog-panel",
        ),
        width="100%",
        align="stretch",
        spacing="5",
        class_name="pc-catalog-content",
    )
    return _app_shell(content, "/services")


def _contact_row(contact: Any) -> rx.Component:
    return rx.el.article(
        rx.vstack(
            rx.text(contact["name"], class_name="pc-service-name"),
            rx.text(contact["phone"], class_name="pc-service-description"),
            spacing="1",
            align="start",
            class_name="pc-service-primary",
        ),
        rx.text(
            contact["source_display"],
            class_name="pc-service-column",
            data_label="Origem",
        ),
        rx.text(
            contact["first_contact_display"],
            class_name="pc-service-column",
            data_label="Primeiro contato",
        ),
        rx.cond(
            contact["status"] == "active",
            rx.text("Ativo", class_name="pc-service-status pc-service-status-active"),
            rx.text("Inativo", class_name="pc-service-status pc-service-status-inactive"),
        ),
        rx.cond(
            AuthState.contact_confirming_id == contact["id"],
            rx.hstack(
                rx.text("Confirmar?", class_name="pc-service-readonly"),
                rx.button(
                    "Sim",
                    type="button",
                    on_click=AuthState.confirm_contact_status,
                    class_name="pc-service-action pc-service-toggle",
                ),
                rx.button(
                    "Não",
                    type="button",
                    on_click=AuthState.cancel_contact_status,
                    class_name="pc-service-action pc-service-edit",
                ),
                class_name="pc-service-actions",
                spacing="3",
            ),
            rx.hstack(
                rx.button(
                    "Editar",
                    type="button",
                    on_click=AuthState.start_edit_contact(contact["id"]),
                    class_name="pc-service-action pc-service-edit",
                ),
                rx.button(
                    rx.cond(contact["status"] == "active", "Desativar", "Ativar"),
                    type="button",
                    disabled=AuthState.is_submitting,
                    on_click=AuthState.request_contact_status(
                        contact["id"],
                        rx.cond(contact["status"] == "active", "inactive", "active"),
                    ),
                    class_name="pc-service-action pc-service-toggle",
                ),
                class_name="pc-service-actions",
                spacing="3",
            ),
        ),
        class_name="pc-service-row",
    )


def _contact_form() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.heading(
                rx.cond(
                    AuthState.contact_editing_id > 0,
                    "Editar cliente",
                    "Novo cliente",
                ),
                class_name="pc-service-form-title",
            ),
            rx.text(
                "Campos marcados com * são obrigatórios. O cliente não terá acesso ao painel.",
                class_name="pc-card-description",
            ),
            rx.form(
                rx.vstack(
                    rx.vstack(
                        rx.el.label("Nome *", html_for="contact-name", class_name="pc-field-label"),
                        rx.input(
                            id="contact-name",
                            name="name",
                            value=AuthState.contact_form_name,
                            on_change=AuthState.set_contact_form_name,
                            placeholder="Nome completo",
                            required=True,
                            max_length=120,
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                    ),
                    rx.vstack(
                        rx.el.label("Telefone *", html_for="contact-phone", class_name="pc-field-label"),
                        rx.input(
                            id="contact-phone",
                            type="tel",
                            name="phone",
                            value=AuthState.contact_form_phone,
                            on_change=AuthState.set_contact_form_phone,
                            placeholder="(00) 00000-0000",
                            required=True,
                            max_length=20,
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.el.label("Origem *", html_for="contact-source", class_name="pc-field-label"),
                            rx.select(
                                list(CONTACT_SOURCE_LABELS.values()),
                                id="contact-source",
                                name="source",
                                value=AuthState.contact_form_source,
                                on_change=AuthState.set_contact_form_source,
                                required=True,
                                class_name="pc-service-filter",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.el.label(
                                "Primeiro contato *",
                                html_for="contact-first-contact",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="contact-first-contact",
                                name="first_contact_at",
                                type="date",
                                value=AuthState.contact_form_first_contact_at,
                                on_change=AuthState.set_contact_form_first_contact_at,
                                required=True,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    rx.vstack(
                        rx.el.label("Observações", html_for="contact-notes", class_name="pc-field-label"),
                        rx.text_area(
                            id="contact-notes",
                            name="notes",
                            value=AuthState.contact_form_notes,
                            on_change=AuthState.set_contact_form_notes,
                            max_length=1000,
                            placeholder="Informações úteis para a equipe",
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                    ),
                    rx.cond(
                        AuthState.contact_form_error != "",
                        rx.text(
                            AuthState.contact_form_error,
                            role="alert",
                            class_name="pc-service-error-text",
                        ),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancelar",
                            type="button",
                            on_click=AuthState.cancel_contact_form,
                            class_name="pc-button pc-button-secondary",
                        ),
                        rx.button(
                            rx.cond(AuthState.is_submitting, "Salvando...", "Salvar contato"),
                            type="submit",
                            disabled=AuthState.is_submitting,
                            class_name="pc-button pc-button-primary",
                        ),
                        spacing="3",
                    ),
                    width="100%",
                    spacing="4",
                ),
                on_submit=AuthState.save_contact,
                reset_on_submit=False,
                width="100%",
                class_name="pc-form",
            ),
            width="100%",
            align="start",
            spacing="3",
        ),
        class_name="pc-service-form-panel",
    )


def contact_catalog_page() -> rx.Component:
    content = rx.vstack(
        rx.box(
            rx.vstack(
                rx.text("GESTÃO DA BARBEARIA", class_name="pc-eyebrow"),
                rx.heading("Clientes e contatos", class_name="pc-page-title"),
                rx.text(
                    "Mantenha uma base compartilhada para toda a equipe.",
                    class_name="pc-page-description",
                ),
                align="start",
                spacing="2",
            ),
            rx.button(
                rx.text("+", aria_hidden="true"),
                "Novo cliente",
                type="button",
                on_click=AuthState.start_new_contact,
                class_name="pc-button pc-button-primary pc-new-service-button",
            ),
            class_name="pc-catalog-header",
        ),
        rx.cond(AuthState.contact_form_open, _contact_form(), rx.fragment()),
        rx.cond(
            AuthState.contact_success_message != "",
            rx.text(
                AuthState.contact_success_message,
                role="status",
                class_name="pc-service-success",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.contact_error_message != "",
            rx.hstack(
                rx.text(AuthState.contact_error_message, role="alert", class_name="pc-service-error-text"),
                rx.button(
                    "Tentar novamente",
                    type="button",
                    on_click=AuthState.refresh_contacts,
                    class_name="pc-service-action pc-service-edit",
                ),
                class_name="pc-service-error",
                align="center",
                justify="between",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.el.section(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Base de clientes", class_name="pc-catalog-title"),
                        rx.text(AuthState.contact_results_summary, class_name="pc-catalog-description"),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.input(
                        type="search",
                        aria_label="Buscar cliente por nome ou telefone",
                        placeholder="Buscar cliente...",
                        value=AuthState.contact_search,
                        on_change=AuthState.set_contact_search,
                        on_blur=AuthState.refresh_contacts,
                        class_name="pc-service-search",
                    ),
                    rx.select(
                        rx.cond(
                            AuthState.role == "admin",
                            ["Todos os status", "Ativos", "Inativos"],
                            ["Ativos"],
                        ),
                        value=AuthState.contact_status_filter,
                        on_change=AuthState.set_contact_status_filter,
                        class_name="pc-service-filter",
                    ),
                    rx.select(
                        [
                            "Todas as origens",
                            *CONTACT_SOURCE_LABELS.values(),
                        ],
                        value=AuthState.contact_source_filter,
                        on_change=AuthState.set_contact_source_filter,
                        class_name="pc-service-filter",
                    ),
                    class_name="pc-catalog-tools",
                    align="center",
                    spacing="3",
                    width="100%",
                ),
                rx.box(
                    rx.text("CLIENTE", class_name="pc-service-table-heading"),
                    rx.text("ORIGEM", class_name="pc-service-table-heading"),
                    rx.text("PRIMEIRO CONTATO", class_name="pc-service-table-heading"),
                    rx.text("STATUS", class_name="pc-service-table-heading"),
                    rx.text("AÇÕES", class_name="pc-service-table-heading"),
                    class_name="pc-service-table-head",
                ),
                rx.cond(
                    AuthState.contact_loading,
                    rx.text("Carregando contatos...", role="status", class_name="pc-service-empty"),
                    rx.cond(
                        AuthState.contacts.length() == 0,
                        rx.vstack(
                            rx.text("Nenhum cliente encontrado.", class_name="pc-service-empty-title"),
                            rx.button(
                                "Cadastrar o primeiro cliente",
                                type="button",
                                on_click=AuthState.start_new_contact,
                                class_name="pc-button pc-button-primary",
                            ),
                            class_name="pc-service-empty",
                            align="center",
                            spacing="3",
                        ),
                        rx.vstack(
                            rx.foreach(AuthState.contacts, _contact_row),
                            width="100%",
                            spacing="0",
                        ),
                    ),
                ),
                rx.hstack(
                    rx.button(
                        "Anterior",
                        type="button",
                        disabled=(AuthState.contact_page <= 1) | AuthState.contact_loading,
                        on_click=AuthState.previous_contact_page,
                        class_name="pc-button pc-button-secondary pc-page-button",
                    ),
                    rx.text(
                        "Página ",
                        AuthState.contact_page,
                        " de ",
                        AuthState.contact_page_count,
                        class_name="pc-service-page-indicator",
                    ),
                    rx.button(
                        "Próxima",
                        type="button",
                        disabled=(AuthState.contact_page >= AuthState.contact_page_count)
                        | AuthState.contact_loading,
                        on_click=AuthState.next_contact_page,
                        class_name="pc-button pc-button-secondary pc-page-button",
                    ),
                    class_name="pc-service-pagination",
                    align="center",
                    justify="end",
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                align="stretch",
                spacing="3",
            ),
            class_name="pc-catalog-content",
        ),
        width="100%",
        align="stretch",
        spacing="4",
        class_name="pc-team-content",
    )
    return _app_shell(content, "/contacts")


def register_pages(app: rx.App):
    app.add_page(
        login_page,
        route="/login",
        title="Entrar | Lotus Barber",
        on_load=AuthState.clear_menu_success_messages,
    )
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
    app.add_page(
        service_catalog_page,
        route="/services",
        title="Serviços | Lotus Barber",
        on_load=AuthState.require_service_access,
    )
    app.add_page(
        contact_catalog_page,
        route="/contacts",
        title="Clientes e contatos | Lotus Barber",
        on_load=AuthState.require_contact_access,
    )
    app.add_page(
        login_page,
        route="/",
        title="Entrar | Lotus Barber",
        on_load=AuthState.clear_menu_success_messages,
    )
