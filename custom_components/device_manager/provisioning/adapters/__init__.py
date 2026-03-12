"""Firmware-specific provisioning adapters.

Each adapter handles provisioning for a specific firmware type (Tasmota, WLED, Zigbee).
"""

from .tasmota import TasmotaAdapter
from .wled import WLEDAdapter
from .zigbee import ZigbeeAdapter

__all__ = [
    "TasmotaAdapter",
    "WLEDAdapter",
    "ZigbeeAdapter",
]
