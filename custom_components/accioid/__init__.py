"""The Accioid integration: evaluate checks and surface the resulting actions.

Set-up wires the core store, runs the compiled-in checks, and exposes the read
paths (services, WebSocket API and the rough card). Tear-down detaches the
state listeners and the exposed surfaces.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from . import services, websocket_api
from .checks import default_checks
from .const import DOMAIN
from .engine import CheckEngine
from .frontend import async_setup_frontend, async_unload_frontend
from .store import ActionStore

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the WebSocket API commands once for the whole runtime."""
    websocket_api.async_setup(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set Accioid up from its single config entry."""
    store = ActionStore(hass)
    engine = CheckEngine(hass, store, default_checks())

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store
    services.async_setup(hass)

    # Evaluate the checks once so actions exist before anything reads them.
    engine.start()
    await async_setup_frontend(hass)

    entry.async_on_unload(engine.stop)
    entry.async_on_unload(partial(services.async_unload, hass))
    entry.async_on_unload(partial(async_unload_frontend, hass))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Drop Accioid's store; the unload hooks handle the rest."""
    stores = hass.data.get(DOMAIN, {})
    stores.pop(entry.entry_id, None)
    if not stores:
        hass.data.pop(DOMAIN, None)
    return True
