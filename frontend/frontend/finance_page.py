import reflex as rx

from frontend.auth_state import AuthState, _app_shell


def _intl_currency(value: rx.Var) -> rx.Var:
    return rx.Var(
        _js_expr=(
            'new Intl.NumberFormat("pt-BR", '
            '{style: "currency", currency: "BRL"}).format('
            f"{value})"
        ),
        _var_type=str,
        _var_data=value._get_all_var_data(),
    )


def _block_error(message: rx.Var) -> rx.Component:
    return rx.box(
        rx.icon("triangle-alert", size=18, aria_hidden="true"),
        rx.text(message),
        role="alert",
        class_name="pc-finance-error",
    )


def _empty_state(title: str, description: str) -> rx.Component:
    return rx.vstack(
        rx.icon("chart-no-axes-combined", size=22, aria_hidden="true"),
        rx.text(title, class_name="pc-finance-empty-title"),
        rx.text(description, class_name="pc-finance-empty-copy"),
        align="center",
        spacing="2",
        class_name="pc-finance-empty",
    )


def _skeleton(class_name: str, label: str) -> rx.Component:
    return rx.box(
        rx.text(label, class_name="pc-visually-hidden"),
        role="status",
        aria_label=label,
        class_name=f"pc-finance-skeleton {class_name}",
    )


def _sparkline(item: rx.Var) -> rx.Component:
    return rx.el.svg(
        rx.el.path(
            d=item["sparkline_area"],
            fill=rx.cond(
                item["accent"] == "purple",
                "url(#finance-spark-purple)",
                rx.cond(
                    item["accent"] == "green",
                    "url(#finance-spark-green)",
                    "url(#finance-spark-blue)",
                ),
            ),
            stroke="none",
        ),
        rx.el.path(
            d=item["sparkline_path"],
            fill="none",
            stroke="currentColor",
            stroke_width="2.5",
            stroke_linecap="round",
            stroke_linejoin="round",
        ),
        view_box="0 0 100 50",
        preserve_aspect_ratio="none",
        role="img",
        aria_label="Tendência de recebimentos",
        class_name=rx.cond(
            item["accent"] == "purple",
            "pc-finance-sparkline pc-finance-sparkline-purple",
            rx.cond(
                item["accent"] == "green",
                "pc-finance-sparkline pc-finance-sparkline-green",
                "pc-finance-sparkline pc-finance-sparkline-blue",
            ),
        ),
    )


def _kpi_card(item: rx.Var) -> rx.Component:
    return rx.el.article(
        rx.box(
            rx.icon("calendar-days", size=21, aria_hidden="true"),
            class_name=rx.cond(
                item["accent"] == "purple",
                "pc-finance-kpi-icon pc-finance-kpi-icon-purple",
                rx.cond(
                    item["accent"] == "green",
                    "pc-finance-kpi-icon pc-finance-kpi-icon-green",
                    "pc-finance-kpi-icon pc-finance-kpi-icon-blue",
                ),
            ),
        ),
        rx.vstack(
            rx.text(item["label"], class_name="pc-finance-kpi-label"),
            rx.text(
                _intl_currency(item["current"]),
                class_name="pc-finance-kpi-value",
            ),
            rx.hstack(
                rx.cond(
                    item["trend"] == "positive",
                    rx.icon("arrow-up-right", size=13, aria_hidden="true"),
                    rx.cond(
                        item["trend"] == "negative",
                        rx.icon("arrow-down-right", size=13, aria_hidden="true"),
                        rx.icon("minus", size=13, aria_hidden="true"),
                    ),
                ),
                rx.text(
                    item["variation"],
                    class_name="pc-finance-kpi-variation",
                ),
                rx.text(item["comparison"], class_name="pc-finance-kpi-comparison"),
                spacing="1",
                align="center",
                class_name=rx.cond(
                    item["trend"] == "positive",
                    "pc-finance-kpi-change pc-finance-kpi-change-positive",
                    rx.cond(
                        item["trend"] == "negative",
                        "pc-finance-kpi-change pc-finance-kpi-change-negative",
                        "pc-finance-kpi-change pc-finance-kpi-change-neutral",
                    ),
                ),
            ),
            align="start",
            spacing="1",
            class_name="pc-finance-kpi-copy",
        ),
        _sparkline(item),
        class_name="pc-finance-kpi-card",
    )


def _period_button(label: str, period: str) -> rx.Component:
    return rx.button(
        label,
        type="button",
        on_click=AuthState.set_finance_period(period),
        aria_label="Exibir fluxo de caixa: " + label,
        aria_pressed=AuthState.finance_period == period,
        class_name=rx.cond(
            AuthState.finance_period == period,
            "pc-finance-period pc-finance-period-active",
            "pc-finance-period",
        ),
    )


