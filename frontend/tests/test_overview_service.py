import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from frontend.auth_state import _contacts_page_from_response
from frontend.finance_service import finance_dashboard_from_transactions
from frontend.overview_service import (
    overview_metrics,
    summarize_contacts,
    upcoming_appointments,
)


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


class OverviewServiceTests(unittest.TestCase):
    def test_metrics_accept_transactions_normalized_by_finance_dashboard(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        dashboard = finance_dashboard_from_transactions(
            {
                "transactions": [
                    {
                        "type": "income",
                        "status": "active",
                        "amount": 75,
                        "occurred_at": "2026-03-10T10:00:00-03:00",
                    }
                ]
            },
            now,
        )

        result = overview_metrics(
            dashboard["transactions"],
            [],
            "7d",
            now,
        )

        self.assertEqual(result["financial"][0]["current"], 75.0)

    def test_paginated_contact_response_uses_reported_total(self):
        items = [{"id": index} for index in range(50, 64)]

        page_items, total = _contacts_page_from_response(
            {"data": {"items": items, "itemsTotal": 64}}
        )

        self.assertEqual(page_items, items)
        self.assertEqual(total, 64)

    def test_selected_period_metrics_exclude_cancelled_transactions(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        transactions = [
            {
                "type": "income",
                "status": "active",
                "amount": 100,
                "occurred_at": "2026-03-10T10:00:00-03:00",
            },
            {
                "type": "expense",
                "status": "active",
                "amount": 20,
                "occurred_at": "2026-03-11T10:00:00-03:00",
            },
            {
                "type": "income",
                "status": "active",
                "amount": 50,
                "occurred_at": "2026-03-04T10:00:00-03:00",
            },
            {
                "type": "expense",
                "status": "active",
                "amount": 10,
                "occurred_at": "2026-03-05T10:00:00-03:00",
            },
            {
                "type": "income",
                "status": "cancelled",
                "amount": 500,
                "occurred_at": "2026-03-12T10:00:00-03:00",
            },
        ]

        result = overview_metrics(
            transactions,
            ["2026-03-10", "2026-03-04"],
            "7d",
            now,
        )

        self.assertEqual(
            [item["current"] for item in result["financial"]],
            [100.0, 20.0, 80.0],
        )
        self.assertEqual(
            [item["variation"] for item in result["financial"]],
            ["+100%", "+100%", "+100%"],
        )
        self.assertEqual(result["clients"]["current"], 1)
        self.assertEqual(result["clients"]["variation"], "0%")
        self.assertEqual(result["financial"][0]["sparkline_path"].count(" C "), 6)

    def test_period_change_and_zero_baseline_comparison(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        transactions = [
            {
                "type": "income",
                "status": "active",
                "amount": 100,
                "occurred_at": "2026-02-13T10:00:00-03:00",
            },
            {
                "type": "income",
                "status": "active",
                "amount": 100,
                "occurred_at": "2026-03-04T10:00:00-03:00",
            },
            {
                "type": "income",
                "status": "active",
                "amount": 50,
                "occurred_at": "2026-03-10T10:00:00-03:00",
            },
        ]

        short_period = overview_metrics(transactions, [], "7d", now)
        month_period = overview_metrics(transactions, [], "30d", now)
        no_baseline = overview_metrics(
            [
                {
                    "type": "income",
                    "status": "active",
                    "amount": 50,
                    "occurred_at": "2026-03-10T10:00:00-03:00",
                }
            ],
            ["2026-03-10"],
            "7d",
            now,
        )

        self.assertEqual(short_period["financial"][0]["current"], 50.0)
        self.assertEqual(month_period["financial"][0]["current"], 150.0)
        self.assertEqual(short_period["financial"][0]["variation"], "-50%")
        self.assertEqual(month_period["financial"][0]["variation"], "+50%")
        self.assertEqual(no_baseline["financial"][0]["variation"], "Sem comparação")
        self.assertEqual(no_baseline["clients"]["variation"], "Sem comparação")

    def test_negative_change_uses_downward_trend(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        result = overview_metrics(
            [
                {
                    "type": "income",
                    "status": "active",
                    "amount": 100,
                    "occurred_at": "2026-03-04T10:00:00-03:00",
                },
                {
                    "type": "income",
                    "status": "active",
                    "amount": 50,
                    "occurred_at": "2026-03-10T10:00:00-03:00",
                },
            ],
            [],
            "7d",
            now,
        )

        self.assertEqual(result["financial"][0]["variation"], "-50%")
        self.assertEqual(result["financial"][0]["trend"], "negative")

    def test_year_to_date_uses_calendar_year_bucket(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        metrics = overview_metrics(
            [
                {
                    "type": "income",
                    "status": "active",
                    "amount": 80,
                    "occurred_at": "2026-02-01T10:00:00-03:00",
                },
                {
                    "type": "income",
                    "status": "active",
                    "amount": 20,
                    "occurred_at": "2026-03-01T10:00:00-03:00",
                },
            ],
            [],
            "year",
            now,
        )

        self.assertEqual(metrics["financial"][0]["current"], 100.0)
        self.assertEqual(metrics["financial"][0]["sparkline_path"].count(" C "), 11)

    def test_contact_summary_reports_active_share_and_new_contacts(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        result = summarize_contacts(
            [
                {"status": "active", "first_contact_at": "2026-03-02"},
                {"status": "inactive", "first_contact_at": "2026-02-20"},
            ],
            2,
            now,
        )

        self.assertEqual(result["active_count"], 1)
        self.assertEqual(result["active_percentage"], 50)
        self.assertEqual(result["variation"], "+100%")
        self.assertEqual(
            result["first_contact_dates"],
            ["2026-03-02", "2026-02-20"],
        )

    def test_upcoming_appointments_filters_past_and_nonactive_statuses(self):
        now = datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO)
        appointments = [
            {
                "status": "confirmed",
                "start_at": "2026-03-15T13:30:00-03:00",
                "contact_name": "Ana Souza",
                "services_snapshot": [{"name": "Corte"}],
            },
            {
                "status": "pending",
                "start_at": "2026-03-15T11:30:00-03:00",
                "contact_name": "Past client",
            },
            {
                "status": "cancelled",
                "start_at": "2026-03-15T14:30:00-03:00",
                "contact_name": "Cancelled client",
            },
            {
                "status": "pending",
                "start_at": "2026-03-16T09:00:00-03:00",
                "contact_name": "Bruno Lima",
                "services_snapshot": [{"name": "Barba"}],
            },
        ]

        result = upcoming_appointments(
            appointments,
            now,
            lambda value: datetime.fromisoformat(value),
        )

        self.assertEqual(
            [(item["contact_name"], item["date_display"]) for item in result],
            [("Ana Souza", "Hoje"), ("Bruno Lima", "16/03")],
        )
        self.assertEqual(result[0]["initials"], "AS")

    def test_upcoming_appointments_returns_empty_for_an_empty_schedule(self):
        result = upcoming_appointments(
            [],
            datetime(2026, 3, 15, 12, 0, tzinfo=SAO_PAULO),
            lambda value: datetime.fromisoformat(value),
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
