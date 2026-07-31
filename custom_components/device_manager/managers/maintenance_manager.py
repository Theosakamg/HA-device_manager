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
    "restart_device",
    "get_status",
    "switch_ap",
    "check_unavailable",
    "force_ap_batch",
]

_MAINTENANCE_BACKENDS: Dict[str, ModuleType] = {
    "tasmota": _tasmota_maintenance,
}


def _backend(firmware: str) -> ModuleType:
    """Return the maintenance backend module for *firmware*."""
    try:
        return _MAINTENANCE_BACKENDS[firmware]
    except KeyError as err:
        raise ValueError(f"No maintenance backend for firmware '{firmware}'") from err


def restart_device(db_path, mac, settings, use_mqtt=False, firmware="tasmota"):
    """Restart a single device via its firmware maintenance backend."""
    return _backend(firmware).restart_device(db_path, mac, settings, use_mqtt)


def get_status(db_path, mac, settings, firmware="tasmota"):
    """Query a single device's status via its firmware maintenance backend."""
    return _backend(firmware).get_status(db_path, mac, settings)


def switch_ap(db_path, mac, settings, ap_id=1, firmware="tasmota"):
    """Switch a single device's active AP via its firmware maintenance backend."""
    return _backend(firmware).switch_ap(db_path, mac, settings, ap_id)


def check_unavailable(db_path, settings, mac_filter=None, firmware="tasmota"):
    """Report offline devices via the firmware maintenance backend (batch)."""
    return _backend(firmware).check_unavailable(db_path, settings, mac_filter)


def force_ap_batch(db_path, settings, ap_id=1, mac_filter=None, firmware="tasmota"):
    """Force the active AP fleet-wide via the firmware maintenance backend."""
    return _backend(firmware).force_ap_batch(db_path, settings, ap_id, mac_filter)
