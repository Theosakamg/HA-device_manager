"""Shared helpers to look up devices in Home Assistant's device registry.

These helpers resolve a Device Manager MAC address (network MAC or Zigbee
``0x``-prefixed EUI-64) to the corresponding Home Assistant ``DeviceEntry``.
All lookups are plain in-memory dict reads (HA preloads registries at
startup), so no ``await`` is needed despite the ``async_`` naming convention
used by Home Assistant's registry helpers.
"""

import logging
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


def get_ha_device(hass: Any, mac: str) -> Optional[Any]:
    """Return the HA ``DeviceEntry`` matching *mac*, or ``None`` if not found.

    Supports standard network MAC addresses (Tasmota, ESPHome, …) and Zigbee
    IEEE addresses stored as ``0x00124b0025156aca``.
    """
    try:
        from homeassistant.helpers import device_registry as dr  # type: ignore[import]
    except Exception:
        return None

    device_reg = dr.async_get(hass)
    ha_device = None

    # Standard network MAC (Tasmota, ESPHome, …)
    try:
        normalized = dr.format_mac(mac)
        ha_device = device_reg.async_get_device(
            connections={(dr.CONNECTION_NETWORK_MAC, normalized)}
        )
    except Exception:
        pass

    # Zigbee IEEE address: DM stores "0x00124b0025156aca" → "00:12:4b:00:25:15:6a:ca"
    if ha_device is None and isinstance(mac, str) and mac.lower().startswith("0x"):
        try:
            raw = mac[2:].lower().zfill(16)
            ieee = ":".join(raw[i:i + 2] for i in range(0, 16, 2))
            ha_device = device_reg.async_get_device(
                connections={(dr.CONNECTION_ZIGBEE, ieee)}
            )
        except Exception:
            pass

    return ha_device


def get_ha_sw_version(hass: Any, mac: str) -> Optional[str]:
    """Return the live firmware version (``sw_version``) reported by HA for *mac*.

    Returns ``None`` when the device isn't registered in HA or has no
    reported firmware version. This value is never persisted locally — it is
    fetched live from HA's device registry on every call.
    """
    ha_device = get_ha_device(hass, mac)
    if ha_device is None:
        return None
    sw_version = ha_device.sw_version
    return str(sw_version) if sw_version is not None else None
