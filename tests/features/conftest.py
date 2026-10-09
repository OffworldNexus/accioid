"""Step definitions for the Accioid BDD scenarios.

pytest-bdd runs step functions synchronously while the Home Assistant ``hass``
fixture is async, so each step drives the event loop explicitly with
``run_until_complete``. That keeps the Gherkin prose async-free while still
exercising the real check engine and action store.
"""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, then, when

from custom_components.accioid.models import ActionState
from tests.helpers import set_telperion, setup_accidio, store_of


@given(
    "Accioid is set up with the Telperion switch off",
    target_fixture="world",
)
def _setup_with_switch_off(hass) -> dict[str, Any]:
    """Bring Accioid up with the fixture switch off."""
    hass.loop.run_until_complete(setup_accidio(hass, telperion="off"))
    store = store_of(hass)
    actions, total = store.list_actions(state="open")
    assert total == 1
    return {"hass": hass, "first_id": actions[0].id}


@when("the Telperion switch is turned on")
def _turn_on(world: dict[str, Any]) -> None:
    """Flip the switch on and let the engine react."""
    set_telperion(world["hass"], "on")
    world["hass"].loop.run_until_complete(world["hass"].async_block_till_done())


@when("the Telperion switch is turned off")
def _turn_off(world: dict[str, Any]) -> None:
    """Flip the switch off and let the engine react."""
    set_telperion(world["hass"], "off")
    world["hass"].loop.run_until_complete(world["hass"].async_block_till_done())


@then('an open action titled "Turn on Telperion" exists')
def _open_action_exists(world: dict[str, Any]) -> None:
    """There is exactly one open action, and capture its id."""
    actions, total = store_of(world["hass"]).list_actions(state="open")
    assert total == 1
    assert actions[0].title == "Turn on Telperion"
    assert actions[0].state is ActionState.OPEN
    world["latest_id"] = actions[0].id


@then("there are no open actions")
def _no_open_actions(world: dict[str, Any]) -> None:
    """The store has nothing currently open."""
    assert store_of(world["hass"]).list_actions(state="open")[1] == 0


@then("the new action has a different id")
def _new_id(world: dict[str, Any]) -> None:
    """Re-creating the situation yields a fresh occurrence."""
    assert world["latest_id"] != world["first_id"]
