"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    good = FIXTURES / "good_series"
    if not good.exists():
        pytest.skip("Fixtures missing — run: uv run python ../scripts/generate_fixtures.py")
    return FIXTURES
