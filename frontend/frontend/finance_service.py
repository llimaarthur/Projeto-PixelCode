from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo


BARBERSHOP_TIMEZONE = ZoneInfo("America/Sao_Paulo")
CHART_WIDTH = 760
CHART_HEIGHT = 280
CHART_LEFT = 76
CHART_RIGHT = 742
CHART_TOP = 22
CHART_BOTTOM = 232


class FinanceDataError(ValueError):
    """Raised when the financial provider returns an invalid dashboard."""


def should_use_finance_mock(
    configured_value: str,
    is_production: bool,
    api_configured: bool = False,
) -> bool:
    return (
        configured_value.strip().lower() == "true"
        and not is_production
        and not api_configured
    )


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise FinanceDataError(f"O valor de {label} é inválido.") from error
    if not result.is_finite():
        raise FinanceDataError(f"O valor de {label} é inválido.")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _finance_datetime(value: Any, label: str) -> datetime:
    if isinstance(value, bool):
        raise FinanceDataError(f"A data de {label} é inválida.")
    if isinstance(value, (int, float)):
        try:
            timestamp = float(value)
            if abs(timestamp) >= 100_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, BARBERSHOP_TIMEZONE)
        except (OverflowError, OSError, ValueError) as error:
            raise FinanceDataError(f"A data de {label} é inválida.") from error
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise FinanceDataError(f"A data de {label} é inválida.") from error
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=BARBERSHOP_TIMEZONE)
        return parsed.astimezone(BARBERSHOP_TIMEZONE)
    raise FinanceDataError(f"A data de {label} é inválida.")


def format_brl(value: Any) -> str:
    amount = _decimal(value, "moeda")
    formatted = f"{abs(amount):,.2f}".replace(",", "\0").replace(".", ",").replace(
        "\0", "."
    )
    return ("−" if amount < 0 else "") + "R$ " + formatted


