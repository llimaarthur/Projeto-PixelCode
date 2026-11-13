import reflex as rx


def intl_currency(value: rx.Var) -> rx.Var:
    return rx.Var(
        _js_expr=(
            'new Intl.NumberFormat("pt-BR", '
            '{style: "currency", currency: "BRL"}).format('
            f"{value})"
        ),
        _var_type=str,
        _var_data=value._get_all_var_data(),
    )


def block_error(message: rx.Var) -> rx.Component:
    return rx.box(
        rx.icon("triangle-alert", size=18, aria_hidden="true"),
        rx.text(message),
        role="alert",
        class_name="pc-finance-error",
    )


def empty_state(title: str, description: str) -> rx.Component:
    return rx.vstack(
        rx.icon("chart-no-axes-combined", size=22, aria_hidden="true"),
        rx.text(title, class_name="pc-finance-empty-title"),
        rx.text(description, class_name="pc-finance-empty-copy"),
        align="center",
        spacing="2",
        class_name="pc-finance-empty",
    )


def skeleton(class_name: str, label: str) -> rx.Component:
    return rx.box(
        rx.text(label, class_name="pc-visually-hidden"),
        role="status",
        aria_label=label,
        class_name=f"pc-finance-skeleton {class_name}",
    )


def sparkline(
    item: rx.Var,
    aria_label: str = "Tendência de recebimentos",
) -> rx.Component:
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
        aria_label=aria_label,
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


def metric_card(
    item: rx.Var,
    value_type: str = "currency",
    sparkline_label: str = "Tendência de recebimentos",
    icon_name: str = "chart-no-axes-combined",
) -> rx.Component:
    value = (
        intl_currency(item["current"])
        if value_type == "currency"
        else item["current"]
    )
    return rx.el.article(
        rx.box(
            rx.icon(icon_name, size=21, aria_hidden="true"),
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
            rx.text(value, class_name="pc-finance-kpi-value"),
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
        sparkline(item, sparkline_label),
        class_name="pc-finance-kpi-card",
    )


def transaction_summary(item: rx.Var) -> rx.Component:
    is_income = item["type"] == "income"
    return rx.hstack(
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
                    intl_currency(item["amount"]),
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
    )


def readonly_transaction_row(item: rx.Var) -> rx.Component:
    return rx.vstack(
        transaction_summary(item),
        rx.cond(
            item["is_cancelled"],
            rx.badge(
                "Estornada",
                color_scheme="red",
                variant="soft",
                class_name="pc-finance-cancelled-badge",
            ),
            rx.fragment(),
        ),
        class_name="pc-finance-transaction-entry pc-overview-transaction-entry",
        align="stretch",
        spacing="2",
    )
