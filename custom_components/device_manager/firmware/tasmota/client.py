"""Low-level Tasmota runtime client.

Shared infrastructure for the Tasmota *maintenance* and *update* treatment
modules: authenticated HTTP command transport, single-publish MQTT transport
and small pure utilities. These helpers are consumed by the sibling
``maintenance`` and ``update`` modules and are not intended to be called
directly by the ``managers`` or ``api`` layers.

The firmware layer never opens the database: device loading lives in the
``managers`` layer (``managers.device_loader``). Every treatment function here
acts only on ``DmDevice`` instances handed to it by its manager.

Migrated from the legacy ``remote_pyscript/tasmota.py`` with these bugs fixed:
  * commands always send the self-referencing Referer header and never place
    credentials in the URL (HTTPBasicAuth is used instead);
  * the inverted ``curlMode`` logic between restart and upgrade is removed;
  * firmware version comparison is numeric (see ``firmware.tasmota.version``).
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped]

from . import common
from ..base.config import get_config

logger = logging.getLogger(__name__)

# HTTP request tuning (aligned with TasmotaAdapter._send_commands).
NUM_RETRY = 3
RETRY_BACKOFF = 1.5
HTTP_TIMEOUT = 10

DEVICE_USER = "admin"
DEFAULT_PASSWORD = "p4ssW0rD"

# Batch operations (force_ap_batch, update_firmware_batch) iterate over every
# device handed in by their manager; serialize them so two concurrent batches
# don't hammer the network at once.
BATCH_LOCK = threading.Lock()


class TasmotaRuntimeError(RuntimeError):
    """Raised for unrecoverable Tasmota runtime failures."""


class BatchInProgressError(RuntimeError):
    """Raised when a batch op is invoked while another is already running."""


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------


def http_get(ip: str, command: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Send an authenticated Tasmota HTTP command with retries.

    Builds the ``/cm?cmnd=<command>`` URL (see
    :func:`firmware.tasmota.common.build_command_url`), always sends the
    self-referencing Referer header (required by Tasmota's CSRF protection)
    and authenticates via HTTPBasicAuth with the password resolved from
    *settings* (see :func:`device_password`), never placing credentials in the
    URL.

    Takes the whole *settings* dict rather than a pre-extracted password so it
    stays symmetric with :func:`mqtt_publish`: both transports share the same
    ``(target, content, settings)`` shape and can read further connection
    settings later without a signature (and call-site) change.

    Args:
        ip: Device IP address.
        command: Raw Tasmota command, e.g. ``"Restart 1"``, ``"Status 0"``.
        settings: Application settings dict (provides the device web password).

    Returns:
        Parsed JSON response (empty dict when the body isn't JSON).

    Raises:
        TasmotaRuntimeError: When all retries fail.
    """
    url = common.build_command_url(ip, command)
    headers = common.referer_headers(ip)
    auth = HTTPBasicAuth(DEVICE_USER, device_password(settings))

    last_error: Optional[Exception] = None
    for attempt in range(1, NUM_RETRY + 1):
        try:
            resp = requests.get(
                url, headers=headers, auth=auth, timeout=HTTP_TIMEOUT
            )
            resp.raise_for_status()
            try:
                return dict(resp.json())
            except ValueError:
                return {}
        except Exception as e:  # noqa: BLE001 - retried below
            last_error = e
            logger.warning(
                "Tasmota HTTP command '%s' to %s failed (attempt %d/%d): %s",
                command, ip, attempt, NUM_RETRY, e,
            )
            if attempt < NUM_RETRY:
                time.sleep(RETRY_BACKOFF)

    raise TasmotaRuntimeError(
        f"HTTP command '{command}' to {ip} failed after {NUM_RETRY} attempts: {last_error}"
    )


def mqtt_publish(topic: str, payload: str, settings: Dict[str, Any]) -> None:
    """Publish a single MQTT command to a Tasmota device.

    Args:
        topic: Full MQTT command topic (e.g. ``cmnd/home/l0/room/POWER``).
        payload: Command payload.
        settings: Settings dict providing optional MQTT broker connection.
    """
    import paho.mqtt.publish as publish  # type: ignore[import-untyped]

    host = settings.get("bus_host", "localhost")
    port = int(settings.get("bus_port", 1883) or 1883)
    username = settings.get("bus_username") or None
    password = settings.get("bus_password") or None
    auth = {"username": username, "password": password} if username else None

    publish.single(
        topic,
        payload=payload,
        hostname=host,
        port=port,
        auth=auth,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Pure utilities
# ---------------------------------------------------------------------------


def device_password(settings: Dict[str, Any]) -> str:
    """Return the Tasmota web password used to authenticate HTTP commands.

    Resolution order mirrors the deploy/provision path so runtime commands
    authenticate with the *same* credentials the device was provisioned with:
    the DB ``device_pass`` setting, then the ``DEVICE_PASS`` config source
    (``.env`` / environment, via :func:`firmware.base.config.get_config`),
    then the built-in default. Reading only the (often empty) DB setting made
    every post-deploy HTTP command fall back to the default password and fail
    authentication against a real device.
    """
    return str(
        settings.get("device_pass")
        or get_config("DEVICE_PASS", None)
        or DEFAULT_PASSWORD
    )


def extract_version(status: Dict[str, Any]) -> str:
    """Extract the firmware version from a Tasmota ``Status 2`` payload."""
    fw = status.get("StatusFWR", {})
    if isinstance(fw, dict):
        return str(fw.get("Version", ""))
    return ""
