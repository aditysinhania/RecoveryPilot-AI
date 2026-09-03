"""UUID helpers."""

from __future__ import annotations

from uuid import UUID, uuid4


def new_uuid() -> UUID:
    """Return a random UUID4."""
    return uuid4()


def new_uuid_str() -> str:
    """Return a random UUID4 as a string."""
    return str(uuid4())
