"""Resolve a Home Assistant device_id to a Device Manager MAC address.

The Tasmota runtime services are targeted by an HA device registry
``device_id`` (a natural device picker in automations and the Developer Tools
UI). This module resolves that ``device_id`` back to the network MAC address
that Device Manager uses as its own primary key, so the rest of the runtime
logic can look the device up in the local DB via
``DeviceRepository.find_by_mac()``.
"""

from typing import Any


class TasmotaTargetError(Exception):
    """Raised when a device_id cannot be resolved to a usable MAC address."""


def resolve_device_id_to_mac(hass: Any, device_id: str) -> str:
    """Resolve an HA ``device_id`` to its network MAC address.

    Args:
        hass: Home Assistant instance.
        device_id: HA device registry id.

    Returns:
        The device's network MAC address, normalised uppercase with colons
        (e.g. ``"AA:BB:CC:DD:EE:FF"``).

    Raises:
        TasmotaTargetError: If the device_id is unknown or the device exposes
            no network MAC connection.
    """
    if not device_id:
        raise TasmotaTargetError("device_id is required")

    from homeassistant.helpers import device_registry as dr  # type: ignore[import]

    device_reg = dr.async_get(hass)
    entry = device_reg.async_get(device_id)

    if entry is None:
        raise TasmotaTargetError(f"Unknown device_id: {device_id}")

    for conn_type, conn_value in entry.connections:
        if conn_type == dr.CONNECTION_NETWORK_MAC:
            return str(dr.format_mac(conn_value)).upper()

    raise TasmotaTargetError(
        f"Device {device_id} has no network MAC address (not a Tasmota device?)"
    )
