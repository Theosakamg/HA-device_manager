"""Tasmota runtime operations (restart, upgrade, status, firmware update...).

These are *runtime* device operations, distinct from provisioning/deploy which
pushes configuration. Each public function runs synchronously inside a Home
Assistant executor thread and talks to devices over HTTP (default) or MQTT
(optional). They mirror the ``provisioning/deploy.py`` pattern: sync entry
points, an own DatabaseManager for DB reads, and a module-level lock for the
batch operations.

Migrated from the legacy ``remote_pyscript/tasmota.py`` with these bugs fixed:
  * restart/upgrade now always send the self-referencing Referer header and
    never place credentials in the URL (HTTPBasicAuth is used instead);
  * the inverted ``curlMode`` logic between restart and upgrade is removed —
    both use the same, correct code path;
  * firmware version comparison is numeric (see ``utils.version_compare``);
  * the AP SSID is read from settings instead of being hardcoded.
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]
from requests.auth import HTTPBasicAuth  # type: ignore[import-untyped]

from ..provisioning.core import tasmota_shared
from ..repositories import DeviceRepository
from ..services.database_manager import DatabaseManager
from ..utils.version_compare import is_newer

logger = logging.getLogger(__name__)

# HTTP request tuning (aligned with TasmotaAdapter._send_commands).
_NUM_RETRY = 3
_RETRY_BACKOFF = 1.5
_HTTP_TIMEOUT = 10

_DEVICE_USER = "admin"
_DEFAULT_PASSWORD = "p4ssW0rD"

# Batch operations (force_ap_batch, update_firmware_batch) each open their own
# DB connection and iterate every device; serialize them so two concurrent
# batches don't race on the same SQLite file / hammer the network.
_BATCH_LOCK = threading.Lock()


class TasmotaRuntimeError(RuntimeError):
    """Raised for unrecoverable Tasmota runtime failures."""


class BatchInProgressError(RuntimeError):
    """Raised when a batch op is invoked while another is already running."""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_get(ip: str, cmd: str, password: str, data: Optional[str] = None) -> Dict[str, Any]:
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
    url = tasmota_shared.build_url(ip, cmd, data)
    headers = tasmota_shared.referer_headers(ip)
    auth = HTTPBasicAuth(_DEVICE_USER, password)

    last_error: Optional[Exception] = None
    for attempt in range(1, _NUM_RETRY + 1):
        try:
            resp = requests.get(
                url, headers=headers, auth=auth, timeout=_HTTP_TIMEOUT
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
                cmd, ip, attempt, _NUM_RETRY, e,
            )
            if attempt < _NUM_RETRY:
                time.sleep(_RETRY_BACKOFF)

    raise TasmotaRuntimeError(
        f"HTTP command '{cmd}' to {ip} failed after {_NUM_RETRY} attempts: {last_error}"
    )


def _mqtt_publish(topic: str, payload: str, settings: Dict[str, Any]) -> None:
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

    publish.single(topic, payload=payload, hostname=host, port=port, auth=auth)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _load_device_by_mac(db: DatabaseManager, mac: str) -> Any:
    """Load a hydrated DmDevice by MAC (sync wrapper)."""

    async def _find() -> Any:
        repo = DeviceRepository(db)
        return await repo.find_by_mac(mac)

    return asyncio.run(_find())


def _load_all_devices(db: DatabaseManager) -> List[Any]:
    """Load all hydrated devices (sync wrapper)."""

    async def _all() -> List[Any]:
        repo = DeviceRepository(db)
        return await repo.find_all()

    return asyncio.run(_all())


def _open_db(db_path: Path) -> DatabaseManager:
    """Open and initialize a DatabaseManager (sync wrapper)."""
    db = DatabaseManager(db_path)

    async def _init() -> None:
        await db.initialize()

    asyncio.run(_init())
    return db


def _device_password(settings: Dict[str, Any]) -> str:
    """Return the Tasmota web password from settings (with default)."""
    return str(settings.get("device_pass") or _DEFAULT_PASSWORD)


# ---------------------------------------------------------------------------
# Single-device operations
# ---------------------------------------------------------------------------


def restart_device(
    db_path: Path,
    mac: str,
    settings: Dict[str, Any],
    use_mqtt: bool = False,
) -> Dict[str, Any]:
    """Restart a single Tasmota device.

    Args:
        db_path: Path to the SQLite database.
        mac: Target device MAC address.
        settings: Application settings dict.
        use_mqtt: Send the command over MQTT instead of HTTP.

    Returns:
        Result dict ``{"mac", "transport", "ok"}``.
    """
    db = _open_db(db_path)
    try:
        device = _load_device_by_mac(db, mac)
        if device is None:
            raise TasmotaRuntimeError(f"Device not found: {mac}")

        if use_mqtt:
            prefix = settings.get("mqtt_topic_prefix", "home")
            topic = f"{tasmota_shared.build_cmnd_topic(device, prefix)}/Restart"
            _mqtt_publish(topic, "1", settings)
        else:
            _http_get(device.ip, "cmnd", _device_password(settings), "Restart%201")

        return {"mac": mac, "transport": "mqtt" if use_mqtt else "http", "ok": True}
    finally:
        _close_db(db)


def upgrade_device(
    db_path: Path,
    mac: str,
    settings: Dict[str, Any],
    use_mqtt: bool = False,
) -> Dict[str, Any]:
    """Trigger an OTA upgrade on a single Tasmota device.

    Uses the *same* correct code path as :func:`restart_device` — the legacy
    inverted ``curlMode`` logic is intentionally not replicated.

    Args:
        db_path: Path to the SQLite database.
        mac: Target device MAC address.
        settings: Application settings dict.
        use_mqtt: Send the command over MQTT instead of HTTP.

    Returns:
        Result dict ``{"mac", "transport", "ok"}``.
    """
    db = _open_db(db_path)
    try:
        device = _load_device_by_mac(db, mac)
        if device is None:
            raise TasmotaRuntimeError(f"Device not found: {mac}")

        if use_mqtt:
            prefix = settings.get("mqtt_topic_prefix", "home")
            topic = f"{tasmota_shared.build_cmnd_topic(device, prefix)}/Upgrade"
            _mqtt_publish(topic, "1", settings)
        else:
            _http_get(device.ip, "cmnd", _device_password(settings), "Upgrade%201")

        return {"mac": mac, "transport": "mqtt" if use_mqtt else "http", "ok": True}
    finally:
        _close_db(db)


def get_status(
    db_path: Path,
    mac: str,
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Query full status (``Status 0``) of a Tasmota device over HTTP.

    Args:
        db_path: Path to the SQLite database.
        mac: Target device MAC address.
        settings: Application settings dict.

    Returns:
        Result dict ``{"mac", "online", "status"}``.
    """
    db = _open_db(db_path)
    try:
        device = _load_device_by_mac(db, mac)
        if device is None:
            raise TasmotaRuntimeError(f"Device not found: {mac}")

        try:
            status = _http_get(device.ip, "cmnd", _device_password(settings), "Status%200")
            return {"mac": mac, "online": True, "status": status}
        except TasmotaRuntimeError:
            return {"mac": mac, "online": False, "status": {}}
    finally:
        _close_db(db)


