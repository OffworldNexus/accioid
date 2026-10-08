# Accioid — agent notes

Home Assistant integration for Accioid: it evaluates compiled-in checks and
surfaces the resulting actions through a service, a WebSocket API and a rough
card. HACS-native, under `custom_components/accioid/`. Python is managed with
`uv`.

## Testing

Fast, quiet commands. Always redirect output to a temp file and dump only
failures; pass an explicit timeout (≈2× the measured wall time).

- **Python static** (ruff format check, ruff check, mypy): `make ha-lint`
  (~1s; timeout 120000ms)
- **Python tests** (unit + BDD): `uv run pytest`
  (~1s; timeout 300000ms)
- **Single Python test**: `uv run pytest tests/test_telperion.py::test_name`
- **Everything**: `make lint` and `make test`
- **Dev Home Assistant** (throwaway, Docker, port **8124** so it can run beside
  a regular HA on 8123 — override with `ACCIOID_HA_PORT`): `make ha-dev` then
  `make ha-dev-logs` / `make ha-dev-stop` / `make ha-dev-reset`
  (first image pull + boot can take minutes; timeout 600000ms)

Last measured: 2026-10-08 — Python 19 passed (~1s), `make ha-lint` green.
