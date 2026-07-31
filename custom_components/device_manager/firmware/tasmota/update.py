"""Tasmota *update* treatment.

Firmware update operations for Tasmota devices: on-demand OTA upgrade of a
single device and a fleet-wide batch that only upgrades devices older than a
target version (numeric comparison, see :mod:`firmware.tasmota.version`).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import client, shared
from .version import is_newer

logger = logging.getLogger(__name__)


def upgrade_device(
    db_path: Path,
    mac: str,
    settings: Dict[str, Any],
    use_mqtt: bool = False,
) -> Dict[str, Any]:
    """Trigger an OTA upgrade on a single Tasmota device.

    Uses the *same* correct code path as
    :func:`firmware.tasmota.maintenance.restart_device` — the legacy inverted
    ``curlMode`` logic is intentionally not replicated.

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
            topic = f"{shared.build_cmnd_topic(device, prefix)}/Upgrade"
            client.mqtt_publish(topic, "1", settings)
        else:
            client.http_get(device.ip, "cmnd", client.device_password(settings), "Upgrade%201")

        return {"mac": mac, "transport": "mqtt" if use_mqtt else "http", "ok": True}
    finally:
        client.close_db(db)


def update_firmware_batch(
    db_path: Path,
    settings: Dict[str, Any],
    target_version: str,
    mac_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Trigger OTA upgrade only on devices older than *target_version*.

    Version comparison is numeric (:func:`firmware.tasmota.version.is_newer`),
    fixing the legacy naive string comparison.

    Args:
        db_path: Path to the SQLite database.
        settings: Application settings dict.
        target_version: The version to upgrade toward.
        mac_filter: Optional list of MACs to restrict the operation to.

    Returns:
        ``{"total", "upgraded": [...], "skipped": [...], "failed": [...]}``.
    """
    if not client.BATCH_LOCK.acquire(blocking=False):
        raise client.BatchInProgressError("A batch operation is already in progress")
    try:
        db = client.open_db(db_path)
        try:
            devices = client.filter_devices(client.load_all_devices(db), mac_filter)
            password = client.device_password(settings)
            upgraded: List[str] = []
            skipped: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    status = client.http_get(device.ip, "cmnd", password, "Status%202")
                    current = client.extract_version(status)
                    if current and not is_newer(target_version, current):
                        skipped.append(device.mac)
                        continue
                    client.http_get(device.ip, "cmnd", password, "Upgrade%201")
                    upgraded.append(device.mac)
                except client.TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "upgraded": upgraded,
                "skipped": skipped,
                "failed": failed,
            }
        finally:
            client.close_db(db)
    finally:
        client.BATCH_LOCK.release()
