"""Resolve fixture paths for local dev and Docker."""

from __future__ import annotations

import os
from pathlib import Path

# backend/app/paths.py → repo root is parents[2] locally; Docker uses /fixtures.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def fixtures_root() -> Path:
    env = os.environ.get("FIXTURES_ROOT")
    if env:
        return Path(env)
    docker = Path("/fixtures")
    if docker.is_dir():
        return docker
    return _REPO_ROOT / "fixtures"
