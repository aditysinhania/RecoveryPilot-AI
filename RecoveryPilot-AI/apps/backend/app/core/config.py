"""Compatibility re-export. Canonical settings live in ``app.config.settings``."""

from app.config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
