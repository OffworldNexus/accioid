"""Validate repository configuration and distribution contents without HA startup.

Use the project's existing PyYAML dependency; network-dependent HACS approval
and a full Home Assistant boot are deliberately outside this smoke check.
"""

from __future__ import annotations

import argparse
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/OffworldNexus/accioid"


def require(condition: bool, message: str) -> None:
    """Fail with a useful diagnostic rather than an optimizable assertion."""
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict:
    """Load a JSON object, rejecting silently overwritten duplicate keys."""

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        """Preserve JSON objects only when every key is unique."""
        result = {}
        for key, value in pairs:
            require(key not in result, f"{path}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=unique_object
    )
    require(isinstance(value, dict), f"{path}: expected a JSON object")
    return value


def validate_configuration(root: Path) -> None:
    """Parse owned config files, excluding generated dev instances and caches."""
    paths = set(root.glob("*"))
    for directory in (".github", "scripts", "custom_components", "tests"):
        paths.update((root / directory).rglob("*"))
    for path in sorted(paths):
        if not path.is_file():
            continue
        if path.suffix == ".json":
            load_json(path)
        elif path.suffix in {".yaml", ".yml"}:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        elif path.suffix == ".toml" or path.name == "uv.lock":
            tomllib.loads(path.read_text(encoding="utf-8"))


def validate_integration(root: Path) -> None:
    """Check the local HA/HACS contract without speculative external rules."""
    integration = root / "custom_components" / "accioid"
    manifest = load_json(integration / "manifest.json")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    require(manifest.get("domain") == integration.name, "Manifest domain mismatch")
    require(manifest.get("name") == "Accioid", "Manifest name mismatch")
    require(
        manifest.get("version") == project["project"]["version"],
        "Manifest and project versions must match",
    )
    require(manifest.get("config_flow") is True, "Config flow must be enabled")
    require((integration / "config_flow.py").is_file(), "Missing config_flow.py")
    require((integration / "__init__.py").is_file(), "Missing integration entry point")
    require(manifest.get("documentation") == REPOSITORY_URL, "Wrong documentation URL")
    require(
        manifest.get("issue_tracker") == f"{REPOSITORY_URL}/issues",
        "Wrong issue tracker URL",
    )
    require(
        isinstance(manifest.get("codeowners"), list)
        and bool(manifest["codeowners"])
        and all(
            isinstance(owner, str) and owner.startswith("@")
            for owner in manifest["codeowners"]
        ),
        "Manifest must name GitHub codeowners",
    )
    hacs = load_json(root / "hacs.json")
    require(hacs.get("name") == manifest["name"], "HACS name mismatch")
    require(hacs.get("render_readme") is True, "HACS must render the README")
    require((root / "README.md").is_file(), "Missing HACS README")
    require(
        load_json(integration / "strings.json")
        == load_json(integration / "translations" / "en.json"),
        "English translation must match strings.json",
    )


def validate_distributions(root: Path, dist: Path) -> None:
    """Ensure both build formats ship every owned integration module and asset."""
    integration = root / "custom_components" / "accioid"
    required = {
        path.relative_to(root).as_posix()
        for path in integration.rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".js", ".yaml", ".yml"}
    }
    wheels = list(dist.glob("*.whl"))
    sources = list(dist.glob("*.tar.gz"))
    require(len(wheels) == 1 and len(sources) == 1, "Expected one wheel and one sdist")
    with zipfile.ZipFile(wheels[0]) as archive:
        missing = required - set(archive.namelist())
        require(not missing, f"Wheel missing integration files: {sorted(missing)}")
    with tarfile.open(sources[0], "r:gz") as archive:
        # An sdist wraps all files in its project-version directory.
        names = {name.partition("/")[2] for name in archive.getnames()}
        missing = required - names
        require(not missing, f"Sdist missing integration files: {sorted(missing)}")
        require(
            "hacs.json" in names and "README.md" in names, "Sdist missing HACS metadata"
        )


def main() -> None:
    """Expose the same deterministic checks to CI and developer commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, help="Also inspect built distributions")
    args = parser.parse_args()
    validate_configuration(ROOT)
    validate_integration(ROOT)
    if args.dist is not None:
        validate_distributions(ROOT, args.dist)
    print("Configuration and integration metadata are valid.")


if __name__ == "__main__":
    main()
