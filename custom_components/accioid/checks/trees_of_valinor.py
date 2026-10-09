"""The first compiled-in rule: a Tree of Valinor left switched off.

An entity counts as a Tree of Valinor when it carries the ``tree_of_valinor``
entity label. Labels are assignable at runtime (in the UI or over the registry
API), so a switch can be marked -- or a new one created and marked -- without a
restart, and the rule picks it up as soon as it appears.

The rule casts a net over the ``input_boolean`` domain, becomes interested in
whichever switches carry the label, and suggests turning each one on. Add
another marked switch and it is handled automatically, even after start-up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from ..const import LABEL_TREE_OF_VALINOR
from ..models import Location, Severity
from .base import Check, Finding

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TreesOfValinorCheck(Check):
    """Suggest turning on any Tree of Valinor that is switched off."""

    @property
    def entity_filter(self) -> dict[str, Any]:
        """Offer every ``input_boolean`` switch as a candidate.

        The label is the real selector, but the domain keeps the net (and the
        per-event filter) cheap.
        """
        return {"include_domains": ["input_boolean"]}

    def is_interested(self, hass: HomeAssistant, entity_id: str) -> bool:
        """Accept any switch carrying the Trees of Valinor label."""
        entry = er.async_get(hass).async_get(entity_id)
        return entry is not None and LABEL_TREE_OF_VALINOR in entry.labels

    def evaluate(self, hass: HomeAssistant, entity_id: str) -> Finding | None:
        """Return an active finding while the tree is off, resolved otherwise."""
        key = f"trees_of_valinor.off.{entity_id}"
        state = hass.states.get(entity_id)
        # A missing, on, or unavailable tree means the situation is not the one
        # we care about, so we deliberately close any open action.
        if state is None or state.state != "off":
            return Finding(key=key, active=False)

        name = state.name or entity_id
        return Finding(
            key=key,
            active=True,
            severity=Severity.SUGGESTION,
            title=f"Turn on {name}",
            message=f"{name} is switched off. Turn it back on to restore it.",
            location=_area_of(hass, entity_id),
            evidence={
                "entity_id": entity_id,
                "value": state.state,
                "threshold": "on",
            },
        )


def _area_of(hass: HomeAssistant, entity_id: str) -> Location:
    """Resolve the area an entity belongs to, when it is assigned to one."""
    registry_entry = er.async_get(hass).async_get(entity_id)
    area_id = registry_entry.area_id if registry_entry else None
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return Location(area_id=area_id, area_name=area.name if area else None)
