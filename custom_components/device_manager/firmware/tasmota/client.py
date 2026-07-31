"""Low-level Tasmota runtime client.

Shared infrastructure for the Tasmota *maintenance* and *update* treatment
modules: authenticated HTTP command transport, single-publish MQTT transport,
database access helpers and small pure utilities. These helpers are consumed
by the sibling ``maintenance`` and ``update`` modules and are not intended to
be called directly by the ``managers`` or ``api`` layers.

Migrated from the legacy ``remote_pyscript/tasmota.py`` with these bugs fixed:
  * commands always send the self-referencing Referer header and never place
    credentials in the URL (HTTPBasicAuth is used instead);
  * the inverted ``curlMode`` logic between restart and upgrade is removed;
  * firmware version comparison is numeric (see ``firmware.tasmota.version``).
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped]

from . import shared
from ...persistence.database_manager import DatabaseManager
from ...persistence.repositories import DeviceRepository

logger = logging.getLogger(__name__)

# HTTP request tuning (aligned with TasmotaAdapter._send_commands).
NUM_RETRY = 3
RETRY_BACKOFF = 1.5
HTTP_TIMEOUT = 10

DEVICE_USER = "admin"
DEFAULT_PASSWORD = "p4ssW0rD"

# Batch operations (force_ap_batch, update_firmware_batch) each open their own
# DB connection and iterate every device; serialize them so two concurrent
# batches don't race on the same SQLite file / hammer the network.
BATCH_LOCK = threading.Lock()


class TasmotaRuntimeError(RuntimeError):
    """Raised for unrecoverable Tasmota runtime failures."""


class BatchInProgressError(RuntimeError):
    """Raised when a batch op is invoked while another is already running."""


# ---------------------------------------------------------------------------
# Transport helpers
# ---------------------------------------------------------------------------


def http_get(ip: str, cmd: str, password: str, data: Optional[str] = None) -> Dict[str, Any]:
    """Send an authenticated Tasmota HTTP command with retries.

    Always sends the self-referencing Referer header (required by Tasmota's
    CSRF protection) and passes credentials via HTTPBasicAuth (never in URL).

    Args:
        ip: Device IP address.
        cmd: Command type (e.g. ``"cmnd"``).
        password: Device web password.
        data: Optional command payload.

    Returns:
        Parsed JSON response (empty dict when the body isn't JSON).

    Raises:
        TasmotaRuntimeError: When all retries fail.
    """
    url = shared.build_url(ip, cmd, data)
    headers = shared.referer_headers(ip)
    auth = HTTPBasicAuth(DEVICE_USER, password)

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
                "Tasmota HTTP %s to %s failed (attempt %d/%d): %s",
                cmd, ip, attempt, NUM_RETRY, e,
            )
            if attempt < NUM_RETRY:
                time.sleep(RETRY_BACKOFF)

    raise TasmotaRuntimeError(
        f"HTTP command '{cmd}' to {ip} failed after {NUM_RETRY} attempts: {last_error}"
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
# Database helpers
# ---------------------------------------------------------------------------


def load_device_by_mac(db: DatabaseManager, mac: str) -> Any:
    """Load a hydrated DmDevice by MAC (sync wrapper)."""

    async def _find() -> Any:
        repo = DeviceRepository(db)
        return await repo.find_by_mac(mac)

    return asyncio.run(_find())


def load_all_devices(db: DatabaseManager) -> List[Any]:
    """Load all hydrated devices (sync wrapper)."""

    async def _all() -> List[Any]:
        repo = DeviceRepository(db)
        return await repo.find_all()

    return asyncio.run(_all())


def open_db(db_path: Path) -> DatabaseManager:
    """Open and initialize a DatabaseManager (sync wrapper)."""
    db = DatabaseManager(db_path)

    async def _init() -> None:
        await db.initialize()

    asyncio.run(_init())
    return db


def close_db(db: DatabaseManager) -> None:
    """Close a DatabaseManager (sync wrapper)."""

    async def _close() -> None:
        await db.close()

    try:
        asyncio.run(_close())
    except Exception as e:  # noqa: BLE001
        logger.debug("Error closing DB: %s", e)


# ---------------------------------------------------------------------------
# Pure utilities
# ---------------------------------------------------------------------------


def device_password(settings: Dict[str, Any]) -> str:
    """Return the Tasmota web password from settings (with default)."""
    return str(settings.get("device_pass") or DEFAULT_PASSWORD)


def filter_devices(devices: List[Any], mac_filter: Optional[List[str]]) -> List[Any]:
    """Return devices with an IP, optionally restricted to *mac_filter*."""
    result = [d for d in devices if getattr(d, "ip", None)]
    if mac_filter:
        wanted = {m.upper() for m in mac_filter}
        result = [d for d in result if d.mac.upper() in wanted]
    return result


def extract_version(status: Dict[str, Any]) -> str:
    """Extract the firmware version from a Tasmota ``Status 2`` payload."""
    fw = status.get("StatusFWR", {})
    if isinstance(fw, dict):
        return str(fw.get("Version", ""))
    return ""