def switch_ap(
    db_path: Path,
    mac: str,
    settings: Dict[str, Any],
    ap_id: int = 1,
) -> Dict[str, Any]:
    """Switch a device's active WiFi AP (``AP <ap_id>``) over HTTP.

    Args:
        db_path: Path to the SQLite database.
        mac: Target device MAC address.
        settings: Application settings dict.
        ap_id: AP slot to activate (0 = toggle, 1, 2).

    Returns:
        Result dict ``{"mac", "ap_id", "ok"}``.
    """
    db = _open_db(db_path)
    try:
        device = _load_device_by_mac(db, mac)
        if device is None:
            raise TasmotaRuntimeError(f"Device not found: {mac}")

        _http_get(device.ip, "cmnd", _device_password(settings), f"AP%20{int(ap_id)}")
        return {"mac": mac, "ap_id": int(ap_id), "ok": True}
    finally:
        _close_db(db)


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


def check_unavailable(
    db_path: Path,
    settings: Dict[str, Any],
    mac_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ping every (or a filtered subset of) device and report which are offline.

    Args:
        db_path: Path to the SQLite database.
        settings: Application settings dict.
        mac_filter: Optional list of MACs to restrict the check to.

    Returns:
        ``{"checked", "online": [...], "offline": [...]}``.
    """
    if not _BATCH_LOCK.acquire(blocking=False):
        raise BatchInProgressError("A batch operation is already in progress")
    try:
        db = _open_db(db_path)
        try:
            devices = _filter_devices(_load_all_devices(db), mac_filter)
            password = _device_password(settings)
            online: List[str] = []
            offline: List[str] = []
            for device in devices:
                try:
                    _http_get(device.ip, "cmnd", password, "Status%200")
                    online.append(device.mac)
                except TasmotaRuntimeError:
                    offline.append(device.mac)
            return {
                "checked": len(devices),
                "online": online,
                "offline": offline,
            }
        finally:
            _close_db(db)
    finally:
        _BATCH_LOCK.release()


def force_ap_batch(
    db_path: Path,
    settings: Dict[str, Any],
    ap_id: int = 1,
    mac_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Switch the active AP on every (or filtered) device.

    The target SSID is derived from settings (``wifi1_ssid`` / ``wifi2_ssid``)
    rather than being hardcoded as in the legacy script.

    Args:
        db_path: Path to the SQLite database.
        settings: Application settings dict.
        ap_id: AP slot to activate.
        mac_filter: Optional list of MACs to restrict the operation to.

    Returns:
        ``{"total", "switched": [...], "failed": [...], "ssid"}``.
    """
    if not _BATCH_LOCK.acquire(blocking=False):
        raise BatchInProgressError("A batch operation is already in progress")
    try:
        db = _open_db(db_path)
        try:
            devices = _filter_devices(_load_all_devices(db), mac_filter)
            password = _device_password(settings)
            ssid_key = "wifi2_ssid" if int(ap_id) == 2 else "wifi1_ssid"
            ssid = settings.get(ssid_key, "")
            switched: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    _http_get(device.ip, "cmnd", password, f"AP%20{int(ap_id)}")
                    switched.append(device.mac)
                except TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "switched": switched,
                "failed": failed,
                "ssid": ssid,
            }
        finally:
            _close_db(db)
    finally:
        _BATCH_LOCK.release()


