"""Tests for the action store lifecycle, filters, history and bus events."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.accioid.const import (
    EVENT_ACTION_CHANGED,
    EVENT_ACTION_CLOSED,
    EVENT_ACTION_CREATED,
)
from custom_components.accioid.models import (
    ActionState,
    EventType,
    Location,
    Severity,
)
from custom_components.accioid.store import ActionStore


def _draft(
    key: str = "telperion.off.input_boolean.telperion",
    *,
    severity: Severity = Severity.SUGGESTION,
    area_id: str | None = "kitchen",
    title: str = "Turn on Telperion",
    message: str = "It is off.",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the keyword arguments for ``ActionStore.open``."""
    return {
        "key": key,
        "severity": severity,
        "location": Location(area_id=area_id, area_name=area_id),
        "title": title,
        "message": message,
        "evidence": evidence or {},
    }


async def test_open_records_opened_event(hass: HomeAssistant) -> None:
    """Opening an action materialises it and logs one ``opened`` event."""
    store = ActionStore(hass)
    action = store.open(**_draft())
    await hass.async_block_till_done()

    assert action.state is ActionState.OPEN
    assert action.disposition.value == "normal"
    assert store.open_for_key(_draft()["key"]) is action
    assert [event.type for event in store.history(action.id)] == [EventType.OPENED]


async def test_repeat_open_updates_in_place(hass: HomeAssistant) -> None:
    """The same key while open is refreshed, never duplicated."""
    store = ActionStore(hass)
    first = store.open(**_draft(title="First"))
    second = store.open(**_draft(title="Second"))
    await hass.async_block_till_done()

    assert first is second
    assert first.title == "Second"
    actions, total = store.list_actions()
    assert total == 1
    assert len(actions) == 1
    assert len(store.history(first.id)) == 1


async def test_close_then_reopen_creates_new_id(hass: HomeAssistant) -> None:
    """A resolved key re-opens as a brand-new action with a new id."""
    store = ActionStore(hass)
    first = store.open(**_draft())
    store.close(first.id, reason="turned on")
    assert first.state is ActionState.CLOSED

    second = store.open(**_draft())
    await hass.async_block_till_done()

    assert second.id != first.id
    assert second.state is ActionState.OPEN
    assert [event.type for event in store.history(first.id)] == [
        EventType.OPENED,
        EventType.CLOSED,
    ]
    _, total = store.list_actions()
    assert total == 2


async def test_close_is_idempotent(hass: HomeAssistant) -> None:
    """Closing twice and closing an unknown key are both no-ops."""
    store = ActionStore(hass)
    action = store.open(**_draft())
    store.close(action.id)
    store.close(action.id)
    await hass.async_block_till_done()

    assert len(store.history(action.id)) == 2
    assert store.close_key(_draft()["key"]) is None


async def test_bus_events_are_fired(hass: HomeAssistant) -> None:
    """Create, change and close each fire their bus event with the action."""
    created: list[Any] = []
    changed: list[Any] = []
    closed: list[Any] = []
    hass.bus.async_listen(EVENT_ACTION_CREATED, created.append)
    hass.bus.async_listen(EVENT_ACTION_CHANGED, changed.append)
    hass.bus.async_listen(EVENT_ACTION_CLOSED, closed.append)

    store = ActionStore(hass)
    action = store.open(**_draft())
    store.open(**_draft(title="Renamed"))
    store.close(action.id, reason="done")
    await hass.async_block_till_done()

    assert [event.data["title"] for event in created] == ["Turn on Telperion"]
    assert [event.data["title"] for event in changed] == ["Renamed"]
    assert [event.data["state"] for event in closed] == ["closed"]


async def test_filters_and_pagination(hass: HomeAssistant) -> None:
    """State, severity and area filters plus limit/offset pagination."""
    store = ActionStore(hass)
    for index in range(5):
        store.open(**_draft(key=f"k{index}", area_id=f"a{index % 2}"))
    store.close_key("k0")
    await hass.async_block_till_done()

    open_actions, open_total = store.list_actions(state="open")
    assert open_total == 4
    assert all(action.state is ActionState.OPEN for action in open_actions)

    closed_actions, closed_total = store.list_actions(state="closed")
    assert closed_total == 1
    assert closed_actions[0].key == "k0"

    assert store.list_actions(area_id="a0")[1] == 3
    assert store.list_actions(severity="emergency")[1] == 0
    assert store.list_actions(disposition="snoozed")[1] == 0

    page, total = store.list_actions(limit=2, offset=1)
    assert total == 5
    assert len(page) == 2
