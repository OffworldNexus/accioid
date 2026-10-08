"""The Accioid core data model: actions, events and their vocabularies.

This mirrors the target data model document. Ticket 1 only exercises part of
it (key derivation, open/closed and the create/close lifecycle) but the shapes
are complete so later features can build on them without a migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


class Severity(StrEnum):
    """How much attention an action deserves."""

    MAINTENANCE = "maintenance"
    SUGGESTION = "suggestion"
    EMERGENCY = "emergency"


class ActionState(StrEnum):
    """Whether the situation behind an action is currently relevant."""

    OPEN = "open"
    CLOSED = "closed"


class Disposition(StrEnum):
    """How an action should be surfaced; orthogonal to its state."""

    NORMAL = "normal"
    SNOOZED = "snoozed"
    IGNORED = "ignored"


class Actor(StrEnum):
    """Who caused an event."""

    SYSTEM = "system"
    USER = "user"
    API = "api"


class EventType(StrEnum):
    """The kinds of change recorded in the append-only log."""

    OPENED = "opened"
    CLOSED = "closed"
    SNOOZED = "snoozed"
    IGNORED = "ignored"
    NORMALISED = "normalised"


@dataclass(slots=True)
class Location:
    """Where an action applies: a Home Assistant area, when assigned."""

    area_id: str | None = None
    area_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form used by the API and events."""
        return {"area_id": self.area_id, "area_name": self.area_name}


@dataclass(slots=True)
class Action:
    """The current, materialised state of one action occurrence.

    Timestamps are deliberately absent: they live in the event log.
    """

    id: str
    key: str
    severity: Severity
    location: Location
    title: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    state: ActionState = ActionState.OPEN
    disposition: Disposition = Disposition.NORMAL
    snoozed_until: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form used by the API and events."""
        return {
            "id": self.id,
            "key": self.key,
            "severity": self.severity.value,
            "location": self.location.as_dict(),
            "title": self.title,
            "message": self.message,
            "evidence": self.evidence,
            "state": self.state.value,
            "disposition": self.disposition.value,
            "snoozed_until": (
                self.snoozed_until.isoformat() if self.snoozed_until else None
            ),
        }


@dataclass(slots=True)
class ActionEvent:
    """One entry in the append-only action history."""

    id: str
    action_id: str
    type: EventType
    at: datetime
    actor: Actor
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form used by the API."""
        return {
            "id": self.id,
            "action_id": self.action_id,
            "type": self.type.value,
            "at": self.at.isoformat(),
            "actor": self.actor.value,
            "data": self.data,
        }
