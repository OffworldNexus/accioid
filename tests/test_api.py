"""Tests for the Accioid read API: the service and the WebSocket commands."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.accioid.const import (
    DOMAIN,
    EVENT_ACTION_CLOSED,
    SERVICE_LIST_ACTIONS,
    WS_TYPE_LIST,
    WS_TYPE_SUBSCRIBE,
)
from tests.helpers import set_telperion, setup_accidio, store_of


async def test_service_lists_open_actions(hass: HomeAssistant) -> None:
    """The read service returns the open action as JSON."""
    await setup_accidio(hass, telperion="off")
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_LIST_ACTIONS,
        {},
        blocking=True,
        return_response=True,
    )

    assert response["total"] == 1
    assert response["actions"][0]["title"] == "Turn on Telperion"
    assert response["actions"][0]["state"] == "open"


async def test_service_filters_by_state(hass: HomeAssistant) -> None:
    """Past (closed) actions are listable and filterable."""
    await setup_accidio(hass, telperion="off")
    action = store_of(hass).list_actions(state="open")[0][0]

    set_telperion(hass, "on")
    await hass.async_block_till_done()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_LIST_ACTIONS,
        {"state": "closed"},
        blocking=True,
        return_response=True,
    )
    assert response["total"] == 1
    assert response["actions"][0]["id"] == action.id


async def test_websocket_list_and_subscribe(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """The card can list actions and receive lifecycle pushes."""
    await setup_accidio(hass, telperion="off")
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": WS_TYPE_LIST})
    listed = await client.receive_json()
    assert listed["success"]
    assert listed["result"]["total"] == 1

    await client.send_json({"id": 2, "type": WS_TYPE_SUBSCRIBE})
    subscribed = await client.receive_json()
    assert subscribed["success"]

    set_telperion(hass, "on")
    await hass.async_block_till_done()

    pushed = await client.receive_json()
    assert pushed["type"] == "event"
    assert pushed["event"]["event"] == EVENT_ACTION_CLOSED
    assert pushed["event"]["action"]["state"] == "closed"


async def test_websocket_list_filters(hass: HomeAssistant, hass_ws_client) -> None:
    """Filters are honoured over WebSocket too."""
    await setup_accidio(hass, telperion="off")
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": WS_TYPE_LIST, "severity": "emergency"})
    result = (await client.receive_json())["result"]
    assert result["total"] == 0
    assert result["actions"] == []
