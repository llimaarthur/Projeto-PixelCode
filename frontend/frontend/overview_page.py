import reflex as rx

from frontend.auth_state import AuthState, _app_shell
from frontend.dashboard_components import (
    block_error,
    empty_state,
    metric_card,
    readonly_transaction_row,
    skeleton,
)
from frontend.finance_page import _cashflow_section, _summary_section
from frontend.overview_service import OVERVIEW_PERIODS


def _period_selector() -> rx.Component:
    return rx.select.root(
        rx.select.trigger(
            aria_label="Período dos indicadores",
            class_name="pc-overview-period-trigger",
            disabled=(
                AuthState.overview_financial_loading
                | AuthState.overview_clients_loading
            ),
        ),
        rx.select.content(
            rx.select.group(
                *[
                    rx.select.item(label, value=value)
                    for value, label in OVERVIEW_PERIODS.items()
                ],
            ),
        ),
        value=AuthState.overview_period,
        on_change=AuthState.set_overview_period,
    )


def _overview_heading() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text("PAINEL ADMINISTRATIVO", class_name="pc-eyebrow"),
            rx.heading(
                rx.cond(
                    AuthState.display_name != "",
                    rx.fragment(
                        "Bem-vindo de volta, ",
                        AuthState.display_name,
                        "!",
                    ),
                    "Bem-vindo de volta!",
                ),
                as_="h1",
                class_name="pc-page-title",
            ),
            rx.text(
                "Aqui está um resumo completo da sua barbearia.",
                class_name="pc-page-description",
            ),
            align="start",
            spacing="2",
        ),
        rx.vstack(
            rx.hstack(
                rx.icon("calendar-days", size=18, aria_hidden="true"),
                _period_selector(),
                align="center",
                spacing="2",
                class_name="pc-overview-period-control",
            ),
            rx.cond(
                AuthState.overview_period_error != "",
                block_error(AuthState.overview_period_error),
                rx.fragment(),
            ),
            align="end",
            spacing="2",
        ),
        align="start",
        spacing="4",
        width="100%",
        class_name="pc-overview-heading",
    )


def _financial_metric_cards() -> rx.Component:
    return rx.cond(
        AuthState.overview_financial_loading,
        rx.fragment(
            skeleton("pc-overview-kpi-skeleton", "Carregando indicador financeiro"),
            skeleton("pc-overview-kpi-skeleton", "Carregando indicador financeiro"),
            skeleton("pc-overview-kpi-skeleton", "Carregando indicador financeiro"),
        ),
        rx.cond(
            AuthState.overview_financial_error != "",
            rx.fragment(
                block_error(AuthState.overview_financial_error),
                block_error(AuthState.overview_financial_error),
                block_error(AuthState.overview_financial_error),
            ),
            rx.foreach(
                AuthState.overview_financial_metrics,
                _overview_financial_metric,
            ),
        ),
    )


def _overview_financial_metric(item: rx.Var) -> rx.Component:
    return rx.cond(
        item["id"] == "inflows",
        metric_card(
            item,
            sparkline_label="Tendência do período selecionado",
            icon_name="arrow-down-left",
        ),
        rx.cond(
            item["id"] == "outflows",
            metric_card(
                item,
                sparkline_label="Tendência do período selecionado",
                icon_name="arrow-up-right",
            ),
            metric_card(
                item,
                sparkline_label="Tendência do período selecionado",
                icon_name="chart-no-axes-combined",
            ),
        ),
    )


def _client_metric_card() -> rx.Component:
    return rx.cond(
        AuthState.overview_clients_loading,
        skeleton("pc-overview-kpi-skeleton", "Carregando total de clientes"),
        rx.cond(
            AuthState.overview_clients_error != "",
            block_error(AuthState.overview_clients_error),
            metric_card(
                AuthState.overview_client_metric,
                value_type="count",
                sparkline_label="Tendência de novos clientes",
                icon_name="users-round",
            ),
        ),
    )


