"""Update treatment manager.

Dispatches firmware update operations (single-device OTA upgrade and the
version-gated fleet batch) to the correct per-firmware backend. Only Tasmota
implements these operations today; the registry makes adding WLED / Zigbee
backends a one-line change.
"""

from types import ModuleType
from typing import Dict

from ..firmware.tasmota import update as _tasmota_update
from ..firmware.tasmota.client import BatchInProgressError, TasmotaRuntimeError

__all__ = [
    "BatchInProgressError",
    "TasmotaRuntimeError",
    "UpdateManager",
]

_UPDATE_BACKENDS: Dict[str, ModuleType] = {
    "tasmota": _tasmota_update,
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
            self._backend = _UPDATE_BACKENDS[firmware]
        except KeyError as err:
            raise ValueError(f"No update backend for firmware '{firmware}'") from err

    def upgrade_device(self, db_path, mac, settings, use_mqtt=False):
        """Trigger a single-device OTA upgrade via its firmware update backend."""
        return self._backend.upgrade_device(db_path, mac, settings, use_mqtt)

    def update_firmware_batch(self, db_path, settings, target_version, mac_filter=None):
        """Trigger a version-gated fleet upgrade via the firmware update backend."""
        return self._backend.update_firmware_batch(db_path, settings, target_version, mac_filter)