def percentage_change(current: Any, previous: Any) -> Decimal | None:
    current_amount = _decimal(current, "valor atual")
    previous_amount = _decimal(previous, "valor anterior")
    if previous_amount <= 0:
        return None
    return (
        (current_amount - previous_amount)
        / previous_amount
        * Decimal("100")
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def finance_dashboard_from_transactions(
    payload: Any, now: datetime | None = None
) -> dict[str, Any]:
    if isinstance(payload, dict):
        payload = payload.get("transactions")
    transactions = _require_list(payload, "movimentações")
    reference = now or datetime.now(BARBERSHOP_TIMEZONE)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=BARBERSHOP_TIMEZONE)
    else:
        reference = reference.astimezone(BARBERSHOP_TIMEZONE)

    normalized_transactions: list[dict[str, Any]] = []
    for item in transactions:
        if not isinstance(item, dict):
            raise FinanceDataError("Uma movimentação financeira é inválida.")
        kind = str(item.get("type", ""))
        if kind not in {"income", "expense"}:
            raise FinanceDataError("O tipo de uma movimentação financeira é inválido.")
        status = str(item.get("status", "active"))
        if status not in {"active", "cancelled"}:
            raise FinanceDataError("O status de uma movimentação financeira é inválido.")
        raw_id = item.get("id")
        try:
            transaction_id = int(raw_id) if raw_id not in (None, "") else 0
        except (TypeError, ValueError) as error:
            raise FinanceDataError(
                "O identificador de uma movimentação é inválido."
            ) from error
        try:
            creator_id = int(item.get("created_by") or 0)
            contact_id = int(item.get("contact_id") or 0)
            appointment_id = int(item.get("appointment_id") or 0)
        except (TypeError, ValueError) as error:
            raise FinanceDataError(
                "Uma referência da movimentação financeira é inválida."
            ) from error
        occurred = _finance_datetime(item.get("occurred_at"), "uma movimentação financeira")
        amount = _decimal(item.get("amount"), "movimentação")
        if amount <= 0:
            raise FinanceDataError("O valor de uma movimentação deve ser positivo.")
        raw_services = item.get("services_snapshot") or []
        if not isinstance(raw_services, list) or not all(
            isinstance(service, dict) for service in raw_services
        ):
            raise FinanceDataError("A lista de serviços da movimentação é inválida.")
        service_names = [
            str(service.get("name") or "").strip()
            for service in raw_services
            if str(service.get("name") or "").strip()
        ]
        contact_name = str(item.get("contact_name_snapshot") or "").strip()
        detail_parts = [str(item.get("detail") or "").strip()]
        cancellation_reason = str(item.get("cancellation_reason") or "").strip()
        if status == "cancelled" and cancellation_reason:
            detail_parts.append(f"Estorno: {cancellation_reason}")
        normalized_transactions.append(
            {
                "id": transaction_id,
                "created_by": creator_id,
                "contact_id": contact_id,
                "appointment_id": appointment_id,
                "type": kind,
                "title": str(item.get("title", "")),
                "detail": " · ".join(part for part in detail_parts if part),
                "amount": float(amount),
                "occurred_at": occurred.isoformat(),
                "status": status,
                "cancellation_reason": cancellation_reason,
                "contact_name_snapshot": contact_name,
                "services_snapshot": raw_services,
                "service_summary": ", ".join(service_names),
                "can_cancel": False,
            }
        )

    normalized_transactions.sort(
        key=lambda item: datetime.fromisoformat(item["occurred_at"]),
        reverse=True,
    )
    if not normalized_transactions:
        return {
            "kpis": [],
            "cashflow": {"6m": [], "12m": [], "year": []},
            "summary": {},
            "transactions": [],
            "errors": {},
        }

    active_transactions = [
        item for item in normalized_transactions if item["status"] == "active"
    ]
    today = reference.date()
    current_month_start = today.replace(day=1)
    current_month_end = today + timedelta(days=1)

    def total(
        start: date,
        end: date,
        kind: str = "income",
    ) -> Decimal:
        return sum(
            (
                _decimal(item["amount"], "movimentação")
                for item in active_transactions
                if item["type"] == kind
                and start <= datetime.fromisoformat(item["occurred_at"]).date() < end
            ),
            Decimal("0"),
        )

    yesterday_start = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    previous_week_start = week_start - timedelta(days=7)
    previous_week_end = previous_week_start + timedelta(days=(today - week_start).days + 1)
    previous_month_start = (
        date(today.year - 1, 12, 1)
        if today.month == 1
        else date(today.year, today.month - 1, 1)
    )
    previous_month_end = previous_month_start.replace(
        day=min(today.day, calendar.monthrange(
            previous_month_start.year, previous_month_start.month
        )[1])
    ) + timedelta(days=1)

    def kpi(
        identifier: str,
        label: str,
        accent: str,
        start: date,
        end: date,
        previous_start: date,
        previous_end: date,
        comparison: str,
    ) -> dict[str, Any]:
        sparkline = [
            float(total(today - timedelta(days=offset), today - timedelta(days=offset - 1)))
            for offset in range(6, -1, -1)
        ]
        return {
            "id": identifier,
            "label": label,
            "current": float(total(start, end)),
            "previous": float(total(previous_start, previous_end)),
            "comparison": comparison,
            "accent": accent,
            "sparkline": sparkline,
        }

    kpis = [
        kpi(
            "today",
            "Recebido Hoje",
            "blue",
            today,
            current_month_end,
            yesterday_start,
            today,
            "em relação a ontem",
        ),
        kpi(
            "week",
            "Recebido na Semana",
            "purple",
            week_start,
            current_month_end,
            previous_week_start,
            previous_week_end,
            "em relação à semana passada",
        ),
        kpi(
            "month",
            "Recebido no Mês",
            "green",
            current_month_start,
            current_month_end,
            previous_month_start,
            previous_month_end,
            "em relação ao mês anterior",
        ),
    ]

    def month_start(offset: int) -> date:
        absolute_month = today.year * 12 + today.month - 1 + offset
        year, month_index = divmod(absolute_month, 12)
        return date(year, month_index + 1, 1)

    def cashflow(months: list[date]) -> list[dict[str, Any]]:
        period_end = (
            date(months[-1].year + 1, 1, 1)
            if months[-1].month == 12
            else date(months[-1].year, months[-1].month + 1, 1)
        )
        if not any(
            months[0] <= datetime.fromisoformat(item["occurred_at"]).date() < period_end
            for item in active_transactions
        ):
            return []

        rows = []
        for month in months:
            end = (
                date(month.year + 1, 1, 1)
                if month.month == 12
                else date(month.year, month.month + 1, 1)
            )
            rows.append(
                {
                    "month": (
                        f"{('Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez')[month.month - 1]}"
                        f"/{month.year % 100:02d}"
                    ),
                    "inflows": float(total(month, end, "income")),
                    "outflows": float(total(month, end, "expense")),
                }
            )
        return rows

    all_time_balance = sum(
        (
            _decimal(item["amount"], "movimentação")
            * (1 if item["type"] == "income" else -1)
            for item in active_transactions
        ),
        Decimal("0"),
    )
    summary = {
        "inflows": float(total(current_month_start, current_month_end, "income")),
        "outflows": float(total(current_month_start, current_month_end, "expense")),
        "current_balance": float(all_time_balance),
    }

    return normalize_finance_dashboard(
        {
            "kpis": kpis,
            "cashflow": {
                "6m": cashflow([month_start(offset) for offset in range(-5, 1)]),
                "12m": cashflow([month_start(offset) for offset in range(-11, 1)]),
                "year": cashflow(
                    [date(today.year, month, 1) for month in range(1, today.month + 1)]
                ),
            },
            "summary": summary,
            "transactions": normalized_transactions,
        },
        reference,
    )


