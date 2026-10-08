"""Home Assistant services Accioid exposes to automations.

The list service is read-only and therefore registered with
``SupportsResponse.ONLY``: callers must ask for the response, which keeps it
out of the regular service-call noise.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_LIMIT,
    DOMAIN,
    MAX_LIMIT,
    SERVICE_LIST_ACTIONS,
)
from .models import ActionState, Disposition, Severity
from .store import get_store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

_LIST_SCHEMA = vol.Schema(
    {
        vol.Optional("state"): vol.In([state.value for state in ActionState]),
        vol.Optional("disposition"): vol.In(
            [disposition.value for disposition in Disposition]
        ),
        vol.Optional("severity"): vol.In([severity.value for severity in Severity]),
        vol.Optional("area_id"): cv.string,
        vol.Optional("limit", default=DEFAULT_LIMIT): vol.All(
            int, vol.Range(min=1, max=MAX_LIMIT)
        ),
        vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0)),
    }
)


def async_setup(hass: HomeAssistant) -> None:
    """Register the Accioid services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_ACTIONS,
        _handle_list_actions,
        schema=_LIST_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload(hass: HomeAssistant) -> None:
    """Remove the Accioid services."""
    hass.services.async_remove(DOMAIN, SERVICE_LIST_ACTIONS)


async def _handle_list_actions(call: ServiceCall) -> dict[str, Any]:
    """Return the requested page of actions and the filtered total."""
    store = get_store(call.hass)
    if store is None:
        return {"actions": [], "total": 0}
    actions, total = store.list_actions(
        state=call.data.get("state"),
        disposition=call.data.get("disposition"),
        severity=call.data.get("severity"),
        area_id=call.data.get("area_id"),
        limit=call.data["limit"],
        offset=call.data["offset"],
    )
    return {"actions": [action.as_dict() for action in actions], "total": total}
