"""Pagination helper unit tests. No database."""

from __future__ import annotations

from app.utils.pagination import build_page_meta, normalize_page


def test_normalize_page_clamps_size_and_offset() -> None:
    """Page size is capped and offset is (page - 1) * size."""
    pager = normalize_page(page=3, size=500)
    assert pager.page == 3
    assert pager.size == 100
    assert pager.offset == 200


def test_build_page_meta_empty() -> None:
    """Zero records yield zero pages and no next/previous."""
    meta = build_page_meta(page=1, page_size=25, total_records=0)
    assert meta.total_records == 0
    assert meta.total_pages == 0
    assert meta.has_next is False
    assert meta.has_previous is False
    assert meta.offset == 0


def test_build_page_meta_window() -> None:
    """has_next / has_previous follow the current page against total_pages."""
    meta = build_page_meta(page=2, page_size=10, total_records=25)
    assert meta.total_records == 25
    assert meta.total_pages == 3
    assert meta.has_next is True
    assert meta.has_previous is True
    assert meta.page_size == 10
    assert meta.offset == 10
