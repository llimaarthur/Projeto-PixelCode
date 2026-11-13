import asyncio
import os
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from math import ceil, isfinite
from pathlib import Path
from typing import Any

import httpx
import reflex as rx
from reflex.utils.exec import is_prod_mode

from frontend.finance_service import (
    BARBERSHOP_TIMEZONE,
    FinanceDataError,
    finance_dashboard_from_transactions,
    mock_finance_dashboard,
    normalize_finance_dashboard,
    prepare_cashflow_chart,
    should_use_finance_mock,
)
from frontend.overview_service import (
    OVERVIEW_PERIODS,
    overview_metrics,
    summarize_contacts,
    upcoming_appointments,
)


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
APPOINTMENT_STATUS_LABELS = {
    "pending": "Pendente",
    "confirmed": "Confirmado",
    "completed": "Concluído",
    "cancelled": "Cancelado",
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
BARBERSHOP_TIMEZONE = timezone(timedelta(hours=-3))
BARBERSHOP_HOURS = {
    0: ((9 * 60, 12 * 60), (13 * 60, 19 * 60)),
    1: ((9 * 60, 12 * 60), (13 * 60, 19 * 60)),
    2: ((9 * 60, 12 * 60), (13 * 60, 19 * 60)),
    3: ((9 * 60, 12 * 60), (13 * 60, 19 * 60)),
    4: ((9 * 60, 12 * 60), (13 * 60, 19 * 60)),
    5: ((9 * 60, 14 * 60),),
}


def _today_in_barbershop_timezone() -> date:
    return datetime.now(BARBERSHOP_TIMEZONE).date()


def _calculate_appointment_time_slots(
    selected_date: date,
    professionals: list[dict[str, Any]],
    duration_minutes: int,
    appointments: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    exclude_appointment_id: int = 0,
) -> list[dict[str, str]]:
    periods = BARBERSHOP_HOURS.get(selected_date.weekday(), ())
    if not periods or not professionals or duration_minutes <= 0:
        return []

    slots: list[dict[str, str]] = []
    for period_start, period_end in periods:
        for start_minutes in range(period_start, period_end, 30):
            slot_start = datetime.combine(
                selected_date,
                time(start_minutes // 60, start_minutes % 60),
                tzinfo=BARBERSHOP_TIMEZONE,
            )
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            fits_working_period = start_minutes + duration_minutes <= period_end
            available_professionals = []
            blocked_count = 0
            for professional in professionals:
                professional_id = professional["id"]
                if not fits_working_period:
                    blocked_count += 1
                    continue
                blocked = any(
                    block["professional_id"] in (0, professional_id)
                    and _parse_appointment_datetime(block["start_at"]) < slot_end
                    and _parse_appointment_datetime(block["end_at"]) > slot_start
                    for block in blocks
                )
                occupied = any(
                    appointment["id"] != exclude_appointment_id
                    and appointment["professional_id"] == professional_id
                    and appointment["status"] != "cancelled"
                    and _parse_appointment_datetime(appointment["start_at"]) < slot_end
                    and _parse_appointment_datetime(appointment["end_at"]) > slot_start
                    for appointment in appointments
                )
                if blocked:
                    blocked_count += 1
                elif not occupied:
                    available_professionals.append(professional)
            state = (
                "available"
                if available_professionals
                else "blocked"
                if blocked_count == len(professionals)
                else "occupied"
            )
            slots.append(
                {
                    "time": slot_start.strftime("%H:%M"),
                    "state": state,
                    "professional_id": str(
                        available_professionals[0]["id"]
                        if available_professionals
                        else 0
                    ),
                    "professional_name": (
                        available_professionals[0]["name"]
                        if available_professionals
                        else ""
                    ),
                }
            )
    return slots


MONTH_LABELS = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _format_service_price(price: Decimal) -> str:
    formatted = f"{price:,.2f}"
    return "R$ " + formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _appointment_status_from_response(payload: Any, appointment_id: int) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        raise ValueError("A confirmação do status é inválida.")
    try:
        response_id = int(payload.get("id") or 0)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "O identificador do agendamento confirmado é inválido."
        ) from error
    if response_id != appointment_id:
        raise ValueError("A API confirmou um agendamento diferente.")
    status = str(payload.get("status") or "")
    if status not in APPOINTMENT_STATUS_LABELS:
        raise ValueError("A API confirmou um status inválido.")
    return status


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


def _parse_appointment_datetime(value: Any) -> datetime:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        timestamp = value / 1000 if abs(value) >= 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(
            BARBERSHOP_TIMEZONE
        )
    text = str(value or "").strip()
    if not text:
        raise ValueError("Horário de agendamento ausente.")
    try:
        timestamp = float(text)
    except ValueError:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=BARBERSHOP_TIMEZONE)
        return parsed.astimezone(BARBERSHOP_TIMEZONE)
    if abs(timestamp) >= 10_000_000_000:
        timestamp /= 1000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(
        BARBERSHOP_TIMEZONE
    )


def _normalize_contact_phone(value: str) -> str:
    digits = "".join(character for character in str(value or "") if "0" <= character <= "9")
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    elif len(digits) in (11, 12) and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _phone_for_api(value: Any) -> str:
    return _normalize_contact_phone(str(value or "").strip())


def _format_contact_phone(value: str) -> str:
    raw_value = str(value or "")
    digits = _normalize_contact_phone(raw_value)
    country_prefix = "+55 " if raw_value.lstrip().startswith("+55") else ""
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


def _normalize_cpf(value: str) -> str:
    return "".join(character for character in value if "0" <= character <= "9")


def _contact_phone_validation_error(value: str) -> str:
    digits = _normalize_contact_phone(value)
    if len(digits) not in (10, 11):
        return "Informe um telefone com DDD e 10 ou 11 dígitos."
    if digits[:2] not in BRAZIL_AREA_CODES:
        return "Informe um DDD válido."
    return ""


def _email_validation_error(value: str) -> str:
    email = _normalize_email(value)
    if not email:
        return ""
    if (
        len(email) > 254
        or not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", email)
    ):
        return "Informe um e-mail válido."
    return ""


def _normalize_email(value: str) -> str:
    return (
        unicodedata.normalize("NFKC", str(value or ""))
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
        .strip()
        .casefold()
    )


def _professional_items_from_response(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict):
        result = (
            result.get("items")
            or result.get("data")
            or result.get("professionals")
            or result.get("users")
        )
    if not isinstance(result, list):
        raise ValueError

    items: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        name = _first_matching_value(
            item, "name", "full_name", "fullName", "display_name", "user_name"
        )
        if not name:
            continue
        role = str(_first_matching_value(item, "role", "user_role") or "").strip().lower()
        items.append(
            {
                "id": int(_first_matching_value(item, "id", "user_id") or 0),
                "name": str(name),
                "email": str(_first_matching_value(item, "email") or ""),
                "phone": _format_contact_phone(
                    str(_first_matching_value(item, "phone", "telephone", "mobile") or "")
                ),
                "role": "Administrador" if role == "admin" else "Profissional",
                "profile_photo_url": str(
                    _first_matching_value(item, "profile_photo_url", "avatar_url") or ""
                ),
            }
        )
    return items


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


def _profile_save_error_message(response: httpx.Response) -> str:
    if response.status_code in (401, 403):
        return "Sua sessão expirou. Entre novamente para salvar as alterações."

    try:
        body = response.json()
    except ValueError:
        body = {}
    if isinstance(body, dict):
        message = " ".join(
            str(body.get(key, ""))
            for key in ("message", "error", "detail")
        ).casefold()
        if "e-mail" in message and ("associado" in message or "cadastrado" in message):
            return "Este e-mail já está cadastrado. Informe outro e-mail."

    return "Não foi possível salvar as alterações. Tente novamente."


def _log_profile_api_error(response: httpx.Response) -> None:
    try:
        body = response.json()
    except ValueError:
        body = response.text[:500]
    print(f"[perfil] API {response.status_code}: {body}")


def _configured_setting(variable_name: str) -> str:
    value = os.environ.get(variable_name, "").strip()
    if value:
        return value

    env_files = [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path.cwd() / ".env",
    ]
    seen_paths: set[Path] = set()
    for env_file in env_files:
        if env_file in seen_paths or not env_file.exists():
            continue
        seen_paths.add(env_file)
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                key, separator, configured_value = line.partition("=")
                if separator and key.strip() == variable_name:
                    return configured_value.strip().strip("\"'")
        except OSError:
            continue
    return ""


def _configured_api_url(variable_name: str) -> str:
    return _configured_setting(variable_name).rstrip("/")


def _first_matching_value(payload: Any, *keys: str) -> Any:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
            key_lower = key.lower()
            for candidate_key, candidate_value in payload.items():
                if isinstance(candidate_key, str) and candidate_key.lower() == key_lower:
                    if candidate_value not in (None, ""):
                        return candidate_value
        for nested_key in ("data", "user", "profile", "result", "session", "auth"):
            nested = payload.get(nested_key)
            value = _first_matching_value(nested, *keys)
            if value is not None:
                return value
    elif isinstance(payload, list):
        for item in payload:
            value = _first_matching_value(item, *keys)
            if value is not None:
                return value
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y", "active", "enabled"}
    return False


def _profile_requires_password_change(profile: Any) -> bool:
    if not isinstance(profile, dict):
        return False
    return _as_bool(
        _first_matching_value(
            profile,
            "must_change_password",
            "mustChangePassword",
            "force_password_change",
            "forcePasswordChange",
            "password_change_required",
            "passwordChangeRequired",
        )
    )