def _chart_point(point: rx.Var) -> rx.Component:
    active = point["index"] == AuthState.finance_chart_active_index
    return rx.fragment(
        rx.el.line(
            x1=point["x"],
            x2=point["x"],
            y1="22",
            y2="232",
            class_name="pc-finance-chart-grid-vertical",
        ),
        rx.cond(
            active,
            rx.el.line(
                x1=point["x"],
                x2=point["x"],
                y1="22",
                y2="232",
                class_name="pc-finance-active-guide",
            ),
            rx.fragment(),
        ),
        rx.el.circle(
            cx=point["x"],
            cy=point["inflow_y"],
            r=rx.cond(active, "6", "4"),
            class_name="pc-finance-chart-point pc-finance-chart-point-inflow",
            tab_index=0,
            role="img",
            aria_label=point["accessible_label"],
            on_mouse_enter=AuthState.select_finance_chart_point(point["index"]),
            on_focus=AuthState.select_finance_chart_point(point["index"]),
        ),
        rx.el.circle(
            cx=point["x"],
            cy=point["outflow_y"],
            r=rx.cond(active, "6", "4"),
            class_name="pc-finance-chart-point pc-finance-chart-point-outflow",
            tab_index=0,
            role="img",
            aria_label=point["accessible_label"],
            on_mouse_enter=AuthState.select_finance_chart_point(point["index"]),
            on_focus=AuthState.select_finance_chart_point(point["index"]),
        ),
        rx.el.text(
            point["month"],
            x=point["x"],
            y="258",
            text_anchor="middle",
            class_name="pc-finance-chart-x-label",
        ),
    )


def _chart_tick(tick: rx.Var) -> rx.Component:
    return rx.fragment(
        rx.el.line(
            x1="76",
            x2="742",
            y1=tick["y"],
            y2=tick["y"],
            class_name="pc-finance-chart-grid",
        ),
        rx.el.text(
            tick["compact_label"],
            x="0",
            y=tick["label_y"],
            class_name="pc-finance-chart-y-label",
        ),
    )


def _cashflow_chart() -> rx.Component:
    return rx.el.svg(
        rx.el.defs(
            rx.el.linear_gradient(
                rx.el.stop(
                    offset="0%",
                    stop_color="var(--pc-blue)",
                    stop_opacity="0.26",
                ),
                rx.el.stop(
                    offset="100%",
                    stop_color="var(--pc-blue)",
                    stop_opacity="0",
                ),
                id="finance-inflow-gradient",
                x1="0",
                y1="0",
                x2="0",
                y2="1",
            ),
            rx.el.linear_gradient(
                rx.el.stop(
                    offset="0%",
                    stop_color="var(--pc-finance-outflow)",
                    stop_opacity="0.22",
                ),
                rx.el.stop(
                    offset="100%",
                    stop_color="var(--pc-finance-outflow)",
                    stop_opacity="0",
                ),
                id="finance-outflow-gradient",
                x1="0",
                y1="0",
                x2="0",
                y2="1",
            ),
        ),
        rx.foreach(AuthState.finance_chart_y_ticks, _chart_tick),
        rx.el.path(
            d=AuthState.finance_chart_inflow_area,
            fill="url(#finance-inflow-gradient)",
            class_name="pc-finance-area",
        ),
        rx.el.path(
            d=AuthState.finance_chart_outflow_area,
            fill="url(#finance-outflow-gradient)",
            class_name="pc-finance-area",
        ),
        rx.el.path(
            d=AuthState.finance_chart_inflow_path,
            class_name="pc-finance-chart-line pc-finance-chart-line-inflow",
        ),
        rx.el.path(
            d=AuthState.finance_chart_outflow_path,
            class_name="pc-finance-chart-line pc-finance-chart-line-outflow",
        ),
        rx.foreach(AuthState.finance_chart_points, _chart_point),
        view_box="0 0 760 280",
        preserve_aspect_ratio="none",
        role="img",
        aria_label="Gráfico de área do fluxo de caixa: entradas e saídas",
        class_name="pc-finance-chart",
    )


