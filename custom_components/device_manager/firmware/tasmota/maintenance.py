"""Tasmota *maintenance* treatment.

Runtime maintenance operations for Tasmota devices: restart, status probe,
WiFi AP switching and fleet-wide availability / AP-forcing batches. Each public
method runs synchronously inside a Home Assistant executor thread and talks to
devices over HTTP (default) or MQTT (optional). Devices are loaded by the
calling manager (``managers.maintenance_manager`` through
``managers.device_loader``) and passed in as ``DmDevice`` instances - this
layer never touches the database. A module-level lock (``client.BATCH_LOCK``)
serializes the fleet batches.
"""

import logging
from typing import Any, Dict, List

from . import client, common
from ...persistence.models.device import DmDevice

logger = logging.getLogger(__name__)


class TasmotaMaintenance:
    """Stateless Tasmota maintenance backend selected by ``MaintenanceManager``.

    Groups the runtime maintenance operations (restart, status probe, AP
    switching and the fleet-wide batches) as bound methods so the
    ``firmware/tasmota`` package exposes one cohesive object per concern,
    mirroring the adapter/provision classes.
    """

    # -----------------------------------------------------------------------
    # Single-device operations
    # -----------------------------------------------------------------------

    def restart_device(
        self,
        device: DmDevice,
        settings: Dict[str, Any],
        use_mqtt: bool = False,
    ) -> Dict[str, Any]:
        """Restart a single Tasmota device.

        Args:
            device: Target device (already loaded by the manager).
            settings: Application settings dict.
            use_mqtt: Send the command over MQTT instead of HTTP.

        Returns:
            Result dict ``{"mac", "transport", "ok"}``.
        """
        if use_mqtt:
            client.mqtt_publish(
                common.build_cmnd_topic(device, settings, common.CMD_RESTART),
                common.PAYLOAD_ON,
                settings,
            )
        else:
            client.http_get(
                device.ip,
                common.build_command(common.CMD_RESTART, common.PAYLOAD_ON),
                settings,
            )

        return {
            "mac": device.mac,
            "transport": "mqtt" if use_mqtt else "http",
            "ok": True,
        }

    def get_status(
        self,
        device: DmDevice,
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Query full status (``Status 0``) of a Tasmota device over HTTP.

        Args:
            device: Target device (already loaded by the manager).
            settings: Application settings dict.

        Returns:
            Result dict ``{"mac", "online", "status"}``.
        """
        try:
            status = client.http_get(
                device.ip,
                common.build_command(common.CMD_STATUS, common.PAYLOAD_STATUS_ALL),
                settings,
            )
            return {"mac": device.mac, "online": True, "status": status}
        except client.TasmotaRuntimeError:
            return {"mac": device.mac, "online": False, "status": {}}

    def switch_ap(
        self,
        device: DmDevice,
        settings: Dict[str, Any],
        ap_id: int = 1,
    ) -> Dict[str, Any]:
        """Switch a device's active WiFi AP (``AP <ap_id>``) over HTTP.

        Args:
            device: Target device (already loaded by the manager).
            settings: Application settings dict.
            ap_id: AP slot to activate (0 = toggle, 1, 2).

        Returns:
            Result dict ``{"mac", "ap_id", "ok"}``.
        """
        client.http_get(
            device.ip,
            common.build_command(common.CMD_AP, str(ap_id)),
            settings,
        )
        return {"mac": device.mac, "ap_id": ap_id, "ok": True}

    # -----------------------------------------------------------------------
    # Batch operations
    # -----------------------------------------------------------------------

    def check_unavailable(
        self,
        devices: List[DmDevice],
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ping every provided device and report which are offline.

        Args:
            devices: Devices to check (already loaded and filtered by the manager).
            settings: Application settings dict.

        Returns:
            ``{"checked", "online": [...], "offline": [...]}``.
        """
        if not client.BATCH_LOCK.acquire(blocking=False):
            raise client.BatchInProgressError("A batch operation is already in progress")
        try:
            online: List[str] = []
            offline: List[str] = []
            for device in devices:
                try:
                    client.http_get(
                        device.ip,
                        common.build_command(common.CMD_STATUS, common.PAYLOAD_STATUS_ALL),
                        settings,
                    )
                    online.append(device.mac)
                except client.TasmotaRuntimeError:
                    offline.append(device.mac)
            return {
                "checked": len(devices),
                "online": online,
                "offline": offline,
            }
        finally:
            client.BATCH_LOCK.release()

    def force_ap_batch(
        self,
        devices: List[DmDevice],
        settings: Dict[str, Any],
        ap_id: int = 1,
    ) -> Dict[str, Any]:
        """Switch the active AP on every provided device.

        The target SSID is derived from settings (``wifi1_ssid`` / ``wifi2_ssid``)
        rather than being hardcoded as in the legacy script.

        Args:
            devices: Devices to switch (already loaded and filtered by the manager).
            settings: Application settings dict.
            ap_id: AP slot to activate.

        Returns:
            ``{"total", "switched": [...], "failed": [...], "ssid"}``.
        """
        if not client.BATCH_LOCK.acquire(blocking=False):
            raise client.BatchInProgressError("A batch operation is already in progress")
        try:
            ssid_key = "wifi2_ssid" if ap_id == 2 else "wifi1_ssid"
            ssid = settings.get(ssid_key, "")
            switched: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    client.http_get(
                        device.ip,
                        common.build_command(common.CMD_AP, str(ap_id)),
                        settings,
                    )
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
            client.BATCH_LOCK.release()

    def restart_batch(
        self,
        devices: List[DmDevice],
        settings: Dict[str, Any],
        use_mqtt: bool = False,
    ) -> Dict[str, Any]:
        """Restart every provided device.

        Each device is restarted with the same per-device transport logic as
        :meth:`restart_device` (HTTP by default, MQTT optional). Failures are
        collected per device instead of aborting the whole batch.

        Args:
            devices: Devices to restart (already loaded and filtered by the manager).
            settings: Application settings dict.
            use_mqtt: Send the command over MQTT instead of HTTP.

        Returns:
            ``{"total", "restarted": [...], "failed": [...]}``.
        """
        if not client.BATCH_LOCK.acquire(blocking=False):
            raise client.BatchInProgressError("A batch operation is already in progress")
        try:
            restarted: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    if use_mqtt:
                        client.mqtt_publish(
                            common.build_cmnd_topic(device, settings, common.CMD_RESTART),
                            common.PAYLOAD_ON,
                            settings,
                        )
                    else:
                        client.http_get(
                            device.ip,
                            common.build_command(common.CMD_RESTART, common.PAYLOAD_ON),
                            settings,
                        )
                    restarted.append(device.mac)
                except client.TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "restarted": restarted,
                "failed": failed,
            }
        finally:
            client.BATCH_LOCK.release()
