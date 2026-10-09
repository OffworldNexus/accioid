"""Shared setup helpers for the Accioid test-suite.

The Home Assistant test harness gives each test a fresh ``hass`` with the
registries loaded, so these helpers only deal with the Accioid-specific bits:
seeding Trees of Valinor (by label), wiring a config entry and reaching the
store.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.accioid.const import (
    DOMAIN,
    LABEL_TREE_OF_VALINOR,
    TELPERION_ENTITY_ID,
)
from custom_components.accioid.store import ActionStore, get_store


def make_entry() -> MockConfigEntry:
    """Build the singleton Accioid config entry."""
    return MockConfigEntry(domain=DOMAIN, data={}, title="Accioid")


async def setup_accidio(
    hass: HomeAssistant, *, telperion: str | None = None
) -> MockConfigEntry:
    """Seed the Telperion switch (labelled), then set the integration up."""
    if telperion is not None:
        register_telperion(hass)
        set_telperion(hass, telperion)
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def store_of(hass: HomeAssistant) -> ActionStore:
    """Return the live store, failing loudly if Accioid is not set up."""
    store = get_store(hass)
    assert store is not None
    return store


def set_telperion(hass: HomeAssistant, state: str) -> None:
    """Set the Telperion switch state."""
    hass.states.async_set(TELPERION_ENTITY_ID, state, {"friendly_name": "Telperion"})


def set_tree(hass: HomeAssistant, entity_id: str, state: str, name: str) -> None:
    """Register a switch, label it a Tree of Valinor, and set its state."""
    register_switch(hass, entity_id, entity_id.split(".", 1)[1])
    set_label(hass, entity_id, LABEL_TREE_OF_VALINOR)
    hass.states.async_set(entity_id, state, {"friendly_name": name})


def register_switch(hass: HomeAssistant, entity_id: str, unique_id: str) -> str:
    """Register an ``input_boolean`` entity id (call before setting its state)."""
    domain, object_id = entity_id.split(".", 1)
    entry = er.async_get(hass).async_get_or_create(
        domain, domain, unique_id, suggested_object_id=object_id
    )
    return entry.entity_id


def set_switch(hass: HomeAssistant, entity_id: str, state: str, name: str) -> None:
    """Set a plain switch state (no marker) with a friendly name."""
    hass.states.async_set(entity_id, state, {"friendly_name": name})


def set_label(hass: HomeAssistant, entity_id: str, label_id: str) -> None:
    """Assign a label to an already-registered entity."""
    er.async_get(hass).async_update_entity(entity_id, labels={label_id})


def create_area(hass: HomeAssistant, name: str) -> ar.AreaEntry:
    """Create an area (or return the existing one)."""
    return ar.async_get(hass).async_get_or_create(name)


def register_telperion(hass: HomeAssistant, area_id: str | None = None) -> str:
    """Register the Telperion switch and label it a Tree of Valinor.

    The harness never runs the real ``input_boolean`` platform, so the entity
    registry entry is created by hand. Register before the state exists so the
    entry keeps the plain ``input_boolean.telperion`` id.
    """
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "input_boolean",
        "input_boolean",
        "telperion",
        suggested_object_id="telperion",
    )
    if area_id is not None:
        registry.async_update_entity(
            entry.entity_id, area_id=area_id, labels={LABEL_TREE_OF_VALINOR}
        )
    else:
        registry.async_update_entity(entry.entity_id, labels={LABEL_TREE_OF_VALINOR})
    return entry.entity_id


def set_area(hass: HomeAssistant, entity_id: str, area_id: str) -> None:
    """Assign an already-registered entity to an area."""
    er.async_get(hass).async_update_entity(entity_id, area_id=area_id)
