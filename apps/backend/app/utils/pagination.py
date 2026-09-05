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


@dataclass(frozen=True)
class PageMeta:
    """Pagination metadata returned on list endpoints."""

    page: int
    page_size: int
    total_records: int
    total_pages: int
    has_next: bool
    has_previous: bool
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


def build_page_meta(
    page: int,
    page_size: int,
    total_records: int,
) -> PageMeta:
    """Build pagination metadata from a 1-based page request and a total count.

    Args:
        page: Requested 1-based page index.
        page_size: Requested page length (clamped like ``normalize_page``).
        total_records: Unfiltered (or filter-matching) row count.

    Returns:
        Offset plus ``total_pages`` / ``has_next`` / ``has_previous``.
    """
    pager = normalize_page(page, page_size)
    safe_total = max(0, total_records)
    total_pages = (safe_total + pager.size - 1) // pager.size if safe_total else 0
    return PageMeta(
        page=pager.page,
        page_size=pager.size,
        total_records=safe_total,
        total_pages=total_pages,
        has_next=pager.page < total_pages,
        has_previous=pager.page > 1,
        offset=pager.offset,
    )
