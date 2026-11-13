import reflex as rx

config = rx.Config(
    app_name="frontend",
    backend_port=3002,
    cors_allowed_origins=("*",),
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="dark",
                accent_color="blue",
                gray_color="slate",
                radius="large",
            )
        ),
    ]
)