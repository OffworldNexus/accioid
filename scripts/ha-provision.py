#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["aiohttp"]
# ///
"""Automatically provision the throwaway Accioid development instance.

Home Assistant is driven through its supported APIs so there is no setup
wizard and no manual clicking:

1. Onboarding (owner user, core config, analytics, integration) — skipped if
   already done.
2. The singleton Accioid config entry, so the integration is loaded.
3. The Telperion fixture is assigned to a dev area, which the first hard-coded
   check uses as the action's location.

Run via ``scripts/ha-dev.sh up``; you normally never call this directly.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import aiohttp

DEFAULT_URL = "http://localhost:8123"
DEFAULT_USER = "dev"
DEFAULT_PASSWORD = "dev"
READY_TIMEOUT = 300  # seconds (first boot on a new version can be slow)
DEV_AREA_NAME = "Dev Room"
TELPERION_ENTITY_ID = "input_boolean.telperion"


def request(
    method: str,
    url: str,
    *,
    body: dict | None = None,
    form: dict | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict | list | str]:
    """Perform one HTTP request and return ``(status, parsed_body)``."""
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        try:
            return err.code, (json.loads(raw) if raw else {})
        except json.JSONDecodeError:
            return err.code, raw
    except OSError as err:
        # URLError and connection resets/refusals while Home Assistant is still
        # booting are all retried by the caller.
        reason = getattr(err, "reason", err)
        return 0, str(reason)


def wait_ready(base: str) -> bool:
    """Wait until the Home Assistant HTTP server answers.

    The onboarding endpoint is a convenient readiness probe, but it returns
    ``404`` once onboarding is complete, so both ``200`` and ``404`` mean the
    server is up.
    """
    deadline = time.time() + READY_TIMEOUT
    while time.time() < deadline:
        status, _ = request("GET", f"{base}/api/onboarding", timeout=5.0)
        if status in (200, 404):
            return True
        time.sleep(2)
    return False


def needs_onboarding(base: str) -> bool:
    """Return whether the instance still needs its owner user created."""
    status, payload = request("GET", f"{base}/api/onboarding", timeout=5.0)
    if status == 200 and isinstance(payload, list):
        return "user" not in done_steps(payload)
    # A 404 means the onboarding endpoint is gone: already onboarded.
    return False


def done_steps(status: list) -> set[str]:
    """Extract the set of completed onboarding steps."""
    return {entry["step"] for entry in status if entry.get("done")}


def onboard(base: str, username: str, password: str) -> str | None:
    """Complete onboarding for a fresh instance; return an access token."""
    client_id = f"{base}/"
    redirect_uri = f"{base}/?auth_callback=1"

    # 1. Owner user. Returns a one-time auth code.
    code, payload = request(
        "POST",
        f"{base}/api/onboarding/users",
        body={
            "client_id": client_id,
            "name": "Accioid Dev",
            "username": username,
            "password": password,
            "language": "en",
        },
    )
    if code != 200 or not isinstance(payload, dict) or "auth_code" not in payload:
        print(f"error: creating user failed ({code}): {payload}", file=sys.stderr)
        return None
    auth_code = payload["auth_code"]

    # 2. Exchange the auth code for an access token.
    token = _exchange_code(base, client_id, auth_code)
    if token is None:
        return None

    # 3. Remaining steps (idempotent; ignore "already done" responses).
    steps = [
        ("core_config", {}),
        ("analytics", {}),
        ("integration", {"client_id": client_id, "redirect_uri": redirect_uri}),
    ]
    for step, body in steps:
        code, payload = request(
            "POST", f"{base}/api/onboarding/{step}", body=body, token=token
        )
        if code not in (200, 201, 403, 409):
            print(f"warning: onboarding step {step} returned {code}: {payload}")
    return token


def login(base: str, username: str, password: str) -> str | None:
    """Log in as an existing user and return an access token."""
    client_id = f"{base}/"
    code, payload = request(
        "POST",
        f"{base}/auth/login_flow",
        body={
            "client_id": client_id,
            "handler": ["homeassistant", None],
            "redirect_uri": f"{base}/?auth_callback=1",
        },
    )
    if code != 200 or not isinstance(payload, dict) or "flow_id" not in payload:
        print(f"error: starting login failed ({code}): {payload}", file=sys.stderr)
        return None
    flow_id = payload["flow_id"]

    code, payload = request(
        "POST",
        f"{base}/auth/login_flow/{flow_id}",
        body={
            "username": username,
            "password": password,
            "client_id": client_id,
        },
    )
    if code != 200 or not isinstance(payload, dict) or "result" not in payload:
        print(f"error: login failed ({code}): {payload}", file=sys.stderr)
        return None
    return _exchange_code(base, client_id, payload["result"])


def _exchange_code(base: str, client_id: str, auth_code: str) -> str | None:
    """Turn an OAuth auth code into an access token."""
    code, payload = request(
        "POST",
        f"{base}/auth/token",
        form={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": client_id,
        },
    )
    if code != 200 or not isinstance(payload, dict) or "access_token" not in payload:
        print(f"error: token exchange failed ({code}): {payload}", file=sys.stderr)
        return None
    return payload["access_token"]


def ensure_config_entry(base: str, token: str) -> None:
    """Create the singleton Accioid config entry if it does not exist yet."""
    # The integration may still be loading right after onboarding; retry.
    for _ in range(15):
        code, payload = request(
            "POST",
            f"{base}/api/config/config_entries/flow",
            body={"handler": "accioid"},
            token=token,
        )
        if code == 200 and isinstance(payload, dict):
            break
        time.sleep(2)
    else:
        print(f"warning: could not start the Accioid flow ({code}): {payload}")
        return

    if payload.get("type") == "abort":
        print("Accioid config entry already exists")
        return
    flow_id = payload.get("flow_id")
    if not flow_id:
        print(f"warning: unexpected Accioid flow payload: {payload}")
        return

    code, payload = request(
        "POST",
        f"{base}/api/config/config_entries/flow/{flow_id}",
        body={},
        token=token,
    )
    if (
        code == 200
        and isinstance(payload, dict)
        and payload.get("type") == "create_entry"
    ):
        print("created the Accioid config entry")
    else:
        print(f"warning: creating the Accioid entry returned {code}: {payload}")


async def assign_dev_area(base: str, token: str) -> None:
    """Put the Telperion switch in a dev area over the WebSocket API."""
    ws_url = base.replace("http", "ws", 1) + "/api/websocket"
    timeout = aiohttp.ClientTimeout(total=30)
    async with (
        aiohttp.ClientSession(timeout=timeout) as session,
        session.ws_connect(ws_url) as ws,
    ):
        await ws.receive_json()  # {"type": "auth_required"}
        await ws.send_json({"type": "auth", "access_token": token})
        auth = await ws.receive_json()
        if auth.get("type") != "auth_ok":
            print(f"warning: websocket auth failed: {auth}")
            return

        await ws.send_json({"id": 1, "type": "config/area_registry/list"})
        areas = await _ws_result(ws, 1)
        area = next((a for a in areas if a["name"] == DEV_AREA_NAME), None)
        if area is None:
            await ws.send_json(
                {"id": 2, "type": "config/area_registry/create", "name": DEV_AREA_NAME}
            )
            area = await _ws_result(ws, 2)

        await ws.send_json(
            {
                "id": 3,
                "type": "config/entity_registry/update",
                "entity_id": TELPERION_ENTITY_ID,
                "area_id": area["area_id"],
            }
        )
        await _ws_result(ws, 3)
        print(f"assigned {TELPERION_ENTITY_ID} to area '{DEV_AREA_NAME}'")


async def _ws_result(ws: aiohttp.ClientWebSocketResponse, msg_id: int) -> object:
    """Read frames until the reply for ``msg_id`` arrives."""
    while True:
        message = await ws.receive_json()
        if message.get("id") != msg_id:
            continue
        if not message.get("success", True):
            reason = message.get("error")
            error = f"command {msg_id} failed: {reason}"
            raise RuntimeError(error)
        return message.get("result")


def provision(base: str, username: str, password: str) -> int:
    """Onboard, seed and authenticate; return a process exit code."""
    base = base.rstrip("/")
    print(f"waiting for Home Assistant at {base} ...")
    if not wait_ready(base):
        print("error: Home Assistant did not become ready in time", file=sys.stderr)
        return 1

    if needs_onboarding(base):
        token = onboard(base, username, password)
    else:
        print("onboarding already complete")
        token = login(base, username, password)
    if token is None:
        return 1

    # Seed the fixture area before creating the entry: setting the entry up
    # runs the checks immediately, and the first action must already be scoped.
    asyncio.run(assign_dev_area(base, token))
    ensure_config_entry(base, token)

    print(f"provisioning complete — log in at {base} as {username} / {password}")
    return 0


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    username = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_USER
    password = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PASSWORD
    return provision(base, username, password)


if __name__ == "__main__":
    raise SystemExit(main())
