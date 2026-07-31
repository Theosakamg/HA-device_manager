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
    "upgrade_device",
    "update_firmware_batch",
]

_UPDATE_BACKENDS: Dict[str, ModuleType] = {
    "tasmota": _tasmota_update,
}


def _backend(firmware: str) -> ModuleType:
    """Return the update backend module for *firmware*."""
    try:
        return _UPDATE_BACKENDS[firmware]
    except KeyError as err:
        raise ValueError(f"No update backend for firmware '{firmware}'") from err


def upgrade_device(db_path, mac, settings, use_mqtt=False, firmware="tasmota"):
    """Trigger a single-device OTA upgrade via its firmware update backend."""
    return _backend(firmware).upgrade_device(db_path, mac, settings, use_mqtt)


def update_firmware_batch(db_path, settings, target_version, mac_filter=None, firmware="tasmota"):
    """Trigger a version-gated fleet upgrade via the firmware update backend."""
    return _backend(firmware).update_firmware_batch(db_path, settings, target_version, mac_filter)