def _metrics_section() -> rx.Component:
    return rx.grid(
        _financial_metric_cards(),
        _client_metric_card(),
        width="100%",
        class_name="pc-overview-kpis",
        aria_label="Indicadores do período",
    )


def _appointments_heading() -> rx.Component:
    return rx.hstack(
        rx.icon("calendar-clock", size=20, aria_hidden="true"),
        rx.heading(
            "Próximos atendimentos",
            as_="h2",
            class_name="pc-finance-card-title",
        ),
        rx.spacer(),
        rx.link(
            "Ver todos →",
            href="/appointments",
            class_name="pc-finance-more-link",
        ),
        align="center",
        spacing="2",
        class_name="pc-finance-side-heading",
    )


def _appointment_row(item: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(item["time_display"], class_name="pc-overview-appointment-time"),
        rx.box(
            rx.text(item["initials"], aria_hidden="true"),
            role="img",
            aria_label=item["contact_name"],
            class_name="pc-overview-appointment-avatar",
        ),
        rx.vstack(
            rx.text(
                item["contact_name"],
                class_name="pc-overview-appointment-name",
            ),
            rx.text(
                item["service_summary"],
                class_name="pc-overview-appointment-service",
            ),
            align="start",
            spacing="1",
            class_name="pc-overview-appointment-copy",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                item["date_display"],
                class_name=rx.cond(
                    item["date_display"] == "Hoje",
                    "pc-overview-appointment-date pc-overview-appointment-today",
                    "pc-overview-appointment-date",
                ),
            ),
            rx.text(
                item["date_accessible"],
                class_name="pc-visually-hidden",
            ),
            align="end",
            spacing="1",
        ),
        align="center",
        class_name="pc-overview-appointment-row",
    )


def _appointments_section() -> rx.Component:
    return rx.el.section(
        _appointments_heading(),
        rx.cond(
            AuthState.overview_appointments_loading,
            skeleton("pc-overview-list-skeleton", "Carregando próximos atendimentos"),
            rx.cond(
                AuthState.overview_appointments_error != "",
                block_error(AuthState.overview_appointments_error),
                rx.cond(
                    AuthState.overview_appointments.length() == 0,
                    empty_state(
                        "Nenhum atendimento próximo",
                        "Os próximos agendamentos confirmados aparecerão aqui.",
                    ),
                    rx.vstack(
                        rx.foreach(
                            AuthState.overview_appointments,
                            _appointment_row,
                        ),
                        align="stretch",
                        spacing="0",
                        width="100%",
                    ),
                ),
            ),
        ),
        aria_label="Próximos atendimentos",
        class_name="pc-finance-card pc-overview-appointments",
    )


