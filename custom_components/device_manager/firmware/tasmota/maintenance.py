"""Tasmota *maintenance* treatment.

Runtime maintenance operations for Tasmota devices: restart, status probe,
WiFi AP switching and fleet-wide availability / AP-forcing batches. Each public
function runs synchronously inside a Home Assistant executor thread and talks to
devices over HTTP (default) or MQTT (optional), mirroring the
``managers/deploy_manager.py`` pattern (sync entry points, own DB connection, a
module-level lock for batch operations).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import client, shared

logger = logging.getLogger(__name__)


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
    db = client.open_db(db_path)
    try:
        device = client.load_device_by_mac(db, mac)
        if device is None:
            raise client.TasmotaRuntimeError(f"Device not found: {mac}")

        if use_mqtt:
            prefix = settings.get("mqtt_topic_prefix", "home")
            topic = f"{shared.build_cmnd_topic(device, prefix)}/Restart"
            client.mqtt_publish(topic, "1", settings)
        else:
            client.http_get(device.ip, "cmnd", client.device_password(settings), "Restart%201")

        return {"mac": mac, "transport": "mqtt" if use_mqtt else "http", "ok": True}
    finally:
        client.close_db(db)


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
    db = client.open_db(db_path)
    try:
        device = client.load_device_by_mac(db, mac)
        if device is None:
            raise client.TasmotaRuntimeError(f"Device not found: {mac}")

        try:
            status = client.http_get(device.ip, "cmnd", client.device_password(settings), "Status%200")
            return {"mac": mac, "online": True, "status": status}
        except client.TasmotaRuntimeError:
            return {"mac": mac, "online": False, "status": {}}
    finally:
        client.close_db(db)


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
    db = client.open_db(db_path)
    try:
        device = client.load_device_by_mac(db, mac)
        if device is None:
            raise client.TasmotaRuntimeError(f"Device not found: {mac}")

        client.http_get(device.ip, "cmnd", client.device_password(settings), f"AP%20{int(ap_id)}")
        return {"mac": mac, "ap_id": int(ap_id), "ok": True}
    finally:
        client.close_db(db)


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
    if not client.BATCH_LOCK.acquire(blocking=False):
        raise client.BatchInProgressError("A batch operation is already in progress")
    try:
        db = client.open_db(db_path)
        try:
            devices = client.filter_devices(client.load_all_devices(db), mac_filter)
            password = client.device_password(settings)
            online: List[str] = []
            offline: List[str] = []
            for device in devices:
                try:
                    client.http_get(device.ip, "cmnd", password, "Status%200")
                    online.append(device.mac)
                except client.TasmotaRuntimeError:
                    offline.append(device.mac)
            return {
                "checked": len(devices),
                "online": online,
                "offline": offline,
            }
        finally:
            client.close_db(db)
    finally:
        client.BATCH_LOCK.release()


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
    if not client.BATCH_LOCK.acquire(blocking=False):
        raise client.BatchInProgressError("A batch operation is already in progress")
    try:
        db = client.open_db(db_path)
        try:
            devices = client.filter_devices(client.load_all_devices(db), mac_filter)
            password = client.device_password(settings)
            ssid_key = "wifi2_ssid" if int(ap_id) == 2 else "wifi1_ssid"
            ssid = settings.get(ssid_key, "")
            switched: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    client.http_get(device.ip, "cmnd", password, f"AP%20{int(ap_id)}")
                    switched.append(device.mac)
                except client.TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "switched": switched,
                "failed": failed,
                "ssid": ssid,
            }
        finally:
            client.close_db(db)
    finally:
        client.BATCH_LOCK.release()
