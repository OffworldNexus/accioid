"""Evaluate the compiled-in checks against the entities they select.

The engine is the only place that turns findings into store mutations, and the
only place that knows how Home Assistant signals entity lifecycle. A check just
declares an entity filter and evaluates the entities it is interested in; the
watcher here presents every matching entity -- including ones created later --
and keeps each action's lifecycle in step with its entity's existence and
interest.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from homeassistant.helpers.entityfilter import FILTER_SCHEMA

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import Event, EventStateChangedData, HomeAssistant
    from homeassistant.helpers.entity_registry import EventEntityRegistryUpdatedData
    from homeassistant.helpers.entityfilter import EntityFilter

    from .checks.base import Check
    from .store import ActionStore

_LOGGER = logging.getLogger(__name__)


class CheckEngine:
    """Own one watcher per check and their shared lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: ActionStore,
        checks: list[Check],
    ) -> None:
        """Bind the engine to a store and a fixed set of checks."""
        self._hass = hass
        self._store = store
        self._watchers = [_CheckWatcher(hass, store, check) for check in checks]

    def start(self) -> None:
        """Catch every check up, then follow new and changing entities."""
        for watcher in self._watchers:
            watcher.start()

    def stop(self) -> None:
        """Detach every watcher."""
        for watcher in self._watchers:
            watcher.stop()


class _CheckWatcher:
    """Keep one check's accepted entity set in step with Home Assistant."""

    def __init__(self, hass: HomeAssistant, store: ActionStore, check: Check) -> None:
        """Build the entity query for a single check."""
        self._hass = hass
        self._store = store
        self._check = check
        self._filter = _build_filter(check.entity_filter)
        self._accepted: set[str] = set()
        #: The action key each accepted entity owns, so interest revocation and
        #: entity removal can close exactly the right action.
        self._keys: dict[str, str] = {}
        self._unsubs: list[Callable[[], None]] = []

    def start(self) -> None:
        """Catch up the current matches, then subscribe to lifecycle events."""
        for entity_id in self._hass.states.async_entity_ids():
            if self._matches(entity_id):
                self._accepted.add(entity_id)
                self._evaluate(entity_id)

        @callback
        def state_filter(data: EventStateChangedData) -> bool:
            """Keep unrelated domains out of this check's state-change handler."""
            return self._filter(data["entity_id"])

        self._unsubs.append(
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._on_state_change, state_filter
            )
        )
        self._unsubs.append(
            self._hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED, self._on_registry_update
            )
        )

    def stop(self) -> None:
        """Detach every listener."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _matches(self, entity_id: str) -> bool:
        """Stage one (the query) then stage two (the check's interest)."""
        return self._filter(entity_id) and self._check.is_interested(
            self._hass, entity_id
        )

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Present a filtered state change to the check."""
        entity_id = event.data["entity_id"]

        if event.data["new_state"] is None:
            # The entity was removed: let the check resolve, then forget it.
            if entity_id in self._accepted:
                self._evaluate(entity_id)
                self._forget(entity_id)
            return

        if not self._check.is_interested(self._hass, entity_id):
            # The marker was removed: the entity is no longer ours.
            self._forget(entity_id)
            return

        if event.data["old_state"] is None:
            # A brand-new entity: track it and catch it up immediately.
            _LOGGER.debug(
                "Check %s picked up entity %s",
                type(self._check).__name__,
                entity_id,
            )
            self._accepted.add(entity_id)

        self._evaluate(entity_id)

    @callback
    def _on_registry_update(self, event: Event[EventEntityRegistryUpdatedData]) -> None:
        """React to registry changes (labels, area, removal)."""
        entity_id = event.data["entity_id"]

        if event.data.get("action") == "remove":
            self._forget(entity_id)
            return

        if entity_id in self._accepted:
            if self._matches(entity_id):
                # Area/name change: refresh the action's location.
                self._evaluate(entity_id)
            else:
                # Interest was revoked (e.g. the label was removed).
                self._forget(entity_id)
        elif self._matches(entity_id):
            # A registry change (e.g. a label just added) made an existing
            # entity interesting: pick it up and catch it up now.
            _LOGGER.debug(
                "Check %s picked up entity %s via a registry change",
                type(self._check).__name__,
                entity_id,
            )
            self._accepted.add(entity_id)
            self._evaluate(entity_id)

    def _forget(self, entity_id: str) -> None:
        """Stop tracking an entity and close whatever action it owns."""
        self._accepted.discard(entity_id)
        key = self._keys.pop(entity_id, None)
        if key is not None:
            self._store.close_key(key)

    def _evaluate(self, entity_id: str) -> None:
        """Apply one entity's finding to the store."""
        finding = self._check.evaluate(self._hass, entity_id)
        if finding is None:
            return
        if finding.active:
            self._keys[entity_id] = finding.key
            self._store.open(
                key=finding.key,
                severity=finding.severity,
                location=finding.location,
                title=finding.title,
                message=finding.message,
                evidence=finding.evidence,
            )
        else:
            self._keys.pop(entity_id, None)
            self._store.close_key(finding.key)


def _build_filter(config: dict[str, Any]) -> EntityFilter:
    """Normalise a check's filter config into a Home Assistant ``EntityFilter``."""
    return FILTER_SCHEMA(config)
