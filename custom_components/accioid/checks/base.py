"""The check abstraction: a compiled-in rule that inspects Home Assistant.

A check is evaluated on start-up and whenever one of the entities it watches
changes. It never mutates the store itself -- it returns findings and the
engine applies the open/close lifecycle. That keeps each rule declarative and
the lifecycle in exactly one place.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..models import Location, Severity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@dataclass(slots=True)
class Finding:
    """One situation a check observed, either active or resolved.

    ``key`` is the situation's stable identity and is always present, so a
    resolved finding (``active=False``) still points at the action to close.
    The rich fields only matter while ``active`` is true.
    """

    key: str
    active: bool
    severity: Severity = Severity.SUGGESTION
    title: str = ""
    message: str = ""
    location: Location = field(default_factory=Location)
    evidence: dict[str, Any] = field(default_factory=dict)


class Check(ABC):
    """A compiled-in rule that produces findings from current HA state."""

    @property
    @abstractmethod
    def watched_entities(self) -> tuple[str, ...]:
        """Return the entity ids whose changes should re-trigger evaluation."""

    @abstractmethod
    def evaluate(self, hass: HomeAssistant) -> list[Finding]:
        """Inspect the current state and return this check's findings."""
