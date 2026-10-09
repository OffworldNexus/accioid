"""The Accioid WebSocket API: list actions and stream lifecycle changes.

This is the read path the rough Lovelace card uses. Commands are registered
globally in ``async_setup`` and look the store up dynamically, so they survive
a config-entry reload without re-registering.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from .const import (
    DEFAULT_LIMIT,
    LIFECYCLE_EVENTS,
    MAX_LIMIT,
    WS_TYPE_LIST,
    WS_TYPE_SUBSCRIBE,
)
from .models import ActionState, Disposition, Severity
from .store import get_store

if TYPE_CHECKING:
    from homeassistant.components.websocket_api import ActiveConnection
    from homeassistant.core import Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)


def async_setup(hass: HomeAssistant) -> None:
    """Register the Accioid WebSocket commands."""
    websocket_api.async_register_command(hass, _ws_list_actions)
    websocket_api.async_register_command(hass, _ws_subscribe_actions)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_LIST,
        vol.Optional("state"): vol.In([state.value for state in ActionState]),
        vol.Optional("disposition"): vol.In(
            [disposition.value for disposition in Disposition]
        ),
        vol.Optional("severity"): vol.In([severity.value for severity in Severity]),
        vol.Optional("area_id"): str,
        vol.Optional("limit", default=DEFAULT_LIMIT): vol.All(
            int, vol.Range(min=1, max=MAX_LIMIT)
        ),
        vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0)),
    }
)
@websocket_api.async_response
async def _ws_list_actions(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send back a filtered, paginated page of actions."""
    store = get_store(hass)
    if store is None:
        connection.send_result(msg["id"], {"actions": [], "total": 0})
        return
    actions, total = store.list_actions(
        state=msg.get("state"),
        disposition=msg.get("disposition"),
        severity=msg.get("severity"),
        area_id=msg.get("area_id"),
        limit=msg["limit"],
        offset=msg["offset"],
    )
    connection.send_result(
        msg["id"],
        {"actions": [action.as_dict() for action in actions], "total": total},
    )


@websocket_api.websocket_command({vol.Required("type"): WS_TYPE_SUBSCRIBE})
@websocket_api.async_response
async def _ws_subscribe_actions(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Forward the three lifecycle bus events to the subscriber."""

    @callback
    def forward(event: Event) -> None:
        connection.send_event(
            msg["id"],
            {"event": event.event_type, "action": event.data},
        )

    unsubs = [
        hass.bus.async_listen(event_name, forward) for event_name in LIFECYCLE_EVENTS
    ]

    @callback
    def unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
