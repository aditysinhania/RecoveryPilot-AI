"""Pagination helpers. No database queries here."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


@dataclass(frozen=True)
class Page:
    """Normalized page and size after clamping."""

    page: int
    size: int
    offset: int


def normalize_page(page: int = 1, size: int = DEFAULT_PAGE_SIZE) -> Page:
    """Clamp page/size and compute a SQL offset.

    Args:
        page: 1-based page index.
        size: Requested page length.

    Returns:
        A ``Page`` with ``size`` capped at ``MAX_PAGE_SIZE``.
    """
    safe_page = max(1, page)
    safe_size = min(MAX_PAGE_SIZE, max(1, size))
    return Page(page=safe_page, size=safe_size, offset=(safe_page - 1) * safe_size)
