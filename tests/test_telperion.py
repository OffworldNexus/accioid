"""Tests for the first hard-coded Telperion check."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.accioid.const import (
    LABEL_TREE_OF_VALINOR,
    TELPERION_ENTITY_ID,
)
from custom_components.accioid.models import (
    ActionState,
    Disposition,
    Severity,
)
from tests.helpers import (
    create_area,
    register_switch,
    register_telperion,
    set_area,
    set_label,
    set_switch,
    set_telperion,
    set_tree,
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


async def test_action_appears_when_switch_is_created_later(
    hass: HomeAssistant,
) -> None:
    """The rule discovers the switch whenever it appears, not only at boot."""
    await setup_accidio(hass)  # the fixture switch does not exist yet
    assert store_of(hass).list_actions(state="open")[1] == 0

    set_tree(hass, TELPERION_ENTITY_ID, "off", "Telperion")
    await hass.async_block_till_done()

    actions, total = store_of(hass).list_actions(state="open")
    assert total == 1
    assert actions[0].title == "Turn on Telperion"


async def test_a_second_marked_tree_is_checked_too(
    hass: HomeAssistant,
) -> None:
    """Adding another marked switch makes the rule act on it as well."""
    await setup_accidio(hass, telperion="on")
    assert store_of(hass).list_actions(state="open")[1] == 0

    set_tree(hass, "input_boolean.laurelin", "off", "Laurelin")
    await hass.async_block_till_done()

    actions, total = store_of(hass).list_actions(state="open")
    assert total == 1
    assert actions[0].title == "Turn on Laurelin"
    assert actions[0].key.endswith("input_boolean.laurelin")


async def test_unmarked_switch_is_ignored(hass: HomeAssistant) -> None:
    """The domain filter casts a wide net; the marker narrows it."""
    await setup_accidio(hass)
    hass.states.async_set("input_boolean.plain", "off")
    await hass.async_block_till_done()
    assert store_of(hass).list_actions(state="open")[1] == 0


async def test_label_added_live_makes_a_switch_interesting(
    hass: HomeAssistant,
) -> None:
    """A label assigned at runtime is picked up without a restart."""
    register_switch(hass, "input_boolean.laurelin", "laurelin")
    set_switch(hass, "input_boolean.laurelin", "off", "Laurelin")
    await setup_accidio(hass, telperion="on")
    assert store_of(hass).list_actions(state="open")[1] == 0

    set_label(hass, "input_boolean.laurelin", LABEL_TREE_OF_VALINOR)
    await hass.async_block_till_done()

    actions, total = store_of(hass).list_actions(state="open")
    assert total == 1
    assert actions[0].title == "Turn on Laurelin"
    assert actions[0].key.endswith("input_boolean.laurelin")


async def test_removing_the_label_closes_the_action(
    hass: HomeAssistant,
) -> None:
    """Revoking the marker resolves the action, even though the state is off."""
    register_switch(hass, "input_boolean.laurelin", "laurelin")
    set_switch(hass, "input_boolean.laurelin", "off", "Laurelin")
    set_label(hass, "input_boolean.laurelin", LABEL_TREE_OF_VALINOR)
    await setup_accidio(hass, telperion="on")
    assert store_of(hass).list_actions(state="open")[1] == 1

    er.async_get(hass).async_update_entity("input_boolean.laurelin", labels=set())
    await hass.async_block_till_done()

    assert store_of(hass).list_actions(state="open")[1] == 0


async def test_action_is_scoped_to_the_switch_area(hass: HomeAssistant) -> None:
    """The action carries the area the switch is assigned to."""
    area = create_area(hass, "Dev Room")
    register_telperion(hass, area_id=area.id)
    await setup_accidio(hass, telperion="off")

    action = store_of(hass).list_actions(state="open")[0][0]
    assert action.location.area_id == area.id
    assert action.location.area_name == "Dev Room"


async def test_area_set_after_creation_updates_location(
    hass: HomeAssistant,
) -> None:
    """A later area assignment is reflected through the registry watcher."""
    register_telperion(hass)
    await setup_accidio(hass, telperion="off")
    action = store_of(hass).list_actions(state="open")[0][0]
    assert action.location.area_id is None

    area = create_area(hass, "Dev Room")
    set_area(hass, TELPERION_ENTITY_ID, area.id)
    await hass.async_block_till_done()

    updated = store_of(hass).get(action.id)
    assert updated is not None
    assert updated.location.area_name == "Dev Room"


async def test_action_without_area_has_an_empty_location(hass: HomeAssistant) -> None:
    """An unassigned switch still produces an action, just without a room."""
    register_telperion(hass)
    await setup_accidio(hass, telperion="off")

    action = store_of(hass).list_actions(state="open")[0][0]
    assert action.location.area_id is None
    assert action.location.area_name is None
