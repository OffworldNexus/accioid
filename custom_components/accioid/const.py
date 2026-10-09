"""Constants shared across the Accioid integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "accioid"
NAME: Final = "Accioid"

#: The first hard-coded check watches this entity. It is seeded by the dev
#: instance and is expected to be a normal Home Assistant virtual switch.
TELPERION_ENTITY_ID: Final = "input_boolean.telperion"

#: Label id marking an entity as one of the Trees of Valinor. Labels are the
#: only marker: they can be assigned at runtime in the UI (or over the registry
#: API), so marked switches need no restart and are picked up as soon as they
#: appear.
LABEL_TREE_OF_VALINOR: Final = "tree_of_valinor"

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
