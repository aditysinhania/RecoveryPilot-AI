"""ASGI entrypoint. The application is built exclusively by ``create_app()``."""

from app.core.lifespan import create_app

app = create_app()
