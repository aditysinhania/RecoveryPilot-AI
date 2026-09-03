"""CLI: generate the FitLife synthetic ecosystem into simulator/output/."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from simulator.dataset_generator import main

if __name__ == "__main__":
    main()
