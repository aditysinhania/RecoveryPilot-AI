"""Small helpers shared by middleware, responses, and routers."""

from app.utils.json import dumps, redact_mapping
from app.utils.pagination import Page, normalize_page
from app.utils.request_id import (
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
)
from app.utils.time import isoformat_now, utc_now
from app.utils.uuid import new_uuid, new_uuid_str

__all__ = [
    "Page",
    "dumps",
    "get_correlation_id",
    "get_request_id",
    "isoformat_now",
    "new_uuid",
    "new_uuid_str",
    "normalize_page",
    "redact_mapping",
    "set_correlation_id",
    "set_request_id",
    "utc_now",
]
