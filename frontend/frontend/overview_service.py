from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from frontend.finance_service import (
    BARBERSHOP_TIMEZONE,
    finance_total,
    percentage_change,
    prepare_sparkline,
)


OVERVIEW_PERIODS = {
    "7d": "Últimos 7 dias",
    "30d": "Últimos 30 dias",
    "90d": "Últimos 90 dias",
    "year": "Ano atual",
}


def _local_datetime(value: datetime | None) -> datetime:
    reference = value or datetime.now(BARBERSHOP_TIMEZONE)
    if reference.tzinfo is None:
        return reference.replace(tzinfo=BARBERSHOP_TIMEZONE)
    return reference.astimezone(BARBERSHOP_TIMEZONE)


def _shift_year(value: date, year: int) -> date:
    return value.replace(
        year=year,
        day=min(value.day, calendar.monthrange(year, value.month)[1]),
    )


def _period_windows(
    period: str,
    reference: datetime,
) -> tuple[str, date, date, date, date, list[tuple[date, date]]]:
    if period not in OVERVIEW_PERIODS:
        raise ValueError("O período selecionado para a visão geral é inválido.")

    today = reference.date()
    current_end = today + timedelta(days=1)
    if period == "year":
        current_start = date(today.year, 1, 1)
        previous_start = date(today.year - 1, 1, 1)
        previous_end = _shift_year(today, today.year - 1) + timedelta(days=1)
        buckets = []
        for month in range(1, 13):
            bucket_start = date(today.year, month, 1)
            if month == 12:
                bucket_end = date(today.year + 1, 1, 1)
            else:
                bucket_end = date(today.year, month + 1, 1)
            buckets.append(
                (bucket_start, min(bucket_end, current_end))
                if bucket_start < current_end
                else (bucket_start, bucket_start)
            )
    else:
        days = int(period[:-1])
        current_start = current_end - timedelta(days=days)
        previous_end = current_start
        previous_start = previous_end - timedelta(days=days)
        total_days = (current_end - current_start).days
        buckets = [
            (
                current_start + timedelta(days=total_days * index // 7),
                current_start + timedelta(days=total_days * (index + 1) // 7),
            )
            for index in range(7)
        ]
    return (
        OVERVIEW_PERIODS[period],
        current_start,
        current_end,
        previous_start,
        previous_end,
        buckets,
    )


def _client_count(
    contact_dates: list[str],
    start: date,
    end: date,
) -> int:
    count = 0
    for raw_value in contact_dates:
        try:
            contact_date = date.fromisoformat(str(raw_value)[:10])
        except ValueError as error:
            raise ValueError("A data do primeiro contato de um cliente é inválida.") from error
        if start <= contact_date < end:
            count += 1
    return count


def _metric(
    identifier: str,
    label: str,
    current: Decimal | int,
    previous: Decimal | int,
    series: list[Decimal | int],
    accent: str,
    icon: str,
    value_type: str,
) -> dict[str, Any]:
    change = percentage_change(current, previous)
    return {
        "id": identifier,
        "label": label,
        "current": int(current) if value_type == "count" else float(current),
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
        "comparison": "vs. período anterior",
        "accent": accent,
        "icon": icon,
        "value_type": value_type,
        **prepare_sparkline([float(value) for value in series]),
    }


def overview_metrics(
    transactions: list[dict[str, Any]],
    contact_dates: list[str],
    period: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    transactions = [
        transaction
        if transaction.get("occurred_at")
        else {
            **transaction,
            "occurred_at": transaction.get("input_datetime"),
        }
        for transaction in transactions
    ]
    reference = _local_datetime(now)
    (
        period_label,
        current_start,
        current_end,
        previous_start,
        previous_end,
        buckets,
    ) = _period_windows(period, reference)

    current_income = finance_total(
        transactions, current_start, current_end, "income"
    )
    previous_income = finance_total(
        transactions, previous_start, previous_end, "income"
    )
    current_expense = finance_total(
        transactions, current_start, current_end, "expense"
    )
    previous_expense = finance_total(
        transactions, previous_start, previous_end, "expense"
    )
    current_profit = current_income - current_expense
    previous_profit = previous_income - previous_expense
    current_clients = _client_count(contact_dates, current_start, current_end)
    previous_clients = _client_count(contact_dates, previous_start, previous_end)

    income_series = [
        finance_total(transactions, start, end, "income")
        for start, end in buckets
    ]
    expense_series = [
        finance_total(transactions, start, end, "expense")
        for start, end in buckets
    ]
    profit_series = [
        income - expense
        for income, expense in zip(income_series, expense_series)
    ]
    client_series = [
        _client_count(contact_dates, start, end) for start, end in buckets
    ]

    return {
        "financial": [
            _metric(
                "inflows",
                f"Entradas · {period_label}",
                current_income,
                previous_income,
                income_series,
                "blue",
                "arrow-down-left",
                "currency",
            ),
            _metric(
                "outflows",
                f"Saídas · {period_label}",
                current_expense,
                previous_expense,
                expense_series,
                "purple",
                "arrow-up-right",
                "currency",
            ),
            _metric(
                "net_profit",
                f"Lucro Líquido · {period_label}",
                current_profit,
                previous_profit,
                profit_series,
                "green",
                "chart-no-axes-combined",
                "currency",
            ),
        ],
        "clients": _metric(
            "new_clients",
            f"Novos Clientes · {period_label}",
            current_clients,
            previous_clients,
            client_series,
            "blue",
            "users-round",
            "count",
        ),
    }


def summarize_contacts(
    contacts: list[dict[str, Any]],
    reported_total: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    if reported_total < 0 or len(contacts) != reported_total:
        raise ValueError("A lista de clientes não corresponde ao total informado.")
    active_count = 0
    first_contact_dates = []
    for contact in contacts:
        status = str(contact.get("status", ""))
        if status not in {"active", "inactive"}:
            raise ValueError("O status de um cliente retornado é inválido.")
        active_count += status == "active"
        first_contact = str(contact.get("first_contact_at", ""))[:10]
        try:
            date.fromisoformat(first_contact)
        except ValueError as error:
            raise ValueError("A data do primeiro contato de um cliente é inválida.") from error
        first_contact_dates.append(first_contact)
    active_percentage = (
        int(
            (Decimal(active_count) / Decimal(reported_total) * 100).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        if reported_total
        else 0
    )
    month_start = _local_datetime(now).date().replace(day=1)
    previous_total = sum(
        date.fromisoformat(value) < month_start
        for value in first_contact_dates
    )
    change = percentage_change(reported_total, previous_total)
    return {
        "total": reported_total,
        "active_count": active_count,
        "active_percentage": active_percentage,
        "first_contact_dates": first_contact_dates,
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
    }


def upcoming_appointments(
    appointments: list[dict[str, Any]],
    now: datetime,
    parse_datetime: Callable[[Any], datetime],
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not isinstance(appointments, list):
        raise ValueError("A resposta da agenda não contém uma lista.")
    reference = _local_datetime(now)
    today = reference.date()
    candidates = []
    for item in appointments:
        if not isinstance(item, dict):
            raise ValueError("Um agendamento retornado possui formato inválido.")
        status = str(item.get("status", ""))
        if status not in {"pending", "confirmed", "completed", "cancelled"}:
            raise ValueError("O status de um agendamento retornado é inválido.")
        start = parse_datetime(item.get("start_at"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=BARBERSHOP_TIMEZONE)
        else:
            start = start.astimezone(BARBERSHOP_TIMEZONE)
        if start < reference or status not in {"pending", "confirmed"}:
            continue
        contact = item.get("contact") if isinstance(item.get("contact"), dict) else {}
        name = str(
            item.get("contact_name")
            or item.get("contact_name_snapshot")
            or contact.get("name")
            or "Cliente"
        ).strip()
        snapshots = item.get("services_snapshot", [])
        if not isinstance(snapshots, list):
            raise ValueError("A lista de serviços de um agendamento é inválida.")
        services = [
            str(service.get("name") or "").strip()
            for service in snapshots
            if isinstance(service, dict) and str(service.get("name") or "").strip()
        ]
        words = name.split()
        initials = "".join(word[0] for word in words[:2]).upper() or "C"
        candidates.append(
            {
                "start": start,
                "contact_name": name or "Cliente",
                "initials": initials,
                "service_summary": ", ".join(services) or "Serviço não informado",
            }
        )
    candidates.sort(key=lambda item: item["start"])
    return [
        {
            "contact_name": item["contact_name"],
            "initials": item["initials"],
            "service_summary": item["service_summary"],
            "time_display": item["start"].strftime("%H:%M"),
            "date_display": (
                "Hoje"
                if item["start"].date() == today
                else item["start"].strftime("%d/%m")
            ),
            "date_accessible": item["start"].strftime("%d/%m/%Y"),
        }
        for item in candidates[:limit]
    ]
