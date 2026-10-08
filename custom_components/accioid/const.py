"""Constants shared across the Accioid integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "accioid"
NAME: Final = "Accioid"

#: The first hard-coded check watches this entity. It is seeded by the dev
#: instance and is expected to be a normal Home Assistant virtual switch.
TELPERION_ENTITY_ID: Final = "input_boolean.telperion"

# -- Home Assistant bus events (the push path for automations) ---------------

EVENT_ACTION_CREATED: Final = f"{DOMAIN}_action_created"
EVENT_ACTION_CHANGED: Final = f"{DOMAIN}_action_changed"
EVENT_ACTION_CLOSED: Final = f"{DOMAIN}_action_closed"

#: The three lifecycle bus events, in the order used by subscribers.
LIFECYCLE_EVENTS: Final = (
    EVENT_ACTION_CREATED,
    EVENT_ACTION_CHANGED,
    EVENT_ACTION_CLOSED,
)

# -- Services ----------------------------------------------------------------

SERVICE_LIST_ACTIONS: Final = "list_actions"

# -- WebSocket API -----------------------------------------------------------

WS_TYPE_LIST: Final = f"{DOMAIN}/action/list"
WS_TYPE_SUBSCRIBE: Final = f"{DOMAIN}/action/subscribe"

# -- Pagination --------------------------------------------------------------

DEFAULT_LIMIT: Final = 50
MAX_LIMIT: Final = 500

# -- Frontend card -----------------------------------------------------------

CARD_URL_PATH: Final = f"/{DOMAIN}/accioid-card.js"
