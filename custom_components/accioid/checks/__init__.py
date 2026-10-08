"""The compiled-in set of checks this build of Accioid ships with."""

from __future__ import annotations

from .base import Check, Finding
from .telperion import TelperionCheck


def default_checks() -> list[Check]:
    """Return the checks Accioid evaluates, in a deterministic order."""
    return [TelperionCheck()]


__all__ = ["Check", "Finding", "TelperionCheck", "default_checks"]