def mock_finance_dashboard(now: datetime | None = None) -> dict[str, Any]:
    reference = now or datetime.now(BARBERSHOP_TIMEZONE)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=BARBERSHOP_TIMEZONE)
    else:
        reference = reference.astimezone(BARBERSHOP_TIMEZONE)
    today = reference.date().isoformat()
    months = ("Mai", "Jun", "Jul", "Ago", "Set", "Out")
    six_months = (
        (10000, 5000),
        (14000, 8200),
        (11500, 6500),
        (10500, 5700),
        (14500, 7600),
        (18720, 9450),
    )
    year_months = (
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez",
    )
    yearly_inflows = (9200, 9800, 11400, 10800, 10000, 14000, 11500, 10500, 14500, 18720, 0, 0)
    yearly_outflows = (5100, 5400, 5900, 5600, 5000, 8200, 6500, 5700, 7600, 9450, 0, 0)

    return {
        "as_of": today,
        "kpis": [
            {
                "id": "today",
                "label": "Recebido Hoje",
                "current": 1245.00,
                "previous": 1111.61,
                "comparison": "em relação a ontem",
                "icon": "calendar-days",
                "accent": "blue",
                "sparkline": [24, 31, 29, 47, 39, 43, 55],
            },
            {
                "id": "week",
                "label": "Recebido na Semana",
                "current": 5860.00,
                "previous": 5425.93,
                "comparison": "em relação à semana passada",
                "icon": "calendar-days",
                "accent": "purple",
                "sparkline": [20, 26, 22, 38, 34, 43, 51],
            },
            {
                "id": "month",
                "label": "Recebido no Mês",
                "current": 18720.00,
                "previous": 16278.26,
                "comparison": "em relação ao mês anterior",
                "icon": "calendar-days",
                "accent": "green",
                "sparkline": [28, 25, 33, 40, 37, 46, 54],
            },
        ],
        "cashflow": {
            "6m": [
                {"month": month, "inflows": inflows, "outflows": outflows}
                for month, (inflows, outflows) in zip(months, six_months)
            ],
            "12m": [
                {"month": month, "inflows": inflows, "outflows": outflows}
                for month, inflows, outflows in zip(
                    year_months, yearly_inflows, yearly_outflows
                )
            ],
            "year": [
                {"month": month, "inflows": yearly_inflows[index], "outflows": yearly_outflows[index]}
                for index, month in enumerate(year_months[: reference.month])
            ],
        },
        "summary": {
            "inflows": 18720.00,
            "outflows": 9450.00,
            "current_balance": 9270.00,
        },
        "transactions": [
            {
                "type": "income",
                "title": "Pagamento de Serviço",
                "detail": "Cliente: João Silva",
                "amount": 120.00,
                "occurred_at": f"{today}T16:20:00-03:00",
            },
            {
                "type": "expense",
                "title": "Pagamento de Fornecedor",
                "detail": "Produtos",
                "amount": 450.00,
                "occurred_at": f"{today}T14:32:00-03:00",
            },
            {
                "type": "income",
                "title": "Serviço Realizado",
                "detail": "Cliente: Lucas Souza",
                "amount": 100.00,
                "occurred_at": f"{today}T13:10:00-03:00",
            },
        ],
    }


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise FinanceDataError(f"A lista de {label} retornada pela API é inválida.")
    return value


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FinanceDataError(f"O bloco {label} retornado pela API é inválido.")
    if value.get("error"):
        raise FinanceDataError(str(value["error"]))
    return value


