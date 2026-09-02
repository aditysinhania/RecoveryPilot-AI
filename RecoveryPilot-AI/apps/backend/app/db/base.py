"""SQLAlchemy declarative base. Models in `app.models` subclass this."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata base for all ORM models."""
