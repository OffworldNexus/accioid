"""The compiled-in set of checks this build of Accioid ships with."""

from __future__ import annotations

from .base import Check, Finding
from .trees_of_valinor import TreesOfValinorCheck


def default_checks() -> list[Check]:
    """Return the checks Accioid evaluates, in a deterministic order."""
    return [TreesOfValinorCheck()]


__all__ = ["Check", "Finding", "TreesOfValinorCheck", "default_checks"]
