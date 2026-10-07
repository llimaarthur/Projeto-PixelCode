import reflex as rx

from rxconfig import config
from frontend.auth_state import register_pages


app = rx.App(
    stylesheets=["/styles.css"],
)
register_pages(app)