def update_firmware_batch(
    db_path: Path,
    settings: Dict[str, Any],
    target_version: str,
    mac_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Trigger OTA upgrade only on devices older than *target_version*.

    Version comparison is numeric (``utils.version_compare.is_newer``), fixing
    the legacy naive string comparison.

    Args:
        db_path: Path to the SQLite database.
        settings: Application settings dict.
        target_version: The version to upgrade toward.
        mac_filter: Optional list of MACs to restrict the operation to.

    Returns:
        ``{"total", "upgraded": [...], "skipped": [...], "failed": [...]}``.
    """
    if not _BATCH_LOCK.acquire(blocking=False):
        raise BatchInProgressError("A batch operation is already in progress")
    try:
        db = _open_db(db_path)
        try:
            devices = _filter_devices(_load_all_devices(db), mac_filter)
            password = _device_password(settings)
            upgraded: List[str] = []
            skipped: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    status = _http_get(device.ip, "cmnd", password, "Status%202")
                    current = _extract_version(status)
                    if current and not is_newer(target_version, current):
                        skipped.append(device.mac)
                        continue
                    _http_get(device.ip, "cmnd", password, "Upgrade%201")
                    upgraded.append(device.mac)
                except TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "upgraded": upgraded,
                "skipped": skipped,
                "failed": failed,
            }
        finally:
            _close_db(db)
    finally:
        _BATCH_LOCK.release()


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _filter_devices(devices: List[Any], mac_filter: Optional[List[str]]) -> List[Any]:
    """Return devices with an IP, optionally restricted to *mac_filter*."""
    result = [d for d in devices if getattr(d, "ip", None)]
    if mac_filter:
        wanted = {m.upper() for m in mac_filter}
        result = [d for d in result if d.mac.upper() in wanted]
    return result


def _extract_version(status: Dict[str, Any]) -> str:
    """Extract the firmware version from a Tasmota ``Status 2`` payload."""
    fw = status.get("StatusFWR", {})
    if isinstance(fw, dict):
        return str(fw.get("Version", ""))
    return ""


def _close_db(db: DatabaseManager) -> None:
    """Close a DatabaseManager (sync wrapper)."""

    async def _close() -> None:
        await db.close()

    try:
        asyncio.run(_close())
    except Exception as e:  # noqa: BLE001
        logger.debug("Error closing DB: %s", e)
