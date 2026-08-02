"""Tasmota *update* treatment.

Firmware update operations for Tasmota devices: on-demand OTA upgrade of a
single device and a fleet-wide batch that only upgrades devices older than a
target version (numeric comparison, see :mod:`firmware.tasmota.version`).

Devices are loaded by the calling manager (``managers.update_manager`` through
``managers.device_loader``) and passed in as ``DmDevice`` instances - this layer
never touches the database.
"""

import logging
from typing import Any, Dict, List

from . import client, common
from .version import is_newer
from ...persistence.models.device import DmDevice

logger = logging.getLogger(__name__)


class TasmotaUpdate:
    """Stateless Tasmota firmware-update backend selected by ``UpdateManager``.

    Groups the OTA upgrade operations (single device, conditional batch and
    unconditional batch) as bound methods so the ``firmware/tasmota`` package
    exposes one cohesive object per concern, mirroring the adapter/provision
    classes.
    """

    def upgrade_device(
        self,
        device: DmDevice,
        settings: Dict[str, Any],
        use_mqtt: bool = False,
    ) -> Dict[str, Any]:
        """Trigger an OTA upgrade on a single Tasmota device.

        Uses the *same* correct code path as
        :meth:`TasmotaMaintenance.restart_device` - the legacy inverted
        ``curlMode`` logic is intentionally not replicated.

        Args:
            device: Target device (already loaded by the manager).
            settings: Application settings dict.
            use_mqtt: Send the command over MQTT instead of HTTP.

        Returns:
            Result dict ``{"mac", "transport", "ok"}``.
        """
        if use_mqtt:
            client.mqtt_publish(
                common.build_cmnd_topic(device, settings, common.CMD_UPGRADE),
                common.PAYLOAD_ON,
                settings,
            )
        else:
            client.http_get(
                device.ip,
                common.build_command(common.CMD_UPGRADE, common.PAYLOAD_ON),
                settings,
            )

        return {
            "mac": device.mac,
            "transport": "mqtt" if use_mqtt else "http",
            "ok": True,
        }

    def update_firmware_batch(
        self,
        devices: List[DmDevice],
        settings: Dict[str, Any],
        target_version: str,
    ) -> Dict[str, Any]:
        """Trigger OTA upgrade only on devices older than *target_version*.

        Version comparison is numeric (:func:`firmware.tasmota.version.is_newer`),
        fixing the legacy naive string comparison.

        Args:
            devices: Devices to consider (already loaded and filtered by the manager).
            settings: Application settings dict.
            target_version: The version to upgrade toward.

        Returns:
            ``{"total", "upgraded": [...], "skipped": [...], "failed": [...]}``.
        """
        if not client.BATCH_LOCK.acquire(blocking=False):
            raise client.BatchInProgressError("A batch operation is already in progress")
        try:
            upgraded: List[str] = []
            skipped: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    status = client.http_get(
                        device.ip,
                        common.build_command(common.CMD_STATUS, common.PAYLOAD_STATUS_FIRMWARE),
                        settings,
                    )
                    current = client.extract_version(status)
                    if current and not is_newer(target_version, current):
                        skipped.append(device.mac)
                        continue
                    client.http_get(
                        device.ip,
                        common.build_command(common.CMD_UPGRADE, common.PAYLOAD_ON),
                        settings,
                    )
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
            client.BATCH_LOCK.release()

    def upgrade_batch(
        self,
        devices: List[DmDevice],
        settings: Dict[str, Any],
        use_mqtt: bool = False,
    ) -> Dict[str, Any]:
        """Trigger an OTA upgrade on every provided device.

        Unlike :meth:`update_firmware_batch`, this is *unconditional*: it does
        not compare versions and always sends ``Upgrade`` to each targeted
        device, mirroring the single-device :meth:`upgrade_device` behaviour.
        Failures are collected per device instead of aborting the whole batch.

        Args:
            devices: Devices to upgrade (already loaded and filtered by the manager).
            settings: Application settings dict.
            use_mqtt: Send the command over MQTT instead of HTTP.

        Returns:
            ``{"total", "upgraded": [...], "failed": [...]}``.
        """
        if not client.BATCH_LOCK.acquire(blocking=False):
            raise client.BatchInProgressError("A batch operation is already in progress")
        try:
            upgraded: List[str] = []
            failed: List[str] = []
            for device in devices:
                try:
                    if use_mqtt:
                        client.mqtt_publish(
                            common.build_cmnd_topic(device, settings, common.CMD_UPGRADE),
                            common.PAYLOAD_ON,
                            settings,
                        )
                    else:
                        client.http_get(
                            device.ip,
                            common.build_command(common.CMD_UPGRADE, common.PAYLOAD_ON),
                            settings,
                        )
                    upgraded.append(device.mac)
                except client.TasmotaRuntimeError:
                    failed.append(device.mac)
            return {
                "total": len(devices),
                "upgraded": upgraded,
                "failed": failed,
            }
        finally:
            client.BATCH_LOCK.release()
