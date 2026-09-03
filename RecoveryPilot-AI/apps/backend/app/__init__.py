"""RecoveryPilot AI FastAPI application package."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SHARED_SRC = _REPO_ROOT / "shared" / "src"
_SERVICES_SRC = _REPO_ROOT / "services" / "src"
for _path in (_REPO_ROOT, _SHARED_SRC, _SERVICES_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
