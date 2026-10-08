"""Tests for the first hard-coded Telperion check."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.accioid.const import TELPERION_ENTITY_ID
from custom_components.accioid.models import (
    ActionState,
    Disposition,
    Severity,
)
from tests.helpers import (
    create_area,
    register_telperion,
    set_telperion,
    setup_accidio,
    store_of,
)


async def test_startup_creates_action_when_off(hass: HomeAssistant) -> None:
    """An off switch at start-up yields exactly one open suggestion."""
    await setup_accidio(hass, telperion="off")
    actions, total = store_of(hass).list_actions(state="open")

    assert total == 1
    action = actions[0]
    assert action.title == "Turn on Telperion"
    assert action.severity is Severity.SUGGESTION
    assert action.state is ActionState.OPEN
    assert action.disposition is Disposition.NORMAL
    assert action.key.endswith(TELPERION_ENTITY_ID)
    assert action.evidence["value"] == "off"


async def test_startup_creates_nothing_when_on(hass: HomeAssistant) -> None:
    """An on switch is not a situation worth an action."""
    await setup_accidio(hass, telperion="on")
    assert store_of(hass).list_actions(state="open")[1] == 0


async def test_off_on_off_creates_a_new_action(hass: HomeAssistant) -> None:
    """Turning off creates, turning on closes, turning off again recreates."""
    await setup_accidio(hass, telperion="on")
    store = store_of(hass)

    set_telperion(hass, "off")
    await hass.async_block_till_done()
    first, total = store.list_actions(state="open")
    assert total == 1
    first_id = first[0].id

    set_telperion(hass, "on")
    await hass.async_block_till_done()
    assert store.list_actions(state="open")[1] == 0
    assert store.get(first_id).state is ActionState.CLOSED

    set_telperion(hass, "off")
    await hass.async_block_till_done()
    open_actions, total = store.list_actions(state="open")
    assert total == 1
    assert open_actions[0].id != first_id


async def test_action_is_scoped_to_the_switch_area(hass: HomeAssistant) -> None:
    """The action carries the area the switch is assigned to."""
    area = create_area(hass, "Dev Room")
    register_telperion(hass, area_id=area.id)
    await setup_accidio(hass, telperion="off")

    action = store_of(hass).list_actions(state="open")[0][0]
    assert action.location.area_id == area.id
    assert action.location.area_name == "Dev Room"


async def test_action_without_area_has_an_empty_location(hass: HomeAssistant) -> None:
    """An unassigned switch still produces an action, just without a room."""
    register_telperion(hass)
    await setup_accidio(hass, telperion="off")

    action = store_of(hass).list_actions(state="open")[0][0]
    assert action.location.area_id is None
    assert action.location.area_name is None
