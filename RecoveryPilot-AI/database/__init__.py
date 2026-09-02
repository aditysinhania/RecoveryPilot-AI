"""Database package: SQLAlchemy models, Alembic env, and seed scaffolding."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SHARED_SRC = _REPO_ROOT / "shared" / "src"
for _path in (_REPO_ROOT, _SHARED_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