def _normalize_finance_dashboard_complete(
    payload: Any, now: datetime | None = None
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FinanceDataError("A resposta financeira retornada pela API é inválida.")

    kpis = _require_list(payload.get("kpis"), "indicadores")
    normalized_kpis: list[dict[str, Any]] = []
    for item in kpis:
        if not isinstance(item, dict):
            raise FinanceDataError("Um indicador financeiro retornado pela API é inválido.")
        current = _decimal(item.get("current"), "indicador")
        previous_value = item.get("previous")
        previous = (
            _decimal(previous_value, "comparativo")
            if previous_value is not None
            else None
        )
        change = (
            percentage_change(current, previous)
            if previous is not None and previous > 0
            else None
        )
        normalized_kpis.append(
            {
                "id": str(item.get("id", "")),
                "label": str(item.get("label", "")),
                "current": float(current),
                "variation": (
                    f"{'+' if change is not None and change > 0 else ''}{change}%"
                    if change is not None
                    else "Sem comparação"
                ),
                "trend": (
                    "positive"
                    if change is not None and change > 0
                    else "negative"
                    if change is not None and change < 0
                    else "neutral"
                ),
                "comparison": str(item.get("comparison", "")),
                "icon": str(item.get("icon") or "calendar-days"),
                "accent": str(item.get("accent") or "blue"),
                "sparkline": [
                    float(_decimal(point, "sparkline"))
                    for point in _require_list(item.get("sparkline", []), "sparkline")
                ],
            }
        )
        values = normalized_kpis[-1]["sparkline"]
        if values:
            low, high = min(values), max(values)
            span = max(high - low, 1)
            coordinates = [
                (round(index * 100 / max(len(values) - 1, 1), 1),
                 round(42 - (value - low) / span * 34, 1))
                for index, value in enumerate(values)
            ]
            path = _smooth_path(coordinates)
            normalized_kpis[-1]["sparkline_path"] = path
            normalized_kpis[-1]["sparkline_area"] = (
                f"{path} L 100 48 L 0 48 Z"
            )

    cashflow = _require_object(payload.get("cashflow"), "fluxo de caixa")
    normalized_cashflow: dict[str, list[dict[str, Any]]] = {}
    for period in ("6m", "12m", "year"):
        points = _require_list(cashflow.get(period), f"fluxo de caixa {period}")
        normalized_cashflow[period] = []
        for item in points:
            if not isinstance(item, dict):
                raise FinanceDataError("Um ponto do fluxo de caixa é inválido.")
            normalized_cashflow[period].append(
                {
                    "month": str(item.get("month", "")),
                    "inflows": float(_decimal(item.get("inflows"), "entrada")),
                    "outflows": float(_decimal(item.get("outflows"), "saída")),
                }
            )

    summary = _require_object(payload.get("summary"), "resumo do mês")
    inflows = _decimal(summary.get("inflows"), "entradas do mês")
    outflows = _decimal(summary.get("outflows"), "saídas do mês")
    normalized_summary = {
        "inflows": float(inflows),
        "outflows": float(outflows),
        "net_profit": float(inflows - outflows),
        "current_balance": float(
            _decimal(summary.get("current_balance"), "saldo atual")
        ),
    }
    circumference = 339.292
    total = inflows + outflows
    inflow_share = float(inflows / total) if total > 0 else 0
    outflow_share = float(outflows / total) if total > 0 else 0
    normalized_summary["donut_inflow_dasharray"] = (
        f"{circumference * inflow_share:.2f} {circumference:.2f}"
    )
    normalized_summary["donut_outflow_dasharray"] = (
        f"{circumference * outflow_share:.2f} {circumference:.2f}"
    )
    normalized_summary["donut_outflow_dashoffset"] = (
        f"{-circumference * inflow_share:.2f}"
    )

    now_local = now or datetime.now(BARBERSHOP_TIMEZONE)
    if now_local.tzinfo is None:
        now_local = now_local.replace(tzinfo=BARBERSHOP_TIMEZONE)
    else:
        now_local = now_local.astimezone(BARBERSHOP_TIMEZONE)
    transactions = _require_list(payload.get("transactions"), "movimentações")
    normalized_transactions: list[dict[str, Any]] = []
    for item in transactions:
        if not isinstance(item, dict):
            raise FinanceDataError("Uma movimentação financeira é inválida.")
        kind = str(item.get("type", ""))
        if kind not in {"income", "expense"}:
            raise FinanceDataError("O tipo de uma movimentação financeira é inválido.")
        occurred = _finance_datetime(item.get("occurred_at"), "uma movimentação financeira")
        relative_date = (
            f"Hoje, {occurred:%H:%M}"
            if occurred.date() == now_local.date()
            else occurred.strftime("%d/%m/%Y, %H:%M")
        )
        amount = abs(_decimal(item.get("amount"), "movimentação"))
        raw_id = item.get("id")
        try:
            transaction_id = int(raw_id) if raw_id not in (None, "") else 0
        except (TypeError, ValueError) as error:
            raise FinanceDataError(
                "O identificador de uma movimentação é inválido."
            ) from error
        try:
            creator_id = int(item.get("created_by") or 0)
            contact_id = int(item.get("contact_id") or 0)
            appointment_id = int(item.get("appointment_id") or 0)
        except (TypeError, ValueError) as error:
            raise FinanceDataError(
                "Uma referência da movimentação financeira é inválida."
            ) from error
        status = str(item.get("status", "active"))
        if status not in {"active", "cancelled"}:
            raise FinanceDataError("O status de uma movimentação financeira é inválido.")
        raw_services = item.get("services_snapshot") or []
        if not isinstance(raw_services, list) or not all(
            isinstance(service, dict) for service in raw_services
        ):
            raise FinanceDataError("A lista de serviços da movimentação é inválida.")
        contact_name = str(item.get("contact_name_snapshot") or "").strip()
        service_names = [
            str(service.get("name") or "").strip()
            for service in raw_services
            if str(service.get("name") or "").strip()
        ]
        detail_parts = [str(item.get("detail") or "").strip()]
        if contact_name:
            detail_parts.append(f"Cliente: {contact_name}")
        if service_names:
            detail_parts.append(f"Serviços: {', '.join(service_names)}")
        cancellation_reason = str(item.get("cancellation_reason") or "")
        if status == "cancelled" and cancellation_reason:
            detail_parts.append(f"Estorno: {cancellation_reason}")
        normalized_transactions.append(
            {
                "id": transaction_id,
                "created_by": creator_id,
                "contact_id": contact_id,
                "appointment_id": appointment_id,
                "type": kind,
                "title": str(item.get("title", "")),
                "detail": " · ".join(part for part in detail_parts if part),
                "amount": float(amount),
                "signed_amount": float(amount if kind == "income" else -amount),
                "date_label": relative_date,
                "input_datetime": occurred.strftime("%Y-%m-%dT%H:%M"),
                "status": status,
                "is_cancelled": status == "cancelled",
                "contact_name_snapshot": contact_name,
                "services_snapshot": raw_services,
                "service_summary": ", ".join(service_names),
                "cancellation_reason": cancellation_reason,
                "can_manage": transaction_id > 0
                and status == "active",
                "can_cancel": False,
                "icon": "arrow-up-right" if kind == "income" else "arrow-down-right",
            }
        )

    return {
        "kpis": normalized_kpis,
        "cashflow": normalized_cashflow,
        "summary": normalized_summary,
        "transactions": normalized_transactions,
    }


def normalize_finance_dashboard(
    payload: Any, now: datetime | None = None
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FinanceDataError("A resposta financeira retornada pela API é inválida.")

    empty_dashboard = {
        "kpis": [],
        "cashflow": {"6m": [], "12m": [], "year": []},
        "summary": {"inflows": 0, "outflows": 0, "current_balance": 0},
        "transactions": [],
    }
    dashboard: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for block in ("kpis", "cashflow", "summary", "transactions"):
        if block not in payload:
            if block == "summary":
                dashboard[block] = {}
            else:
                errors[block] = f"A API não retornou o bloco {block}."
                dashboard[block] = empty_dashboard[block]
            continue

        value = payload[block]
        if isinstance(value, dict) and value.get("error"):
            errors[block] = str(value["error"])
            dashboard[block] = empty_dashboard[block]
            continue
        if block == "summary" and value in (None, {}):
            dashboard[block] = {}
            continue

        candidate = {**empty_dashboard, block: value}
        try:
            normalized = _normalize_finance_dashboard_complete(candidate, now)
        except FinanceDataError as error:
            errors[block] = str(error)
            dashboard[block] = empty_dashboard[block]
        else:
            dashboard[block] = normalized[block]

    provider_errors = payload.get("errors")
    if isinstance(provider_errors, dict):
        for block in dashboard:
            if provider_errors.get(block):
                errors[block] = str(provider_errors[block])
                dashboard[block] = empty_dashboard[block]

    dashboard["errors"] = errors
    return dashboard


def _smooth_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    path = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for index in range(1, len(points)):
        previous_x, previous_y = points[index - 1]
        current_x, current_y = points[index]
        middle_x = (previous_x + current_x) / 2
        path += (
            f" C {middle_x:.1f} {previous_y:.1f},"
            f" {middle_x:.1f} {current_y:.1f},"
            f" {current_x:.1f} {current_y:.1f}"
        )
    return path


def prepare_cashflow_chart(
    rows: list[dict[str, Any]], active_index: int = -1
) -> dict[str, Any]:
    if not rows:
        return {"points": [], "inflow_path": "", "outflow_path": "", "inflow_area": "", "outflow_area": "", "y_ticks": []}

    maximum = max(
        Decimal("0"),
        *(
            _decimal(row[key], key)
            for row in rows
            for key in ("inflows", "outflows")
        ),
    )
    if maximum == 0:
        axis_maximum = Decimal("1")
    else:
        rough_step = maximum / Decimal("5")
        step_magnitude = Decimal(10) ** rough_step.adjusted()
        normalized_step = rough_step / step_magnitude
        step_multiplier = (
            Decimal("1")
            if normalized_step <= 1
            else Decimal("2")
            if normalized_step <= 2
            else Decimal("5")
            if normalized_step <= 5
            else Decimal("10")
        )
        step = step_multiplier * step_magnitude
        axis_maximum = (
            (maximum / step).to_integral_value(rounding=ROUND_CEILING) * step
        )
    x_span = CHART_RIGHT - CHART_LEFT
    y_span = CHART_BOTTOM - CHART_TOP
    points = []
    inflow_coordinates = []
    outflow_coordinates = []
    for index, row in enumerate(rows):
        x = (
            CHART_LEFT + x_span * index / (len(rows) - 1)
            if len(rows) > 1
            else CHART_LEFT + x_span / 2
        )
        inflows = _decimal(row["inflows"], "entradas")
        outflows = _decimal(row["outflows"], "saídas")
        inflow_y = CHART_BOTTOM - float(inflows / axis_maximum) * y_span
        outflow_y = CHART_BOTTOM - float(outflows / axis_maximum) * y_span
        inflow_coordinates.append((x, inflow_y))
        outflow_coordinates.append((x, outflow_y))
        points.append(
            {
                "index": index,
                "month": str(row["month"]),
                "x": round(x, 1),
                "inflow_y": round(inflow_y, 1),
                "outflow_y": round(outflow_y, 1),
                "inflows": float(inflows),
                "outflows": float(outflows),
                "inflows_label": format_brl(inflows),
                "outflows_label": format_brl(outflows),
                "accessible_label": (
                    f"{row['month']} — Entradas: {format_brl(inflows)} / "
                    f"Saídas: {format_brl(outflows)}"
                ),
            }
        )

    inflow_path = _smooth_path(inflow_coordinates)
    outflow_path = _smooth_path(outflow_coordinates)
    area_baseline = f"{CHART_RIGHT} {CHART_BOTTOM} L {CHART_LEFT} {CHART_BOTTOM} Z"
    inflow_area = f"{inflow_path} L {area_baseline}"
    outflow_area = f"{outflow_path} L {area_baseline}"
    tick_count = 5
    y_ticks = []
    for index in range(tick_count + 1):
        value = axis_maximum * index / tick_count
        compact_value = value / 1000 if value >= 1000 else value
        compact_number = f"{compact_value:,.2f}".replace(",", "\0").replace(
            ".", ","
        ).replace("\0", ".").rstrip("0").rstrip(",")
        y_ticks.append(
            {
                "value": float(value),
                "label": format_brl(value),
                "compact_label": (
                    f"R$ {compact_number}{'k' if value >= 1000 else ''}"
                ),
                "y": round(CHART_BOTTOM - y_span * index / tick_count, 1),
                "label_y": round(CHART_BOTTOM - y_span * index / tick_count + 4, 1),
            }
        )
    return {
        "points": points,
        "inflow_path": inflow_path,
        "outflow_path": outflow_path,
        "inflow_area": inflow_area,
        "outflow_area": outflow_area,
        "y_ticks": y_ticks,
        "active_index": active_index if 0 <= active_index < len(points) else len(points) - 1,
        "axis_maximum": float(axis_maximum),
    }
