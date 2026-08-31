from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def test_runs_on_python_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_env_example_declares_no_values() -> None:
    """A committed .env.example must name secrets, never carry them."""
    lines = Path(__file__).parents[1].joinpath(".env.example").read_text().splitlines()
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        assert value == "" or key == "NIFTY_SHOP_ALLOW_LIVE", f"{key} has a committed value"


def test_lint_config_forbids_blind_except() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as fh:
        cfg = tomllib.load(fh)
    selected = cfg["tool"]["ruff"]["lint"]["select"]
    assert "BLE" in selected, "spec requires no bare except"
    assert "DTZ" in selected, "spec requires timezone-aware datetimes"
    assert cfg["tool"]["mypy"]["strict"] is True
