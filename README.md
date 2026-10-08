# Accioid

**Accioid** is a Home Assistant integration that evaluates *checks* about your
home and turns the situations it finds into **actions** — things that need
doing, with a severity, a room and a lifecycle.

This is the first vertical slice. It deliberately stops before branding and
to-do sync; its job is to prove the spine end to end:

> integration → check evaluation → action emitted → read API → display

## What works today

* A HACS-native custom integration (`custom_components/accioid/`).
* One compiled-in check: when `input_boolean.telperion` is **off**, Accioid
  opens a `suggestion` action *"Turn on Telperion"*, scoped to the switch's
  area. It closes again when the switch turns on, and a new off creates a new
  action with a new id.
* A read API: an `accioid.list_actions` service (filterable and paginated) and
  the matching `accioid/action/list` + `accioid/action/subscribe` WebSocket
  commands. Lifecycle changes are also fired on the bus as
  `accioid_action_created`, `accioid_action_changed` and
  `accioid_action_closed`.
* A rough, unstyled Lovelace card listing the open actions.

## The model

Actions carry a stable `key` (the identity of a situation), a severity
(`maintenance` | `suggestion` | `emergency`), a location (area), a state
(`open` | `closed`) and a disposition (`normal` | `snoozed` | `ignored`).
History is an append-only event log. See the target data model for the full
picture; only the subset the Telperion rule needs is implemented here.

## Development

```bash
make ha-dev        # throwaway Home Assistant at http://localhost:8124 (dev/dev)
make ha-lint       # ruff format --check + ruff check + mypy
make ha-test       # pytest (unit + BDD)
```

`make ha-dev` brings up `ghcr.io/home-assistant/home-assistant:stable` in
Docker with the integration mounted, onboards a `dev` / `dev` owner
automatically, seeds the Telperion switch and a scratch dashboard, and creates
the Accioid config entry — no setup wizard. It runs on port **8124** so it can
sit beside a regular Home Assistant on 8123 (override with
`ACCIOID_HA_PORT`). The scratch dashboard is at `/accioid-dev/main`.

Repository layout follows the git-flow convention (`main` / `develop` /
`feature/*`).
