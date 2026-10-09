"""Serve and register the rough Accioid Lovelace card.

The card is deliberately unstyled: ticket 1 exists to prove the read path, not
to look good. It is injected as an extra frontend module so a scratch dashboard
can use ``custom:accioid-actions-card`` without any resource wrangling.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import CARD_URL_PATH, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_CARD_FILE = Path(__file__).parent / "frontend" / "accioid-card.js"
#: ``hass.data`` key remembering that the static path is already served, so an
#: integration reload does not try to register the same route twice.
_STATIC_PATH_KEY = f"{DOMAIN}_card_served"


async def async_setup_frontend(hass: HomeAssistant) -> bool:
    """Serve the card file and load it on every frontend page.

    Returns whether the card was registered. A headless test harness has no
    ``frontend`` (or ``http``) component, so registration is skipped rather
    than failing the whole setup.
    """
    if "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend is not set up; skipping Accioid card registration")
        return False
    if not hass.data.get(_STATIC_PATH_KEY):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(_CARD_FILE), cache_headers=False)]
        )
        hass.data[_STATIC_PATH_KEY] = True
    # A set add, so it is safe to call again after a reload removed the URL.
    add_extra_js_url(hass, CARD_URL_PATH)
    return True


def async_unload_frontend(hass: HomeAssistant) -> None:
    """Stop injecting the card into frontend pages."""
    if "frontend" in hass.config.components:
        with contextlib.suppress(KeyError):
            remove_extra_js_url(hass, CARD_URL_PATH)