def _chart_tooltip(point: rx.Var) -> rx.Component:
    return rx.cond(
        point["index"] == AuthState.finance_chart_active_index,
        rx.hstack(
            rx.text(point["month"], class_name="pc-finance-tooltip-month"),
            rx.text("Entradas:", class_name="pc-finance-tooltip-label"),
            rx.text(
                _intl_currency(point["inflows"]),
                class_name="pc-finance-tooltip-inflow",
            ),
            rx.text("Saídas:", class_name="pc-finance-tooltip-label"),
            rx.text(
                _intl_currency(point["outflows"]),
                class_name="pc-finance-tooltip-outflow",
            ),
            role="status",
            class_name="pc-finance-tooltip",
            align="center",
            wrap="wrap",
            spacing="2",
        ),
        rx.fragment(),
    )


def _cashflow_section() -> rx.Component:
    return rx.el.section(
        rx.hstack(
            rx.icon("chart-no-axes-combined", size=21, aria_hidden="true"),
            rx.vstack(
                rx.heading("Fluxo de Caixa", as_="h2", class_name="pc-finance-card-title"),
                rx.text(
                    rx.cond(
                        AuthState.finance_period == "6m",
                        "Entradas e saídas dos últimos 6 meses",
                        rx.cond(
                            AuthState.finance_period == "12m",
                            "Entradas e saídas dos últimos 12 meses",
                            "Entradas e saídas do ano atual",
                        ),
                    ),
                    class_name="pc-finance-card-subtitle",
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                _period_button("6 meses", "6m"),
                _period_button("12 meses", "12m"),
                _period_button("Ano atual", "year"),
                role="group",
                aria_label="Período do fluxo de caixa",
                class_name="pc-finance-period-control",
                spacing="0",
            ),
            class_name="pc-finance-section-heading",
            align="center",
            width="100%",
        ),
        rx.hstack(
            rx.hstack(
                rx.box(class_name="pc-finance-legend-dot pc-finance-legend-inflow"),
                rx.text("Entradas"),
                spacing="2",
                align="center",
            ),
            rx.hstack(
                rx.box(class_name="pc-finance-legend-dot pc-finance-legend-outflow"),
                rx.text("Saídas"),
                spacing="2",
                align="center",
            ),
            class_name="pc-finance-legend",
            spacing="4",
        ),
        rx.cond(
            AuthState.finance_chart_loading,
            _skeleton("pc-finance-chart-skeleton", "Carregando fluxo de caixa"),
            rx.cond(
                AuthState.finance_chart_error != "",
                _block_error(AuthState.finance_chart_error),
                rx.cond(
                    AuthState.finance_chart_points.length() == 0,
                    _empty_state(
                        "Sem dados para este período",
                        "Quando houver movimentações, o fluxo de caixa aparecerá aqui.",
                    ),
                    rx.vstack(
                        _cashflow_chart(),
                        rx.foreach(AuthState.finance_chart_points, _chart_tooltip),
                        rx.text(
                            "Os valores do gráfico estão disponíveis nos pontos e nesta descrição acessível.",
                            class_name="pc-visually-hidden",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
            ),
        ),
        aria_label="Fluxo de caixa",
        class_name="pc-finance-card pc-finance-cashflow",
    )


def _summary_donut() -> rx.Component:
    return rx.el.svg(
        rx.el.circle(
            cx="70",
            cy="70",
            r="54",
            fill="none",
            stroke="var(--pc-finance-outflow)",
            stroke_width="14",
            class_name="pc-finance-donut-track",
        ),
        rx.el.circle(
            cx="70",
            cy="70",
            r="54",
            fill="none",
            stroke="var(--pc-success)",
            stroke_width="14",
            stroke_dasharray=AuthState.finance_summary["donut_inflow_dasharray"],
            transform="rotate(-90 70 70)",
            class_name="pc-finance-donut-inflow",
        ),
        rx.el.circle(
            cx="70",
            cy="70",
            r="54",
            fill="none",
            stroke="var(--pc-finance-outflow)",
            stroke_width="14",
            stroke_dasharray=AuthState.finance_summary["donut_outflow_dasharray"],
            stroke_dashoffset=AuthState.finance_summary["donut_outflow_dashoffset"],
            transform="rotate(-90 70 70)",
            class_name="pc-finance-donut-outflow",
        ),
        view_box="0 0 140 140",
        role="img",
        aria_label="Donut com proporção de entradas e saídas do mês",
        class_name="pc-finance-donut",
    )


def _summary_section() -> rx.Component:
    return rx.el.section(
        rx.hstack(
            rx.icon("chart-pie", size=20, aria_hidden="true"),
            rx.heading("Resumo do Mês", as_="h2", class_name="pc-finance-card-title"),
            class_name="pc-finance-side-heading",
            align="center",
            spacing="2",
        ),
        rx.cond(
            AuthState.finance_summary_loading,
            _skeleton("pc-finance-summary-skeleton", "Carregando resumo do mês"),
            rx.cond(
                AuthState.finance_summary_error != "",
                _block_error(AuthState.finance_summary_error),
                rx.cond(
                    AuthState.finance_summary_empty,
                    _empty_state(
                        "Resumo indisponível",
                        "Ainda não há dados para este mês.",
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                _summary_donut(),
                                rx.vstack(
                                    rx.text(
                                        _intl_currency(AuthState.finance_summary["net_profit"]),
                                        class_name="pc-finance-donut-value",
                                    ),
                                    rx.text(
                                        "Lucro Líquido",
                                        class_name="pc-finance-donut-label",
                                    ),
                                    align="center",
                                    spacing="0",
                                    class_name="pc-finance-donut-center",
                                ),
                                class_name="pc-finance-donut-wrap",
                            ),
                            rx.vstack(
                                rx.hstack(
                                    rx.box(class_name="pc-finance-legend-dot pc-finance-legend-inflow"),
                                    rx.text("Entradas", class_name="pc-finance-summary-label"),
                                    rx.spacer(),
                                    rx.text(
                                        _intl_currency(AuthState.finance_summary["inflows"]),
                                        class_name="pc-finance-summary-value",
                                    ),
                                    width="100%",
                                    align="center",
                                    spacing="2",
                                ),
                                rx.hstack(
                                    rx.box(class_name="pc-finance-legend-dot pc-finance-legend-outflow"),
                                    rx.text("Saídas", class_name="pc-finance-summary-label"),
                                    rx.spacer(),
                                    rx.text(
                                        _intl_currency(AuthState.finance_summary["outflows"]),
                                        class_name="pc-finance-summary-value",
                                    ),
                                    width="100%",
                                    align="center",
                                    spacing="2",
                                ),
                                align="stretch",
                                justify="center",
                                spacing="4",
                                class_name="pc-finance-summary-details",
                            ),
                            class_name="pc-finance-summary-main",
                            align="center",
                            spacing="4",
                        ),
                        rx.box(class_name="pc-finance-divider", aria_hidden="true"),
                        rx.hstack(
                            rx.vstack(
                                rx.text("Saldo acumulado", class_name="pc-finance-balance-label"),
                                rx.text(
                                    _intl_currency(AuthState.finance_summary["current_balance"]),
                                    class_name="pc-finance-balance-value",
                                ),
                                align="start",
                                spacing="1",
                            ),
                            rx.spacer(),
                            rx.icon("trending-up", size=19, aria_hidden="true"),
                            class_name="pc-finance-balance",
                            align="center",
                            width="100%",
                        ),
                        align="stretch",
                        spacing="4",
                        width="100%",
                    ),
                    ),
                ),
            ),
        aria_label="Resumo do mês",
        class_name="pc-finance-card pc-finance-summary",
    )


def _transaction_row(item: rx.Var) -> rx.Component:
    is_income = item["type"] == "income"
    return rx.vstack(
        rx.hstack(
            rx.box(
                rx.cond(
                    is_income,
                    rx.icon("arrow-up-right", size=17, aria_hidden="true"),
                    rx.icon("arrow-down-right", size=17, aria_hidden="true"),
                ),
                aria_label=rx.cond(is_income, "Entrada", "Saída"),
                class_name=rx.cond(
                    is_income,
                    "pc-finance-transaction-icon pc-finance-transaction-icon-in",
                    "pc-finance-transaction-icon pc-finance-transaction-icon-out",
                ),
            ),
            rx.vstack(
                rx.text(item["title"], class_name="pc-finance-transaction-title"),
                rx.text(item["detail"], class_name="pc-finance-transaction-detail"),
                align="start",
                spacing="1",
                class_name="pc-finance-transaction-copy",
            ),
            rx.spacer(),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        rx.cond(is_income, "+", "−"),
                        class_name=rx.cond(
                            is_income,
                            "pc-finance-transaction-amount pc-finance-amount-in",
                            "pc-finance-transaction-amount pc-finance-amount-out",
                        ),
                    ),
                    rx.text(
                        _intl_currency(item["amount"]),
                        class_name=rx.cond(
                            is_income,
                            "pc-finance-transaction-amount pc-finance-amount-in",
                            "pc-finance-transaction-amount pc-finance-amount-out",
                        ),
                    ),
                    spacing="0",
                ),
                rx.text(item["date_label"], class_name="pc-finance-transaction-date"),
                align="end",
                spacing="1",
                class_name="pc-finance-transaction-values",
            ),
            class_name="pc-finance-transaction",
            align="center",
        ),
        rx.cond(
            item["is_cancelled"],
            rx.badge(
                "Estornada",
                color_scheme="red",
                variant="soft",
                class_name="pc-finance-cancelled-badge",
            ),
            rx.cond(
                item["can_manage"],
                rx.hstack(
                    rx.button(
                        "Editar",
                        type="button",
                        on_click=AuthState.edit_finance_transaction(
                            item["id"],
                            item["type"],
                            item["title"],
                            item["detail"],
                            item["amount"],
                            item["input_datetime"],
                        ),
                        variant="soft",
                        color_scheme="gray",
                        class_name="pc-finance-transaction-action",
                    ),
                    rx.cond(
                        item["can_cancel"],
                        rx.button(
                            "Estornar",
                            type="button",
                            on_click=AuthState.request_finance_cancellation(item["id"]),
                            variant="soft",
                            color_scheme="red",
                            class_name="pc-finance-transaction-action pc-finance-transaction-action-danger",
                        ),
                        rx.fragment(),
                    ),
                    class_name="pc-finance-transaction-actions",
                    spacing="3",
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            AuthState.finance_cancel_transaction_id == item["id"],
            rx.vstack(
                rx.text(
                    "O estorno preserva a movimentação no histórico e a remove dos totais. Informe o motivo para continuar.",
                    class_name="pc-finance-card-subtitle",
                ),
                rx.input(
                    value=AuthState.finance_cancel_reason,
                    on_change=AuthState.set_finance_cancel_reason,
                    placeholder="Motivo do estorno",
                    max_length=250,
                    aria_label="Motivo do estorno",
                    class_name="pc-input",
                    width="100%",
                ),
                rx.cond(
                    AuthState.finance_cancel_error != "",
                    rx.text(
                        AuthState.finance_cancel_error,
                        role="alert",
                        class_name="pc-finance-form-error",
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.button(
                        "Voltar",
                        type="button",
                        disabled=AuthState.finance_cancel_submitting,
                        on_click=AuthState.request_finance_cancellation(item["id"]),
                        class_name="pc-button pc-button-secondary",
                    ),
                    rx.button(
                        rx.cond(
                            AuthState.finance_cancel_submitting,
                            "Estornando...",
                            "Confirmar estorno",
                        ),
                        type="button",
                        disabled=(
                            (AuthState.finance_cancel_reason.length() < 3)
                            | AuthState.finance_cancel_submitting
                        ),
                        on_click=AuthState.cancel_finance_transaction(item["id"]),
                        class_name="pc-button pc-button-danger",
                    ),
                    spacing="2",
                ),
                align="stretch",
                spacing="3",
                class_name="pc-finance-cancel-confirmation",
            ),
            rx.fragment(),
        ),
        class_name="pc-finance-transaction-entry",
        align="stretch",
        spacing="2",
    )


def _transactions_section() -> rx.Component:
    return rx.el.section(
        rx.hstack(
            rx.hstack(
                rx.icon("list", size=19, aria_hidden="true"),
                rx.heading(
                    "Movimentações Recentes",
                    as_="h2",
                    class_name="pc-finance-card-title",
                ),
                align="center",
                spacing="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    AuthState.finance_has_cancelled_transactions,
                    rx.button(
                        rx.cond(
                            AuthState.finance_show_cancelled_transactions,
                            "Ocultar estornadas",
                            "Mostrar estornadas",
                        ),
                        type="button",
                        on_click=AuthState.toggle_finance_cancelled_transactions,
                        class_name="pc-finance-more-link",
                    ),
                    rx.fragment(),
                ),
                class_name="pc-finance-transaction-list-controls",
                align="center",
                spacing="3",
            ),
            class_name="pc-finance-side-heading",
            align="center",
            width="100%",
        ),
        rx.cond(
            AuthState.finance_transactions_loading,
            _skeleton(
                "pc-finance-transactions-skeleton",
                "Carregando movimentações recentes",
            ),
            rx.cond(
                AuthState.finance_transactions_error != "",
                _block_error(AuthState.finance_transactions_error),
                rx.cond(
                    AuthState.finance_filtered_transactions.length() == 0,
                    rx.vstack(
                        rx.cond(
                            AuthState.finance_has_cancelled_transactions
                            & ~AuthState.finance_show_cancelled_transactions,
                            _empty_state(
                                "Nenhuma movimentação ativa",
                                "As movimentações estornadas estão ocultas. Você pode exibi-las pelo controle acima.",
                            ),
                            _empty_state(
                                "Nenhuma movimentação recente",
                                "As entradas e saídas aparecerão aqui quando disponíveis.",
                            ),
                        ),
                        class_name="pc-finance-page-list",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.foreach(AuthState.finance_visible_transactions, _transaction_row),
                        class_name="pc-finance-page-list",
                        id="finance-transactions",
                        align="stretch",
                        spacing="0",
                        width="100%",
                    ),
                ),
            ),
        ),
        rx.cond(
            (AuthState.finance_transactions_error == "")
            & ~AuthState.finance_transactions_loading,
            rx.hstack(
                rx.text(
                    AuthState.finance_transactions_summary,
                    class_name="pc-finance-card-subtitle",
                    role="status",
                ),
                rx.spacer(),
                rx.button(
                    "Anterior",
                    type="button",
                    disabled=(AuthState.finance_transactions_page <= 1),
                    on_click=AuthState.previous_finance_transactions_page,
                    class_name="pc-finance-more-link",
                ),
                rx.button(
                    "Próxima",
                    type="button",
                    disabled=(
                        AuthState.finance_transactions_page
                        >= AuthState.finance_transactions_page_count
                    ),
                    on_click=AuthState.next_finance_transactions_page,
                    class_name="pc-finance-more-link",
                ),
                class_name="pc-finance-pagination",
                align="center",
                width="100%",
            ),
            rx.fragment(),
        ),
        aria_label="Movimentações recentes",
        class_name="pc-finance-card pc-finance-transactions",
    )


def _finance_kpis() -> rx.Component:
    return rx.cond(
        AuthState.finance_kpis_loading,
        rx.grid(
            _skeleton("pc-finance-kpi-skeleton", "Carregando indicadores"),
            _skeleton("pc-finance-kpi-skeleton", "Carregando indicadores"),
            _skeleton("pc-finance-kpi-skeleton", "Carregando indicadores"),
            class_name="pc-finance-kpis",
        ),
        rx.cond(
            AuthState.finance_kpis_error != "",
            _block_error(AuthState.finance_kpis_error),
            rx.cond(
                AuthState.finance_kpis.length() == 0,
                _empty_state(
                    "Indicadores indisponíveis",
                    "Não há recebimentos para os períodos selecionados.",
                ),
                rx.grid(
                    rx.foreach(AuthState.finance_kpis, _kpi_card),
                    class_name="pc-finance-kpis",
                ),
            ),
        ),
    )


def _finance_selected_service(item: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(item["name"], class_name="pc-finance-service-name"),
            rx.text(item["price_display"], class_name="pc-finance-card-subtitle"),
            align="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.button(
            "Remover",
            type="button",
            disabled=AuthState.finance_form_appointment_id > 0,
            on_click=AuthState.remove_finance_form_service(item["id"]),
            class_name="pc-finance-more-link",
        ),
        align="center",
        class_name="pc-finance-selected-service",
        width="100%",
    )


