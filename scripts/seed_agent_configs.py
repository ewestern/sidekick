#!/usr/bin/env python3
"""Upsert agent_configs. Run from repo root:

    uv run --directory services/ingestion python -m sidekick.seed_configs

Or: sidekick seed-configs (after uv sync in workspace).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    ing = root / "services" / "ingestion"
    r = subprocess.run(
        [
            "uv",
            "run",
            "--directory",
            str(ing),
            "python",
            "-m",
            "sidekick.seed_configs",
        ],
        cwd=root,
    )
    sys.exit(r.returncode)