def _contacts_page_from_response(payload: Any) -> tuple[list[Any], int]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
        payload = payload["data"]
    if isinstance(payload, list):
        return payload, len(payload)
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        try:
            total_value = payload.get(
                "total",
                payload.get("itemsTotal", len(payload["items"])),
            )
            total = int(len(payload["items"]) if total_value is None else total_value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("O total de clientes retornado é inválido.") from error
        if total < 0:
            raise ValueError("O total de clientes retornado é inválido.")
        return payload["items"], total
    raise ValueError("A resposta de clientes não contém uma lista.")


class AuthState(rx.State):
    _auth_token: str = rx.LocalStorage("", name="pixelcode_auth_token", sync=True)

    display_name: str = ""
    profile_name: str = ""
    user_id: int = 0
    role: str = ""
    error_message: str = ""
    is_submitting: bool = False
    professional_email: str = ""
    professional_phone: str = ""
    professional_cpf: str = ""
    professionals: list[dict[str, Any]] = []
    professionals_loading: bool = False
    professionals_error: str = ""
    professional_success_message: str = ""
    professional_page: int = 1
    professional_page_size: int = 4
    profile_email: str = ""
    profile_phone: str = ""
    profile_cpf: str = ""
    profile_photo_url: str = ""
    profile_error_message: str = ""
    profile_form_success_message: str = ""
    profile_photo_success_message: str = ""
    profile_form_error: str = ""
    profile_is_submitting: bool = False
    profile_password_error: str = ""
    profile_current_password_error: str = ""
    profile_new_password_error: str = ""
    profile_confirmation_error: str = ""
    profile_password_success: str = ""
    profile_password_submitting: bool = False
    profile_editor_open: bool = False
    login_password_visible: bool = False
    temporary_password_visible: bool = False
    temporary_confirmation_visible: bool = False
    profile_current_password_visible: bool = False
    profile_new_password_visible: bool = False
    profile_confirmation_visible: bool = False
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
    contact_form_cpf: str = ""
    contact_form_birth_date: str = ""
    contact_form_email: str = ""
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
    appointments: list[dict[str, Any]] = []
    appointment_blocks: list[dict[str, Any]] = []
    appointment_professionals: list[dict[str, Any]] = []
    appointment_contacts: list[dict[str, Any]] = []
    appointment_loading: bool = False
    appointment_options_loading: bool = False
    appointment_error_message: str = ""
    appointment_success_message: str = ""
    appointment_form_error: str = ""
    appointment_form_open: bool = False
    appointment_editing_id: int = 0
    appointment_date: str = ""
    appointment_professional_id: int = 0
    appointment_form_professional_id: int = 0
    appointment_form_contact_id: int = 0
    appointment_form_service_ids: list[int] = []
    appointment_form_date: str = ""
    appointment_form_time: str = ""
    appointment_form_notes: str = ""
    appointment_form_status: str = "pending"
    appointment_form_submitting: bool = False
    appointment_view: str = "calendar"
    appointment_return_view: str = "calendar"
    appointment_calendar_month: str = ""
    appointment_search: str = ""
    appointment_status_filter: str = "Não cancelados"
    appointment_selected_detail: dict[str, Any] = {
        "id": 0,
        "contact_name": "",
        "contact_phone": "",
        "date_display": "",
        "time_display": "",
        "service_details": [],
        "total_display": "",
        "professional_name": "",
        "status": "",
        "status_display": "",
        "notes": "",
    }
    appointment_selected_detail_services: list[dict[str, str]] = []
    appointment_cancel_confirm_id: int = 0
    appointment_success_details: dict[str, Any] = {
        "contact_name": "",
        "contact_phone": "",
        "date_display": "",
        "time_display": "",
        "service_summary": "",
        "total_display": "",
        "professional_name": "",
    }
    appointment_quick_contact_open: bool = False
    appointment_quick_contact_name: str = ""
    appointment_quick_contact_phone: str = ""
    appointment_quick_contact_cpf: str = ""
    appointment_quick_contact_birth_date: str = ""
    appointment_quick_contact_email: str = ""
    appointment_quick_contact_source: str = "WhatsApp"
    appointment_quick_contact_first_contact_at: str = ""
    appointment_quick_contact_notes: str = ""
    appointment_quick_contact_error: str = ""
    appointment_quick_contact_submitting: bool = False
    appointment_block_form_open: bool = False
    appointment_block_professional_id: int = 0
    appointment_block_start_time: str = ""
    appointment_block_end_time: str = ""
    appointment_block_reason: str = ""
    appointment_block_error: str = ""
    appointment_block_submitting: bool = False
    finance_kpis: list[dict[str, Any]] = []
    finance_dashboard_loaded: bool = False
    finance_kpis_loading: bool = True
    finance_kpis_error: str = ""
    finance_cashflow: dict[str, list[dict[str, Any]]] = {}
    finance_period: str = "6m"
    finance_chart_points: list[dict[str, Any]] = []
    finance_chart_y_ticks: list[dict[str, Any]] = []
    finance_chart_inflow_path: str = ""
    finance_chart_outflow_path: str = ""
    finance_chart_inflow_area: str = ""
    finance_chart_outflow_area: str = ""
    finance_chart_loading: bool = True
    finance_chart_error: str = ""
    finance_chart_active_index: int = -1
    finance_summary: dict[str, Any] = {}
    finance_summary_empty: bool = True
    finance_summary_loading: bool = True
    finance_summary_error: str = ""
    finance_transactions: list[dict[str, Any]] = []
    finance_transactions_loading: bool = True
    finance_transactions_error: str = ""
    finance_transactions_total: int = 0
    finance_transactions_page: int = 1
    finance_transactions_page_size: int = 3
    finance_has_cancelled_transactions: bool = False
    finance_show_cancelled_transactions: bool = False
    finance_api_available: bool = False
    finance_mock_mode: bool = False
    finance_contacts: list[dict[str, Any]] = []
    finance_services: list[dict[str, Any]] = []
    finance_appointment_options: list[dict[str, Any]] = []
    finance_appointment_options_loading: bool = False
    finance_form_options_loading: bool = False
    finance_form_options_loaded: bool = False
    finance_form_options_error: str = ""
    finance_form_open: bool = False
    finance_form_type: str = "income"
    finance_form_mode: str = "create"
    finance_form_transaction_id: int = 0
    finance_form_title: str = ""
    finance_form_detail: str = ""
    finance_form_amount: str = ""
    finance_form_occurred_at: str = ""
    finance_form_contact_id: int = 0
    finance_form_contact_option: str = "Selecione um cliente..."
    finance_form_service_option: str = "Selecione um serviço..."
    finance_form_service_ids: list[int] = []
    finance_form_appointment_id: int = 0
    finance_form_appointment_option: str = "Sem vínculo de agendamento"
    finance_form_confirming: bool = False
    finance_form_error: str = ""
    finance_form_success_message: str = ""
    finance_form_submitting: bool = False
    finance_cancel_transaction_id: int = 0
    finance_cancel_reason: str = ""
    finance_cancel_error: str = ""
    finance_cancel_submitting: bool = False
    overview_period: str = "30d"
    overview_period_error: str = ""
    overview_finance_transactions: list[dict[str, Any]] = []
    overview_financial_metrics: list[dict[str, Any]] = []
    overview_financial_loading: bool = True
    overview_financial_error: str = ""
    overview_transactions_loading: bool = True
    overview_transactions_error: str = ""
    overview_client_metric: dict[str, Any] = {}
    overview_clients_loading: bool = True
    overview_clients_error: str = ""
    overview_client_total: int = 0
    overview_client_active_count: int = 0
    overview_client_active_percentage: int = 0
    overview_client_total_variation: str = "Sem comparação"
    overview_client_total_trend: str = "neutral"
    overview_first_contact_dates: list[str] = []
    overview_appointments: list[dict[str, Any]] = []
    overview_appointments_loading: bool = True
    overview_appointments_error: str = ""
    overview_recent_transactions: list[dict[str, Any]] = []

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        error_context: str = "serviço de acesso",
        query_params: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response | None:
        endpoint_path = path.lstrip("/")
        api_group_variable = (
            "XANO_APPOINTMENTS_API_URL"
            if endpoint_path == "appointments" or endpoint_path.startswith("appointments/")
            else "XANO_FINANCE_API_URL"
            if endpoint_path == "finance" or endpoint_path.startswith("finance/")
            else "XANO_SERVICES_API_URL"
            if endpoint_path == "services" or endpoint_path.startswith("services/")
            else "XANO_CONTACTS_API_URL"
            if endpoint_path == "contacts" or endpoint_path.startswith("contacts/")
            else "XANO_API_URL"
        )
        base_url = _configured_api_url(api_group_variable)
        if (
            not base_url
            and api_group_variable not in ("XANO_API_URL", "XANO_FINANCE_API_URL")
        ):
            base_url = _configured_api_url("XANO_API_URL")
        if not base_url:
            self.error_message = (
                "Configure XANO_FINANCE_API_URL com a URL base do grupo Finance "
                "para conectar ao Xano."
                if api_group_variable == "XANO_FINANCE_API_URL"
                else f"Configure {api_group_variable} ou XANO_API_URL para conectar ao Xano."
                if api_group_variable != "XANO_API_URL"
                else "Configure XANO_API_URL para conectar ao Xano."
            )
            return None

        headers = {}
        if self._auth_token:
            headers["Authorization"] = "Bearer " + self._auth_token

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                return await client.request(
                    method,
                    f"{base_url}/{endpoint_path}",
                    json=payload if files is None else None,
                    files=files,
                    params=query_params,
                    headers=headers,
                )
        except httpx.HTTPError:
            self.error_message = f"Não foi possível conectar ao {error_context}."
            return None

    def _clear_session(self):
        self._auth_token = ""
        self.display_name = ""
        self.profile_name = ""
        self.role = ""
        self.error_message = ""
        self.is_submitting = False
        self.user_id = 0
        self.profile_email = ""
        self.profile_phone = ""
        self.profile_cpf = ""
        self.profile_photo_url = ""
        self.profile_error_message = ""
        self.profile_form_success_message = ""
        self.profile_photo_success_message = ""
        self.profile_form_error = ""
        self.profile_password_error = ""
        self.profile_current_password_error = ""
        self.profile_new_password_error = ""
        self.profile_confirmation_error = ""
        self.profile_password_success = ""
        self.profile_password_submitting = False
        self.profile_editor_open = False
        self.overview_period = "30d"
        self.overview_period_error = ""
        self.overview_finance_transactions = []
        self.overview_financial_metrics = []
        self.overview_financial_loading = False
        self.overview_financial_error = ""
        self.overview_transactions_loading = False
        self.overview_transactions_error = ""
        self.overview_client_metric = {}
        self.overview_clients_loading = False
        self.overview_clients_error = ""
        self.overview_client_total = 0
        self.overview_client_active_count = 0
        self.overview_client_active_percentage = 0
        self.overview_client_total_variation = "Sem comparação"
        self.overview_client_total_trend = "neutral"
        self.overview_first_contact_dates = []
        self.overview_appointments = []
        self.overview_appointments_loading = False
        self.overview_appointments_error = ""
        self.overview_recent_transactions = []

    @rx.event
    def clear_menu_success_messages(self):
        self.service_success_message = ""
        self.contact_success_message = ""
        self.appointment_success_message = ""
        self.profile_form_success_message = ""
        self.profile_photo_success_message = ""
        self.professional_success_message = ""
        self.profile_editor_open = False

    async def _load_identity(self) -> dict | None:
        response = await self._request("GET", "auth/me")
        if response is None or response.status_code != 200:
            return None

        try:
            profile = response.json()
        except ValueError:
            return None

        if not isinstance(profile, dict):
            return None
        profile = profile.get("user") if isinstance(profile.get("user"), dict) else profile
        profile = profile.get("data") if isinstance(profile.get("data"), dict) else profile
        if not isinstance(profile, dict):
            return None
        self.display_name = str(_first_matching_value(profile, "name", "display_name") or "")
        self.profile_name = self.display_name
        self.user_id = int(_first_matching_value(profile, "id", "user_id") or 0)
        self.role = str(_first_matching_value(profile, "role") or "").strip().lower()
        self.profile_email = str(_first_matching_value(profile, "email") or "")
        self.profile_phone = _format_contact_phone(
            str(_first_matching_value(profile, "phone") or "")
        )
        self.profile_cpf = _format_cpf(str(_first_matching_value(profile, "cpf") or ""))
        self.profile_photo_url = str(
            _first_matching_value(profile, "profile_photo_url", "avatar_url") or ""
        )
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
        if not isinstance(result, dict):
            self.error_message = "Resposta do login inválida. Verifique o backend e a conta informada."
            self.is_submitting = False
            return

        token = _first_matching_value(
            result,
            "authToken",
            "auth_token",
            "token",
            "access_token",
            "accessToken",
            "jwt",
        )
        user_payload = result.get("user") if isinstance(result.get("user"), dict) else {}
        profile_payload = result.get("profile") if isinstance(result.get("profile"), dict) else {}
        data_payload = result.get("data") if isinstance(result.get("data"), dict) else {}
        login_profile = user_payload or profile_payload or data_payload or result

        self._auth_token = str(token) if token not in (None, "") else ""
        self.display_name = str(_first_matching_value(login_profile, "name", "display_name") or "")
        self.role = str(_first_matching_value(login_profile, "role") or "").strip().lower()
        self.is_submitting = False

        if not self._auth_token:
            self.error_message = "Resposta do login inválida. Verifique o backend e a conta informada."
            return

        if _profile_requires_password_change(login_profile):
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
            self._clear_session()
            return rx.redirect("/login")
        if _profile_requires_password_change(profile):
            return rx.redirect("/change-password")

    @rx.event
    async def require_overview_access(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            yield rx.redirect("/login")
            return
        if _profile_requires_password_change(profile):
            yield rx.redirect("/change-password")
            return

        self.overview_financial_loading = True
        self.overview_financial_error = ""
        self.overview_transactions_loading = True
        self.overview_transactions_error = ""
        self.overview_clients_loading = True
        self.overview_clients_error = ""
        self.overview_appointments_loading = True
        self.overview_appointments_error = ""
        self.overview_period_error = ""
        self.overview_recent_transactions = []
        self.overview_finance_transactions = []
        self.finance_kpis_loading = True
        self.finance_chart_loading = True
        self.finance_summary_loading = True
        self.finance_transactions_loading = True
        yield
        await asyncio.gather(
            self._load_finance_dashboard(load_transaction_page=False),
            self._load_overview_contacts(),
            self._load_overview_appointments(),
        )
        self.overview_financial_loading = False
        self.overview_transactions_loading = False
        self.overview_transactions_error = self.overview_financial_error
        if not self.overview_transactions_error:
            self.overview_recent_transactions = self.overview_finance_transactions[:3]
        self._refresh_overview_metrics()

    async def _load_overview_contacts(self):
        self.overview_clients_loading = True
        self.overview_clients_error = ""
        contacts: list[dict[str, Any]] = []
        page_size = 50

        async def fetch_page(
            page: int,
        ) -> tuple[tuple[list[Any], int] | None, str]:
            response = await self._request(
                "GET",
                "contacts",
                error_context="clientes da visão geral",
                query_params={"page": page, "page_size": page_size},
            )
            if response is None:
                return None, "Não foi possível carregar os dados de clientes."
            if response.status_code != 200:
                return None, _api_error_message(
                    response, "Não foi possível carregar os dados de clientes."
                )
            try:
                return _contacts_page_from_response(response.json()), ""
            except (TypeError, ValueError, OverflowError) as error:
                print(f"[overview] Invalid contacts page {page}: {error}")
                return (
                    None,
                    "Os dados de clientes estão temporariamente indisponíveis.",
                )

        def append_contacts(items: list[Any]):
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("Um cliente retornado possui formato inválido.")
                first_contact_at = _contact_date_iso_value(
                    item.get("first_contact_at")
                )
                if not first_contact_at:
                    raise ValueError(
                        "A data do primeiro contato de um cliente é inválida."
                    )
                contacts.append(
                    {
                        "id": int(item["id"]),
                        "status": str(item.get("status", "")),
                        "first_contact_at": first_contact_at,
                    }
                )

        first_page, page_error = await fetch_page(1)
        if first_page is None:
            self.overview_clients_error = page_error
            self.overview_clients_loading = False
            return
        first_items, reported_total = first_page
        try:
            append_contacts(first_items)
            if len(contacts) > reported_total:
                raise ValueError("A paginação excedeu o total de clientes.")
            if not first_items and reported_total:
                raise ValueError("A paginação de clientes terminou antes do total.")
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            print(f"[overview] Invalid contacts response: {error}")
            self.overview_clients_error = (
                "Os dados de clientes estão temporariamente indisponíveis."
            )
            self.overview_clients_loading = False
            return

        page_count = (reported_total + page_size - 1) // page_size
        for batch_start in range(2, page_count + 1, 4):
            pages = range(batch_start, min(batch_start + 4, page_count + 1))
            results = await asyncio.gather(
                *(fetch_page(page) for page in pages)
            )
            for page, (page_result, page_error) in zip(pages, results):
                if page_result is None:
                    self.overview_clients_error = page_error
                    self.overview_clients_loading = False
                    return
                page_items, page_total = page_result
                try:
                    if page_total != reported_total:
                        raise ValueError(
                            "O total de clientes mudou durante a consulta."
                        )
                    if not page_items and len(contacts) < reported_total:
                        raise ValueError(
                            "A paginação de clientes terminou antes do total."
                        )
                    append_contacts(page_items)
                    if len(contacts) > reported_total:
                        raise ValueError("A paginação excedeu o total de clientes.")
                except (KeyError, TypeError, ValueError, OverflowError) as error:
                    print(f"[overview] Invalid contacts page {page}: {error}")
                    self.overview_clients_error = (
                        "Os dados de clientes estão temporariamente indisponíveis."
                    )
                    self.overview_clients_loading = False
                    return

        if len(contacts) != reported_total:
            print("[overview] Contacts pagination did not match the reported total.")
            self.overview_clients_error = (
                "Os dados de clientes estão temporariamente indisponíveis."
            )
            self.overview_clients_loading = False
            return

        try:
            summary = summarize_contacts(contacts, reported_total)
        except ValueError as error:
            print(f"[overview] Invalid contacts summary: {error}")
            self.overview_clients_error = (
                "Os dados de clientes estão temporariamente indisponíveis."
            )
            self.overview_clients_loading = False
            return

        self.overview_client_total = summary["total"]
        self.overview_client_active_count = summary["active_count"]
        self.overview_client_active_percentage = summary["active_percentage"]
        self.overview_client_total_variation = summary["variation"]
        self.overview_client_total_trend = summary["trend"]
        self.overview_first_contact_dates = summary["first_contact_dates"]
        self.overview_clients_loading = False


    async def _load_overview_appointments(self):
        self.overview_appointments_loading = True
        self.overview_appointments_error = ""
        now = datetime.now(BARBERSHOP_TIMEZONE)
        day_start = datetime.combine(
            now.date(),
            time.min,
            tzinfo=BARBERSHOP_TIMEZONE,
        )
        day_end = day_start + timedelta(days=30)
        query_params: dict[str, Any] = {
            "day_start": int(day_start.timestamp() * 1000),
            "day_end": int(day_end.timestamp() * 1000),
        }
        if self.role != "admin":
            query_params["professional_id"] = self.user_id

        response = await self._request(
            "GET",
            "appointments",
            error_context="agenda da visão geral",
            query_params=query_params,
        )
        if response is None:
            self.overview_appointments_error = (
                "Não foi possível carregar os próximos atendimentos."
            )
            self.overview_appointments_loading = False
            return
        if response.status_code != 200:
            self.overview_appointments_error = _api_error_message(
                response,
                "Não foi possível carregar os próximos atendimentos.",
            )
            self.overview_appointments_loading = False
            return
        try:
            result = response.json()
            if isinstance(result, dict) and isinstance(result.get("data"), list):
                result = result["data"]
            self.overview_appointments = upcoming_appointments(
                result,
                now,
                _parse_appointment_datetime,
            )
        except (KeyError, TypeError, ValueError) as error:
            print(f"[overview] Invalid appointments response: {error}")
            self.overview_appointments_error = (
                "Os próximos atendimentos estão temporariamente indisponíveis."
            )
        self.overview_appointments_loading = False

    def _refresh_overview_metrics(self):
        try:
            metrics = overview_metrics(
                self.overview_finance_transactions,
                self.overview_first_contact_dates,
                self.overview_period,
            )
        except FinanceDataError as error:
            print(f"[overview] Invalid finance transactions: {error}")
            self.overview_financial_error = (
                "Os indicadores financeiros estão temporariamente indisponíveis."
            )
            self.overview_transactions_error = self.overview_financial_error
            self.overview_financial_metrics = []
            self.overview_recent_transactions = []
            client_metrics = overview_metrics(
                [],
                self.overview_first_contact_dates,
                self.overview_period,
            )
            self.overview_client_metric = client_metrics["clients"]
            return
        self.overview_financial_metrics = metrics["financial"]
        self.overview_client_metric = metrics["clients"]

    @rx.event
    def set_overview_period(self, period: str):
        if period not in OVERVIEW_PERIODS:
            self.overview_period_error = "Selecione um período válido."
            return
        self.overview_period = period
        self.overview_period_error = ""
        self._refresh_overview_metrics()

    @rx.event
    async def require_finance_access(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            yield rx.redirect("/login")
            return
        if _profile_requires_password_change(profile):
            yield rx.redirect("/change-password")
            return
        if self.role not in ("admin", "professional"):
            yield rx.redirect("/app")
            return

        if not self.finance_dashboard_loaded:
            self.finance_kpis_loading = True
            self.finance_chart_loading = True
            self.finance_summary_loading = True
            self.finance_transactions_loading = True
        self.finance_kpis_error = ""
        self.finance_chart_error = ""
        self.finance_summary_error = ""
        self.finance_transactions_error = ""
        self.finance_form_error = ""
        self.finance_form_success_message = ""
        yield
        await self._load_finance_dashboard()

    async def _load_finance_dashboard(self, load_transaction_page: bool = True):
        if not self.finance_dashboard_loaded:
            self.finance_kpis_loading = True
            self.finance_chart_loading = True
            self.finance_summary_loading = True
            self.finance_transactions_loading = True
        self.finance_kpis_error = ""
        self.finance_chart_error = ""
        self.finance_summary_error = ""
        self.finance_transactions_error = ""

        api_configured = bool(_configured_api_url("XANO_FINANCE_API_URL"))
        mock_enabled = should_use_finance_mock(
            _configured_setting("FINANCE_MOCK_ENABLED"),
            is_prod_mode(),
            api_configured,
        )
        self.finance_api_available = api_configured
        self.finance_mock_mode = mock_enabled
        if not api_configured:
            self.finance_form_open = False
        if mock_enabled:
            payload = mock_finance_dashboard()
        else:
            response = await self._request(
                "GET",
                "finance/dashboard",
                error_context="serviço financeiro",
            )
            if response is None:
                self._set_finance_error(
                    "Não foi possível carregar os dados financeiros. Tente novamente."
                )
                return
            if response.status_code != 200:
                self._set_finance_error(
                    "Não foi possível carregar os dados financeiros. Tente novamente."
                )
                return
            try:
                payload = response.json()
            except ValueError:
                self._set_finance_error(
                    "Os dados financeiros estão temporariamente indisponíveis."
                )
                return
            if isinstance(payload, dict):
                if isinstance(payload.get("data"), dict):
                    payload = payload["data"]

        try:
            dashboard = (
                normalize_finance_dashboard(payload)
                if mock_enabled
                else finance_dashboard_from_transactions(payload)
            )
        except FinanceDataError as error:
            print(f"[finance] Invalid dashboard response: {error}")
            self._set_finance_error(
                "Os dados financeiros estão temporariamente indisponíveis."
            )
            return

        self.finance_kpis = dashboard["kpis"]
        self.finance_cashflow = dashboard["cashflow"]
        self.finance_summary = dashboard["summary"]
        self.finance_summary_empty = not bool(dashboard["summary"])
        self.finance_transactions = dashboard["transactions"]
        self.overview_finance_transactions = dashboard["transactions"]
        self._apply_finance_transaction_permissions(self.finance_transactions)
        self.finance_dashboard_loaded = True
        self.finance_transactions_total = len(dashboard["transactions"])
        self.finance_has_cancelled_transactions = any(
            transaction.get("is_cancelled", False)
            for transaction in dashboard["transactions"]
        )
        self.finance_period = "6m"
        self.finance_chart_active_index = -1
        self._refresh_finance_chart()
        errors = dashboard.get("errors", {})
        self.finance_kpis_error = errors.get("kpis", "")
        self.finance_chart_error = errors.get("cashflow", "")
        self.finance_summary_error = errors.get("summary", "")
        self.finance_transactions_error = errors.get("transactions", "")
        self.overview_financial_error = errors.get("transactions", "")
        self.finance_kpis_loading = False
        self.finance_chart_loading = False
        self.finance_summary_loading = False
        self.finance_transactions_loading = False
        if not mock_enabled and load_transaction_page:
            await self._load_finance_transactions()

    async def _load_finance_transactions(self):
        self.finance_transactions_loading = True
        self.finance_transactions_error = ""
        response = await self._request(
            "GET",
            "finance/transactions",
            error_context="serviço financeiro",
            query_params={
                "page": self.finance_transactions_page,
                "include_cancelled": self.finance_show_cancelled_transactions,
            },
        )
        if response is None:
            self.finance_transactions_error = self.error_message
            self.finance_transactions_loading = False
            return
        if response.status_code != 200:
            self.finance_transactions_error = _api_error_message(
                response,
                "Não foi possível carregar as movimentações. Tente novamente.",
            )
            self.finance_transactions_loading = False
            return

        try:
            result = response.json()
            if isinstance(result, dict) and isinstance(result.get("data"), dict):
                result = result["data"]
            if not isinstance(result, dict) or not isinstance(result.get("items"), list):
                raise ValueError("A resposta paginada de movimentações é inválida.")
            total = int(result.get("total", -1))
            page = int(result.get("page", self.finance_transactions_page))
            page_size = int(result.get("page_size", self.finance_transactions_page_size))
            has_cancelled = result.get("has_cancelled", False)
            if total < 0 or page < 1 or page_size != self.finance_transactions_page_size:
                raise ValueError("Os metadados de paginação são inválidos.")
            if not isinstance(has_cancelled, bool):
                raise ValueError("O indicador de estornos é inválido.")
            page_dashboard = finance_dashboard_from_transactions(
                {"transactions": result["items"]}
            )
            transactions = page_dashboard["transactions"]
            if len(transactions) > self.finance_transactions_page_size:
                raise ValueError("A API excedeu o tamanho de página solicitado.")
            for transaction in transactions:
                self._apply_finance_transaction_permissions([transaction])
        except (FinanceDataError, KeyError, TypeError, ValueError) as error:
            print(f"[finance] Invalid paginated response: {error}")
            self.finance_transactions_error = (
                "As movimentações estão temporariamente indisponíveis."
            )
            self.finance_transactions_loading = False
            return

        page_count = max(1, ceil(total / self.finance_transactions_page_size))
        if self.finance_transactions_page > page_count:
            self.finance_transactions_page = page_count
            self.finance_transactions_loading = False
            await self._load_finance_transactions()
            return
        self.finance_transactions = transactions
        self.finance_transactions_total = total
        self.finance_transactions_page = page
        self.finance_has_cancelled_transactions = has_cancelled
        self.finance_transactions_loading = False

    def _apply_finance_transaction_permissions(
        self,
        transactions: list[dict[str, Any]],
    ):
        for transaction in transactions:
            is_active = transaction["status"] == "active"
            transaction["can_manage"] = (
                self.finance_api_available
                and is_active
                and transaction["id"] > 0
            )
            transaction["can_cancel"] = (
                transaction["can_manage"]
                and (
                    self.role == "admin"
                    or transaction["created_by"] == self.user_id
                )
            )

    async def _load_finance_form_options(self):
        self.finance_form_options_loading = True
        self.finance_form_options_error = ""
        contacts: list[dict[str, Any]] = []
        page = 1
        total_contacts = 0
        while True:
            response = await self._request(
                "GET",
                "contacts",
                error_context="clientes do financeiro",
                query_params={
                    "status": "active",
                    "page": page,
                    "page_size": 50,
                },
            )
            if response is None or response.status_code != 200:
                self.finance_form_options_error = (
                    self.error_message
                    if response is None
                    else _api_error_message(
                        response,
                        "Não foi possível carregar os clientes cadastrados.",
                    )
                )
                self.finance_form_options_loading = False
                return
            try:
                result = response.json()
                if isinstance(result, dict) and isinstance(result.get("data"), dict):
                    result = result["data"]
                if isinstance(result, list):
                    items = result
                    total_contacts = len(result)
                elif isinstance(result, dict) and isinstance(result.get("items"), list):
                    items = result["items"]
                    if page == 1:
                        total_contacts = int(result.get("total", len(items)))
                else:
                    raise ValueError("A resposta de clientes é inválida.")
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError("Um cliente retornado é inválido.")
                    contacts.append(
                        {
                            "id": int(item["id"]),
                            "name": str(item["name"]).strip(),
                            "phone": str(item.get("phone") or ""),
                        }
                    )
                if len(contacts) >= total_contacts:
                    break
                if not items:
                    raise ValueError("A paginação de clientes terminou antes do total informado.")
                page += 1
            except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                print(f"[finance] Invalid contact options: {error}")
                self.finance_form_options_error = (
                    "A lista de clientes retornada é inválida."
                )
                self.finance_form_options_loading = False
                return

        services_response = await self._request(
            "GET",
            "services",
            error_context="serviços do financeiro",
        )
        if services_response is None or services_response.status_code != 200:
            self.finance_form_options_error = (
                self.error_message
                if services_response is None
                else _api_error_message(
                    services_response,
                    "Não foi possível carregar os serviços cadastrados.",
                )
            )
            self.finance_form_options_loading = False
            return
        try:
            result = services_response.json()
            if isinstance(result, dict) and isinstance(result.get("data"), list):
                result = result["data"]
            if not isinstance(result, list):
                raise ValueError("A lista de serviços é inválida.")
            services: list[dict[str, Any]] = []
            for item in result:
                if not isinstance(item, dict):
                    raise ValueError("Um serviço retornado é inválido.")
                price = Decimal(str(item["price"]))
                service_id = int(item["id"])
                name = str(item["name"]).strip()
                if not name or not price.is_finite() or price < 0:
                    raise ValueError("Um serviço retornado possui dados inválidos.")
                services.append(
                    {
                        "id": service_id,
                        "name": name,
                        "price": str(price),
                        "price_display": _format_service_price(price),
                    }
                )
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            print(f"[finance] Invalid service options: {error}")
            self.finance_form_options_error = (
                "A lista de serviços retornada é inválida."
            )
            self.finance_form_options_loading = False
            return

        self.finance_contacts = contacts
        self.finance_services = sorted(
            services, key=lambda service: service["name"].casefold()
        )
        self.finance_form_options_loaded = True
        self.finance_form_options_loading = False

    @rx.event
    async def set_finance_form_open(self, is_open: bool):
        if is_open:
            self.finance_form_mode = "create"
            self.finance_form_transaction_id = 0
            self.finance_cancel_transaction_id = 0
            self.finance_cancel_reason = ""
            self.finance_form_type = "income"
            self.finance_form_title = ""
            self.finance_form_detail = ""
            self.finance_form_amount = ""
            self.finance_form_contact_id = 0
            self.finance_form_contact_option = "Selecione um cliente..."
            self.finance_form_service_option = "Selecione um serviço..."
            self.finance_form_service_ids = []
            self.finance_form_appointment_id = 0
            self.finance_form_appointment_option = "Sem vínculo de agendamento"
            self.finance_appointment_options = []
            self.finance_appointment_options_loading = False
            self.finance_form_confirming = False
            self.finance_form_occurred_at = datetime.now(
                BARBERSHOP_TIMEZONE
            ).strftime("%Y-%m-%dT%H:%M")
        else:
            self.finance_form_mode = "create"
            self.finance_form_transaction_id = 0
            self.finance_form_title = ""
            self.finance_form_detail = ""
            self.finance_form_amount = ""
            self.finance_form_occurred_at = ""
            self.finance_form_contact_id = 0
            self.finance_form_contact_option = "Selecione um cliente..."
            self.finance_form_service_option = "Selecione um serviço..."
            self.finance_form_service_ids = []
            self.finance_form_appointment_id = 0
            self.finance_form_appointment_option = "Sem vínculo de agendamento"
            self.finance_appointment_options = []
            self.finance_appointment_options_loading = False
            self.finance_form_confirming = False
        self.finance_form_open = is_open
        self.finance_form_error = ""
        if is_open and self.finance_api_available and not self.finance_form_options_loaded:
            yield
            await self._load_finance_form_options()

    @rx.event
    def edit_finance_transaction(
        self,
        transaction_id: int,
        transaction_type: str,
        title: str,
        detail: str,
        amount: float,
        occurred_at: str,
    ):
        if not self.finance_api_available or transaction_id <= 0:
            return
        self.finance_form_mode = "edit"
        self.finance_form_transaction_id = transaction_id
        self.finance_form_type = transaction_type
        self.finance_form_title = title
        self.finance_form_detail = detail
        self.finance_form_amount = f"{amount:.2f}"
        self.finance_form_occurred_at = occurred_at
        self.finance_form_confirming = False
        self.finance_cancel_transaction_id = 0
        self.finance_cancel_reason = ""
        self.finance_form_error = ""
        self.finance_form_success_message = ""
        self.finance_form_open = True

    @rx.event
    def set_finance_form_type(self, transaction_type: str):
        if transaction_type in {"income", "expense"}:
            self.finance_form_type = transaction_type
            self.finance_form_error = ""
            self.finance_form_confirming = False
            if transaction_type == "expense":
                self.finance_form_contact_id = 0
                self.finance_form_contact_option = "Selecione um cliente..."
                self.finance_form_service_ids = []
                self.finance_form_appointment_id = 0
                self.finance_form_appointment_option = "Sem vínculo de agendamento"
                self.finance_appointment_options = []
                self.finance_appointment_options_loading = False

    @rx.event
    async def set_finance_form_contact(self, value: str):
        if value == "Selecione um cliente...":
            self.finance_form_contact_id = 0
            self.finance_form_contact_option = value
            self.finance_form_appointment_id = 0
            self.finance_form_appointment_option = "Sem vínculo de agendamento"
            self.finance_appointment_options = []
            self.finance_appointment_options_loading = False
            self.finance_form_options_error = ""
            return
        try:
            contact_id = int(value.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            self.finance_form_error = "Selecione um cliente cadastrado."
            return
        if not any(contact["id"] == contact_id for contact in self.finance_contacts):
            self.finance_form_error = "O cliente selecionado não está mais disponível."
            return

        was_linked_to_appointment = self.finance_form_appointment_id > 0
        self.finance_form_contact_id = contact_id
        self.finance_form_contact_option = value
        self.finance_form_appointment_id = 0
        self.finance_form_appointment_option = "Sem vínculo de agendamento"
        self.finance_form_options_error = ""
        self.finance_appointment_options = []
        self.finance_appointment_options_loading = True
        if was_linked_to_appointment:
            self.finance_form_amount = ""
        self.finance_form_error = ""
        yield
        response = await self._request(
            "GET",
            "finance/appointment-options",
            error_context="agendamentos do cliente",
            query_params={"contact_id": contact_id},
        )
        if response is None or response.status_code != 200:
            if self.finance_form_contact_id != contact_id:
                return
            self.finance_form_options_error = (
                self.error_message
                if response is None
                else _api_error_message(
                    response,
                    "Não foi possível carregar os agendamentos deste cliente.",
                )
            )
            self.finance_appointment_options_loading = False
            return
        try:
            appointments = response.json()
            if isinstance(appointments, dict) and isinstance(appointments.get("data"), list):
                appointments = appointments["data"]
            if not isinstance(appointments, list):
                raise ValueError("A lista de agendamentos é inválida.")
            options = []
            for item in appointments:
                if not isinstance(item, dict):
                    raise ValueError("Um agendamento retornado é inválido.")
                status = str(item["status"])
                if status not in {"pending", "confirmed"}:
                    raise ValueError("O status do agendamento é inválido.")
                start_at = _parse_appointment_datetime(item["start_at"])
                services_snapshot = item.get("services_snapshot", [])
                if not isinstance(services_snapshot, list) or not all(
                    isinstance(service, dict) for service in services_snapshot
                ):
                    raise ValueError("Os serviços do agendamento são inválidos.")
                appointment_services = [
                    {
                        "id": int(service["id"]),
                        "name": str(service["name"]),
                        "price": str(Decimal(str(service["price"]))),
                        "price_display": _format_service_price(
                            Decimal(str(service["price"]))
                        ),
                    }
                    for service in services_snapshot
                ]
                appointment_total = Decimal(str(item["total_price"]))
                if not appointment_total.is_finite() or appointment_total < 0:
                    raise ValueError("O total do agendamento é inválido.")
                options.append(
                    {
                        "id": int(item["id"]),
                        "label": (
                            f"{start_at:%d/%m/%Y %H:%M} · "
                            f"{APPOINTMENT_STATUS_LABELS[status]} · #{int(item['id'])}"
                        ),
                        "total_price": str(appointment_total),
                        "services": appointment_services,
                    }
                )
        except (KeyError, TypeError, ValueError) as error:
            print(f"[finance] Invalid appointment options: {error}")
            if self.finance_form_contact_id != contact_id:
                return
            self.finance_form_options_error = (
                "A lista de agendamentos retornada é inválida."
            )
            self.finance_appointment_options_loading = False
            return

        if self.finance_form_contact_id != contact_id:
            return
        self.finance_appointment_options = options
        self.finance_form_options_error = ""
        self.finance_appointment_options_loading = False

    @rx.event
    def set_finance_form_appointment(self, value: str):
        if value == "Sem vínculo de agendamento":
            was_linked_to_appointment = self.finance_form_appointment_id > 0
            self.finance_form_appointment_id = 0
            self.finance_form_appointment_option = value
            if was_linked_to_appointment and not self.finance_form_service_ids:
                self.finance_form_amount = ""
            self.finance_form_error = ""
            return
        try:
            appointment_id = int(value.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            self.finance_form_error = "Selecione um agendamento válido."
            return
        if not any(
            appointment["id"] == appointment_id
            for appointment in self.finance_appointment_options
        ):
            self.finance_form_error = "O agendamento selecionado não está mais disponível."
            return
        self.finance_form_appointment_id = appointment_id
        self.finance_form_appointment_option = value
        selected_appointment = next(
            appointment
            for appointment in self.finance_appointment_options
            if appointment["id"] == appointment_id
        )
        self.finance_form_service_ids = []
        self.finance_form_amount = selected_appointment["total_price"]
        self.finance_form_confirming = False
        self.finance_form_error = ""

    @rx.event
    def set_finance_form_service_option(self, value: str):
        if self.finance_form_appointment_id:
            self.finance_form_error = (
                "Os serviços do agendamento vinculado não podem ser alterados."
            )
            return
        if value == "Selecione um serviço...":
            self.finance_form_service_option = value
            return
        try:
            service_id = int(value.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            self.finance_form_error = "Selecione um serviço cadastrado."
            return
        if service_id in self.finance_form_service_ids:
            self.finance_form_error = "Esse serviço já foi adicionado."
            return
        if not any(service["id"] == service_id for service in self.finance_services):
            self.finance_form_error = "O serviço selecionado não está mais disponível."
            return
        self.finance_form_service_ids.append(service_id)
        self._refresh_finance_form_service_total()
        self.finance_form_service_option = "Selecione um serviço..."
        self.finance_form_error = ""

    @rx.event
    def remove_finance_form_service(self, service_id: int):
        self.finance_form_service_ids = [
            selected_id
            for selected_id in self.finance_form_service_ids
            if selected_id != service_id
        ]
        self._refresh_finance_form_service_total()
        self.finance_form_error = ""

    def _refresh_finance_form_service_total(self):
        amount = sum(
            (
                Decimal(service["price"])
                for service in self.finance_services
                if service["id"] in self.finance_form_service_ids
            ),
            Decimal("0"),
        )
        self.finance_form_amount = (
            f"{amount:.2f}" if self.finance_form_service_ids else ""
        )
        self.finance_form_confirming = False

    @rx.event
    def set_finance_form_title(self, value: str):
        self.finance_form_title = value
        self.finance_form_confirming = False

    @rx.event
    def set_finance_form_detail(self, value: str):
        self.finance_form_detail = value
        self.finance_form_confirming = False

    @rx.event
    def set_finance_form_amount(self, value: str):
        self.finance_form_amount = value
        self.finance_form_confirming = False

    @rx.event
    def set_finance_form_occurred_at(self, value: str):
        self.finance_form_occurred_at = value
        self.finance_form_confirming = False

    @rx.event
    def set_finance_cancel_reason(self, value: str):
        self.finance_cancel_reason = value
        self.finance_cancel_error = ""

    @rx.event
    async def save_finance_transaction(self, form_data: dict[str, Any]):
        if self.finance_form_submitting:
            return
        if not self.finance_api_available:
            self.finance_form_error = (
                "O registro de movimentações fica disponível quando a API "
                "financeira está configurada."
            )
            return

        is_edit = self.finance_form_mode == "edit"
        transaction_type = self.finance_form_type
        title = str(form_data.get("title", self.finance_form_title)).strip()
        detail = str(form_data.get("detail", self.finance_form_detail)).strip()
        amount_value = str(form_data.get("amount", self.finance_form_amount)).strip()
        occurred_at_value = str(
            form_data.get("occurred_at", self.finance_form_occurred_at)
        ).strip()
        if transaction_type not in {"income", "expense"}:
            self.finance_form_error = "Selecione o tipo da movimentação."
            return
        if not title or len(title) > 100:
            self.finance_form_error = "Informe uma descrição com até 100 caracteres."
            return
        if len(detail) > 250:
            self.finance_form_error = "O detalhe deve ter até 250 caracteres."
            return
        try:
            amount = Decimal(amount_value.replace(",", "."))
        except (InvalidOperation, ValueError):
            self.finance_form_error = "Informe um valor válido."
            return
        if not amount.is_finite() or amount <= 0:
            self.finance_form_error = "O valor deve ser maior que zero."
            return
        try:
            if amount != amount.quantize(Decimal("0.01")):
                self.finance_form_error = (
                    "O valor deve ter no máximo duas casas decimais."
                )
                return
        except InvalidOperation:
            self.finance_form_error = "Informe um valor válido."
            return
        if not is_edit and self.finance_form_service_ids and not self.finance_form_contact_id:
            self.finance_form_error = (
                "Selecione um cliente para associar os serviços."
            )
            return
        if not is_edit and self.finance_form_appointment_id and not self.finance_form_contact_id:
            self.finance_form_error = (
                "Selecione o cliente antes de vincular um agendamento."
            )
            return
        try:
            occurred_at = datetime.fromisoformat(occurred_at_value)
        except ValueError:
            self.finance_form_error = "Informe uma data e horário válidos."
            return
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=BARBERSHOP_TIMEZONE)
        occurred_at = occurred_at.astimezone(BARBERSHOP_TIMEZONE)
        if occurred_at > datetime.now(BARBERSHOP_TIMEZONE):
            self.finance_form_error = "A data da movimentação não pode estar no futuro."
            return

        if is_edit and not self.finance_form_confirming:
            self.finance_form_confirming = True
            self.finance_form_error = ""
            return

        linked_appointment_id = (
            self.finance_form_appointment_id if not is_edit else 0
        )
        self.finance_form_submitting = True
        self.finance_form_error = ""
        self.finance_form_success_message = ""
        yield

        payload: dict[str, Any] = {
            "type": transaction_type,
            "title": title,
            "detail": detail,
            "amount": str(amount),
            "occurred_at": occurred_at.isoformat(),
        }
        if not is_edit and transaction_type == "income":
            if self.finance_form_contact_id:
                payload["contact_id"] = self.finance_form_contact_id
            if self.finance_form_service_ids:
                payload["service_ids"] = self.finance_form_service_ids
            if self.finance_form_appointment_id:
                payload["appointment_id"] = self.finance_form_appointment_id
        endpoint = (
            f"finance/transactions/{self.finance_form_transaction_id}"
            if is_edit
            else "finance/transactions"
        )
        response = await self._request(
            "PATCH" if is_edit else "POST",
            endpoint,
            payload,
            error_context="serviço financeiro",
        )
        if response is None or response.status_code not in (200, 201):
            self.finance_form_error = _api_error_message(
                response,
                (
                    "Não foi possível salvar as alterações. Tente novamente."
                    if is_edit
                    else "Não foi possível registrar a movimentação. Tente novamente."
                ),
            )
            self.finance_form_submitting = False
            return

        if not is_edit:
            try:
                result = response.json()
                if isinstance(result, dict) and isinstance(result.get("data"), dict):
                    result = result["data"]
                if not isinstance(result, dict):
                    raise ValueError("A confirmação da movimentação é inválida.")
                appointment_id = int(result.get("appointment_id") or 0)
                appointment_status = str(result.get("appointment_status") or "")
                if appointment_id:
                    if appointment_status not in APPOINTMENT_STATUS_LABELS:
                        raise ValueError("O status confirmado do agendamento é inválido.")
                    self._update_loaded_appointment_status(
                        appointment_id,
                        appointment_status,
                    )
            except (TypeError, ValueError) as error:
                print(f"[finance] Invalid payment response: {error}")
                if self.finance_form_appointment_id:
                    self.appointment_error_message = (
                        "O pagamento foi registrado, mas não foi possível confirmar "
                        "o status retornado do agendamento."
                    )

        self.finance_form_open = False
        self.finance_form_mode = "create"
        self.finance_form_transaction_id = 0
        self.finance_form_title = ""
        self.finance_form_detail = ""
        self.finance_form_amount = ""
        self.finance_form_occurred_at = ""
        self.finance_form_contact_id = 0
        self.finance_form_contact_option = "Selecione um cliente..."
        self.finance_form_service_ids = []
        self.finance_form_appointment_id = 0
        self.finance_form_appointment_option = "Sem vínculo de agendamento"
        self.finance_form_confirming = False
        self.finance_form_success_message = (
            "Movimentação atualizada com sucesso."
            if is_edit
            else "Movimentação registrada com sucesso."
        )
        self.finance_form_submitting = False
        self.finance_transactions_page = 1
        yield
        await self._load_finance_dashboard()
        if linked_appointment_id:
            await self._load_appointments()

    def _update_loaded_appointment_status(self, appointment_id: int, status: str):
        if status not in APPOINTMENT_STATUS_LABELS:
            return
        self.appointments = [
            {
                **appointment,
                "status": status,
                "status_display": APPOINTMENT_STATUS_LABELS[status],
            }
            if appointment["id"] == appointment_id
            else appointment
            for appointment in self.appointments
        ]
        if self.appointment_selected_detail.get("id") == appointment_id:
            self.appointment_selected_detail = {
                **self.appointment_selected_detail,
                "status": status,
                "status_display": APPOINTMENT_STATUS_LABELS[status],
            }

    @rx.event
    def request_finance_cancellation(self, transaction_id: int):
        if self.finance_cancel_submitting:
            return
        if transaction_id <= 0:
            return
        if self.finance_cancel_transaction_id == transaction_id:
            self.finance_cancel_transaction_id = 0
        else:
            self.finance_cancel_transaction_id = transaction_id
        self.finance_cancel_reason = ""
        self.finance_cancel_error = ""

    @rx.event
    async def cancel_finance_transaction(self, transaction_id: int):
        if self.finance_cancel_submitting:
            return
        if transaction_id <= 0 or transaction_id != self.finance_cancel_transaction_id:
            self.finance_cancel_error = "Selecione uma movimentação válida."
            return
        reason = self.finance_cancel_reason.strip()
        if not reason or len(reason) > 250:
            self.finance_cancel_error = (
                "Informe o motivo do estorno (até 250 caracteres)."
            )
            return
        linked_appointment_id = next(
            (
                int(transaction.get("appointment_id") or 0)
                for transaction in self.finance_transactions
                if transaction["id"] == transaction_id
            ),
            0,
        )
        self.finance_cancel_submitting = True
        self.finance_cancel_error = ""
        yield

        response = await self._request(
            "PATCH",
            f"finance/transactions/{transaction_id}/cancel",
            {"reason": reason},
            error_context="serviço financeiro",
        )
        if response is None or response.status_code not in (200, 204):
            self.finance_cancel_error = _api_error_message(
                response,
                "Não foi possível estornar a movimentação. Tente novamente.",
            )
            self.finance_cancel_submitting = False
            return

        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, dict) and isinstance(result.get("data"), dict):
                    result = result["data"]
                if not isinstance(result, dict):
                    raise ValueError("A confirmação do estorno é inválida.")
                appointment_id = int(result.get("appointment_id") or 0)
                appointment_status = str(result.get("appointment_status") or "")
                if appointment_id:
                    if appointment_status not in APPOINTMENT_STATUS_LABELS:
                        raise ValueError("O status restaurado do agendamento é inválido.")
                    self._update_loaded_appointment_status(
                        appointment_id,
                        appointment_status,
                    )
            except (TypeError, ValueError) as error:
                print(f"[finance] Invalid cancellation response: {error}")
                self.appointment_error_message = (
                    "O estorno foi registrado, mas não foi possível confirmar "
                    "o status retornado do agendamento."
                )

        self.finance_cancel_transaction_id = 0
        self.finance_cancel_reason = ""
        self.finance_cancel_submitting = False
        self.finance_form_success_message = (
            "Movimentação estornada. O histórico foi preservado."
        )
        await self._load_finance_dashboard()
        if linked_appointment_id:
            await self._load_appointments()

    def _set_finance_error(self, message: str):
        self.finance_kpis_error = message
        self.finance_chart_error = message
        self.finance_summary_error = message
        self.finance_transactions_error = message
        self.overview_financial_error = message
        self.finance_kpis_loading = False
        self.finance_chart_loading = False
        self.finance_summary_loading = False
        self.finance_transactions_loading = False

    def _refresh_finance_chart(self):
        chart = prepare_cashflow_chart(
            self.finance_cashflow.get(self.finance_period, []),
            self.finance_chart_active_index,
        )
        self.finance_chart_points = chart["points"]
        self.finance_chart_y_ticks = chart["y_ticks"]
        self.finance_chart_inflow_path = chart["inflow_path"]
        self.finance_chart_outflow_path = chart["outflow_path"]
        self.finance_chart_inflow_area = chart["inflow_area"]
        self.finance_chart_outflow_area = chart["outflow_area"]
        self.finance_chart_active_index = chart.get("active_index", -1)

    @rx.event
    def set_finance_period(self, period: str):
        if period not in {"6m", "12m", "year"}:
            return
        self.finance_period = period
        self.finance_chart_active_index = -1
        self._refresh_finance_chart()

    @rx.event
    def select_finance_chart_point(self, index: int):
        if 0 <= index < len(self.finance_chart_points):
            self.finance_chart_active_index = index

    @rx.event
    async def toggle_finance_cancelled_transactions(self):
        self.finance_show_cancelled_transactions = (
            not self.finance_show_cancelled_transactions
        )
        self.finance_transactions_page = 1
        if self.finance_api_available:
            await self._load_finance_transactions()

    @rx.event
    async def previous_finance_transactions_page(self):
        if self.finance_transactions_page > 1:
            self.finance_transactions_page -= 1
            if not self.finance_mock_mode:
                await self._load_finance_transactions()

    @rx.event
    async def next_finance_transactions_page(self):
        if self.finance_transactions_page < self.finance_transactions_page_count:
            self.finance_transactions_page += 1
            if not self.finance_mock_mode:
                await self._load_finance_transactions()

    @rx.var
    def finance_filtered_transactions(self) -> list[dict[str, Any]]:
        if self.finance_show_cancelled_transactions or not self.finance_mock_mode:
            return self.finance_transactions
        return [
            transaction
            for transaction in self.finance_transactions
            if not transaction.get("is_cancelled", False)
        ]

    @rx.var
    def finance_visible_transactions(self) -> list[dict[str, Any]]:
        if not self.finance_mock_mode:
            return self.finance_filtered_transactions
        start = (self.finance_transactions_page - 1) * self.finance_transactions_page_size
        return self.finance_filtered_transactions[
            start : start + self.finance_transactions_page_size
        ]

    @rx.var
    def finance_transactions_page_count(self) -> int:
        total = (
            len(self.finance_filtered_transactions)
            if self.finance_mock_mode
            else self.finance_transactions_total
        )
        return max(1, ceil(total / self.finance_transactions_page_size))

    @rx.var
    def finance_transactions_summary(self) -> str:
        total = (
            len(self.finance_filtered_transactions)
            if self.finance_mock_mode
            else self.finance_transactions_total
        )
        first = (
            (self.finance_transactions_page - 1) * self.finance_transactions_page_size + 1
            if total
            else 0
        )
        last = min(
            first + self.finance_transactions_page_size - 1,
            total,
        )
        return (
            f"Mostrando {first}–{last} de {total} registros · "
            f"Página {self.finance_transactions_page} de "
            f"{self.finance_transactions_page_count}"
        )

    @rx.var
    def finance_contact_options(self) -> list[str]:
        options = ["Selecione um cliente..."]
        options.extend(
            f"{contact['name']} · {contact['phone']} · #{contact['id']}"
            for contact in self.finance_contacts
        )
        return options

    @rx.var
    def finance_service_options(self) -> list[str]:
        options = ["Selecione um serviço..."]
        options.extend(
            f"{service['name']} · {service['price_display']} · #{service['id']}"
            for service in self.finance_services
            if service["id"] not in self.finance_form_service_ids
        )
        return options

    @rx.var
    def finance_selected_services(self) -> list[dict[str, Any]]:
        if self.finance_form_appointment_id:
            appointment = next(
                (
                    item
                    for item in self.finance_appointment_options
                    if item["id"] == self.finance_form_appointment_id
                ),
                None,
            )
            if appointment:
                return appointment["services"]
        return [
            service
            for service in self.finance_services
            if service["id"] in self.finance_form_service_ids
        ]

    @rx.var
    def finance_appointment_options_labels(self) -> list[str]:
        return [
            "Sem vínculo de agendamento",
            *[appointment["label"] for appointment in self.finance_appointment_options],
        ]

    @rx.event
    async def route_root(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            return rx.redirect("/login")
        if _profile_requires_password_change(profile):
            return rx.redirect("/change-password")
        return rx.redirect("/app")

    @rx.event
    async def require_password_change(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            return rx.redirect("/login")
        if not _profile_requires_password_change(profile):
            return rx.redirect("/app")

    @rx.event
    async def require_admin(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            return rx.redirect("/login")
        if _profile_requires_password_change(profile):
            return rx.redirect("/change-password")
        if str(profile.get("role") or "").strip().lower() != "admin":
            return rx.redirect("/app")
        await self.load_professionals()

    @rx.event
    async def load_professionals(self):
        self.professionals_loading = True
        self.professionals_error = ""
        response = await self._request(
            "GET",
            "auth/professionals",
            error_context="equipe",
        )
        if response is None or response.status_code != 200:
            self.professionals_error = (
                self.error_message
                if response is None
                else _api_error_message(
                    response,
                    "Não foi possível carregar os profissionais.",
                )
            )
            self.professionals_loading = False
            return
        try:
            self.professionals = _professional_items_from_response(response.json())
        except (TypeError, ValueError, KeyError):
            self.professionals_error = "A API retornou uma lista de profissionais inválida."
        self.professionals_loading = False
        self.professional_page = min(self.professional_page, self.professional_page_count)

    @rx.event
    async def previous_professional_page(self):
        if self.professional_page > 1:
            self.professional_page -= 1

    @rx.event
    async def next_professional_page(self):
        if self.professional_page < self.professional_page_count:
            self.professional_page += 1

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
        phone = _format_contact_phone(
            str(form_data.get("phone") or self.professional_phone).strip()
        )
        normalized_phone = _phone_for_api(phone)
        cpf = _normalize_cpf(
            str(form_data.get("cpf") or self.professional_cpf).strip()
        )
        email = _normalize_email(form_data.get("email") or self.professional_email)
        password = str(form_data.get("password") or "")
        phone_error = _contact_phone_validation_error(normalized_phone)
        email_error = _email_validation_error(email)
        if (
            len(password) < 8
            or not any(character.isalpha() for character in password)
            or not any(character.isdigit() for character in password)
        ):
            self.error_message = "A senha deve ter pelo menos 8 caracteres, uma letra e um número."
            return
        if email_error:
            self.error_message = email_error
            return
        if phone_error:
            self.error_message = phone_error
            return
        self.is_submitting = True
        self.error_message = ""
        self.professional_success_message = ""
        yield
        response = await self._request(
            "POST",
            "auth/professionals",
            {
                "name": form_data.get("name", "").strip(),
                "email": email,
                "phone": normalized_phone,
                "professional_cpf": cpf,
                "professional_password": password,
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

        self.professional_email = ""
        self.professional_phone = ""
        self.professional_cpf = ""
        await self.load_professionals()
        self.professional_success_message = "Profissional cadastrado com sucesso."
        self.is_submitting = False
        yield rx.call_script("document.getElementById('professional-form').reset()")

    @rx.event
    def set_professional_email(self, value: str):
        self.professional_email = value

    @rx.event
    def set_professional_phone(self, value: str):
        self.professional_phone = _format_contact_phone(value)

    @rx.event
    def set_professional_cpf(self, value: str):
        self.professional_cpf = _format_cpf(value)

    @rx.event
    def logout(self):
        self.clear_menu_success_messages()
        self._clear_session()
        return rx.redirect("/login")

    @rx.event
    async def require_profile_access(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            return rx.redirect("/login")
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            return rx.redirect("/login")
        if _profile_requires_password_change(profile):
            return rx.redirect("/change-password")
        if self.role not in ("admin", "professional"):
            return rx.redirect("/app")

    @rx.event
    def open_profile_editor(self):
        self.profile_name = self.display_name
        self.profile_form_error = ""
        self.profile_error_message = ""
        self.profile_form_success_message = ""
        self.profile_photo_success_message = ""
        self.profile_password_error = ""
        self.profile_password_success = ""
        self.profile_current_password_visible = False
        self.profile_new_password_visible = False
        self.profile_confirmation_visible = False
        self.profile_editor_open = True

    @rx.event
    def set_profile_editor_open(self, is_open: bool):
        self.profile_editor_open = is_open

    @rx.event
    def toggle_password_visibility(self, field: str):
        if field == "login":
            self.login_password_visible = not self.login_password_visible
        elif field == "temporary":
            self.temporary_password_visible = not self.temporary_password_visible
        elif field == "temporary_confirmation":
            self.temporary_confirmation_visible = not self.temporary_confirmation_visible
        elif field == "profile_current":
            self.profile_current_password_visible = not self.profile_current_password_visible
        elif field == "profile_new":
            self.profile_new_password_visible = not self.profile_new_password_visible
        elif field == "profile_confirmation":
            self.profile_confirmation_visible = not self.profile_confirmation_visible

    @rx.event
    def set_profile_name(self, value: str):
        self.profile_name = value
        self.profile_form_success_message = ""

    @rx.event
    def set_profile_email(self, value: str):
        self.profile_email = value
        self.profile_form_success_message = ""

    @rx.event
    def set_profile_phone(self, value: str):
        self.profile_phone = value
        self.profile_form_success_message = ""

    @rx.event
    def format_profile_phone(self):
        self.profile_phone = _format_contact_phone(self.profile_phone)
        self.profile_form_success_message = ""

    @rx.event
    async def save_profile(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.profile_is_submitting:
            return

        name = str(form_data.get("name", self.profile_name)).strip()
        self.profile_form_success_message = ""
        email = _normalize_email(form_data.get("email", self.profile_email))
        phone = _format_contact_phone(
            str(form_data.get("phone", self.profile_phone)).strip()
        )
        phone_error = _contact_phone_validation_error(phone)
        if not name:
            self.profile_form_error = "Informe seu nome."
        elif len(name) > 120:
            self.profile_form_error = "O nome deve ter no máximo 120 caracteres."
        elif _email_validation_error(email):
            self.profile_form_error = _email_validation_error(email)
        elif phone_error:
            self.profile_form_error = phone_error
        else:
            self.profile_form_error = ""
        if self.profile_form_error:
            return

        self.profile_is_submitting = True
        self.profile_form_error = ""
        yield
        response = await self._request(
            "PATCH",
            "auth/me",
            {
                "profile_name": name,
                "profile_email": email,
                "profile_phone": _normalize_contact_phone(phone),
            },
            error_context="perfil",
        )
        self.profile_is_submitting = False
        if response is None:
            self.profile_form_error = (
                "Não foi possível conectar ao serviço de perfil. Verifique sua conexão e tente novamente."
            )
            return
        if response.status_code != 200:
            _log_profile_api_error(response)
            self.profile_form_error = _profile_save_error_message(response)
            return
        try:
            result = response.json()
        except ValueError:
            self.profile_form_error = "Não foi possível salvar as alterações. Tente novamente."
            return
        if not isinstance(result, dict):
            self.profile_form_error = "Não foi possível salvar as alterações. Tente novamente."
            return
        self.display_name = str(result.get("name") or name)
        self.profile_name = self.display_name
        self.profile_email = str(result.get("email") or email)
        self.profile_phone = _format_contact_phone(str(result.get("phone") or phone))
        self.profile_form_success_message = "Seus dados foram atualizados com sucesso."

    @rx.event
    async def change_profile_password(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.profile_password_submitting:
            return

        current_password = str(form_data.get("current_password", ""))
        new_password = str(form_data.get("new_password", ""))
        confirm_password = str(form_data.get("confirm_password", ""))
        self.profile_password_error = ""
        self.profile_password_success = ""
        self.profile_current_password_error = ""
        self.profile_new_password_error = ""
        self.profile_confirmation_error = ""
        if not current_password:
            self.profile_current_password_error = "Informe sua senha atual."
            self.profile_password_error = "Informe sua senha atual."
        elif not new_password:
            self.profile_new_password_error = "Informe uma nova senha."
            self.profile_password_error = "Informe uma nova senha."
        elif not confirm_password:
            self.profile_confirmation_error = "Confirme a nova senha."
            self.profile_password_error = "Confirme a nova senha."
        elif (
            len(new_password) < 8
            or not re.search(r"[A-Za-z]", new_password)
            or not re.search(r"\d", new_password)
        ):
            self.profile_new_password_error = (
                "A nova senha deve ter ao menos 8 caracteres, uma letra e um número."
            )
            self.profile_password_error = (
                "A nova senha deve ter ao menos 8 caracteres, uma letra e um número."
            )
        elif new_password != confirm_password:
            self.profile_confirmation_error = "A confirmação da nova senha não confere."
            self.profile_password_error = "A confirmação da nova senha não confere."
        elif new_password == current_password:
            self.profile_new_password_error = "A nova senha deve ser diferente da senha atual."
            self.profile_password_error = "A nova senha deve ser diferente da senha atual."

        if self.profile_password_error:
            return

        self.profile_password_submitting = True
        yield
        response = await self._request(
            "POST",
            "auth/change-password",
            {
                "current_password": current_password,
                "new_password": new_password,
                "confirm_password": confirm_password,
            },
            error_context="perfil",
        )
        self.profile_password_submitting = False
        if response is None:
            self.profile_password_error = self.error_message or (
                "Não foi possível conectar ao serviço de autenticação. Tente novamente."
            )
            return
        if response.status_code != 200:
            _log_profile_api_error(response)
            self.profile_password_error = _api_error_message(
                response,
                "Não foi possível alterar a senha. Confira a senha atual e tente novamente.",
            )
            return
        self.profile_password_error = ""
        self.profile_current_password_error = ""
        self.profile_new_password_error = ""
        self.profile_confirmation_error = ""
        self.profile_password_success = "Senha alterada com sucesso."
        yield rx.call_script("document.getElementById('profile-password-form').reset()")

    @rx.event
    async def upload_profile_photo(self, files: list[rx.UploadFile]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        self.profile_photo_success_message = ""
        if not files:
            self.profile_error_message = "Selecione uma imagem para enviar."
            return
        if len(files) != 1:
            self.profile_error_message = "Selecione apenas uma imagem por vez."
            return

        uploaded = files[0]
        if uploaded.size is not None and uploaded.size > 5 * 1024 * 1024:
            self.profile_error_message = "A imagem deve ter no máximo 5 MB."
            return
        photo_data = await uploaded.read()
        content_type = uploaded.headers.get("content-type", "").split(";", 1)[0].lower()
        signatures = {
            "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
            "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": lambda data: (
                len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
            ),
        }
        validator = signatures.get(content_type)
        if len(photo_data) > 5 * 1024 * 1024:
            self.profile_error_message = "A imagem deve ter no máximo 5 MB."
            return
        if validator is None or not validator(photo_data):
            self.profile_error_message = "Envie uma imagem JPEG, PNG ou WebP válida."
            return

        self.profile_is_submitting = True
        self.profile_error_message = ""
        yield
        cloud_name = _configured_setting("VITE_CLOUDINARY_CLOUD_NAME")
        upload_preset = _configured_setting("VITE_CLOUDINARY_UPLOAD_PRESET")
        if not cloud_name or not upload_preset:
            self.profile_is_submitting = False
            self.profile_error_message = (
                "O armazenamento de fotos ainda não está configurado. "
                "Defina o Cloudinary e tente novamente."
            )
            return
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                cloudinary_response = await client.post(
                    f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
                    data={
                        "upload_preset": upload_preset,
                        "folder": "lotus-barber",
                    },
                    files={
                        "file": (uploaded.name, photo_data, content_type),
                    },
                )
        except httpx.HTTPError:
            cloudinary_response = None
        if cloudinary_response is None:
            self.profile_is_submitting = False
            self.profile_error_message = (
                "Não foi possível conectar ao armazenamento de fotos. Tente novamente."
            )
            return
        if cloudinary_response.status_code not in (200, 201):
            self.profile_is_submitting = False
            self.profile_error_message = _api_error_message(
                cloudinary_response,
                "Não foi possível enviar a foto ao armazenamento. Tente novamente.",
            )
            return
        try:
            cloudinary_result = cloudinary_response.json()
            secure_url = str(cloudinary_result["secure_url"])
            public_id = str(cloudinary_result["public_id"])
        except (KeyError, TypeError, ValueError):
            self.profile_is_submitting = False
            self.profile_error_message = "O armazenamento retornou uma resposta inválida."
            return
        response = await self._request(
            "POST",
            "auth/me/avatar",
            payload={"secure_url": secure_url, "public_id": public_id},
            error_context="perfil",
        )
        self.profile_is_submitting = False
        if response is None:
            self.profile_error_message = self.error_message
        elif response.status_code != 200:
            self.profile_error_message = _api_error_message(
                response,
                "Não foi possível atualizar sua foto de perfil.",
            )
        else:
            try:
                result = response.json()
            except ValueError:
                self.profile_error_message = "O servidor retornou uma resposta inválida."
                return
            photo_url = _first_matching_value(result, "profile_photo_url", "avatar_url")
            if not isinstance(photo_url, str) or not photo_url:
                self.profile_error_message = "A API não retornou a foto atualizada."
                return
            self.profile_photo_url = photo_url
            self.profile_photo_success_message = "Foto de perfil atualizada."
            yield rx.clear_selected_files("profile-photo-upload")
        yield

    @rx.event
    async def remove_profile_photo(self):
        if not self._auth_token:
            return rx.redirect("/login")
        self.profile_photo_success_message = ""
        response = await self._request(
            "DELETE",
            "auth/me/avatar",
            error_context="perfil",
        )
        if response is None:
            self.profile_error_message = self.error_message
        elif response.status_code != 200:
            self.profile_error_message = _api_error_message(
                response,
                "Não foi possível remover sua foto de perfil.",
            )
        else:
            try:
                result = response.json()
            except ValueError:
                self.profile_error_message = (
                    "O servidor não confirmou a remoção da foto. Tente novamente."
                )
                return
            photo_url = (
                _first_matching_value(result, "profile_photo_url", "avatar_url")
                if isinstance(result, dict)
                else None
            )
            if photo_url not in (None, ""):
                self.profile_error_message = (
                    "O servidor não confirmou a remoção da foto. Tente novamente."
                )
                return
            self.profile_photo_url = ""
            self.profile_error_message = ""
            self.profile_photo_success_message = "Foto de perfil removida."

    @rx.event
    async def require_appointment_access(self):
        self.clear_menu_success_messages()
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        profile = await self._load_identity()
        if profile is None:
            self._clear_session()
            yield rx.redirect("/login")
            return
        if _profile_requires_password_change(profile):
            yield rx.redirect("/change-password")
            return
        if self.role not in ("admin", "professional"):
            yield rx.redirect("/app")
            return
        if not self.appointment_date:
            self.appointment_date = date.today().isoformat()
        if not self.appointment_calendar_month:
            self.appointment_calendar_month = self.appointment_date[:7]
        self.appointment_professional_id = self.user_id if self.role == "professional" else 0
        self.appointment_options_loading = True
        yield
        await self._load_appointment_options()
        await self._load_appointments()

    @rx.var
    def appointment_professional_options(self) -> list[dict[str, Any]]:
        return [
            {
                "value": str(professional["id"]),
                "label": professional["name"],
                "disabled": False,
            }
            for professional in self.appointment_professionals
        ]

    @rx.var
    def professional_page_count(self) -> int:
        return max(1, ceil(len(self.professionals) / self.professional_page_size))

    @rx.var
    def professional_page_items(self) -> list[dict[str, Any]]:
        start = (self.professional_page - 1) * self.professional_page_size
        return self.professionals[start : start + self.professional_page_size]

    @rx.var
    def professional_results_summary(self) -> str:
        if not self.professionals:
            return "Nenhum profissional encontrado"
        start = (self.professional_page - 1) * self.professional_page_size + 1
        end = start + len(self.professional_page_items) - 1
        return f"Mostrando {start} – {end} de {len(self.professionals)} profissionais"

    @rx.var
    def appointment_form_professional_options(self) -> list[dict[str, Any]]:
        return [
            {
                "value": "0",
                "label": "Selecione um funcionário",
                "disabled": True,
            },
            *[
                {
                    "value": str(professional["id"]),
                    "label": professional["name"],
                    "disabled": False,
                }
                for professional in self.appointment_professionals
            ],
        ]

    @rx.var
    def appointment_block_professional_options(self) -> list[dict[str, Any]]:
        if self.role != "admin":
            return []
        return [
            {"value": "0", "label": "Toda a equipe", "disabled": False},
            *[
                {
                    "value": str(professional["id"]),
                    "label": professional["name"],
                    "disabled": False,
                }
                for professional in self.appointment_professionals
            ],
        ]

    @rx.var
    def appointment_block_professional_value(self) -> str:
        return str(self.appointment_block_professional_id)

    @rx.var
    def appointment_contact_options(self) -> list[dict[str, Any]]:
        return [
            {
                "value": "0",
                "label": "Selecione um cliente",
                "disabled": True,
            },
            *[
                {
                    "value": str(contact["id"]),
                    "label": f'{contact["name"]} · {contact["phone"]}',
                    "disabled": False,
                }
                for contact in self.appointment_contacts
            ],
        ]

    @rx.var
    def today_iso(self) -> str:
        return _today_in_barbershop_timezone().isoformat()

    @rx.var
    def appointment_professional_value(self) -> str:
        return str(self.appointment_professional_id)

    @rx.var
    def appointment_form_professional_value(self) -> str:
        return str(self.appointment_form_professional_id)

    @rx.var
    def appointment_contact_value(self) -> str:
        return str(self.appointment_form_contact_id)

    @rx.var
    def appointment_selected_contact_details(self) -> dict[str, str]:
        contact = next(
            (
                item
                for item in self.appointment_contacts
                if item["id"] == self.appointment_form_contact_id
            ),
            None,
        )
        if contact is None:
            return {"name": "", "phone": ""}
        return {
            "name": contact["name"],
            "phone": contact["phone"],
        }

    @rx.var
    def appointment_selected_services(self) -> list[dict[str, Any]]:
        return [
            service
            for service in self.services
            if service["id"] in self.appointment_form_service_ids
            and service["status"] == "active"
        ]

    @rx.var
    def appointment_selected_total_display(self) -> str:
        total = sum(
            (
                Decimal(str(service["price"]))
                for service in self.appointment_selected_services
            ),
            Decimal("0"),
        )
        return _format_service_price(total)

    @rx.var
    def appointment_selected_duration_display(self) -> str:
        duration = sum(
            int(service["duration_minutes"])
            for service in self.appointment_selected_services
        )
        return _format_service_duration(duration) if duration else "—"

    @rx.var
    def appointment_available_services(self) -> list[dict[str, Any]]:
        return [
            service for service in self.services if service["status"] == "active"
        ]

    @rx.var
    def appointment_month_label(self) -> str:
        try:
            selected_month = date.fromisoformat(self.appointment_calendar_month + "-01")
        except ValueError:
            selected_month = date.today().replace(day=1)
        return f"{MONTH_LABELS[selected_month.month - 1]} {selected_month.year}"

    @rx.var
    def appointment_calendar_days(self) -> list[dict[str, Any]]:
        try:
            first_day = date.fromisoformat(self.appointment_calendar_month + "-01")
        except ValueError:
            first_day = date.today().replace(day=1)
        grid_start = first_day - timedelta(days=first_day.weekday())
        marked_dates = {
            _parse_appointment_datetime(item["start_at"]).date().isoformat()
            for item in self.appointments
        }
        today = date.today().isoformat()
        return [
            {
                "date": (grid_start + timedelta(days=index)).isoformat(),
                "label": str((grid_start + timedelta(days=index)).day),
                "in_month": (grid_start + timedelta(days=index)).month == first_day.month,
                "selected": (grid_start + timedelta(days=index)).isoformat()
                == self.appointment_date,
                "has_appointments": (grid_start + timedelta(days=index)).isoformat()
                in marked_dates,
                "is_today": (grid_start + timedelta(days=index)).isoformat() == today,
            }
            for index in range(42)
        ]

    @rx.var
    def appointment_day_items(self) -> list[dict[str, Any]]:
        selected_day = self.appointment_date
        return [
            appointment
            for appointment in self.appointments
            if _parse_appointment_datetime(appointment["start_at"]).date().isoformat()
            == selected_day
            and (
                self.role != "admin"
                or not self.appointment_professional_id
                or appointment["professional_id"] == self.appointment_professional_id
            )
        ]

    @rx.var
    def appointment_day_blocks(self) -> list[dict[str, Any]]:
        return [
            block
            for block in self.appointment_blocks
            if _parse_appointment_datetime(block["start_at"]).date().isoformat()
            == self.appointment_date
        ]

    @rx.var
    def appointment_filtered_items(self) -> list[dict[str, Any]]:
        query = self.appointment_search.strip().casefold()
        return [
            appointment
            for appointment in self.appointment_day_items
            if (
                (
                    self.appointment_status_filter == "Não cancelados"
                    and appointment["status"] != "cancelled"
                )
                or appointment["status_display"] == self.appointment_status_filter
            )
            and (
                not query
                or query in appointment["contact_name"].casefold()
                or query in appointment["professional_name"].casefold()
                or query in appointment["service_summary"].casefold()
                or query in appointment["time_display"]
            )
        ]

    @rx.var
    def appointment_time_slots(self) -> list[dict[str, str]]:
        try:
            selected_date = date.fromisoformat(self.appointment_date)
        except ValueError:
            return []
        professionals = [
            professional
            for professional in self.appointment_professionals
            if not self.appointment_professional_id
            or professional["id"] == self.appointment_professional_id
        ]
        if self.role == "professional":
            professionals = [
                professional
                for professional in professionals
                if professional["id"] == self.user_id
            ]
        duration_minutes = 30
        return _calculate_appointment_time_slots(
            selected_date,
            professionals,
            duration_minutes,
            self.appointments,
            self.appointment_blocks,
        )

    @rx.var
    def appointment_form_time_options(self) -> list[dict[str, Any]]:
        if self.appointment_loading or self.appointment_error_message:
            return []
        try:
            selected_date = date.fromisoformat(self.appointment_form_date)
        except ValueError:
            return []
        professionals = [
            professional
            for professional in self.appointment_professionals
            if professional["id"] == self.appointment_form_professional_id
        ]
        duration_minutes = sum(
            int(service["duration_minutes"])
            for service in self.appointment_selected_services
        )
        available_slots = _calculate_appointment_time_slots(
            selected_date,
            professionals,
            duration_minutes,
            self.appointments,
            self.appointment_blocks,
            self.appointment_editing_id,
        )
        return [
            {
                "value": "0",
                "label": "Selecione um horário",
                "disabled": True,
            },
            *[
                {"value": slot["time"], "label": slot["time"], "disabled": False}
                for slot in available_slots
                if slot["state"] == "available"
            ],
        ]

    @rx.var
    def appointment_form_time_value(self) -> str:
        return self.appointment_form_time or "0"

    @rx.var
    def appointment_detail_value(self) -> dict[str, Any]:
        return self.appointment_selected_detail

    @rx.var
    def has_appointment_detail(self) -> bool:
        return self.appointment_selected_detail.get("id", 0) > 0

    @rx.event
    async def set_appointment_date(self, value: str):
        try:
            selected_date = date.fromisoformat(value)
        except ValueError:
            self.appointment_error_message = "Selecione uma data válida."
            return
        self.appointment_date = value
        self.appointment_calendar_month = selected_date.strftime("%Y-%m")
        await self._load_appointments()

    @rx.event
    async def change_appointment_month(self, direction: int):
        try:
            current_month = date.fromisoformat(
                self.appointment_calendar_month + "-01"
            )
        except ValueError:
            current_month = date.today().replace(day=1)
        month_index = current_month.year * 12 + current_month.month - 1 + direction
        year, month_index = divmod(month_index, 12)
        next_month = date(year, month_index + 1, 1)
        self.appointment_calendar_month = next_month.strftime("%Y-%m")
        if self.appointment_date[:7] != self.appointment_calendar_month:
            self.appointment_date = next_month.isoformat()
        await self._load_appointments()

    @rx.event
    async def set_appointment_month(self, value: str):
        try:
            selected_month = date.fromisoformat(value + "-01")
        except ValueError:
            self.appointment_error_message = "Selecione um mês válido."
            return
        self.appointment_calendar_month = selected_month.strftime("%Y-%m")
        self.appointment_date = selected_month.isoformat()
        await self._load_appointments()

    @rx.event
    async def set_appointment_professional(self, value: str):
        try:
            professional_id = int(value)
        except ValueError:
            self.appointment_error_message = "Selecione um profissional válido."
            return
        if self.role != "admin" and professional_id != self.user_id:
            self.appointment_error_message = "Você só pode consultar sua própria agenda."
            return
        self.appointment_professional_id = professional_id
        await self._load_appointments()

    @rx.event
    def set_appointment_search(self, value: str):
        self.appointment_search = value

    @rx.event
    def set_appointment_status_filter(self, value: str):
        self.appointment_status_filter = value or "Não cancelados"

    async def _load_appointment_options(self):
        self.appointment_error_message = ""
        professionals_response = await self._request(
            "GET",
            "appointments/professionals",
            error_context="equipe",
        )
        if professionals_response is None or professionals_response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if professionals_response is None
                else _api_error_message(
                    professionals_response,
                    "Não foi possível carregar a lista de profissionais.",
                )
            )
            self.appointment_options_loading = False
            return
        try:
            professionals = professionals_response.json()
            if not isinstance(professionals, list):
                raise ValueError("A lista de profissionais retornada é inválida.")
            self.appointment_professionals = [
                {"id": int(item["id"]), "name": str(item["name"]).strip()}
                for item in professionals
                if isinstance(item, dict) and item.get("name")
            ]
            if self.appointment_professionals and not self.appointment_professional_id:
                self.appointment_professional_id = self.appointment_professionals[0]["id"]
        except (KeyError, TypeError, ValueError):
            self.appointment_error_message = (
                "A API retornou uma lista de profissionais inválida."
            )
            self.appointment_options_loading = False
            return

        contacts_response = await self._request(
            "GET",
            "contacts",
            error_context="clientes",
            query_params={"status": "active", "page": 1, "page_size": 50},
        )
        if contacts_response is None or contacts_response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if contacts_response is None
                else _api_error_message(
                    contacts_response,
                    "Não foi possível carregar a lista de clientes.",
                )
            )
            self.appointment_options_loading = False
            return
        try:
            result = contacts_response.json()
            contacts = result if isinstance(result, list) else result.get("items", [])
            if not isinstance(contacts, list):
                raise ValueError("A lista de clientes retornada é inválida.")
            total_contacts = (
                len(contacts)
                if isinstance(result, list)
                else int(result.get("total", len(contacts)))
            )
            all_contacts = list(contacts)
            page = 1
            while len(all_contacts) < total_contacts:
                page += 1
                page_response = await self._request(
                    "GET",
                    "contacts",
                    error_context="clientes",
                    query_params={
                        "status": "active",
                        "page": page,
                        "page_size": 50,
                    },
                )
                if page_response is None or page_response.status_code != 200:
                    self.appointment_error_message = (
                        self.error_message
                        if page_response is None
                        else _api_error_message(
                            page_response,
                            "Não foi possível carregar todos os clientes.",
                        )
                    )
                    self.appointment_options_loading = False
                    return
                page_result = page_response.json()
                page_items = (
                    page_result
                    if isinstance(page_result, list)
                    else page_result.get("items", [])
                )
                if not isinstance(page_items, list) or not page_items:
                    raise ValueError(
                        "A API não retornou todos os clientes ativos."
                    )
                all_contacts.extend(page_items)
            self.appointment_contacts = [
                {
                    "id": int(item["id"]),
                    "name": str(item["name"]).strip(),
                    "phone": _format_contact_phone(str(item["phone"])),
                }
                for item in all_contacts
                if isinstance(item, dict) and item.get("name") and item.get("phone")
            ]
        except (AttributeError, KeyError, TypeError, ValueError):
            self.appointment_error_message = "A API retornou uma lista de clientes inválida."
            self.appointment_options_loading = False
            return

        await self._load_services()
        if self.service_error_message:
            self.appointment_error_message = self.service_error_message
        self.appointment_options_loading = False

    async def _load_appointments(self):
        if not self.appointment_date:
            self.appointment_error_message = "Selecione uma data para consultar a agenda."
            return
        self.appointment_loading = True
        self.appointment_error_message = ""
        try:
            selected_month = date.fromisoformat(
                self.appointment_calendar_month + "-01"
            )
        except ValueError:
            selected_month = date.fromisoformat(self.appointment_date).replace(day=1)
            self.appointment_calendar_month = selected_month.strftime("%Y-%m")
        next_month = (
            date(selected_month.year + 1, 1, 1)
            if selected_month.month == 12
            else date(selected_month.year, selected_month.month + 1, 1)
        )
        day_start = datetime.combine(selected_month, time.min, tzinfo=BARBERSHOP_TIMEZONE)
        day_end = datetime.combine(
            next_month,
            time.min,
            tzinfo=BARBERSHOP_TIMEZONE,
        )
        query_params: dict[str, Any] = {
            "day_start": int(day_start.timestamp() * 1000),
            "day_end": int(day_end.timestamp() * 1000),
        }
        if self.role == "admin":
            if self.appointment_professional_id:
                query_params["professional_id"] = self.appointment_professional_id
        else:
            query_params["professional_id"] = self.user_id
        response = await self._request(
            "GET",
            "appointments",
            error_context="agenda",
            query_params=query_params,
        )
        if response is None or response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if response is None
                else _api_error_message(response, "Não foi possível carregar a agenda.")
            )
            self.appointment_loading = False
            return
        try:
            result = response.json()
            if not isinstance(result, list):
                raise ValueError("A API retornou uma agenda inválida.")
            appointments = []
            for item in result:
                if not isinstance(item, dict):
                    raise ValueError("Um agendamento retornado está inválido.")
                start_at = str(item.get("start_at", ""))
                parsed_start = _parse_appointment_datetime(item.get("start_at"))
                contact = item.get("contact") if isinstance(item.get("contact"), dict) else {}
                professional = (
                    item.get("professional")
                    if isinstance(item.get("professional"), dict)
                    else {}
                )
                snapshots = item.get("services_snapshot", [])
                if not isinstance(snapshots, list):
                    raise ValueError("A lista de serviços de um agendamento está inválida.")
                contact_id = int(item["contact_id"])
                professional_id = int(item["professional_id"])
                appointments.append(
                    {
                        "id": int(item["id"]),
                        "contact_id": contact_id,
                        "contact_name": str(
                            item.get("contact_name")
                            or item.get("contact_name_snapshot")
                            or contact.get("name")
                            or next(
                                (
                                    contact_option["name"]
                                    for contact_option in self.appointment_contacts
                                    if contact_option["id"] == contact_id
                                ),
                                "Cliente",
                            )
                        ),
                        "contact_phone": _format_contact_phone(
                            str(
                                item.get("contact_phone")
                                or item.get("contact_phone_snapshot")
                                or contact.get("phone")
                                or next(
                                    (
                                        contact_option["phone"]
                                        for contact_option in self.appointment_contacts
                                        if contact_option["id"] == contact_id
                                    ),
                                    "",
                                )
                            )
                        ),
                        "professional_id": professional_id,
                        "professional_name": str(
                            item.get("professional_name")
                            or item.get("professional_name_snapshot")
                            or professional.get("name")
                            or next(
                                (
                                    professional_option["name"]
                                    for professional_option in self.appointment_professionals
                                    if professional_option["id"] == professional_id
                                ),
                                "Profissional",
                            )
                        ),
                        "start_at": start_at,
                        "date_display": parsed_start.strftime("%d/%m/%Y"),
                        "time_display": parsed_start.strftime("%H:%M"),
                        "end_at": str(item.get("end_at") or ""),
                        "status": str(item["status"]),
                        "status_display": APPOINTMENT_STATUS_LABELS[str(item["status"])],
                        "notes": str(item.get("notes") or ""),
                        "service_ids": [
                            int(service["id"])
                            for service in snapshots
                            if isinstance(service, dict) and service.get("id")
                        ],
                        "service_details": [
                            {
                                "name": str(service.get("name", "Serviço")),
                                "price_display": _format_service_price(
                                    Decimal(str(service.get("price", "0")))
                                ),
                                "duration_display": _format_service_duration(
                                    int(service.get("duration_minutes", 0))
                                ),
                            }
                            for service in snapshots
                            if isinstance(service, dict)
                        ],
                        "service_summary": ", ".join(
                            str(service.get("name", "Serviço"))
                            for service in snapshots
                            if isinstance(service, dict)
                        ),
                        "total_display": _format_service_price(
                            Decimal(str(item.get("total_price", "0")))
                        ),
                    }
                )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            self.appointment_error_message = (
                "A API retornou dados inválidos para a agenda. Contate o suporte."
            )
            self.appointment_loading = False
            return
        self.appointments = appointments
        blocks_response = await self._request(
            "GET",
            "appointments/blocks",
            error_context="bloqueios da agenda",
            query_params=query_params,
        )
        if blocks_response is None or blocks_response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if blocks_response is None
                else _api_error_message(
                    blocks_response,
                    "Não foi possível carregar os bloqueios da agenda.",
                )
            )
            self.appointment_loading = False
            return
        try:
            blocks = blocks_response.json()
            if not isinstance(blocks, list):
                raise ValueError("A API retornou uma lista de bloqueios inválida.")
            parsed_blocks = []
            for item in blocks:
                if not isinstance(item, dict):
                    raise ValueError("Um bloqueio retornado possui formato inválido.")
                raw_professional = item.get("professional_id")
                if isinstance(raw_professional, dict):
                    raw_professional = raw_professional.get("id")
                block_start = _parse_appointment_datetime(item["start_at"])
                block_end = _parse_appointment_datetime(item["end_at"])
                parsed_blocks.append(
                    {
                        "id": int(item["id"]),
                        "professional_id": int(raw_professional or 0),
                        "professional_name": str(item.get("professional_name") or ""),
                        "start_at": str(item["start_at"]),
                        "start_time_display": block_start.strftime("%H:%M"),
                        "end_at": str(item["end_at"]),
                        "end_time_display": block_end.strftime("%H:%M"),
                        "reason": str(item.get("reason") or ""),
                    }
                )
            self.appointment_blocks = parsed_blocks
        except (KeyError, TypeError, ValueError):
            self.appointment_error_message = (
                "A API retornou dados inválidos para os bloqueios da agenda."
            )
            self.appointment_loading = False
            return
        self.appointment_loading = False

    @rx.event
    async def refresh_appointments(self):
        await self._load_appointments()

    @rx.event
    def start_new_appointment(self):
        if self.appointment_options_loading:
            self.appointment_form_error = "Aguarde o carregamento das opções da agenda."
            return
        self.appointment_return_view = (
            self.appointment_view
            if self.appointment_view in ("calendar", "list")
            else "calendar"
        )
        self.appointment_editing_id = 0
        self.appointment_form_contact_id = 0
        self.appointment_form_professional_id = (
            self.user_id
            if self.role == "professional"
            else self.appointment_professional_id
        )
        self.appointment_form_service_ids = []
        self.appointment_form_date = self.appointment_date or date.today().isoformat()
        self.appointment_form_time = ""
        self.appointment_form_notes = ""
        self.appointment_form_status = "pending"
        self.appointment_form_error = ""
        self.appointment_form_open = True
        self.appointment_quick_contact_open = False
        self.appointment_view = "form"

    @rx.event
    def start_appointment_from_slot(
        self,
        slot_time: str,
        professional_id: str,
    ):
        try:
            selected_professional_id = int(professional_id)
            time.fromisoformat(slot_time)
        except ValueError:
            self.appointment_error_message = "O horário selecionado é inválido."
            return
        if not selected_professional_id:
            self.appointment_error_message = (
                "Selecione um profissional disponível para este horário."
            )
            return
        self.start_new_appointment()
        if not self.appointment_form_open:
            return
        self.appointment_form_professional_id = selected_professional_id
        self.appointment_form_date = self.appointment_date
        self.appointment_form_time = slot_time
        self.appointment_form_service_ids = []

    @rx.event
    def show_appointment_list(self):
        self.appointment_view = "list"

    @rx.event
    def show_appointment_calendar(self):
        self.appointment_view = "calendar"

    @rx.event
    def show_appointment_detail(self, appointment_id: int):
        appointment = next(
            (item for item in self.appointments if item["id"] == appointment_id),
            None,
        )
        if appointment is None:
            self.appointment_error_message = "O agendamento não está mais disponível."
            return
        self.appointment_selected_detail = appointment
        self.appointment_selected_detail_services = [
            {
                "name": str(service.get("name", "Serviço")),
                "price_display": str(service.get("price_display", "")),
                "duration_display": str(service.get("duration_display", "")),
            }
            for service in appointment["service_details"]
            if isinstance(service, dict)
        ]

    @rx.event
    def close_appointment_detail(self):
        self.appointment_selected_detail = {
            "id": 0,
            "contact_name": "",
            "contact_phone": "",
            "date_display": "",
            "time_display": "",
            "service_details": [],
            "total_display": "",
            "professional_name": "",
            "status": "",
            "status_display": "",
            "notes": "",
        }
        self.appointment_selected_detail_services = []

    @rx.event
    def request_appointment_cancel(self, appointment_id: int):
        self.appointment_cancel_confirm_id = appointment_id

    @rx.event
    def dismiss_appointment_cancel(self):
        self.appointment_cancel_confirm_id = 0

    @rx.event
    async def confirm_appointment_cancel(self):
        appointment_id = self.appointment_cancel_confirm_id
        self.appointment_cancel_confirm_id = 0
        if appointment_id:
            await self.set_appointment_status(appointment_id, "cancelled")

    @rx.event
    def start_edit_appointment(self, appointment_id: int):
        appointment = next(
            (item for item in self.appointments if item["id"] == appointment_id),
            None,
        )
        if appointment is None:
            self.appointment_error_message = "O agendamento não está mais disponível."
            return
        if appointment["status"] in ("completed", "cancelled"):
            self.appointment_error_message = (
                "Atendimentos concluídos ou cancelados não podem ser editados."
            )
            return
        try:
            start_at = _parse_appointment_datetime(appointment["start_at"])
        except (OverflowError, OSError, ValueError):
            self.appointment_error_message = "O horário do agendamento é inválido."
            return
        self.appointment_editing_id = appointment_id
        self.appointment_return_view = self.appointment_view
        self.appointment_form_contact_id = appointment["contact_id"]
        self.appointment_form_professional_id = appointment["professional_id"]
        self.appointment_form_service_ids = appointment["service_ids"]
        self.appointment_form_date = start_at.date().isoformat()
        self.appointment_form_time = start_at.strftime("%H:%M")
        self.appointment_form_notes = appointment["notes"]
        self.appointment_form_status = appointment["status"]
        self.appointment_form_error = ""
        self.appointment_form_open = True
        self.appointment_view = "form"
        self.appointment_selected_detail = {
            "id": 0,
            "contact_name": "",
            "contact_phone": "",
            "date_display": "",
            "time_display": "",
            "service_details": [],
            "total_display": "",
            "professional_name": "",
            "status": "",
            "status_display": "",
            "notes": "",
        }
        self.appointment_selected_detail_services = []

    @rx.event
    def set_appointment_contact(self, value: str):
        try:
            self.appointment_form_contact_id = int(value)
        except ValueError:
            self.appointment_form_contact_id = 0

    @rx.event
    async def set_appointment_form_professional(self, value: str):
        try:
            professional_id = int(value)
        except ValueError:
            professional_id = 0
        if self.role == "professional" and professional_id != self.user_id:
            self.appointment_form_error = "Você só pode agendar para sua própria agenda."
            return
        self.appointment_form_professional_id = professional_id
        self.appointment_form_time = ""
        if self.role == "admin":
            self.appointment_professional_id = professional_id
            await self._load_appointments()

    @rx.event
    async def set_appointment_form_date(self, value: str):
        self.appointment_form_date = value
        self.appointment_form_time = ""
        try:
            selected_date = date.fromisoformat(value)
        except ValueError:
            return
        self.appointment_date = value
        self.appointment_calendar_month = selected_date.strftime("%Y-%m")
        await self._load_appointments()

    @rx.event
    def set_appointment_form_time(self, value: str):
        self.appointment_form_time = "" if value == "0" else value

    @rx.event
    def set_appointment_form_notes(self, value: str):
        self.appointment_form_notes = value

    @rx.event
    def toggle_appointment_service(self, service_id: int):
        if service_id in self.appointment_form_service_ids:
            self.appointment_form_service_ids = [
                selected_id
                for selected_id in self.appointment_form_service_ids
                if selected_id != service_id
            ]
        else:
            self.appointment_form_service_ids = [
                *self.appointment_form_service_ids,
                service_id,
            ]
        self.appointment_form_time = ""

    @rx.event
    def cancel_appointment_form(self):
        self.appointment_form_open = False
        self.appointment_form_error = ""
        self.appointment_view = self.appointment_return_view

    @rx.event
    def open_quick_contact_form(self):
        self.appointment_quick_contact_name = ""
        self.appointment_quick_contact_phone = ""
        self.appointment_quick_contact_cpf = ""
        self.appointment_quick_contact_birth_date = ""
        self.appointment_quick_contact_email = ""
        self.appointment_quick_contact_source = "WhatsApp"
        self.appointment_quick_contact_first_contact_at = _today_in_barbershop_timezone().isoformat()
        self.appointment_quick_contact_notes = ""
        self.appointment_quick_contact_error = ""
        self.appointment_quick_contact_open = True

    @rx.event
    def close_quick_contact_form(self):
        self.appointment_quick_contact_open = False
        self.appointment_quick_contact_error = ""

    @rx.event
    def set_appointment_quick_contact_name(self, value: str):
        self.appointment_quick_contact_name = value

    @rx.event
    def set_quick_contact_phone(self, value: str):
        self.appointment_quick_contact_phone = _format_contact_phone(value)

    @rx.event
    def set_quick_contact_cpf(self, value: str):
        self.appointment_quick_contact_cpf = _format_cpf(value)

    @rx.event
    def set_quick_contact_birth_date(self, value: str):
        self.appointment_quick_contact_birth_date = value

    @rx.event
    def set_quick_contact_email(self, value: str):
        self.appointment_quick_contact_email = value

    @rx.event
    def set_quick_contact_source(self, value: str):
        self.appointment_quick_contact_source = value

    @rx.event
    def set_quick_contact_first_contact_at(self, value: str):
        self.appointment_quick_contact_first_contact_at = value

    @rx.event
    def set_quick_contact_notes(self, value: str):
        self.appointment_quick_contact_notes = value

    @rx.event
    async def save_quick_contact(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.appointment_quick_contact_submitting:
            return
        name = str(form_data.get("name") or self.appointment_quick_contact_name).strip()
        phone = _normalize_contact_phone(
            str(form_data.get("phone") or self.appointment_quick_contact_phone)
        )
        cpf = _normalize_cpf(
            str(form_data.get("cpf") or self.appointment_quick_contact_cpf)
        )
        birth_date = str(
            form_data.get("birth_date") or self.appointment_quick_contact_birth_date
        ).strip()
        email = _normalize_email(
            form_data.get("email") or self.appointment_quick_contact_email
        )
        source_label = str(
            form_data.get("source") or self.appointment_quick_contact_source
        )
        source = CONTACT_SOURCE_VALUES.get(source_label)
        first_contact_at = str(
            form_data.get(
                "first_contact_at"
            )
            or self.appointment_quick_contact_first_contact_at
        ).strip()
        notes = str(
            form_data.get("notes") or self.appointment_quick_contact_notes
        ).strip()
        self.appointment_quick_contact_error = ""
        birth_date_error = ""
        if birth_date:
            try:
                if date.fromisoformat(birth_date) > _today_in_barbershop_timezone():
                    birth_date_error = "A data de nascimento não pode estar no futuro."
            except ValueError:
                birth_date_error = "Informe uma data de nascimento válida."
        first_contact_error = ""
        if first_contact_at:
            try:
                if date.fromisoformat(first_contact_at) > _today_in_barbershop_timezone():
                    first_contact_error = (
                        "A data do primeiro contato não pode estar no futuro."
                    )
            except ValueError:
                first_contact_error = "Informe uma data de primeiro contato válida."
        if not name or len(name) > 120:
            self.appointment_quick_contact_error = "Informe um nome válido de até 120 caracteres."
        elif _contact_phone_validation_error(phone):
            self.appointment_quick_contact_error = _contact_phone_validation_error(phone)
        elif birth_date_error:
            self.appointment_quick_contact_error = birth_date_error
        elif source is None:
            self.appointment_quick_contact_error = "Selecione uma origem válida."
        elif not first_contact_at:
            self.appointment_quick_contact_error = "Informe a data do primeiro contato."
        elif first_contact_error:
            self.appointment_quick_contact_error = first_contact_error
        elif len(notes) > 1000:
            self.appointment_quick_contact_error = "As observações devem ter no máximo 1000 caracteres."
        if self.appointment_quick_contact_error:
            return

        self.appointment_quick_contact_submitting = True
        yield
        response = await self._request(
            "POST",
            "contacts",
            {
                "name": name,
                "phone": phone,
                "cpf": cpf,
                "birth_date": birth_date,
                "email": email,
                "source": source,
                "first_contact_at": first_contact_at,
                "notes": notes,
            },
            error_context="cadastro rápido de cliente",
        )
        self.appointment_quick_contact_submitting = False
        if response is None:
            self.appointment_quick_contact_error = self.error_message
            return
        if response.status_code not in (200, 201):
            self.appointment_quick_contact_error = _api_error_message(
                response,
                "Não foi possível cadastrar o cliente. Confira os dados e tente novamente.",
            )
            return
        try:
            contact = response.json()
            contact_id = int(contact["id"])
        except (KeyError, TypeError, ValueError):
            self.appointment_quick_contact_error = (
                "A API cadastrou o cliente, mas retornou dados inválidos. "
                "Atualize a lista antes de continuar."
            )
            await self._load_appointment_options()
            return
        new_contact = {
            "id": contact_id,
            "name": name,
            "phone": _format_contact_phone(phone),
        }
        self.appointment_contacts = [
            *self.appointment_contacts,
            new_contact,
        ]
        self.appointment_form_contact_id = contact_id
        self.appointment_quick_contact_open = False
        self.appointment_quick_contact_error = ""

    @rx.event
    def open_appointment_block_form(self):
        self.appointment_block_professional_id = (
            self.user_id
            if self.role == "professional"
            else self.appointment_professional_id
        )
        self.appointment_block_start_time = ""
        self.appointment_block_end_time = ""
        self.appointment_block_reason = ""
        self.appointment_block_error = ""
        self.appointment_block_form_open = True

    @rx.event
    def close_appointment_block_form(self):
        self.appointment_block_form_open = False
        self.appointment_block_error = ""

    @rx.event
    def set_appointment_block_professional(self, value: str):
        try:
            professional_id = int(value)
        except ValueError:
            self.appointment_block_error = "Selecione um profissional válido."
            return
        self.appointment_block_professional_id = professional_id

    @rx.event
    async def save_appointment_block(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.appointment_block_submitting:
            return
        try:
            block_start = datetime.combine(
                date.fromisoformat(self.appointment_date),
                time.fromisoformat(str(form_data.get("start_time", ""))),
                tzinfo=BARBERSHOP_TIMEZONE,
            )
            block_end = datetime.combine(
                date.fromisoformat(self.appointment_date),
                time.fromisoformat(str(form_data.get("end_time", ""))),
                tzinfo=BARBERSHOP_TIMEZONE,
            )
        except ValueError:
            self.appointment_block_error = "Informe um intervalo de horário válido."
            return
        professional_id = self.appointment_block_professional_id
        if self.role == "professional" and professional_id != self.user_id:
            self.appointment_block_error = "Você só pode bloquear sua própria agenda."
            return
        if professional_id < 0:
            self.appointment_block_error = "Selecione um escopo válido para o bloqueio."
            return
        if block_end <= block_start:
            self.appointment_block_error = "O fim do bloqueio deve ser posterior ao início."
            return
        reason = str(form_data.get("reason", "")).strip()
        if len(reason) > 200:
            self.appointment_block_error = (
                "O motivo do bloqueio deve ter no máximo 200 caracteres."
            )
            return
        self.appointment_block_submitting = True
        self.appointment_block_error = ""
        yield
        response = await self._request(
            "POST",
            "appointments/blocks",
            {
                "professional_id": professional_id,
                "start_at": block_start.isoformat(),
                "end_at": block_end.isoformat(),
                "reason": reason,
            },
            error_context="bloqueios da agenda",
        )
        self.appointment_block_submitting = False
        if response is None:
            self.appointment_block_error = self.error_message
            return
        if response.status_code not in (200, 201):
            self.appointment_block_error = _api_error_message(
                response,
                "Não foi possível bloquear esse intervalo.",
            )
            return
        self.appointment_block_form_open = False
        await self._load_appointments()

    @rx.event
    async def remove_appointment_block(self, block_id: int):
        response = await self._request(
            "DELETE",
            f"appointments/blocks/{block_id}",
            error_context="bloqueios da agenda",
        )
        if response is None or response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if response is None
                else _api_error_message(response, "Não foi possível remover o bloqueio.")
            )
            return
        await self._load_appointments()

    @rx.event
    async def save_appointment(self, form_data: dict[str, Any]):
        if not self._auth_token:
            yield rx.redirect("/login")
            return
        if self.appointment_form_submitting:
            return
        contact_id = self.appointment_form_contact_id
        professional_id = self.appointment_form_professional_id
        service_ids = self.appointment_form_service_ids
        appointment_date = self.appointment_form_date.strip()
        appointment_time = self.appointment_form_time.strip()
        notes = self.appointment_form_notes.strip()
        try:
            start_at = datetime.combine(
                date.fromisoformat(appointment_date),
                time.fromisoformat(appointment_time),
                tzinfo=BARBERSHOP_TIMEZONE,
            )
        except ValueError:
            start_at = None
        if not contact_id:
            self.appointment_form_error = "Selecione um cliente."
        elif not professional_id:
            self.appointment_form_error = "Selecione um profissional."
        elif self.role == "professional" and professional_id != self.user_id:
            self.appointment_form_error = "Você só pode agendar para sua própria agenda."
        elif not service_ids:
            self.appointment_form_error = "Selecione ao menos um serviço."
        elif start_at is None:
            self.appointment_form_error = "Informe uma data e um horário válidos."
        elif len(notes) > 1000:
            self.appointment_form_error = "As observações devem ter no máximo 1000 caracteres."
        else:
            self.appointment_form_error = ""
        if self.appointment_form_error:
            return
        selected_services = self.appointment_selected_services
        if len(selected_services) != len(service_ids):
            self.appointment_form_error = "Selecione ao menos um serviço ativo."
            return
        duration_minutes = sum(
            int(service["duration_minutes"]) for service in selected_services
        )
        service_end = start_at + timedelta(minutes=duration_minutes)
        opening_periods = BARBERSHOP_HOURS.get(start_at.weekday(), ())
        start_minutes = start_at.hour * 60 + start_at.minute
        end_minutes = service_end.hour * 60 + service_end.minute
        if (
            start_at.minute % 30 != 0
            or not any(
                start_minutes >= opening_start and end_minutes <= opening_end
                for opening_start, opening_end in opening_periods
            )
        ):
            self.appointment_form_error = (
                "O serviço não cabe no expediente ou no intervalo selecionado."
            )
            return
        if any(
            block["professional_id"] in (0, professional_id)
            and _parse_appointment_datetime(block["start_at"]) < service_end
            and _parse_appointment_datetime(block["end_at"]) > start_at
            for block in self.appointment_blocks
        ):
            self.appointment_form_error = (
                "O profissional possui um bloqueio nesse intervalo."
            )
            return
        if self.appointment_error_message or self.appointment_loading:
            self.appointment_form_error = (
                "Não foi possível verificar a disponibilidade. Tente novamente."
            )
            return
        if any(
            appointment["id"] != self.appointment_editing_id
            and appointment["professional_id"] == professional_id
            and appointment["status"] != "cancelled"
            and _parse_appointment_datetime(appointment["start_at"]) < service_end
            and _parse_appointment_datetime(appointment["end_at"]) > start_at
            for appointment in self.appointments
        ):
            self.appointment_form_error = (
                "O profissional possui um agendamento nesse intervalo."
            )
            return

        self.appointment_date = appointment_date
        self.appointment_calendar_month = appointment_date[:7]
        self.appointment_form_submitting = True
        self.appointment_form_error = ""
        yield
        is_editing = self.appointment_editing_id > 0
        selected_contact = next(
            (
                contact
                for contact in self.appointment_contacts
                if contact["id"] == contact_id
            ),
            {},
        )
        selected_professional = next(
            (
                professional
                for professional in self.appointment_professionals
                if professional["id"] == professional_id
            ),
            {},
        )
        self.appointment_success_details = {
            "contact_name": selected_contact.get("name", ""),
            "contact_phone": selected_contact.get("phone", ""),
            "date_display": start_at.strftime("%d/%m/%Y"),
            "time_display": start_at.strftime("%H:%M"),
            "service_summary": ", ".join(
                service["name"] for service in selected_services
            ),
            "total_display": _format_service_price(
                sum(
                    (Decimal(str(service["price"])) for service in selected_services),
                    Decimal("0"),
                )
            ),
            "professional_name": selected_professional.get("name", ""),
        }
        path = (
            f"appointments/{self.appointment_editing_id}"
            if is_editing
            else "appointments"
        )
        response = await self._request(
            "PATCH" if is_editing else "POST",
            path,
            {
                "contact_id": contact_id,
                "professional_id": professional_id,
                "service_ids": service_ids,
                "start_at": start_at.isoformat(),
                "notes": notes,
            },
            error_context="agenda",
        )
        self.appointment_form_submitting = False
        if response is None:
            self.appointment_form_error = self.error_message
            return
        if response.status_code not in (200, 201):
            self.appointment_form_error = _api_error_message(
                response,
                "Não foi possível salvar o agendamento. Confira os dados e tente novamente.",
            )
            return
        self.appointment_form_open = False
        self.appointment_success_message = (
            "Agendamento atualizado com sucesso."
            if is_editing
            else "Agendamento criado com sucesso."
        )
        await self._load_appointments()
        self.appointment_view = "success" if not is_editing else "list"

    @rx.event
    async def set_appointment_status(self, appointment_id: int, status: str):
        if not self._auth_token:
            return rx.redirect("/login")
        if status not in APPOINTMENT_STATUS_LABELS:
            self.appointment_error_message = "Status de agendamento inválido."
            return
        self.appointment_success_message = ""
        self.appointment_error_message = ""
        response = await self._request(
            "PATCH",
            f"appointments/{appointment_id}/status",
            {"status": status},
            error_context="agenda",
        )
        if response is None or response.status_code != 200:
            self.appointment_error_message = (
                self.error_message
                if response is None
                else _api_error_message(response, "Não foi possível atualizar o atendimento.")
            )
            return
        try:
            saved_status = _appointment_status_from_response(
                response.json(),
                appointment_id,
            )
        except (TypeError, ValueError) as error:
            print(f"[appointments] Invalid status response: {error}")
            self.appointment_selected_detail = {}
            await self._load_appointments()
            if not self.appointment_error_message:
                self.appointment_error_message = (
                    "Não foi possível confirmar o status salvo. A agenda foi atualizada."
                )
            return
        self._update_loaded_appointment_status(appointment_id, saved_status)
        if saved_status != status:
            self.appointment_success_message = ""
            self.appointment_selected_detail = {}
            await self._load_appointments()
            if not self.appointment_error_message:
                self.appointment_error_message = (
                    "O status foi alterado por outra operação. A tela foi atualizada "
                    "com o valor salvo."
                )
            return
        self.appointment_success_message = (
            "Atendimento cancelado."
            if saved_status == "cancelled"
            else "Status do atendimento atualizado."
        )
        self.appointment_selected_detail = {}
        await self._load_appointments()

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
            self._clear_session()
            yield rx.redirect("/login")
            return
        if _profile_requires_password_change(profile):
            yield rx.redirect("/change-password")
            return
        self.service_status_filter = (
            "Todos os status"
            if str(profile.get("role") or "").strip().lower() == "admin"
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
                        "cpf": _format_cpf(str(item.get("cpf") or "")),
                        "birth_date": str(item.get("birth_date") or ""),
                        "email": str(item.get("email") or ""),
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
            self._clear_session()
            yield rx.redirect("/login")
            return
        if _profile_requires_password_change(profile):
            yield rx.redirect("/change-password")
            return
        role = str(profile.get("role") or "").strip().lower()
        if role not in ("admin", "professional"):
            yield rx.redirect("/app")
            return
        self.contact_status_filter = "Todos os status" if role == "admin" else "Ativos"
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
        self.contact_form_cpf = ""
        self.contact_form_birth_date = ""
        self.contact_form_email = ""
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
        self.contact_form_cpf = _format_cpf(contact.get("cpf", ""))
        self.contact_form_birth_date = contact.get("birth_date", "")
        self.contact_form_email = contact.get("email", "")
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
    def set_contact_form_cpf(self, value: str):
        self.contact_form_cpf = _format_cpf(value)

    @rx.event
    def set_contact_form_birth_date(self, value: str):
        self.contact_form_birth_date = value

    @rx.event
    def set_contact_form_email(self, value: str):
        self.contact_form_email = value

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
        name = str(form_data.get("name") or self.contact_form_name).strip()
        phone = _format_contact_phone(
            str(form_data.get("phone") or self.contact_form_phone).strip()
        )
        cpf = _normalize_cpf(str(form_data.get("cpf") or self.contact_form_cpf))
        birth_date = str(
            form_data.get("birth_date") or self.contact_form_birth_date
        ).strip()
        email = _normalize_email(form_data.get("email") or self.contact_form_email)
        notes = str(form_data.get("notes") or self.contact_form_notes).strip()
        first_contact_at = str(
            form_data.get("first_contact_at") or self.contact_form_first_contact_at
        ).strip()
        source_label = str(
            form_data.get("source") or self.contact_form_source
        )
        source = CONTACT_SOURCE_VALUES.get(source_label)
        phone_error = _contact_phone_validation_error(phone)
        birth_date_error = ""
        if birth_date:
            try:
                if date.fromisoformat(birth_date) > date.today():
                    raise ValueError
            except ValueError:
                birth_date_error = (
                    "Informe uma data de nascimento válida, que não esteja no futuro."
                )
        first_contact_error = ""
        if first_contact_at:
            try:
                if date.fromisoformat(first_contact_at) > _today_in_barbershop_timezone():
                    raise ValueError
            except ValueError:
                first_contact_error = (
                    "Informe uma data de primeiro contato válida, que não esteja no futuro."
                )
        if not name:
            self.contact_form_error = "Informe o nome do cliente."
        elif len(name) > 120:
            self.contact_form_error = "O nome deve ter no máximo 120 caracteres."
        elif not phone:
            self.contact_form_error = "Informe o telefone do cliente."
        elif phone_error:
            self.contact_form_error = phone_error
        elif birth_date_error:
            self.contact_form_error = birth_date_error
        elif first_contact_error:
            self.contact_form_error = first_contact_error
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
            "phone": _phone_for_api(phone),
            "cpf": cpf,
            "birth_date": birth_date,
            "email": email,
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
        spacing="4",
        align="center",
    )


def _nav_icon(name: str) -> rx.Component:
    return rx.icon(
        name,
        size=20,
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


def _password_input(
    field_id: str,
    name: str,
    visibility_key: str,
    visible: Any,
    placeholder: str = "",
    min_length: int = 0,
    invalid: Any = False,
    required: bool = True,
) -> rx.Component:
    input_props: dict[str, Any] = {
        "id": field_id,
        "name": name,
        "type": rx.cond(visible, "text", "password"),
        "required": required,
        "class_name": "pc-password-input-field",
        "width": "100%",
        "aria_invalid": invalid,
    }
    if placeholder:
        input_props["placeholder"] = placeholder
    if min_length:
        input_props["min_length"] = min_length

    return rx.el.div(
        rx.el.input(**input_props),
        rx.button(
            rx.cond(
                visible,
                rx.icon("eye-off", size=18, aria_hidden="true"),
                rx.icon("eye", size=18, aria_hidden="true"),
            ),
            type="button",
            on_click=AuthState.toggle_password_visibility(visibility_key),
            aria_label=rx.cond(visible, "Ocultar senha", "Mostrar senha"),
            class_name="pc-password-visibility",
        ),
        class_name=rx.cond(
            invalid,
            "pc-password-input pc-password-input-invalid",
            "pc-password-input",
        ),
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
                    placeholder="nome.barbearia.com",
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
                _password_input(
                    "login-password",
                    "password",
                    "login",
                    AuthState.login_password_visible,
                    "Digite sua senha",
                    invalid=AuthState.error_message != "",
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
                _password_input(
                    "new-password",
                    "new_password",
                    "temporary",
                    AuthState.temporary_password_visible,
                    "Mínimo de 8 caracteres",
                    min_length=8,
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.vstack(
                rx.el.label("Confirme a nova senha", html_for="confirm-password", class_name="pc-field-label"),
                _password_input(
                    "confirm-password",
                    "confirm_password",
                    "temporary_confirmation",
                    AuthState.temporary_confirmation_visible,
                    "Digite novamente a nova senha",
                    min_length=8,
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
            rx.link(
                _nav_icon("calendar-days"),
                rx.text("Agenda"),
                href="/appointments",
                tab_index=0,
                aria_current="page" if active_route == "/appointments" else None,
                class_name=(
                    "pc-nav-link pc-nav-link-active"
                    if active_route == "/appointments"
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
            rx.link(
                _nav_icon("chart-no-axes-combined"),
                rx.text("Financeiro"),
                href="/financeiro",
                tab_index=0,
                aria_current="page" if active_route == "/financeiro" else None,
                class_name=(
                    "pc-nav-link pc-nav-link-active"
                    if active_route == "/financeiro"
                    else "pc-nav-link"
                ),
            ),
            width="100%",
            spacing="0",
            class_name="pc-nav",
        ),
        rx.vstack(
            rx.button(
                rx.hstack(
                    rx.cond(
                        AuthState.profile_photo_url != "",
                        rx.image(
                            src=AuthState.profile_photo_url,
                            alt="",
                            class_name="pc-sidebar-avatar",
                        ),
                        rx.icon(
                            "circle-user-round",
                            size=24,
                            stroke_width=1.7,
                            aria_hidden="true",
                            class_name="pc-profile-icon",
                        ),
                    ),
                    rx.vstack(
                        rx.text(AuthState.display_name, class_name="pc-sidebar-user"),
                        rx.text(
                            rx.cond(
                                AuthState.role == "admin",
                                "Administradora",
                                "Profissional",
                            ),
                            class_name="pc-sidebar-role",
                        ),
                        spacing="1",
                        align="start",
                        class_name="pc-sidebar-profile-copy",
                    ),
                    class_name="pc-sidebar-profile-identity",
                    align="center",
                ),
                type="button",
                on_click=AuthState.open_profile_editor,
                aria_label="Abrir meu perfil",
                title="Abrir meu perfil",
                class_name="pc-sidebar-profile-link",
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
                            else "Agenda"
                            if active_route == "/appointments"
                            else "Financeiro"
                            if active_route == "/financeiro"
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
        _profile_editor(),
        class_name="pc-app-shell",
    )


def app_page() -> rx.Component:
    from frontend.overview_page import overview_page

    return overview_page()


def _professional_row(professional: Any) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.cond(
                professional["profile_photo_url"] != "",
                rx.image(
                    src=professional["profile_photo_url"],
                    alt=professional["name"],
                    class_name="pc-team-avatar",
                ),
                rx.icon(
                    "circle-user-round",
                    size=28,
                    stroke_width=1.3,
                    aria_hidden="true",
                    class_name="pc-team-avatar-icon",
                ),
            ),
            rx.el.div(
                rx.text(professional["name"], class_name="pc-team-name"),
                rx.text(professional["email"], class_name="pc-team-email"),
                class_name="pc-team-copy",
            ),
            class_name="pc-team-primary",
        ),
        rx.el.div(
            rx.el.div(
                rx.text(professional["phone"], class_name="pc-team-phone-value"),
                data_label="Telefone",
                class_name="pc-team-phone",
            ),
            rx.el.div(
                rx.text(professional["role"], class_name="pc-team-role-value"),
                data_label="Perfil",
                class_name="pc-team-role",
            ),
            class_name="pc-team-meta",
        ),
        class_name="pc-team-member-row",
    )


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
                    value=AuthState.professional_email,
                    on_change=AuthState.set_professional_email,
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
            rx.vstack(
                rx.el.label("Senha", html_for="professional-password", class_name="pc-field-label"),
                rx.input(
                    id="professional-password",
                    name="password",
                    type="password",
                    placeholder="Mínimo de 8 caracteres, uma letra e um número",
                    required=True,
                    min_length=8,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="2",
            ),
            rx.cond(
                AuthState.professional_success_message != "",
                rx.text(
                    AuthState.professional_success_message,
                    role="status",
                    class_name="pc-service-success",
                ),
                rx.fragment(),
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
        reset_on_submit=False,
        width="100%",
        class_name="pc-form",
        id="professional-form",
    )
    content = rx.vstack(
        rx.text("GESTÃO DA EQUIPE", class_name="pc-eyebrow"),
        rx.heading("Cadastrar profissional", class_name="pc-page-title"),
        rx.text(
            "Todos os campos são obrigatórios. Defina a senha de acesso do profissional.",
            class_name="pc-page-description",
        ),
        rx.el.section(
            rx.hstack(
                rx.el.section(
                    professional_form,
                    class_name="pc-form-panel pc-team-form-panel",
                ),
                rx.el.section(
                    rx.vstack(
                        rx.heading("Profissionais cadastrados", class_name="pc-catalog-title"),
                        rx.cond(
                            AuthState.professionals_loading,
                            rx.text("Carregando profissionais...", role="status", class_name="pc-service-empty"),
                            rx.cond(
                                AuthState.professionals_error != "",
                                rx.text(AuthState.professionals_error, role="alert", class_name="pc-service-error-text"),
                                rx.cond(
                                    AuthState.professionals.length() == 0,
                                    rx.text("Nenhum profissional cadastrado.", class_name="pc-service-empty"),
                                    rx.vstack(
                                        rx.foreach(AuthState.professional_page_items, _professional_row),
                                        rx.hstack(
                                            rx.text(
                                                AuthState.professional_results_summary,
                                                class_name="pc-service-page-indicator",
                                            ),
                                            rx.spacer(),
                                            rx.button(
                                                "Anterior",
                                                type="button",
                                                disabled=AuthState.professional_page <= 1,
                                                on_click=AuthState.previous_professional_page,
                                                class_name="pc-button pc-button-secondary pc-page-button",
                                            ),
                                            rx.text(
                                                "Página ",
                                                AuthState.professional_page,
                                                " de ",
                                                AuthState.professional_page_count,
                                                class_name="pc-service-page-indicator",
                                            ),
                                            rx.button(
                                                "Próxima",
                                                type="button",
                                                disabled=AuthState.professional_page >= AuthState.professional_page_count,
                                                on_click=AuthState.next_professional_page,
                                                class_name="pc-button pc-button-secondary pc-page-button",
                                            ),
                                            width="100%",
                                            align="center",
                                            class_name="pc-service-pagination",
                                        ),
                                        width="100%",
                                        spacing="0",
                                    ),
                                ),
                            ),
                        ),
                        align="stretch",
                        spacing="4",
                        width="100%",
                    ),
                    class_name="pc-form-panel pc-team-list-panel",
                ),
                align="start",
                width="100%",
                spacing="5",
                class_name="pc-team-columns",
            ),
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
                            spacing="3",
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
                            spacing="3",
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
                        spacing="4",
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
                            rx.el.label(
                                "CPF",
                                html_for="contact-cpf",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="contact-cpf",
                                name="cpf",
                                value=AuthState.contact_form_cpf,
                                on_change=AuthState.set_contact_form_cpf,
                                input_mode="numeric",
                                max_length=14,
                                placeholder="000.000.000-00",
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.el.label(
                                "Data de nascimento",
                                html_for="contact-birth-date",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="contact-birth-date",
                                name="birth_date",
                                type="date",
                                max=AuthState.today_iso,
                                value=AuthState.contact_form_birth_date,
                                on_change=AuthState.set_contact_form_birth_date,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            width="100%",
                        ),
                        class_name="pc-appointment-form-row",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.el.label(
                            "E-mail",
                            html_for="contact-email",
                            class_name="pc-field-label",
                        ),
                        rx.input(
                            id="contact-email",
                            name="email",
                            type="email",
                            input_mode="email",
                            value=AuthState.contact_form_email,
                            on_change=AuthState.set_contact_form_email,
                            max_length=254,
                            placeholder="cliente@email.com",
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
                            spacing="3",
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
                                max=AuthState.today_iso,
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


def _appointment_select(
    options: Any,
    value: Any,
    on_change: Any,
    aria_label: str,
    class_name: str,
    element_id: str = "",
    disabled: Any = False,
) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(
            aria_label=aria_label,
            class_name=class_name,
            id=element_id or None,
            disabled=disabled,
        ),
        rx.select.content(
            rx.select.group(
                rx.foreach(
                    options,
                    lambda option: rx.select.item(
                        option["label"],
                        value=option["value"],
                        disabled=option["disabled"],
                    ),
                ),
            ),
        ),
        value=value,
        on_change=on_change,
    )


def _appointment_service_option(service: Any) -> rx.Component:
    is_selected = AuthState.appointment_form_service_ids.contains(service["id"])
    return rx.button(
        rx.hstack(
            rx.cond(
                is_selected,
                rx.icon(
                    "circle-check",
                    size=18,
                    stroke_width=1.8,
                    aria_hidden="true",
                    class_name="pc-appointment-service-check pc-appointment-service-check-selected",
                ),
                rx.icon(
                    "circle",
                    size=18,
                    stroke_width=1.5,
                    aria_hidden="true",
                    class_name="pc-appointment-service-check",
                ),
            ),
            rx.vstack(
                rx.text(service["name"], class_name="pc-appointment-service-name"),
                rx.text(
                    service["price_display"],
                    " · ",
                    service["duration_display"],
                    class_name="pc-appointment-service-meta",
                ),
                align="start",
                spacing="1",
                class_name="pc-appointment-service-copy",
            ),
            align="start",
            spacing="3",
            width="100%",
        ),
        type="button",
        on_click=AuthState.toggle_appointment_service(service["id"]),
        class_name=rx.cond(
            is_selected,
            "pc-appointment-service-option pc-appointment-service-option-selected",
            "pc-appointment-service-option",
        ),
        aria_pressed=is_selected,
        aria_label=rx.cond(
            is_selected,
            "Remover serviço da seleção",
            "Adicionar serviço à seleção",
        ),
    )


def _appointment_calendar_day(day: Any) -> rx.Component:
    return rx.button(
        rx.text(day["label"]),
        rx.cond(
            day["has_appointments"],
            rx.el.span(class_name="pc-calendar-day-marker", aria_hidden="true"),
            rx.fragment(),
        ),
        type="button",
        disabled=~day["in_month"],
        aria_label=day["date"],
        aria_pressed=day["selected"],
        on_click=AuthState.set_appointment_date(day["date"]),
        class_name=rx.cond(
            day["selected"],
            "pc-calendar-day pc-calendar-day-selected",
            rx.cond(
                day["in_month"],
                "pc-calendar-day",
                "pc-calendar-day pc-calendar-day-outside",
            ),
        ),
    )


def _appointment_slot(slot: Any) -> rx.Component:
    return rx.button(
        rx.text(slot["time"], class_name="pc-availability-time"),
        rx.text(
            rx.cond(
                slot["state"] == "available",
                "Disponível",
                rx.cond(
                    slot["state"] == "blocked",
                    "Bloqueado",
                    "Ocupado",
                ),
            ),
            class_name="pc-availability-status",
        ),
        type="button",
        disabled=slot["state"] != "available",
        on_click=AuthState.start_appointment_from_slot(
            slot["time"],
            slot["professional_id"],
        ),
        class_name=rx.cond(
            slot["state"] == "available",
            "pc-availability-slot pc-availability-slot-open",
            rx.cond(
                slot["state"] == "blocked",
                "pc-availability-slot pc-availability-slot-blocked",
                "pc-availability-slot pc-availability-slot-busy",
            ),
        ),
    )


def _appointment_table_row(appointment: Any) -> rx.Component:
    return rx.el.tr(
        rx.el.td(appointment["time_display"]),
        rx.el.td(
            rx.vstack(
                rx.text(appointment["contact_name"]),
                rx.text(
                    appointment["contact_phone"],
                    class_name="pc-table-muted",
                ),
                align="start",
                spacing="1",
            )
        ),
        rx.el.td(appointment["service_summary"]),
        rx.el.td(appointment["professional_name"]),
        rx.el.td(
            rx.text(
                appointment["status_display"],
                class_name=rx.cond(
                    appointment["status"] == "confirmed",
                    "pc-appointment-status pc-status-confirmed",
                    rx.cond(
                        appointment["status"] == "completed",
                        "pc-appointment-status pc-status-completed",
                        rx.cond(
                            appointment["status"] == "cancelled",
                            "pc-appointment-status pc-status-cancelled",
                            "pc-appointment-status pc-status-pending",
                        ),
                    ),
                ),
            )
        ),
        rx.el.td(
            rx.hstack(
                rx.button(
                    rx.icon("eye", size=15, aria_hidden="true"),
                    type="button",
                    on_click=AuthState.show_appointment_detail(appointment["id"]),
                    aria_label="Ver detalhes",
                    class_name="pc-icon-action",
                ),
                rx.cond(
                    (appointment["status"] == "pending")
                    | (appointment["status"] == "confirmed"),
                    rx.fragment(
                        rx.cond(
                            appointment["status"] == "pending",
                            rx.button(
                                rx.icon("check", size=15, aria_hidden="true"),
                                "Confirmar",
                                type="button",
                                on_click=AuthState.set_appointment_status(
                                    appointment["id"], "confirmed"
                                ),
                                aria_label="Confirmar agendamento",
                                class_name="pc-service-action pc-service-edit",
                            ),
                            rx.button(
                                rx.icon("check", size=15, aria_hidden="true"),
                                "Concluir",
                                type="button",
                                on_click=AuthState.set_appointment_status(
                                    appointment["id"], "completed"
                                ),
                                aria_label="Concluir atendimento",
                                class_name="pc-service-action pc-service-edit",
                            ),
                        ),
                        rx.button(
                            rx.icon("pencil", size=15, aria_hidden="true"),
                            type="button",
                            on_click=AuthState.start_edit_appointment(
                                appointment["id"]
                            ),
                            aria_label="Editar agendamento",
                            class_name="pc-icon-action",
                        ),
                        rx.button(
                            rx.icon("ban", size=15, aria_hidden="true"),
                            type="button",
                            on_click=AuthState.request_appointment_cancel(
                                appointment["id"]
                            ),
                            aria_label="Cancelar agendamento",
                            class_name="pc-icon-action pc-icon-action-danger",
                        ),
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                align="center",
            )
        ),
        class_name="pc-appointment-table-row",
    )


def _appointment_calendar_view() -> rx.Component:
    return rx.hstack(
        rx.el.section(
            rx.vstack(
                rx.hstack(
                    rx.heading("Calendário", class_name="pc-catalog-title"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("chevron-left", size=16, aria_hidden="true"),
                        type="button",
                        on_click=AuthState.change_appointment_month(-1),
                        aria_label="Mês anterior",
                        class_name="pc-icon-action",
                    ),
                    rx.text(
                        AuthState.appointment_month_label,
                        class_name="pc-calendar-month",
                    ),
                    rx.button(
                        rx.icon("chevron-right", size=16, aria_hidden="true"),
                        type="button",
                        on_click=AuthState.change_appointment_month(1),
                        aria_label="Próximo mês",
                        class_name="pc-icon-action",
                    ),
                    align="center",
                    width="100%",
                ),
                rx.grid(
                    *[
                        rx.text(label, class_name="pc-calendar-weekday")
                        for label in ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
                    ],
                    columns="repeat(7, minmax(0, 1fr))",
                    width="100%",
                    class_name="pc-calendar-weekdays",
                ),
                rx.grid(
                    rx.foreach(AuthState.appointment_calendar_days, _appointment_calendar_day),
                    columns="repeat(7, minmax(0, 1fr))",
                    width="100%",
                    class_name="pc-calendar-grid",
                ),
                rx.hstack(
                    rx.el.span(class_name="pc-calendar-day-marker"),
                    rx.text("Dia com agendamentos", class_name="pc-table-muted"),
                    spacing="2",
                    align="center",
                ),
                align="stretch",
                spacing="4",
                width="100%",
            ),
            class_name="pc-appointment-calendar-panel",
        ),
        rx.el.section(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            "Horários disponíveis",
                            class_name="pc-catalog-title",
                        ),
                        rx.text(
                            AuthState.appointment_date,
                            class_name="pc-catalog-description",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    _appointment_select(
                        AuthState.appointment_professional_options,
                        AuthState.appointment_professional_value,
                        AuthState.set_appointment_professional,
                        "Filtrar profissional",
                        "pc-service-filter",
                    ),
                    align="start",
                    width="100%",
                ),
                rx.hstack(
                    rx.text("● Disponível", class_name="pc-slot-legend-open"),
                    rx.text("● Ocupado", class_name="pc-slot-legend-busy"),
                    rx.text("● Bloqueado", class_name="pc-slot-legend-blocked"),
                    class_name="pc-slot-legend",
                    spacing="3",
                ),
                rx.cond(
                    AuthState.appointment_loading
                    | AuthState.appointment_options_loading,
                    rx.text(
                        "Carregando disponibilidade...",
                        role="status",
                        class_name="pc-service-empty",
                    ),
                    rx.cond(
                        AuthState.appointment_time_slots.length() == 0,
                        rx.text(
                            "Não há expediente nesta data.",
                            class_name="pc-service-empty",
                        ),
                        rx.vstack(
                            rx.foreach(
                                AuthState.appointment_time_slots,
                                _appointment_slot,
                            ),
                            align="stretch",
                            spacing="2",
                            width="100%",
                            class_name="pc-availability-list",
                        ),
                    ),
                ),
                rx.button(
                    "Bloquear horário",
                    type="button",
                    on_click=AuthState.open_appointment_block_form,
                    class_name="pc-button pc-button-secondary pc-block-button",
                ),
                rx.cond(
                    AuthState.appointment_day_blocks.length() > 0,
                    rx.vstack(
                        rx.text("Bloqueios do dia", class_name="pc-field-label"),
                        rx.foreach(
                            AuthState.appointment_day_blocks,
                            lambda block: rx.hstack(
                                rx.text(
                                    block["start_time_display"],
                                    "–",
                                    block["end_time_display"],
                                    " · ",
                                    rx.cond(
                                        block["reason"] != "",
                                        block["reason"],
                                        "Sem motivo informado",
                                    ),
                                    class_name="pc-table-muted",
                                ),
                                rx.cond(
                                    (AuthState.role == "admin")
                                    | (
                                        block["professional_id"]
                                        == AuthState.user_id
                                    ),
                                    rx.button(
                                        "Liberar",
                                        type="button",
                                        on_click=AuthState.remove_appointment_block(
                                            block["id"]
                                        ),
                                        class_name="pc-icon-action",
                                    ),
                                    rx.fragment(),
                                ),
                                justify="between",
                                width="100%",
                            ),
                        ),
                        align="stretch",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                align="stretch",
                spacing="4",
                width="100%",
            ),
            class_name="pc-availability-panel",
        ),
        align="start",
        spacing="5",
        width="100%",
        class_name="pc-appointment-calendar-layout",
    )


def _appointment_list_view() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Agendamentos", class_name="pc-catalog-title"),
                    rx.text(
                        "Consulte e filtre os atendimentos da data selecionada.",
                        class_name="pc-catalog-description",
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.input(
                    type="date",
                    value=AuthState.appointment_date,
                    on_change=AuthState.set_appointment_date,
                    aria_label="Data dos agendamentos",
                    class_name="pc-service-filter",
                ),
                rx.input(
                    placeholder="Buscar cliente, serviço ou profissional",
                    value=AuthState.appointment_search,
                    on_change=AuthState.set_appointment_search,
                    aria_label="Buscar agendamentos",
                    class_name="pc-service-filter pc-appointment-search",
                ),
                rx.select(
                    [
                        "Não cancelados",
                        "Pendente",
                        "Confirmado",
                        "Concluído",
                        "Cancelado",
                    ],
                    value=AuthState.appointment_status_filter,
                    on_change=AuthState.set_appointment_status_filter,
                    aria_label="Filtrar status",
                    class_name="pc-service-filter",
                ),
                align="center",
                class_name="pc-catalog-tools pc-appointment-list-tools",
                width="100%",
            ),
            rx.cond(
                AuthState.appointment_loading,
                rx.text("Carregando agendamentos...", role="status"),
                rx.cond(
                    AuthState.appointment_filtered_items.length() == 0,
                    rx.text(
                        "Nenhum agendamento corresponde aos filtros.",
                        class_name="pc-service-empty",
                    ),
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    *[
                                        rx.el.th(label)
                                        for label in (
                                            "Horário",
                                            "Cliente",
                                            "Serviço",
                                            "Funcionário",
                                            "Status",
                                            "Ações",
                                        )
                                    ],
                                    class_name="pc-appointment-table-head",
                                )
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    AuthState.appointment_filtered_items,
                                    _appointment_table_row,
                                )
                            ),
                            class_name="pc-appointment-table",
                        ),
                        class_name="pc-appointment-table-scroll",
                    ),
                ),
            ),
            align="stretch",
            spacing="4",
            width="100%",
        ),
        class_name="pc-appointment-list-panel",
    )


def _appointment_success_view() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.icon(
                "circle-check",
                size=54,
                stroke_width=2,
                aria_hidden="true",
                class_name="pc-appointment-success-icon",
            ),
            rx.heading("Agendamento confirmado!", class_name="pc-panel-title"),
            rx.text(
                "O atendimento foi registrado com sucesso.",
                class_name="pc-panel-description",
            ),
            rx.el.dl(
                rx.el.dt("Cliente"),
                rx.el.dd(AuthState.appointment_success_details["contact_name"]),
                rx.el.dt("Telefone"),
                rx.el.dd(AuthState.appointment_success_details["contact_phone"]),
                rx.el.dt("Data"),
                rx.el.dd(AuthState.appointment_success_details["date_display"]),
                rx.el.dt("Horário"),
                rx.el.dd(AuthState.appointment_success_details["time_display"]),
                rx.el.dt("Serviço"),
                rx.el.dd(AuthState.appointment_success_details["service_summary"]),
                rx.el.dt("Valor"),
                rx.el.dd(AuthState.appointment_success_details["total_display"]),
                rx.el.dt("Funcionário"),
                rx.el.dd(AuthState.appointment_success_details["professional_name"]),
                class_name="pc-appointment-success-summary",
            ),
            rx.hstack(
                rx.button(
                    "Ver todos os agendamentos",
                    type="button",
                    on_click=AuthState.show_appointment_list,
                    class_name="pc-button pc-button-primary",
                ),
                rx.button(
                    "Novo agendamento",
                    type="button",
                    on_click=AuthState.start_new_appointment,
                    class_name="pc-button pc-button-secondary",
                ),
                class_name="pc-service-form-actions",
                spacing="4",
            ),
            align="center",
            spacing="4",
            class_name="pc-appointment-success-card",
        ),
        class_name="pc-appointment-list-panel",
    )


def _appointment_detail_modal() -> rx.Component:
    return rx.el.div(
        rx.el.section(
            rx.hstack(
                rx.heading(
                    "Detalhes do Agendamento",
                    id="appointment-detail-heading",
                    class_name="pc-catalog-title",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("x", size=17, aria_hidden="true"),
                    type="button",
                    on_click=AuthState.close_appointment_detail,
                    aria_label="Fechar detalhes",
                    class_name="pc-icon-action",
                ),
                width="100%",
                align="center",
            ),
            rx.el.dl(
                rx.el.dt("Cliente"),
                rx.el.dd(AuthState.appointment_selected_detail["contact_name"]),
                rx.el.dt("Telefone"),
                rx.el.dd(AuthState.appointment_selected_detail["contact_phone"]),
                rx.el.dt("Data e horário"),
                rx.el.dd(
                    AuthState.appointment_selected_detail["time_display"],
                    " · ",
                    AuthState.appointment_selected_detail["date_display"],
                ),
                rx.el.dt("Serviço"),
                rx.el.dd(
                    rx.foreach(
                        AuthState.appointment_selected_detail_services,
                        lambda service: rx.text(
                            service["name"],
                            " · ",
                            service["price_display"],
                            " · ",
                            service["duration_display"],
                        ),
                    )
                ),
                rx.el.dt("Valor"),
                rx.el.dd(AuthState.appointment_selected_detail["total_display"]),
                rx.el.dt("Funcionário"),
                rx.el.dd(AuthState.appointment_selected_detail["professional_name"]),
                rx.el.dt("Status"),
                rx.el.dd(AuthState.appointment_selected_detail["status_display"]),
                rx.el.dt("Observações"),
                rx.el.dd(
                    rx.cond(
                        AuthState.appointment_selected_detail["notes"] != "",
                        AuthState.appointment_selected_detail["notes"],
                        "Sem observações",
                    )
                ),
                class_name="pc-appointment-detail-list",
            ),
            rx.hstack(
                rx.cond(
                    (AuthState.appointment_selected_detail["status"] == "pending")
                    | (
                        AuthState.appointment_selected_detail["status"]
                        == "confirmed"
                    ),
                    rx.fragment(
                        rx.cond(
                            AuthState.appointment_selected_detail["status"]
                            == "pending",
                            rx.button(
                                "Confirmar agendamento",
                                type="button",
                                on_click=AuthState.set_appointment_status(
                                    AuthState.appointment_selected_detail["id"],
                                    "confirmed",
                                ),
                                class_name="pc-button pc-button-primary",
                            ),
                            rx.button(
                                "Concluir atendimento",
                                type="button",
                                on_click=AuthState.set_appointment_status(
                                    AuthState.appointment_selected_detail["id"],
                                    "completed",
                                ),
                                class_name="pc-button pc-button-primary",
                            ),
                        ),
                        rx.button(
                            "Editar",
                            type="button",
                            on_click=AuthState.start_edit_appointment(
                                AuthState.appointment_selected_detail["id"]
                            ),
                            class_name="pc-button pc-button-secondary",
                        ),
                        rx.button(
                            "Cancelar Agendamento",
                            type="button",
                            on_click=AuthState.request_appointment_cancel(
                                AuthState.appointment_selected_detail["id"]
                            ),
                            class_name="pc-button pc-button-secondary pc-service-danger",
                        ),
                    ),
                    rx.fragment(),
                ),
                class_name="pc-service-form-actions",
                spacing="4",
            ),
            role="dialog",
            aria_modal="true",
            aria_labelledby="appointment-detail-heading",
            class_name="pc-appointment-modal",
        ),
        class_name="pc-modal-backdrop",
    )


def _appointment_cancel_confirmation() -> rx.Component:
    return rx.el.div(
        rx.el.section(
            rx.heading(
                "Cancelar agendamento?",
                id="appointment-cancel-heading",
                class_name="pc-catalog-title",
            ),
            rx.text(
                "O histórico será preservado e o horário ficará disponível novamente.",
                class_name="pc-catalog-description",
            ),
            rx.hstack(
                rx.button(
                    "Voltar",
                    type="button",
                    on_click=AuthState.dismiss_appointment_cancel,
                    class_name="pc-button pc-button-secondary",
                ),
                rx.button(
                    "Confirmar cancelamento",
                    type="button",
                    on_click=AuthState.confirm_appointment_cancel,
                    class_name="pc-button pc-button-danger",
                ),
                class_name="pc-service-form-actions",
                spacing="3",
            ),
            role="alertdialog",
            aria_modal="true",
            aria_labelledby="appointment-cancel-heading",
            class_name="pc-appointment-modal pc-appointment-confirm",
        ),
        class_name="pc-modal-backdrop",
    )


def _appointment_block_form() -> rx.Component:
    return rx.el.div(
        rx.form(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        "Bloquear horário",
                        id="appointment-block-heading",
                        class_name="pc-catalog-title",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16, aria_hidden="true"),
                        type="button",
                        on_click=AuthState.close_appointment_block_form,
                        aria_label="Fechar",
                        class_name="pc-icon-action",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.text(
                    "O bloqueio será aplicado à data selecionada.",
                    class_name="pc-catalog-description",
                ),
                rx.cond(
                    AuthState.role == "admin",
                    _appointment_select(
                        AuthState.appointment_block_professional_options,
                        AuthState.appointment_block_professional_value,
                        AuthState.set_appointment_block_professional,
                        "Profissional do bloqueio",
                        "pc-input",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.input(
                        name="start_time",
                        type="time",
                        required=True,
                        step="1800",
                        aria_label="Início do bloqueio",
                        class_name="pc-input",
                    ),
                    rx.input(
                        name="end_time",
                        type="time",
                        required=True,
                        step="1800",
                        aria_label="Fim do bloqueio",
                        class_name="pc-input",
                    ),
                    class_name="pc-appointment-form-row",
                    width="100%",
                ),
                rx.input(
                    name="reason",
                    max_length=200,
                    placeholder="Motivo (opcional)",
                    class_name="pc-input",
                ),
                rx.cond(
                    AuthState.appointment_block_error != "",
                    rx.text(
                        AuthState.appointment_block_error,
                        role="alert",
                        class_name="pc-service-error-text",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.button(
                        rx.cond(
                            AuthState.appointment_block_submitting,
                            "Salvando...",
                            "Salvar bloqueio",
                        ),
                        type="submit",
                        disabled=AuthState.appointment_block_submitting,
                        class_name="pc-button pc-button-primary",
                    ),
                    rx.button(
                        "Cancelar",
                        type="button",
                        on_click=AuthState.close_appointment_block_form,
                        class_name="pc-button pc-button-secondary",
                    ),
                    class_name="pc-service-form-actions",
                    spacing="3",
                ),
                role="dialog",
                aria_modal="true",
                aria_labelledby="appointment-block-heading",
                align="stretch",
                spacing="4",
                width="100%",
                class_name="pc-appointment-modal",
            ),
            on_submit=AuthState.save_appointment_block,
            reset_on_submit=False,
        ),
        class_name="pc-modal-backdrop",
    )


def _appointment_quick_contact_form() -> rx.Component:
    return rx.el.div(
        rx.form(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        "Cadastrar novo cliente",
                        id="quick-contact-heading",
                        class_name="pc-catalog-title",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("x", size=16, aria_hidden="true"),
                        type="button",
                        on_click=AuthState.close_quick_contact_form,
                        aria_label="Fechar cadastro de cliente",
                        class_name="pc-icon-action",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.el.label(
                            "Nome completo *",
                            html_for="quick-contact-name",
                            class_name="pc-field-label",
                        ),
                        rx.input(
                            id="quick-contact-name",
                            name="name",
                            value=AuthState.appointment_quick_contact_name,
                            on_change=AuthState.set_appointment_quick_contact_name,
                            required=True,
                            max_length=120,
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.el.label(
                            "Telefone *",
                            html_for="quick-contact-phone",
                            class_name="pc-field-label",
                        ),
                        rx.input(
                            id="quick-contact-phone",
                            name="phone",
                            type="tel",
                            value=AuthState.appointment_quick_contact_phone,
                            on_change=AuthState.set_quick_contact_phone,
                            required=True,
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    class_name="pc-appointment-form-row",
                    width="100%",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.el.label("CPF", html_for="quick-contact-cpf", class_name="pc-field-label"),
                        rx.input(
                            id="quick-contact-cpf",
                            name="cpf",
                            value=AuthState.appointment_quick_contact_cpf,
                            on_change=AuthState.set_quick_contact_cpf,
                            max_length=14,
                            placeholder="000.000.000-00",
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.el.label("Data de nascimento", html_for="quick-contact-birth-date", class_name="pc-field-label"),
                        rx.input(
                            id="quick-contact-birth-date",
                            name="birth_date",
                            type="date",
                            max=AuthState.today_iso,
                            value=AuthState.appointment_quick_contact_birth_date,
                            on_change=AuthState.set_quick_contact_birth_date,
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    class_name="pc-appointment-form-row",
                    width="100%",
                ),
                rx.vstack(
                    rx.el.label("E-mail", html_for="quick-contact-email", class_name="pc-field-label"),
                    rx.input(
                        id="quick-contact-email",
                        name="email",
                        type="email",
                        input_mode="email",
                        value=AuthState.appointment_quick_contact_email,
                        on_change=AuthState.set_quick_contact_email,
                        max_length=254,
                        placeholder="cliente@email.com",
                        class_name="pc-input",
                    ),
                    class_name="pc-field",
                    align="stretch",
                    width="100%",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.el.label("Origem *", html_for="quick-contact-source", class_name="pc-field-label"),
                        rx.select(
                            list(CONTACT_SOURCE_LABELS.values()),
                            id="quick-contact-source",
                            name="source",
                            value=AuthState.appointment_quick_contact_source,
                            on_change=AuthState.set_quick_contact_source,
                            required=True,
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.el.label("Primeiro contato *", html_for="quick-contact-first-contact", class_name="pc-field-label"),
                        rx.input(
                            id="quick-contact-first-contact",
                            name="first_contact_at",
                            type="date",
                            max=AuthState.today_iso,
                            value=AuthState.appointment_quick_contact_first_contact_at,
                            on_change=AuthState.set_quick_contact_first_contact_at,
                            required=True,
                            class_name="pc-input",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        width="100%",
                    ),
                    class_name="pc-appointment-form-row",
                    width="100%",
                ),
                rx.vstack(
                    rx.el.label("Observações", html_for="quick-contact-notes", class_name="pc-field-label"),
                    rx.text_area(
                        id="quick-contact-notes",
                        name="notes",
                        value=AuthState.appointment_quick_contact_notes,
                        on_change=AuthState.set_quick_contact_notes,
                        max_length=1000,
                        class_name="pc-input",
                    ),
                    class_name="pc-field",
                    align="stretch",
                    width="100%",
                ),
                rx.cond(
                    AuthState.appointment_quick_contact_error != "",
                    rx.text(
                        AuthState.appointment_quick_contact_error,
                        role="alert",
                        class_name="pc-service-error-text",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.button(
                        rx.cond(
                            AuthState.appointment_quick_contact_submitting,
                            "Salvando...",
                            "Cadastrar Cliente",
                        ),
                        type="submit",
                        disabled=AuthState.appointment_quick_contact_submitting,
                        class_name="pc-button pc-button-primary",
                    ),
                    rx.button(
                        "Cancelar",
                        type="button",
                        on_click=AuthState.close_quick_contact_form,
                        class_name="pc-button pc-button-secondary",
                    ),
                    class_name="pc-service-form-actions",
                    spacing="3",
                ),
                role="dialog",
                aria_modal="true",
                aria_labelledby="quick-contact-heading",
                align="stretch",
                spacing="4",
                width="100%",
                class_name="pc-appointment-modal",
            ),
            on_submit=AuthState.save_quick_contact,
            reset_on_submit=False,
        ),
        class_name="pc-modal-backdrop",
    )


def _appointment_row(appointment: Any) -> rx.Component:
    actions = rx.cond(
        (appointment["status"] == "pending")
        | (appointment["status"] == "confirmed"),
        rx.hstack(
            rx.button(
                "Editar",
                type="button",
                on_click=AuthState.start_edit_appointment(appointment["id"]),
                class_name="pc-service-action pc-service-edit",
            ),
            rx.cond(
                appointment["status"] == "pending",
                rx.button(
                    "Confirmar",
                    type="button",
                    on_click=AuthState.set_appointment_status(
                        appointment["id"], "confirmed"
                    ),
                    class_name="pc-service-action pc-service-edit",
                ),
                rx.button(
                    "Concluir",
                    type="button",
                    on_click=AuthState.set_appointment_status(
                        appointment["id"], "completed"
                    ),
                    class_name="pc-service-action pc-service-edit",
                ),
            ),
            rx.button(
                "Cancelar",
                type="button",
                on_click=AuthState.request_appointment_cancel(appointment["id"]),
                class_name="pc-service-action pc-service-danger",
            ),
            class_name="pc-appointment-actions",
            spacing="2",
        ),
        rx.text(
            "Histórico preservado",
            class_name="pc-appointment-readonly",
        ),
    )
    return rx.el.article(
        rx.hstack(
            rx.text(appointment["time_display"], class_name="pc-appointment-time"),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        appointment["contact_name"],
                        class_name="pc-appointment-client",
                    ),
                    rx.text(
                        appointment["status_display"],
                        class_name="pc-appointment-status",
                    ),
                    class_name="pc-appointment-title-row",
                    align="center",
                ),
                rx.text(
                    appointment["service_summary"],
                    class_name="pc-appointment-services",
                ),
                rx.text(
                    appointment["professional_name"],
                    " · ",
                    appointment["contact_phone"],
                    class_name="pc-appointment-details",
                ),
                rx.cond(
                    appointment["notes"] != "",
                    rx.text(
                        appointment["notes"],
                        class_name="pc-appointment-notes",
                    ),
                    rx.fragment(),
                ),
                align="start",
                spacing="2",
                class_name="pc-appointment-main",
            ),
            rx.spacer(),
            rx.vstack(
                rx.text(appointment["total_display"], class_name="pc-appointment-total"),
                actions,
                align="end",
                spacing="2",
                class_name="pc-appointment-side",
            ),
            align="start",
            width="100%",
            class_name="pc-appointment-row",
        ),
        class_name="pc-appointment-card",
    )


def _appointment_form() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.vstack(
                rx.heading(
                    rx.cond(
                        AuthState.appointment_editing_id > 0,
                        "Editar agendamento",
                        "Novo agendamento",
                    ),
                    class_name="pc-service-form-title",
                ),
                rx.text(
                    "Selecione o cliente, profissional, serviços e horário.",
                    class_name="pc-service-form-description",
                ),
                align="start",
                spacing="1",
            ),
            rx.form(
                rx.vstack(
                    rx.vstack(
                        rx.el.label(
                            "Dados do cliente",
                            html_for="appointment-contact",
                            class_name="pc-field-label",
                        ),
                        _appointment_select(
                            AuthState.appointment_contact_options,
                            AuthState.appointment_contact_value,
                            AuthState.set_appointment_contact,
                            "Selecione o cliente",
                            "pc-input",
                            element_id="appointment-contact",
                        ),
                        rx.cond(
                            AuthState.appointment_form_contact_id > 0,
                            rx.vstack(
                                rx.text(
                                    AuthState.appointment_selected_contact_details[
                                        "name"
                                    ],
                                    class_name="pc-appointment-client",
                                ),
                                rx.text(
                                    AuthState.appointment_selected_contact_details[
                                        "phone"
                                    ],
                                    class_name="pc-appointment-details",
                                ),
                                align="start",
                                spacing="1",
                                class_name="pc-appointment-selected-contact",
                            ),
                            rx.fragment(),
                        ),
                        rx.button(
                            "+ Cadastrar novo cliente",
                            type="button",
                            on_click=AuthState.open_quick_contact_form,
                            class_name="pc-button pc-button-secondary pc-quick-contact-button",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="3",
                        width="100%",
                    ),
                    rx.cond(
                        AuthState.role == "admin",
                        rx.vstack(
                            rx.el.label(
                                "Funcionário responsável",
                                html_for="appointment-professional",
                                class_name="pc-field-label",
                            ),
                            _appointment_select(
                                AuthState.appointment_form_professional_options,
                                AuthState.appointment_form_professional_value,
                                AuthState.set_appointment_form_professional,
                                "Funcionário responsável",
                                "pc-input",
                                element_id="appointment-professional",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    rx.vstack(
                        rx.el.label(
                            "Seleção do serviço",
                            class_name="pc-field-label",
                        ),
                        rx.text(
                            "Selecione todos os serviços deste atendimento.",
                            class_name="pc-catalog-description",
                        ),
                        rx.cond(
                            AuthState.appointment_available_services.length() == 0,
                            rx.text(
                                "Não há serviços ativos disponíveis.",
                                class_name="pc-service-empty",
                            ),
                            rx.foreach(
                                AuthState.appointment_available_services,
                                _appointment_service_option,
                            ),
                        ),
                        rx.cond(
                            AuthState.appointment_selected_services.length() > 0,
                            rx.vstack(
                                rx.hstack(
                                    rx.text("Total", class_name="pc-field-label"),
                                    rx.spacer(),
                                    rx.text(
                                        AuthState.appointment_selected_total_display,
                                        class_name="pc-appointment-total",
                                    ),
                                    rx.text(
                                        "· ",
                                        AuthState.appointment_selected_duration_display,
                                        class_name="pc-appointment-service-meta",
                                    ),
                                    width="100%",
                                    align="center",
                                ),
                                rx.foreach(
                                    AuthState.appointment_selected_services,
                                    lambda service: rx.text(
                                        service["name"],
                                        " · ",
                                        service["price_display"],
                                        " · ",
                                        service["duration_display"],
                                        class_name="pc-appointment-selected-service",
                                    ),
                                ),
                                align="start",
                                spacing="1",
                            ),
                            rx.fragment(),
                        ),
                        class_name="pc-field pc-appointment-service-picker",
                        align="stretch",
                        spacing="2",
                        width="100%",
                    ),
                    rx.el.section(
                        rx.heading(
                            "Data e horário",
                            class_name="pc-field-label",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.el.label(
                                    "Data",
                                    html_for="appointment-date",
                                    class_name="pc-field-label",
                                ),
                                rx.input(
                                    id="appointment-date",
                                    name="appointment_date",
                                    type="date",
                                    value=AuthState.appointment_form_date,
                                    on_change=AuthState.set_appointment_form_date,
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
                                    "Horário disponível",
                                    html_for="appointment-time",
                                    class_name="pc-field-label",
                                ),
                                _appointment_select(
                                    AuthState.appointment_form_time_options,
                                    AuthState.appointment_form_time_value,
                                    AuthState.set_appointment_form_time,
                                    "Horário disponível",
                                    "pc-input",
                                    element_id="appointment-time",
                                    disabled=(
                                        AuthState.appointment_form_time_options.length()
                                        <= 1
                                    ),
                                ),
                                rx.cond(
                                    AuthState.appointment_loading,
                                    rx.text(
                                        "Consultando horários disponíveis...",
                                        role="status",
                                        class_name="pc-catalog-description",
                                    ),
                                    rx.cond(
                                        (AuthState.appointment_form_professional_id == 0)
                                        | (
                                            AuthState.appointment_form_service_ids.length()
                                            == 0
                                        ),
                                        rx.text(
                                            "Selecione funcionário e serviço para consultar os horários.",
                                            class_name="pc-catalog-description",
                                        ),
                                        rx.cond(
                                            (AuthState.appointment_form_time_options.length()
                                            <= 1)
                                            & (AuthState.appointment_error_message == ""),
                                            rx.text(
                                                "Não há horários disponíveis para essa seleção.",
                                                class_name="pc-catalog-description",
                                            ),
                                            rx.fragment(),
                                        ),
                                    ),
                                ),
                                class_name="pc-field",
                                align="stretch",
                                spacing="2",
                                width="100%",
                            ),
                            class_name="pc-appointment-form-row",
                            width="100%",
                            spacing="4",
                        ),
                        class_name="pc-appointment-form-section",
                    ),
                    rx.vstack(
                        rx.el.label(
                            "Observações",
                            html_for="appointment-notes",
                            class_name="pc-field-label",
                        ),
                        rx.text_area(
                            id="appointment-notes",
                            name="notes",
                            value=AuthState.appointment_form_notes,
                            on_change=AuthState.set_appointment_form_notes,
                            max_length=1000,
                            placeholder="Informações úteis para o atendimento",
                            class_name="pc-input",
                            width="100%",
                        ),
                        class_name="pc-field",
                        align="stretch",
                        spacing="2",
                        width="100%",
                    ),
                    rx.cond(
                        AuthState.appointment_form_error != "",
                        rx.text(
                            AuthState.appointment_form_error,
                            role="alert",
                            class_name="pc-service-error-text",
                        ),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancelar",
                            type="button",
                            on_click=AuthState.cancel_appointment_form,
                            class_name="pc-button pc-button-secondary",
                        ),
                        rx.button(
                            rx.cond(
                                AuthState.appointment_form_submitting,
                                "Confirmando...",
                                "Confirmar Agendamento",
                            ),
                            type="submit",
                            disabled=(
                                AuthState.appointment_form_submitting
                                | (AuthState.appointment_form_contact_id == 0)
                                | (AuthState.appointment_form_professional_id == 0)
                                | (AuthState.appointment_form_service_ids.length() == 0)
                                | (AuthState.appointment_form_date == "")
                                | (AuthState.appointment_form_time == "")
                            ),
                            class_name="pc-button pc-button-primary",
                        ),
                        class_name="pc-service-form-actions",
                        spacing="3",
                    ),
                    align="stretch",
                    spacing="4",
                    width="100%",
                ),
                on_submit=AuthState.save_appointment,
                reset_on_submit=False,
                width="100%",
                class_name="pc-form",
            ),
            align="stretch",
            spacing="4",
            width="100%",
        ),
        class_name="pc-service-form-panel pc-appointment-form-panel",
        width="100%",
    )


def appointment_page() -> rx.Component:
    content = rx.vstack(
        rx.box(
            rx.vstack(
                rx.text("GESTÃO DA BARBEARIA", class_name="pc-eyebrow"),
                rx.heading(
                    rx.cond(
                        AuthState.appointment_view == "list",
                        "Agendamentos",
                        rx.cond(
                            AuthState.appointment_view == "form",
                            rx.cond(
                                AuthState.appointment_editing_id > 0,
                                "Editar Agendamento",
                                "Novo Agendamento",
                            ),
                            rx.cond(
                                AuthState.appointment_view == "success",
                                "Agendamento confirmado",
                                "Agendamento",
                            ),
                        ),
                    ),
                    class_name="pc-page-title",
                ),
                rx.text(
                    "Consulte horários, organize a equipe e acompanhe os atendimentos.",
                    class_name="pc-page-description",
                ),
                align="start",
                spacing="2",
            ),
            rx.hstack(
                rx.cond(
                    (AuthState.appointment_view == "calendar")
                    | (AuthState.appointment_view == "list"),
                    rx.fragment(
                        rx.button(
                            "Calendário",
                            type="button",
                            on_click=AuthState.show_appointment_calendar,
                            class_name=rx.cond(
                                AuthState.appointment_view == "calendar",
                                "pc-button pc-button-secondary pc-view-toggle pc-view-toggle-active",
                                "pc-button pc-button-secondary pc-view-toggle",
                            ),
                        ),
                        rx.button(
                            "Agendamentos",
                            type="button",
                            on_click=AuthState.show_appointment_list,
                            class_name=rx.cond(
                                AuthState.appointment_view == "list",
                                "pc-button pc-button-secondary pc-view-toggle pc-view-toggle-active",
                                "pc-button pc-button-secondary pc-view-toggle",
                            ),
                        ),
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    "+ Novo agendamento",
                    type="button",
                    on_click=AuthState.start_new_appointment,
                    disabled=AuthState.appointment_options_loading,
                    class_name="pc-button pc-button-primary",
                ),
                class_name="pc-appointment-header-actions",
                align="center",
            ),
            class_name="pc-catalog-header",
        ),
        rx.cond(
            AuthState.appointment_success_message != "",
            rx.text(
                AuthState.appointment_success_message,
                role="status",
                class_name="pc-service-success",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.appointment_error_message != "",
            rx.hstack(
                rx.text(
                    AuthState.appointment_error_message,
                    role="alert",
                    class_name="pc-service-error-text",
                ),
                rx.button(
                    "Tentar novamente",
                    type="button",
                    on_click=AuthState.refresh_appointments,
                    class_name="pc-service-action pc-service-edit",
                ),
                class_name="pc-service-error",
                align="center",
                justify="between",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.appointment_view == "form",
            _appointment_form(),
            rx.cond(
                AuthState.appointment_view == "success",
                _appointment_success_view(),
                rx.cond(
                    AuthState.appointment_view == "list",
                    _appointment_list_view(),
                    _appointment_calendar_view(),
                ),
            ),
        ),
        rx.cond(
            AuthState.appointment_quick_contact_open,
            _appointment_quick_contact_form(),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.appointment_block_form_open,
            _appointment_block_form(),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.has_appointment_detail,
            _appointment_detail_modal(),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.appointment_cancel_confirm_id > 0,
            _appointment_cancel_confirmation(),
            rx.fragment(),
        ),
        width="100%",
        align="stretch",
        spacing="4",
        class_name="pc-team-content pc-appointment-content",
    )
    return _app_shell(content, "/appointments")


def _profile_editor() -> rx.Component:
    profile_form = rx.form(
        rx.vstack(
            rx.vstack(
                rx.el.label(
                    "Nome completo",
                    html_for="profile-name",
                    class_name="pc-field-label",
                ),
                rx.input(
                    id="profile-name",
                    name="name",
                    value=AuthState.profile_name,
                    on_change=AuthState.set_profile_name,
                    required=True,
                    max_length=120,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.el.label(
                    "E-mail",
                    html_for="profile-email",
                    class_name="pc-field-label",
                ),
                rx.input(
                    id="profile-email",
                    name="email",
                    type="email",
                    value=AuthState.profile_email,
                    on_change=AuthState.set_profile_email,
                    required=True,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.el.label(
                    "Telefone",
                    html_for="profile-phone",
                    class_name="pc-field-label",
                ),
                rx.input(
                    id="profile-phone",
                    name="phone",
                    type="tel",
                    value=AuthState.profile_phone,
                    on_change=AuthState.set_profile_phone,
                    on_blur=AuthState.format_profile_phone,
                    required=True,
                    max_length=20,
                    class_name="pc-input",
                    width="100%",
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.cond(
                AuthState.profile_form_error != "",
                rx.text(
                    AuthState.profile_form_error,
                    role="alert",
                    class_name="pc-service-error-text",
                ),
                rx.fragment(),
            ),
            rx.cond(
                AuthState.profile_form_success_message != "",
                rx.text(
                    AuthState.profile_form_success_message,
                    role="status",
                    class_name="pc-service-success",
                ),
                rx.fragment(),
            ),
            rx.button(
                rx.cond(
                    AuthState.profile_is_submitting,
                    "Salvando...",
                    "Salvar alterações",
                ),
                type="submit",
                disabled=AuthState.profile_is_submitting,
                class_name="pc-button pc-button-primary",
            ),
            align="stretch",
            spacing="5",
            width="100%",
        ),
        on_submit=AuthState.save_profile,
        reset_on_submit=False,
        width="100%",
        class_name="pc-form pc-profile-form",
        id="profile-form",
    )

    password_form = rx.form(
        rx.vstack(
            rx.vstack(
                rx.el.label(
                    "Senha atual",
                    html_for="profile-current-password",
                    class_name="pc-field-label",
                ),
                _password_input(
                    "profile-current-password",
                    "current_password",
                    "profile_current",
                    AuthState.profile_current_password_visible,
                    invalid=AuthState.profile_current_password_error != "",
                    required=False,
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.el.label(
                    "Nova senha",
                    html_for="profile-new-password",
                    class_name="pc-field-label",
                ),
                _password_input(
                    "profile-new-password",
                    "new_password",
                    "profile_new",
                    AuthState.profile_new_password_visible,
                    invalid=AuthState.profile_new_password_error != "",
                    required=False,
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.el.label(
                    "Confirmar nova senha",
                    html_for="profile-confirm-password",
                    class_name="pc-field-label",
                ),
                _password_input(
                    "profile-confirm-password",
                    "confirm_password",
                    "profile_confirmation",
                    AuthState.profile_confirmation_visible,
                    invalid=AuthState.profile_confirmation_error != "",
                    required=False,
                ),
                class_name="pc-field",
                align="stretch",
                spacing="3",
                width="100%",
            ),
            rx.cond(
                AuthState.profile_password_error != "",
                rx.text(
                    AuthState.profile_password_error,
                    role="alert",
                    class_name="pc-service-error-text",
                ),
                rx.fragment(),
            ),
            rx.button(
                rx.cond(
                    AuthState.profile_password_submitting,
                    "Atualizando...",
                    "Alterar senha",
                ),
                type="submit",
                disabled=AuthState.profile_password_submitting,
                class_name="pc-button pc-button-primary",
            ),
            align="stretch",
            spacing="5",
            width="100%",
        ),
        on_submit=AuthState.change_profile_password,
        reset_on_submit=False,
        width="100%",
        class_name="pc-form pc-profile-password-form",
        id="profile-password-form",
    )

    content = rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("SUA CONTA", class_name="pc-eyebrow"),
                rx.dialog.title("Meu perfil", class_name="pc-page-title"),
                rx.text(
                    "Atualize seus dados pessoais e as informações de acesso.",
                    class_name="pc-page-description",
                ),
                align="start",
                spacing="2",
            ),
            rx.dialog.close(
                rx.button(
                    rx.icon("x", size=18, aria_hidden="true"),
                    type="button",
                    aria_label="Fechar edição do perfil",
                    class_name="pc-icon-action",
                ),
            ),
            align="start",
            justify="between",
            width="100%",
        ),
        rx.cond(
            AuthState.profile_error_message != "",
            rx.text(
                AuthState.profile_error_message,
                role="alert",
                class_name="pc-service-error-text",
            ),
            rx.fragment(),
        ),
        rx.el.section(
            rx.vstack(
                rx.cond(
                    AuthState.profile_photo_success_message != "",
                    rx.text(
                        AuthState.profile_photo_success_message,
                        role="status",
                        class_name="pc-service-success",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.cond(
                        AuthState.profile_photo_url != "",
                        rx.image(
                            src=AuthState.profile_photo_url,
                            alt="Foto de perfil",
                            class_name="pc-profile-avatar",
                            width="84px",
                            height="84px",
                            max_width="84px",
                            min_width="84px",
                            object_fit="cover",
                        ),
                        rx.icon(
                            "circle-user-round",
                            size=68,
                            stroke_width=1.3,
                            aria_hidden="true",
                            class_name="pc-profile-avatar-placeholder",
                        ),
                    ),
                    rx.vstack(
                        rx.heading("Foto de perfil", class_name="pc-service-form-title"),
                        rx.text(
                            "JPEG, PNG ou WebP · até 5 MB",
                            class_name="pc-service-form-description",
                        ),
                        rx.upload(
                            rx.button(
                                "Escolher imagem",
                                type="button",
                                class_name="pc-button pc-button-secondary",
                            ),
                            id="profile-photo-upload",
                            max_files=1,
                            accept={
                                "image/jpeg": [".jpg", ".jpeg"],
                                "image/png": [".png"],
                                "image/webp": [".webp"],
                            },
                            class_name="pc-profile-upload",
                        ),
                        rx.foreach(
                            rx.selected_files("profile-photo-upload"),
                            lambda filename: rx.text(
                                filename,
                                class_name="pc-profile-selected-file",
                            ),
                        ),
                        rx.hstack(
                            rx.button(
                                "Enviar foto",
                                type="button",
                                on_click=AuthState.upload_profile_photo(
                                    rx.upload_files("profile-photo-upload")
                                ),
                                disabled=AuthState.profile_is_submitting
                                | (rx.selected_files("profile-photo-upload").length() == 0),
                                class_name="pc-button pc-button-primary",
                            ),
                            rx.cond(
                                AuthState.profile_photo_url != "",
                                rx.button(
                                    "Remover foto",
                                    type="button",
                                    on_click=AuthState.remove_profile_photo,
                                    disabled=AuthState.profile_is_submitting,
                                    class_name="pc-button pc-button-secondary",
                                ),
                                rx.fragment(),
                            ),
                            class_name="pc-service-form-actions",
                            spacing="3",
                        ),
                        align="start",
                        spacing="5",
                    ),
                    align="center",
                    class_name="pc-profile-photo-panel",
                    width="100%",
                ),
                width="100%",
                align="stretch",
                spacing="5",
            ),
            class_name="pc-service-catalog-panel pc-profile-section",
        ),
        rx.el.section(
            rx.vstack(
                rx.heading("Dados pessoais", class_name="pc-service-form-title"),
                rx.text(
                    "Essas informações identificam seu acesso na equipe.",
                    class_name="pc-service-form-description",
                ),
                profile_form,
                align="stretch",
                spacing="5",
                width="100%",
            ),
            class_name="pc-form-panel pc-profile-section",
        ),
        rx.el.section(
            rx.vstack(
                rx.heading("Segurança", class_name="pc-service-form-title"),
                rx.text(
                    "Para alterar a senha, informe primeiro a senha atual.",
                    class_name="pc-service-form-description",
                ),
                rx.cond(
                    AuthState.profile_password_success != "",
                    rx.text(
                        AuthState.profile_password_success,
                        role="status",
                        class_name="pc-service-success",
                    ),
                    rx.fragment(),
                ),
                password_form,
                align="stretch",
                spacing="5",
                width="100%",
            ),
            class_name="pc-form-panel pc-profile-section",
        ),
        width="100%",
        align="stretch",
        spacing="5",
        class_name="pc-team-content pc-profile-content",
    )
    return rx.dialog.root(
        rx.dialog.content(
            content,
            class_name="pc-appointment-modal pc-profile-dialog",
        ),
        open=AuthState.profile_editor_open,
        on_open_change=AuthState.set_profile_editor_open,
    )


def register_pages(app: rx.App):
    from frontend.finance_page import finance_page

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
        on_load=AuthState.require_overview_access,
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
        appointment_page,
        route="/appointments",
        title="Agenda | Lotus Barber",
        on_load=AuthState.require_appointment_access,
    )
    app.add_page(
        finance_page,
        route="/financeiro",
        title="Financeiro | Lotus Barber",
        on_load=AuthState.require_finance_access,
    )
    app.add_page(
        login_page,
        route="/",
        title="Entrar | Lotus Barber",
        on_load=AuthState.clear_menu_success_messages,
    )
