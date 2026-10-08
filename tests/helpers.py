"""Shared setup helpers for the Accioid test-suite.

The Home Assistant test harness gives each test a fresh ``hass`` with the
registries loaded, so these helpers only deal with the Accioid-specific bits:
seeding the Telperion state, wiring a config entry and reaching the store.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.accioid.const import DOMAIN, TELPERION_ENTITY_ID
from custom_components.accioid.store import ActionStore, get_store


def make_entry() -> MockConfigEntry:
    """Build the singleton Accioid config entry."""
    return MockConfigEntry(domain=DOMAIN, data={}, title="Accioid")


async def setup_accidio(
    hass: HomeAssistant, *, telperion: str | None = None
) -> MockConfigEntry:
    """Seed the Telperion switch, then set the integration up."""
    if telperion is not None:
        hass.states.async_set(TELPERION_ENTITY_ID, telperion)
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
    """Change the Telperion switch state."""
    hass.states.async_set(TELPERION_ENTITY_ID, state)


def create_area(hass: HomeAssistant, name: str) -> ar.AreaEntry:
    """Create an area (or return the existing one)."""
    return ar.async_get(hass).async_get_or_create(name)


def register_telperion(hass: HomeAssistant, area_id: str | None = None) -> str:
    """Register the switch in the entity registry, optionally in an area.

    The harness never runs the real ``input_boolean`` platform, so the entity
    registry entry is created by hand; the check only cares that looking it up
    by entity id resolves an area.
    """
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        "input_boolean",
        "input_boolean",
        "telperion",
        suggested_object_id="telperion",
    )
    if area_id is not None:
        registry.async_update_entity(entry.entity_id, area_id=area_id)
        entry = registry.async_get(entry.entity_id)
    return entry.entity_id
