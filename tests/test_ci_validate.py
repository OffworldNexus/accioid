"""Regression coverage for the repository-only CI validation smoke checks."""

from __future__ import annotations

import runpy
import shutil
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = runpy.run_path(str(ROOT / "scripts" / "ci_validate.py"))


def test_repository_configuration_is_valid() -> None:
    """The checked-in HA/HACS metadata and config pass the local validator."""
    VALIDATOR["validate_configuration"](ROOT)
    VALIDATOR["validate_integration"](ROOT)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    """Duplicate keys must not silently mask malformed integration metadata."""
    path = tmp_path / "manifest.json"
    path.write_text('{"domain": "accioid", "domain": "other"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        VALIDATOR["load_json"](path)


def test_version_drift_is_rejected(tmp_path: Path) -> None:
    """Packaging and HACS must advertise the same integration release version."""
    shutil.copytree(ROOT / "custom_components", tmp_path / "custom_components")
    for filename in ("hacs.json", "README.md", "pyproject.toml"):
        shutil.copyfile(ROOT / filename, tmp_path / filename)
    project = tmp_path / "pyproject.toml"
    metadata = tomllib.loads(project.read_text(encoding="utf-8"))
    current_version = metadata["project"]["version"]
    project.write_text(
        project.read_text(encoding="utf-8").replace(
            f'version = "{current_version}"', 'version = "999.0.0"', 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="versions must match"):
        VALIDATOR["validate_integration"](tmp_path)
