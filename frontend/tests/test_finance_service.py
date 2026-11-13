import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from frontend.finance_service import (
    FinanceDataError,
    finance_dashboard_from_transactions,
    format_brl,
    mock_finance_dashboard,
    normalize_finance_dashboard,
    percentage_change,
    prepare_cashflow_chart,
    should_use_finance_mock,
)


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


class FinanceServiceTests(unittest.TestCase):
    def test_formats_brl_with_pt_br_separators(self):
        self.assertEqual(format_brl(18720), "R$ 18.720,00")
        self.assertEqual(format_brl(-450), "−R$ 450,00")

    def test_percentage_change_handles_increase_decrease_and_zero(self):
        self.assertEqual(percentage_change(1245, 1111.61), 12)
        self.assertEqual(percentage_change(90, 100), -10)
        self.assertIsNone(percentage_change(100, 0))

    def test_mock_requires_explicit_development_configuration(self):
        self.assertTrue(should_use_finance_mock("true", is_production=False))
        self.assertFalse(should_use_finance_mock("true", is_production=True))
        self.assertFalse(
            should_use_finance_mock(
                "true",
                is_production=False,
                api_configured=True,
            )
        )
        self.assertFalse(should_use_finance_mock("", is_production=False))

    def test_mock_matches_reference_values_and_today_label(self):
        now = datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
        dashboard = normalize_finance_dashboard(mock_finance_dashboard(now), now)

        self.assertEqual(
            [item["current"] for item in dashboard["kpis"]],
            [1245.0, 5860.0, 18720.0],
        )
        self.assertEqual(
            [item["variation"] for item in dashboard["kpis"]],
            ["+12%", "+8%", "+15%"],
        )
        self.assertEqual(dashboard["summary"]["net_profit"], 9270.0)
        self.assertEqual(
            [item["date_label"] for item in dashboard["transactions"]],
            ["Hoje, 16:20", "Hoje, 14:32", "Hoje, 13:10"],
        )

    def test_cashflow_chart_generates_smooth_series_and_fixed_reference_axis(self):
        dashboard = normalize_finance_dashboard(
            mock_finance_dashboard(
                datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
            )
        )
        chart = prepare_cashflow_chart(dashboard["cashflow"]["6m"])

        self.assertEqual(len(chart["points"]), 6)
        self.assertEqual(chart["axis_maximum"], 20000)
        self.assertTrue(chart["inflow_path"].startswith("M "))
        self.assertIn("Out", [point["month"] for point in chart["points"]])
        self.assertTrue(chart["inflow_area"].endswith("Z"))

    def test_invalid_provider_payload_is_not_silently_accepted(self):
        with self.assertRaises(FinanceDataError):
            normalize_finance_dashboard(None)

    def test_partial_provider_failure_does_not_hide_other_blocks(self):
        payload = mock_finance_dashboard(
            datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
        )
        payload["transactions"] = {"error": "Movimentações temporariamente indisponíveis."}

        dashboard = normalize_finance_dashboard(payload)

        self.assertIn("transactions", dashboard["errors"])
        self.assertEqual(dashboard["transactions"], [])
        self.assertEqual(dashboard["summary"]["net_profit"], 9270.0)
        self.assertEqual(dashboard["kpis"][0]["variation"], "+12%")

    def test_missing_sections_are_reported_without_filling_mock_data(self):
        dashboard = normalize_finance_dashboard({"kpis": [], "transactions": []})

        self.assertEqual(dashboard["kpis"], [])
        self.assertEqual(dashboard["transactions"], [])
        self.assertIn("cashflow", dashboard["errors"])
        self.assertEqual(dashboard["cashflow"]["6m"], [])
        self.assertEqual(dashboard["summary"], {})

    def test_dashboard_aggregates_real_ledger_entries_and_expenses(self):
        now = datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
        dashboard = finance_dashboard_from_transactions(
            {
                "transactions": [
                    {
                        "type": "income",
                        "title": "Pagamento de serviço",
                        "amount": 120,
                        "occurred_at": "2026-11-09T16:20:00-03:00",
                    },
                    {
                        "type": "expense",
                        "title": "Compra de produtos",
                        "amount": 45,
                        "occurred_at": "2026-11-09T14:00:00-03:00",
                    },
                    {
                        "type": "income",
                        "title": "Serviço",
                        "amount": 50,
                        "occurred_at": "2026-10-05T10:00:00-03:00",
                    },
                ]
            },
            now,
        )

        self.assertEqual([item["current"] for item in dashboard["kpis"]], [120, 120, 120])
        self.assertEqual(dashboard["summary"]["inflows"], 120)
        self.assertEqual(dashboard["summary"]["outflows"], 45)
        self.assertEqual(dashboard["summary"]["net_profit"], 75)
        self.assertEqual(dashboard["summary"]["current_balance"], 125)
        self.assertEqual(dashboard["kpis"][2]["variation"], "+140%")
        self.assertEqual(dashboard["cashflow"]["6m"][-1]["inflows"], 120)
        self.assertEqual(dashboard["cashflow"]["6m"][-1]["outflows"], 45)
        self.assertEqual(len(dashboard["cashflow"]["6m"]), 6)
        self.assertEqual(len(dashboard["cashflow"]["12m"]), 12)
        self.assertEqual(len(dashboard["cashflow"]["year"]), 11)
        self.assertEqual(dashboard["transactions"][0]["title"], "Pagamento de serviço")

    def test_dashboard_returns_empty_blocks_without_ledger_data(self):
        dashboard = finance_dashboard_from_transactions([], datetime(2026, 11, 9, tzinfo=SAO_PAULO))

        self.assertEqual(dashboard["kpis"], [])
        self.assertEqual(dashboard["cashflow"], {"6m": [], "12m": [], "year": []})
        self.assertEqual(dashboard["summary"], {})
        self.assertEqual(dashboard["transactions"], [])
        self.assertEqual(dashboard["errors"], {})

    def test_dashboard_accepts_xano_epoch_timestamps(self):
        now = datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
        occurred_at = int(datetime(2026, 11, 9, 16, 20, tzinfo=SAO_PAULO).timestamp() * 1000)
        dashboard = finance_dashboard_from_transactions(
            [
                {
                    "type": "income",
                    "title": "Pagamento de serviço",
                    "amount": 120,
                    "occurred_at": occurred_at,
                }
            ],
            now,
        )

        self.assertEqual(dashboard["transactions"][0]["title"], "Pagamento de serviço")
        self.assertEqual(dashboard["summary"]["inflows"], 120)
        self.assertEqual(dashboard["cashflow"]["6m"][-1]["inflows"], 120)

    def test_dashboard_preserves_transaction_owner_and_service_links(self):
        now = datetime(2026, 11, 9, 17, 0, tzinfo=SAO_PAULO)
        dashboard = finance_dashboard_from_transactions(
            {
                "transactions": [
                    {
                        "id": 31,
                        "created_by": 7,
                        "contact_id": 12,
                        "contact_name_snapshot": "Ana Souza",
                        "services_snapshot": [
                            {"id": 4, "name": "Corte", "price": 65}
                        ],
                        "appointment_id": 28,
                        "appointment_status_before_payment": "confirmed",
                        "type": "income",
                        "title": "Pagamento de serviço",
                        "amount": 65,
                        "occurred_at": "2026-11-09T16:20:00-03:00",
                    }
                ]
            },
            now,
        )

        transaction = dashboard["transactions"][0]
        self.assertEqual(transaction["created_by"], 7)
        self.assertEqual(transaction["contact_id"], 12)
        self.assertEqual(transaction["appointment_id"], 28)
        self.assertEqual(transaction["services_snapshot"][0]["name"], "Corte")
        self.assertEqual(transaction["status"], "active")
        self.assertIn("Cliente: Ana Souza", transaction["detail"])
        self.assertIn("Serviços: Corte", transaction["detail"])
        self.assertEqual(transaction["detail"].count("Cliente: Ana Souza"), 1)
        self.assertEqual(transaction["detail"].count("Serviços: Corte"), 1)

    def test_dashboard_rejects_invalid_service_snapshot(self):
        with self.assertRaises(FinanceDataError):
            finance_dashboard_from_transactions(
                [
                    {
                        "type": "income",
                        "title": "Pagamento",
                        "amount": 65,
                        "occurred_at": "2026-11-09T16:20:00-03:00",
                        "services_snapshot": {"name": "Corte"},
                    }
                ]
            )

    def test_dashboard_shows_historical_transactions_on_scaled_cashflow(self):
        now = datetime(2026, 11, 11, 0, 14, tzinfo=SAO_PAULO)
        dashboard = finance_dashboard_from_transactions(
            [
                {
                    "type": "income",
                    "title": "Entrada de outubro",
                    "amount": 100,
                    "occurred_at": "2026-10-20T12:30:00-03:00",
                },
                {
                    "type": "income",
                    "title": "Entrada de setembro",
                    "amount": 90,
                    "occurred_at": "2026-09-26T20:30:00-03:00",
                },
            ],
            now,
        )
        chart = prepare_cashflow_chart(dashboard["cashflow"]["6m"])

        self.assertEqual(dashboard["cashflow"]["6m"][3]["inflows"], 90)
        self.assertEqual(dashboard["cashflow"]["6m"][4]["inflows"], 100)
        self.assertEqual(chart["axis_maximum"], 100)
        self.assertEqual(chart["points"][3]["inflows"], 90)
        self.assertEqual(chart["points"][4]["inflows"], 100)
        self.assertLess(chart["points"][4]["inflow_y"], chart["points"][3]["inflow_y"])
        self.assertEqual(dashboard["summary"]["inflows"], 0)
        self.assertEqual(dashboard["summary"]["outflows"], 0)
        self.assertEqual(dashboard["summary"]["current_balance"], 190)

    def test_cancelled_transactions_remain_visible_but_leave_financial_totals(self):
        now = datetime(2026, 11, 11, 0, 14, tzinfo=SAO_PAULO)
        dashboard = finance_dashboard_from_transactions(
            [
                {
                    "id": 8,
                    "type": "income",
                    "status": "active",
                    "title": "Entrada válida",
                    "amount": 125,
                    "occurred_at": "2026-11-10T12:00:00-03:00",
                },
                {
                    "id": 7,
                    "type": "expense",
                    "status": "cancelled",
                    "title": "Compra estornada",
                    "cancellation_reason": "Compra duplicada",
                    "amount": 40,
                    "occurred_at": "2026-11-09T12:00:00-03:00",
                },
            ],
            now,
        )

        self.assertEqual(dashboard["summary"]["inflows"], 125)
        self.assertEqual(dashboard["summary"]["outflows"], 0)
        self.assertEqual(dashboard["summary"]["current_balance"], 125)
        self.assertEqual(dashboard["transactions"][0]["id"], 8)
        self.assertEqual(dashboard["transactions"][0]["status"], "active")
        self.assertFalse(dashboard["transactions"][0]["is_cancelled"])
        self.assertEqual(dashboard["transactions"][1]["id"], 7)
        self.assertEqual(dashboard["transactions"][1]["status"], "cancelled")
        self.assertTrue(dashboard["transactions"][1]["is_cancelled"])
        self.assertIn("Estorno: Compra duplicada", dashboard["transactions"][1]["detail"])

    def test_dashboard_rejects_invalid_or_non_positive_ledger_amounts(self):
        with self.assertRaises(FinanceDataError):
            finance_dashboard_from_transactions(
                [
                    {
                        "type": "income",
                        "title": "Invalid",
                        "amount": 0,
                        "occurred_at": "2026-11-09T16:20:00-03:00",
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()
