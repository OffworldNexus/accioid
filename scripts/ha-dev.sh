#!/usr/bin/env bash
# Run a throwaway Home Assistant Core locally with the Accioid integration.
#
# Managed lifecycle so it always responds to Ctrl+C and never traps your shell:
#
#   ./scripts/ha-dev.sh up        start (detached) + auto-onboard + print info
#   ./scripts/ha-dev.sh logs      follow the logs (Ctrl+C just stops following)
#   ./scripts/ha-dev.sh restart   down + up
#   ./scripts/ha-dev.sh down      stop and remove the container
#   ./scripts/ha-dev.sh reset     down + wipe the config
#
# Onboarding is automatic: there is no setup wizard. Log in with dev / dev.
# The Accioid config entry, the Telperion switch and a scratch dashboard are
# seeded automatically. This never touches production.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="${ACCIOID_HA_CONFIG:-${ROOT}/.dev/homeassistant}"
export ACCIOID_HA_CONFIG="${CONFIG_DIR}"
export ACCIOID_HA_IMAGE="${ACCIOID_HA_IMAGE:-ghcr.io/home-assistant/home-assistant:stable}"
export ACCIOID_HA_UID="${ACCIOID_HA_UID:-$(id -u)}"
export ACCIOID_HA_GID="${ACCIOID_HA_GID:-$(id -g)}"
COMPOSE=(docker compose -f "${ROOT}/scripts/ha-dev.compose.yml")

# Accioid's dev instance runs on its own host port (8124 by default) so it can
# coexist with a regular Home Assistant on 8123. Home Assistant itself always
# listens on 8123 inside the container; this is only the host mapping.
ACCIOID_HA_PORT="${ACCIOID_HA_PORT:-8124}"
export ACCIOID_HA_PORT
URL="http://localhost:${ACCIOID_HA_PORT}"

require_docker() {
    command -v docker >/dev/null 2>&1 || {
        echo "error: docker is not installed" >&2
        exit 1
    }
    docker info >/dev/null 2>&1 || {
        echo "error: cannot talk to the Docker daemon" >&2
        exit 1
    }
}

seed_config() {
    mkdir -p "${CONFIG_DIR}/custom_components"
    # Refresh the mounted copy of the integration on every start.
    rm -rf "${CONFIG_DIR}/custom_components/accioid"
    cp -r "${ROOT}/custom_components/accioid" "${CONFIG_DIR}/custom_components/accioid"
    find "${CONFIG_DIR}/custom_components/accioid" -name __pycache__ -type d \
        -exec rm -rf {} + 2>/dev/null || true

    # Static throwaway config: only written once, so local tweaks stick.
    if [ ! -f "${CONFIG_DIR}/configuration.yaml" ]; then
        cat > "${CONFIG_DIR}/configuration.yaml" <<'YAML'
# Throwaway Accioid development instance. No secrets, no production data.
default_config:

# The card is injected by the integration; the frontend must be up for that.
frontend:

# The seeded fixture the first hard-coded check watches.
input_boolean:
  telperion:
    name: Telperion
    icon: mdi:lightbulb

logger:
  default: info
  logs:
    custom_components.accioid: debug

# A scratch dashboard showing the rough card, in YAML mode.
lovelace:
  mode: storage
  dashboards:
    accioid-dev:
      mode: yaml
      title: Accioid Dev
      show_in_sidebar: true
      filename: accioid-dashboard.yaml
YAML
    fi

    # Always regenerated: it is pure scaffolding, not something you edit here.
    cat > "${CONFIG_DIR}/accioid-dashboard.yaml" <<'YAML'
# Scratch dashboard for the rough Accioid card. Regenerated on every start.
title: Accioid Dev
views:
  - title: Actions
    path: main
    cards:
      - type: custom:accioid-actions-card
        title: Open actions
YAML
}

cmd_up() {
    require_docker
    seed_config
    echo "==> starting Home Assistant (${ACCIOID_HA_IMAGE})"
    "${COMPOSE[@]}" up -d
    echo "==> waiting for it to become ready, onboarding and seeding automatically"
    PYTHONUNBUFFERED=1 uv run --no-project "${ROOT}/scripts/ha-provision.py" "${URL}" || true
    echo
    echo "Home Assistant: ${URL}   (login: dev / dev)"
    echo "Accioid Dev dashboard: ${URL}/accioid-dev/main"
    echo "Follow logs:    ./scripts/ha-dev.sh logs"
    echo "Stop:           ./scripts/ha-dev.sh down"
    echo
}

cmd_logs() {
    require_docker
    "${COMPOSE[@]}" logs -f --tail=100
}

cmd_down() {
    require_docker
    "${COMPOSE[@]}" down --remove-orphans
    # Belt and braces in case a previous `docker run` left the name behind.
    docker rm -f accioid-ha >/dev/null 2>&1 || true
    echo "stopped and removed accioid-ha"
}

cmd_reset() {
    cmd_down
    rm -rf "${CONFIG_DIR}"
    echo "wiped ${CONFIG_DIR} (next 'up' will onboard fresh with dev / dev)"
}

case "${1:-up}" in
    up) cmd_up ;;
    up-fg)
        require_docker
        seed_config
        # Foreground mode; the compose file sets `init: true` so Ctrl+C works.
        "${COMPOSE[@]}" up
        ;;
    logs) cmd_logs ;;
    restart)
        cmd_down
        cmd_up
        ;;
    down) cmd_down ;;
    reset) cmd_reset ;;
    *)
        echo "usage: $0 {up|up-fg|logs|restart|down|reset}" >&2
        exit 2
        ;;
esac
