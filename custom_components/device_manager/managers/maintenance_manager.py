"""Maintenance treatment manager.

Dispatches runtime maintenance operations (restart, status, AP switching and
fleet batches) to the correct per-firmware backend. Only Tasmota implements
these operations today; the registry makes adding WLED / Zigbee backends a
one-line change.
"""

from types import ModuleType
from typing import Dict

from ..firmware.tasmota import maintenance as _tasmota_maintenance
from ..firmware.tasmota.client import BatchInProgressError, TasmotaRuntimeError

__all__ = [
    "BatchInProgressError",
    "TasmotaRuntimeError",
    "MaintenanceManager",
]

_MAINTENANCE_BACKENDS: Dict[str, ModuleType] = {
    "tasmota": _tasmota_maintenance,
}


class MaintenanceManager:
    """Dispatches runtime maintenance operations to a per-firmware backend.

    The firmware family is selected once at construction; every method then
    forwards to that backend. Only Tasmota is implemented today.
    """

    def __init__(self, firmware: str = "tasmota") -> None:
        """Resolve the maintenance backend for *firmware*.

        Args:
            firmware: Firmware family key (defaults to ``"tasmota"``).

        Raises:
            ValueError: If no maintenance backend is registered for *firmware*.
        """
        try:
            self._backend = _MAINTENANCE_BACKENDS[firmware]
        except KeyError as err:
            raise ValueError(f"No maintenance backend for firmware '{firmware}'") from err

    def restart_device(self, db_path, mac, settings, use_mqtt=False):
        """Restart a single device via its firmware maintenance backend."""
        return self._backend.restart_device(db_path, mac, settings, use_mqtt)

    def get_status(self, db_path, mac, settings):
        """Query a single device's status via its firmware maintenance backend."""
        return self._backend.get_status(db_path, mac, settings)

    def switch_ap(self, db_path, mac, settings, ap_id=1):
        """Switch a single device's active AP via its firmware maintenance backend."""
        return self._backend.switch_ap(db_path, mac, settings, ap_id)

    def check_unavailable(self, db_path, settings, mac_filter=None):
        """Report offline devices via the firmware maintenance backend (batch)."""
        return self._backend.check_unavailable(db_path, settings, mac_filter)

    def force_ap_batch(self, db_path, settings, ap_id=1, mac_filter=None):
        """Force the active AP fleet-wide via the firmware maintenance backend."""
        return self._backend.force_ap_batch(db_path, settings, ap_id, mac_filter)
