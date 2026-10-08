"""Evaluate the compiled-in checks and drive the action lifecycle.

The engine is the only place that turns findings into store mutations, so the
create/close policy (open while active, close while resolved, refresh in
between) is defined exactly once for every check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from .checks.base import Check
    from .store import ActionStore


class CheckEngine:
    """Run the checks on start-up and on watched state changes."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: ActionStore,
        checks: list[Check],
    ) -> None:
        """Bind the engine to a store and a fixed set of checks."""
        self._hass = hass
        self._store = store
        self._checks = checks
        self._unsubs: list[Callable[[], None]] = []

    @property
    def watched_entities(self) -> set[str]:
        """Return every entity any check wants to observe."""
        entities: set[str] = set()
        for check in self._checks:
            entities.update(check.watched_entities)
        return entities

    def start(self) -> None:
        """Evaluate once now, then re-evaluate whenever a watched entity moves."""
        self.run()
        watched = self.watched_entities
        if watched:
            self._unsubs.append(
                async_track_state_change_event(
                    self._hass, list(watched), self._on_state_change
                )
            )

    def stop(self) -> None:
        """Detach every state-change listener."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def run(self) -> None:
        """Evaluate every check and apply its findings to the store."""
        for check in self._checks:
            for finding in check.evaluate(self._hass):
                if finding.active:
                    self._store.open(
                        key=finding.key,
                        severity=finding.severity,
                        location=finding.location,
                        title=finding.title,
                        message=finding.message,
                        evidence=finding.evidence,
                    )
                else:
                    self._store.close_key(finding.key)

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Re-evaluate after a watched entity changed."""
        self.run()
