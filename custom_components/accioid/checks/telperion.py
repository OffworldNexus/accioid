"""The first hard-coded rule: Telperion (a virtual switch) left off.

When ``input_boolean.telperion`` is off, Accioid suggests turning it on. The
action is keyed by the entity, so the same occurrence never duplicates, and is
scoped to whatever area the switch lives in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from ..const import TELPERION_ENTITY_ID
from ..models import Location, Severity
from .base import Check, Finding

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TelperionCheck(Check):
    """Suggest turning Telperion on while it is off."""

    @property
    def watched_entities(self) -> tuple[str, ...]:
        """Watch the one Telperion switch."""
        return (TELPERION_ENTITY_ID,)

    def evaluate(self, hass: HomeAssistant) -> list[Finding]:
        """Return an active finding while the switch is off, resolved otherwise."""
        key = f"telperion.off.{TELPERION_ENTITY_ID}"
        state = hass.states.get(TELPERION_ENTITY_ID)
        # A missing, on, or unavailable switch means the situation is not the
        # one we care about, so we deliberately close any open action.
        if state is None or state.state != "off":
            return [Finding(key=key, active=False)]

        return [
            Finding(
                key=key,
                active=True,
                severity=Severity.SUGGESTION,
                title="Turn on Telperion",
                message="Telperion is switched off. Turn it back on to restore it.",
                location=_area_of(hass, TELPERION_ENTITY_ID),
                evidence={
                    "entity_id": TELPERION_ENTITY_ID,
                    "value": state.state,
                    "threshold": "on",
                },
            )
        ]


def _area_of(hass: HomeAssistant, entity_id: str) -> Location:
    """Resolve the area an entity belongs to, when it is assigned to one."""
    registry_entry = er.async_get(hass).async_get(entity_id)
    area_id = registry_entry.area_id if registry_entry else None
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return Location(area_id=area_id, area_name=area.name if area else None)