def _client_section() -> rx.Component:
    return rx.el.section(
        rx.hstack(
            rx.icon("users-round", size=20, aria_hidden="true"),
            rx.heading("Clientes", as_="h2", class_name="pc-finance-card-title"),
            rx.spacer(),
            rx.link(
                "Ver todos →",
                href="/contacts",
                class_name="pc-finance-more-link",
            ),
            align="center",
            spacing="2",
            class_name="pc-finance-side-heading",
        ),
        rx.cond(
            AuthState.overview_clients_loading,
            skeleton("pc-overview-client-skeleton", "Carregando clientes"),
            rx.cond(
                AuthState.overview_clients_error != "",
                block_error(AuthState.overview_clients_error),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "Clientes cadastrados",
                                class_name="pc-overview-client-label",
                            ),
                            rx.heading(
                                AuthState.overview_client_total,
                                as_="p",
                                class_name="pc-overview-client-total",
                            ),
                            align="start",
                            spacing="1",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.cond(
                                AuthState.overview_client_total_trend == "positive",
                                rx.icon("arrow-up-right", size=15, aria_hidden="true"),
                                rx.cond(
                                    AuthState.overview_client_total_trend == "negative",
                                    rx.icon("arrow-down-right", size=15, aria_hidden="true"),
                                    rx.icon("minus", size=15, aria_hidden="true"),
                                ),
                            ),
                            rx.text(AuthState.overview_client_total_variation),
                            rx.text("vs. mês anterior"),
                            align="center",
                            spacing="1",
                            class_name=rx.cond(
                                AuthState.overview_client_total_trend == "positive",
                                "pc-finance-kpi-change pc-finance-kpi-change-positive",
                                rx.cond(
                                    AuthState.overview_client_total_trend == "negative",
                                    "pc-finance-kpi-change pc-finance-kpi-change-negative",
                                    "pc-finance-kpi-change pc-finance-kpi-change-neutral",
                                ),
                            ),
                        ),
                        align="center",
                        width="100%",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.text("Clientes ativos"),
                            rx.text(
                                AuthState.overview_client_active_percentage,
                                "%",
                            ),
                            justify="between",
                            width="100%",
                            class_name="pc-overview-active-labels",
                        ),
                        rx.box(
                            rx.box(
                                class_name="pc-overview-active-progress-value",
                                width=(
                                    AuthState.overview_client_active_percentage.to_string()
                                    + "%"
                                ),
                            ),
                            role="progressbar",
                            aria_label="Percentual de clientes ativos",
                            aria_valuemin=0,
                            aria_valuemax=100,
                            aria_valuenow=AuthState.overview_client_active_percentage,
                            class_name="pc-overview-active-progress",
                        ),
                        class_name="pc-overview-active-progress-wrap",
                    ),
                    align="stretch",
                    spacing="5",
                    class_name="pc-overview-client-content",
                ),
            ),
        ),
        aria_label="Resumo de clientes",
        class_name="pc-finance-card pc-overview-clients",
    )


def _transactions_section() -> rx.Component:
    return rx.el.section(
        rx.hstack(
            rx.icon("arrow-left-right", size=20, aria_hidden="true"),
            rx.vstack(
                rx.heading(
                    "Movimentações Recentes",
                    as_="h2",
                    class_name="pc-finance-card-title",
                ),
                rx.text(
                    "Últimas entradas e saídas da barbearia",
                    class_name="pc-finance-card-subtitle",
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.link(
                "Ver todas →",
                href="/financeiro",
                class_name="pc-finance-more-link",
            ),
            align="center",
            spacing="2",
            class_name="pc-finance-side-heading",
        ),
        rx.cond(
            AuthState.overview_transactions_loading,
            skeleton("pc-overview-list-skeleton", "Carregando movimentações"),
            rx.cond(
                AuthState.overview_transactions_error != "",
                block_error(AuthState.overview_transactions_error),
                rx.cond(
                    AuthState.overview_recent_transactions.length() == 0,
                    empty_state(
                        "Nenhuma movimentação recente",
                        "As entradas e saídas registradas aparecerão aqui.",
                    ),
                    rx.vstack(
                        rx.foreach(
                            AuthState.overview_recent_transactions,
                            readonly_transaction_row,
                        ),
                        align="stretch",
                        spacing="0",
                        width="100%",
                    ),
                ),
            ),
        ),
        aria_label="Movimentações recentes",
        class_name="pc-finance-card pc-overview-transactions",
    )


def overview_page() -> rx.Component:
    content = rx.vstack(
        _overview_heading(),
        _metrics_section(),
        rx.grid(
            _summary_section(
                title="Visão Rápida do Financeiro",
                link_label="Ver mais",
                link_href="/financeiro",
                balance_label="Saldo Atual",
                aria_label="Visão Rápida do Financeiro",
            ),
            _appointments_section(),
            _cashflow_section(),
            class_name="pc-overview-primary-grid",
            width="100%",
        ),
        rx.grid(
            _client_section(),
            _transactions_section(),
            class_name="pc-overview-secondary-grid",
            width="100%",
        ),
        align="stretch",
        spacing="5",
        width="100%",
        class_name="pc-overview-content",
    )
    return _app_shell(content, "/app")
