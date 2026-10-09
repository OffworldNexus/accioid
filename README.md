# Accioid

**Accioid** is a Home Assistant integration that evaluates *checks* about your
home and turns the situations it finds into **actions** — things that need
doing, with a severity, a room and a lifecycle.

This is the first vertical slice. It deliberately stops before branding and
to-do sync; its job is to prove the spine end to end:

> integration → check evaluation → action emitted → read API → display

## What works today

* A HACS-native custom integration (`custom_components/accioid/`).
* One compiled-in check: any `input_boolean` carrying the `tree_of_valinor`
  entity label is a **Tree of Valinor**. When one is **off**, Accioid opens a
  `suggestion` action *"Turn on \<name\>"*, scoped to its area. It closes when
  the switch turns on, a new off creates a new action with a new id, and a
  second labelled switch is picked up automatically — including one created and
  labelled at runtime.

  To mark a switch, create a Toggle helper and give it the **Tree of Valinor**
  label (`tree_of_valinor`); no restart needed. The dev instance labels
  Telperion automatically (`scripts/ha-provision.py`).
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
History is an append-only event log **in memory**, not durable persistence.
Actions and history are lost when Home Assistant restarts or the integration
is unloaded; checks recreate currently active situations with new action ids
when the integration starts again. Only the lifecycle subset needed by the
Tree of Valinor check is implemented; to-do sync and durable storage are not.

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

Feature work is proposed through pull requests targeting **`develop`**. Keep
`develop` as the integration branch; `main` is reserved for releases, not the
default target for feature PRs. Merge only after all CI jobs are green.

## Continuous integration

`.github/workflows/python.yml` runs on branch pushes and pull requests with
read-only repository permissions, per-job timeouts and cancellation of stale
runs. Dependency installation uses `uv sync --locked` to reject a stale
`uv.lock`; subsequent Python commands use `--frozen`.

The required checks cover:

* Ruff formatting/lint and mypy for the integration.
* The complete unit + BDD pytest suite, with JUnit and Allure result artifacts
  retained for seven days even when tests fail.
* Repository YAML/JSON/TOML syntax and local HA/HACS metadata consistency,
  including versions, GitHub links and English translations.
* Bash syntax and ShellCheck, Node.js syntax for the Lovelace card, and Docker
  Compose configuration validation (no containers started).
* Source and wheel builds, with checks that Python modules and integration
  assets are included; distributions are retained for seven days.

These are deterministic repository checks, not a claim of HACS default-store
approval or compatibility with every Home Assistant release. Runtime coverage
uses the Home Assistant version pinned in `uv.lock`.

To reproduce the additional checks locally (Node.js, ShellCheck and Docker
Compose must be installed):

```bash
uv sync --locked
uv run --frozen scripts/ci_validate.py
bash -n scripts/ha-dev.sh
shellcheck scripts/ha-dev.sh
node --check custom_components/accioid/frontend/accioid-card.js
ACCIOID_HA_CONFIG=/tmp/accioid-ci-config docker compose -f scripts/ha-dev.compose.yml config --quiet
uv build --no-sources
uv run --frozen scripts/ci_validate.py --dist dist
```