def _finance_entry_form() -> rx.Component:
    return rx.el.section(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        rx.cond(
                            AuthState.finance_form_mode == "edit",
                            "Editar movimentação",
                            "Registrar movimentação",
                        ),
                        as_="h2",
                        class_name="pc-finance-card-title",
                    ),
                    rx.text(
                        rx.cond(
                            AuthState.finance_form_mode == "edit",
                            "As alterações serão registradas no histórico financeiro.",
                            "Os lançamentos são compartilhados com a equipe e atualizam os indicadores.",
                        ),
                        class_name="pc-finance-card-subtitle",
                    ),
                    align="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    "Cancelar",
                    type="button",
                    on_click=AuthState.set_finance_form_open(False),
                    class_name="pc-button pc-button-secondary",
                ),
                align="center",
                width="100%",
            ),
            rx.form(
                rx.vstack(
                    rx.hstack(
                        rx.button(
                            "Entrada",
                            type="button",
                            on_click=AuthState.set_finance_form_type("income"),
                            aria_pressed=AuthState.finance_form_type == "income",
                            class_name=rx.cond(
                                AuthState.finance_form_type == "income",
                                "pc-finance-type-button pc-finance-type-button-active",
                                "pc-finance-type-button",
                            ),
                        ),
                        rx.button(
                            "Saída",
                            type="button",
                            on_click=AuthState.set_finance_form_type("expense"),
                            aria_pressed=AuthState.finance_form_type == "expense",
                            class_name=rx.cond(
                                AuthState.finance_form_type == "expense",
                                "pc-finance-type-button pc-finance-type-button-active",
                                "pc-finance-type-button",
                            ),
                        ),
                        role="group",
                        aria_label="Tipo da movimentação",
                        spacing="2",
                    ),
                    rx.cond(
                        (AuthState.finance_form_mode == "create")
                        & (AuthState.finance_form_type == "income"),
                        rx.vstack(
                            rx.vstack(
                                rx.el.label(
                                    "Cliente cadastrado",
                                    html_for="finance-contact",
                                    class_name="pc-field-label",
                                ),
                                rx.select(
                                    AuthState.finance_contact_options,
                                    id="finance-contact",
                                    value=AuthState.finance_form_contact_option,
                                    on_change=AuthState.set_finance_form_contact,
                                    disabled=AuthState.finance_form_options_loading,
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
                                    "Serviços cadastrados · selecione para adicionar",
                                    html_for="finance-service",
                                    class_name="pc-field-label",
                                ),
                                rx.select(
                                    AuthState.finance_service_options,
                                    id="finance-service",
                                    value=AuthState.finance_form_service_option,
                                    on_change=AuthState.set_finance_form_service_option,
                                    disabled=(
                                        (AuthState.finance_form_contact_id == 0)
                                        | (AuthState.finance_form_appointment_id > 0)
                                        | AuthState.finance_form_options_loading
                                    ),
                                    class_name="pc-input",
                                    width="100%",
                                ),
                                rx.foreach(
                                    AuthState.finance_selected_services,
                                    _finance_selected_service,
                                ),
                                class_name="pc-field",
                                align="stretch",
                                spacing="2",
                                width="100%",
                            ),
                            rx.cond(
                                AuthState.finance_form_contact_id > 0,
                                rx.vstack(
                                    rx.el.label(
                                        "Agendamento vinculado (opcional)",
                                        html_for="finance-appointment",
                                        class_name="pc-field-label",
                                    ),
                                    rx.select(
                                        AuthState.finance_appointment_options_labels,
                                        id="finance-appointment",
                                        value=AuthState.finance_form_appointment_option,
                                        on_change=AuthState.set_finance_form_appointment,
                                        disabled=AuthState.finance_appointment_options_loading,
                                        class_name="pc-input",
                                        width="100%",
                                    ),
                                    rx.cond(
                                        AuthState.finance_appointment_options_loading,
                                        rx.text(
                                            "Carregando agendamentos do cliente...",
                                            role="status",
                                            class_name="pc-finance-card-subtitle",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="pc-field",
                                    align="stretch",
                                    width="100%",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                AuthState.finance_form_options_loading,
                                rx.text(
                                    "Carregando clientes e serviços...",
                                    role="status",
                                    class_name="pc-finance-card-subtitle",
                                ),
                                rx.cond(
                                    AuthState.finance_form_options_error != "",
                                    rx.text(
                                        AuthState.finance_form_options_error,
                                        role="alert",
                                        class_name="pc-finance-form-error",
                                    ),
                                    rx.fragment(),
                                ),
                            ),
                            align="stretch",
                            spacing="3",
                            width="100%",
                            class_name="pc-finance-service-selection",
                        ),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.el.label(
                                "Descrição",
                                html_for="finance-title",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="finance-title",
                                name="title",
                                placeholder="Ex.: Pagamento de serviço",
                                max_length=100,
                                required=True,
                                value=AuthState.finance_form_title,
                                on_change=AuthState.set_finance_form_title,
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
                                "Valor (R$)",
                                html_for="finance-amount",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="finance-amount",
                                name="amount",
                                type="number",
                                min="0.01",
                                step="0.01",
                                placeholder="0,00",
                                required=True,
                                value=AuthState.finance_form_amount,
                                on_change=AuthState.set_finance_form_amount,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        class_name="pc-finance-form-row",
                        align="start",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.el.label(
                                "Detalhe (opcional)",
                                html_for="finance-detail",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="finance-detail",
                                name="detail",
                                placeholder="Ex.: Cliente, fornecedor ou observação",
                                max_length=250,
                                value=AuthState.finance_form_detail,
                                on_change=AuthState.set_finance_form_detail,
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
                                "Data e horário",
                                html_for="finance-occurred-at",
                                class_name="pc-field-label",
                            ),
                            rx.input(
                                id="finance-occurred-at",
                                name="occurred_at",
                                type="datetime-local",
                                required=True,
                                value=AuthState.finance_form_occurred_at,
                                on_change=AuthState.set_finance_form_occurred_at,
                                class_name="pc-input",
                                width="100%",
                            ),
                            class_name="pc-field",
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        class_name="pc-finance-form-row",
                        align="start",
                        width="100%",
                    ),
                    rx.cond(
                        AuthState.finance_form_error != "",
                        rx.text(
                            AuthState.finance_form_error,
                            role="alert",
                            class_name="pc-finance-form-error",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        AuthState.finance_form_confirming,
                        rx.text(
                            "Confira os dados alterados e confirme para gravar a nova versão no histórico.",
                            role="status",
                            class_name="pc-finance-form-confirmation",
                        ),
                        rx.fragment(),
                    ),
                    rx.button(
                        rx.cond(
                            AuthState.finance_form_submitting,
                            "Salvando...",
                            rx.cond(
                                AuthState.finance_form_mode == "edit",
                                rx.cond(
                                    AuthState.finance_form_confirming,
                                    "Confirmar alterações",
                                    "Revisar alterações",
                                ),
                                "Registrar movimentação",
                            ),
                        ),
                        type="submit",
                        disabled=AuthState.finance_form_submitting,
                        class_name="pc-button pc-button-primary",
                    ),
                    align="stretch",
                    spacing="4",
                    width="100%",
                ),
                on_submit=AuthState.save_finance_transaction,
                reset_on_submit=False,
                class_name="pc-finance-entry-form",
            ),
            align="stretch",
            spacing="4",
            width="100%",
        ),
        class_name="pc-finance-entry pc-finance-card",
    )


def finance_page() -> rx.Component:
    content = rx.vstack(
        rx.text("FINANCEIRO", class_name="pc-eyebrow"),
        rx.heading(
            "Controle financeiro da sua barbearia",
            as_="h1",
            class_name="pc-page-title",
        ),
        rx.text(
            "Acompanhe seus recebimentos, visualize o fluxo de caixa e mantenha suas finanças em dia.",
            class_name="pc-page-description pc-finance-page-description",
        ),
        rx.hstack(
            rx.cond(
                AuthState.finance_form_success_message != "",
                rx.text(
                    AuthState.finance_form_success_message,
                    role="status",
                    class_name="pc-finance-form-success",
                ),
                rx.fragment(),
            ),
            rx.spacer(),
            rx.cond(
                AuthState.finance_api_available,
                rx.cond(
                    AuthState.finance_form_open,
                    rx.fragment(),
                    rx.button(
                        rx.icon("plus", size=16, aria_hidden="true"),
                        "Adicionar movimentação",
                        type="button",
                        on_click=AuthState.set_finance_form_open(True),
                        class_name="pc-button pc-button-primary pc-finance-add-button",
                    ),
                ),
                rx.cond(
                    AuthState.finance_mock_mode,
                    rx.text(
                        "Modo de demonstração — não salva movimentações.",
                        role="status",
                        class_name="pc-finance-card-subtitle",
                    ),
                    rx.fragment(),
                ),
            ),
            align="center",
            width="100%",
        ),
        rx.cond(
            AuthState.finance_form_open,
            _finance_entry_form(),
            rx.fragment(),
        ),
        _finance_kpis(),
        rx.grid(
            _cashflow_section(),
            rx.vstack(
                _summary_section(),
                _transactions_section(),
                align="stretch",
                spacing="4",
                class_name="pc-finance-sidebar",
            ),
            class_name="pc-finance-layout",
        ),
        align="stretch",
        spacing="4",
        width="100%",
        class_name="pc-finance-content",
    )
    page = rx.box(
        rx.el.svg(
            rx.el.defs(
                rx.el.linear_gradient(
                    rx.el.stop(
                        offset="0%",
                        stop_color="var(--pc-blue)",
                        stop_opacity="0.34",
                    ),
                    rx.el.stop(
                        offset="100%",
                        stop_color="var(--pc-blue)",
                        stop_opacity="0",
                    ),
                    id="finance-spark-blue",
                    x1="0",
                    y1="0",
                    x2="0",
                    y2="1",
                ),
                rx.el.linear_gradient(
                    rx.el.stop(
                        offset="0%",
                        stop_color="var(--pc-finance-outflow)",
                        stop_opacity="0.34",
                    ),
                    rx.el.stop(
                        offset="100%",
                        stop_color="var(--pc-finance-outflow)",
                        stop_opacity="0",
                    ),
                    id="finance-spark-purple",
                    x1="0",
                    y1="0",
                    x2="0",
                    y2="1",
                ),
                rx.el.linear_gradient(
                    rx.el.stop(
                        offset="0%",
                        stop_color="var(--pc-success)",
                        stop_opacity="0",
                    ),
                    rx.el.stop(
                        offset="100%",
                        stop_color="var(--pc-success)",
                        stop_opacity="0",
                    ),
                    id="finance-spark-green",
                    x1="0",
                    y1="0",
                    x2="0",
                    y2="1",
                ),
            ),
            class_name="pc-finance-gradient-defs",
            aria_hidden="true",
        ),
        content,
        class_name="pc-finance-page",
    )
    return _app_shell(page, "/financeiro")
