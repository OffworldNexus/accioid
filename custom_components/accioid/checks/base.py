"""The check abstraction: a compiled-in rule over a set of entities.

A check describes the entities it cares about with a Home Assistant entity
filter -- the same include/exclude config used by history and the recorder.
The engine watches that query, offers every matching entity to
:meth:`Check.is_interested` and, for the ones the check accepts, calls
:meth:`Check.evaluate`. Entities created after start-up are offered as soon as
they appear, so a check never hard-codes an entity id or listens for anything
itself.
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
    """One situation a check observed for one entity, active or resolved.

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
    """A compiled-in rule that selects a set of entities, then evaluates them."""

    @property
    @abstractmethod
    def entity_filter(self) -> dict[str, Any]:
        """Return an entity-filter config selecting the candidate entities.

        The config uses the standard Home Assistant keys ``include_domains``,
        ``include_entity_globs``, ``include_entities`` and their ``exclude_``
        counterparts. Every entity currently -- or later -- matching it is
        offered to :meth:`is_interested`.
        """

    def is_interested(self, hass: HomeAssistant, entity_id: str) -> bool:
        """Return whether the check cares about a candidate entity.

        This is the second stage after the filter: the filter casts a wide net,
        and this decides, entity by entity, whether the rule applies. It is
        called with the entity's *current* state present (except on removal),
        so it may inspect state, attributes or the registry.
        """
        return True

    @abstractmethod
    def evaluate(self, hass: HomeAssistant, entity_id: str) -> Finding | None:
        """Return the finding for one accepted entity, or ``None``.

        Called on start-up, on every state change, when the entity appears and
        just before it disappears -- so an inactive finding closes the action
        when the entity is removed.
        """
