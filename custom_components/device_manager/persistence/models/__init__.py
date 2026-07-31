"""Models package for the Device Manager integration.

Exports all dataclass models used across the component.
"""

from .base import SerializableMixin
from .device import DmDevice
from .device_firmware import DmDeviceFirmware
from .device_function import DmDeviceFunction
from .device_model import DmDeviceModel
from .building import DmBuilding
from .floor import DmFloor
from .room import DmRoom

__all__ = [
    "SerializableMixin",
    "DmDevice",
    "DmDeviceFirmware",
    "DmDeviceFunction",
    "DmDeviceModel",
    "DmBuilding",
    "DmFloor",
    "DmRoom",
]
