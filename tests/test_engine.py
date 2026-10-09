"""Tests for the query-driven check engine (filter + interest stages)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.accioid.checks.base import Check, Finding
from custom_components.accioid.engine import CheckEngine
from custom_components.accioid.store import ActionStore


class _RecordingCheck(Check):
    """A check that records what the engine presents to it."""

    def __init__(self) -> None:
        """Start with empty observation logs."""
        self.offered: list[str] = []
        self.evaluated: list[str] = []

    @property
    def entity_filter(self) -> dict[str, Any]:
        """Watch the whole ``sensor`` domain."""
        return {"include_domains": ["sensor"]}

    def is_interested(self, hass: HomeAssistant, entity_id: str) -> bool:
        """Record every candidate and accept only ``*_watched``."""
        self.offered.append(entity_id)
        return entity_id.endswith("_watched")

    def evaluate(self, hass: HomeAssistant, entity_id: str) -> Finding | None:
        """Open an action while the accepted sensor is ``on``."""
        self.evaluated.append(entity_id)
        key = f"recording.{entity_id}"
        state = hass.states.get(entity_id)
        if state is None or state.state != "on":
            return Finding(key=key, active=False)
        return Finding(key=key, active=True, title="Watched")


async def test_engine_offers_the_filtered_domain_then_narrows(
    hass: HomeAssistant,
) -> None:
    """Every sensor is offered to the interest stage; only some are evaluated."""
    store = ActionStore(hass)
    check = _RecordingCheck()
    engine = CheckEngine(hass, store, [check])
    hass.states.async_set("sensor.a_watched", "on")
    hass.states.async_set("sensor.b_ignored", "on")
    hass.states.async_set("binary_sensor.c_watched", "on")

    engine.start()
    await hass.async_block_till_done()

    assert set(check.offered) == {"sensor.a_watched", "sensor.b_ignored"}
    assert check.evaluated == ["sensor.a_watched"]
    actions, total = store.list_actions(state="open")
    assert total == 1
    assert actions[0].title == "Watched"
    engine.stop()


async def test_engine_catches_up_entities_created_later(
    hass: HomeAssistant,
) -> None:
    """A matching entity created after start-up is picked up automatically."""
    store = ActionStore(hass)
    check = _RecordingCheck()
    engine = CheckEngine(hass, store, [check])
    engine.start()
    await hass.async_block_till_done()
    assert store.list_actions(state="open")[1] == 0

    hass.states.async_set("sensor.late_watched", "on")
    await hass.async_block_till_done()

    assert "sensor.late_watched" in check.evaluated
    assert store.list_actions(state="open")[1] == 1
    engine.stop()


async def test_engine_closes_when_entity_disappears(hass: HomeAssistant) -> None:
    """A removed entity gets one last evaluation that closes its action."""
    store = ActionStore(hass)
    check = _RecordingCheck()
    engine = CheckEngine(hass, store, [check])
    hass.states.async_set("sensor.gone_watched", "on")
    engine.start()
    await hass.async_block_till_done()
    assert store.list_actions(state="open")[1] == 1

    hass.states.async_remove("sensor.gone_watched")
    await hass.async_block_till_done()

    assert store.list_actions(state="open")[1] == 0
    assert store.list_actions(state="closed")[1] == 1
    engine.stop()
