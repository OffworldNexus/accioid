"""The in-memory action store and its lifecycle transitions.

The store is the canonical core: it owns every action Accioid has produced,
open or closed, plus the append-only event log. Every transition fires the
matching Home Assistant bus event so the WebSocket stream and automations stay
in sync without polling.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import (
    DEFAULT_LIMIT,
    DOMAIN,
    EVENT_ACTION_CHANGED,
    EVENT_ACTION_CLOSED,
    EVENT_ACTION_CREATED,
)
from .ids import new_ulid
from .models import (
    Action,
    ActionEvent,
    ActionState,
    Actor,
    EventType,
    Location,
    Severity,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def get_store(hass: HomeAssistant) -> ActionStore | None:
    """Return the configured store, or ``None`` when Accioid is not set up.

    Accioid is a singleton, but the store still lives keyed by config-entry id
    in ``hass.data`` so an unload can clean up after itself.
    """
    stores = hass.data.get(DOMAIN, {})
    return next(iter(stores.values()), None)


class ActionStore:
    """Hold every action and drive its open/close lifecycle.

    Two indexes are kept: by opaque id (the whole history) and by key for the
    currently-open action, because the model promises at most one open action
    per key.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Create an empty store bound to a running Home Assistant."""
        self._hass = hass
        self._actions: dict[str, Action] = {}
        self._open_by_key: dict[str, str] = {}
        self._events: list[ActionEvent] = []

    # -- queries ---------------------------------------------------------

    def get(self, action_id: str) -> Action | None:
        """Return one action by id, open or closed."""
        return self._actions.get(action_id)

    def open_for_key(self, key: str) -> Action | None:
        """Return the open action for a key, if the situation is active."""
        action_id = self._open_by_key.get(key)
        return self._actions.get(action_id) if action_id is not None else None

    def list_actions(
        self,
        *,
        state: str | None = None,
        disposition: str | None = None,
        severity: str | None = None,
        area_id: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Action], int]:
        """Return a newest-first page of actions and the unpaged total.

        Every filter is optional and applied before pagination so ``total``
        always describes the full filtered set, not just the page.
        """
        items = list(self._actions.values())
        if state is not None:
            items = [a for a in items if a.state.value == state]
        if disposition is not None:
            items = [a for a in items if a.disposition.value == disposition]
        if severity is not None:
            items = [a for a in items if a.severity.value == severity]
        if area_id is not None:
            items = [a for a in items if a.location.area_id == area_id]
        # ULIDs are lexicographically time-ordered, so a plain sort is enough.
        items.sort(key=lambda action: action.id, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total

    def history(self, action_id: str) -> list[ActionEvent]:
        """Return the event log for one action, oldest first."""
        return [event for event in self._events if event.action_id == action_id]

    # -- lifecycle -------------------------------------------------------

    def open(
        self,
        *,
        key: str,
        severity: Severity,
        location: Location,
        title: str,
        message: str,
        evidence: dict[str, Any] | None = None,
        actor: Actor = Actor.SYSTEM,
    ) -> Action:
        """Open the action for ``key``, or refresh it if already open.

        The key guarantees at most one open action per situation: a repeat
        evaluation updates the existing action in place instead of duplicating
        it. A brand-new occurrence gets a fresh ULID.
        """
        existing = self.open_for_key(key)
        if existing is not None:
            self._update(
                existing,
                severity=severity,
                location=location,
                title=title,
                message=message,
                evidence=evidence or {},
            )
            return existing

        action = Action(
            id=new_ulid(),
            key=key,
            severity=severity,
            location=location,
            title=title,
            message=message,
            evidence=evidence or {},
        )
        self._actions[action.id] = action
        self._open_by_key[key] = action.id
        self._record(action, EventType.OPENED, actor=actor)
        self._emit(EVENT_ACTION_CREATED, action)
        return action

    def close(
        self,
        action_id: str,
        *,
        actor: Actor = Actor.SYSTEM,
        reason: str | None = None,
    ) -> Action | None:
        """Close an action once its situation has resolved.

        Closing is idempotent: an already-closed or unknown action is returned
        untouched so callers can safely close on every evaluation.
        """
        action = self._actions.get(action_id)
        if action is None or action.state is ActionState.CLOSED:
            return action

        action.state = ActionState.CLOSED
        self._open_by_key.pop(action.key, None)
        data: dict[str, Any] = {"reason": reason} if reason else {}
        self._record(action, EventType.CLOSED, actor=actor, data=data)
        self._emit(EVENT_ACTION_CLOSED, action)
        return action

    def close_key(
        self,
        key: str,
        *,
        actor: Actor = Actor.SYSTEM,
        reason: str | None = None,
    ) -> Action | None:
        """Close the open action for a key, if there is one."""
        action = self.open_for_key(key)
        if action is None:
            return None
        return self.close(action.id, actor=actor, reason=reason)

    # -- internals -------------------------------------------------------

    def _update(self, action: Action, **fields: Any) -> None:
        """Apply changed fields in place and announce a ``changed`` event.

        Unlike create/close this is not a modelled log event, so only the bus
        event is fired: the append-only log records lifecycle and disposition
        changes, not incidental field refreshes.
        """
        changed = False
        for name, value in fields.items():
            if getattr(action, name) != value:
                setattr(action, name, value)
                changed = True
        if changed:
            self._emit(EVENT_ACTION_CHANGED, action)

    def _record(
        self,
        action: Action,
        event_type: EventType,
        *,
        actor: Actor,
        data: dict[str, Any] | None = None,
    ) -> ActionEvent:
        """Append one entry to the action's history."""
        event = ActionEvent(
            id=new_ulid(),
            action_id=action.id,
            type=event_type,
            at=datetime.now(UTC),
            actor=actor,
            data=data or {},
        )
        self._events.append(event)
        return event

    def _emit(self, event_name: str, action: Action) -> None:
        """Fire a lifecycle bus event carrying the action's current state."""
        _LOGGER.debug("Firing %s for action %s", event_name, action.id)
        self._hass.bus.async_fire(event_name, action.as_dict())
