"""Update treatment manager.

Dispatches firmware update operations (single-device OTA upgrade and the
version-gated fleet batch) to the correct per-firmware backend. Only Tasmota
implements these operations today; the registry makes adding WLED / Zigbee
backends a one-line change.

Device loading is owned here (via ``device_loader``): the manager resolves the
target ``DmDevice`` object(s) from the database and hands them to the firmware
backend, which stays persistence-free.
"""

from typing import Dict, Type

from . import device_loader
from ..firmware.tasmota.update import TasmotaUpdate
from ..firmware.tasmota.client import BatchInProgressError, TasmotaRuntimeError

__all__ = [
    "BatchInProgressError",
    "TasmotaRuntimeError",
    "UpdateManager",
]

_UPDATE_BACKENDS: Dict[str, Type[TasmotaUpdate]] = {
    "tasmota": TasmotaUpdate,
}


class UpdateManager:
    """Dispatches firmware update operations to a per-firmware backend.

    The firmware family is selected once at construction; every method then
    forwards to that backend. Only Tasmota is implemented today.
    """

    def __init__(self, firmware: str = "tasmota") -> None:
        """Resolve the update backend for *firmware*.

        Args:
            firmware: Firmware family key (defaults to ``"tasmota"``).

        Raises:
            ValueError: If no update backend is registered for *firmware*.
        """
        try:
            self._backend: TasmotaUpdate = _UPDATE_BACKENDS[firmware]()
        except KeyError as err:
            raise ValueError(f"No update backend for firmware '{firmware}'") from err

    def upgrade_device(self, db_path, mac, settings, use_mqtt=False):
        """Trigger a single-device OTA upgrade via its firmware update backend."""
        device = device_loader.get_device(db_path, mac)
        if device is None:
            raise TasmotaRuntimeError(f"Device not found: {mac}")
        return self._backend.upgrade_device(device, settings, use_mqtt)

    def update_firmware_batch(self, db_path, settings, target_version, mac_filter=None):
        """Trigger a version-gated fleet upgrade via the firmware update backend."""
        devices = device_loader.get_devices(db_path, mac_filter)
        return self._backend.update_firmware_batch(devices, settings, target_version)

    def upgrade_batch(self, db_path, settings, mac_filter=None, use_mqtt=False):
        """Trigger an unconditional fleet OTA upgrade via the firmware update backend."""
        devices = device_loader.get_devices(db_path, mac_filter)
        return self._backend.upgrade_batch(devices, settings, use_mqtt)
