"""Look up devices in Home Assistant's device registry.

:class:`HaDeviceLookup` resolves a Device Manager MAC address (network MAC or
Zigbee ``0x``-prefixed EUI-64) to the corresponding Home Assistant
``DeviceEntry`` and derives firmware-version state from it. All lookups are
plain in-memory dict reads (HA preloads registries at startup), so no ``await``
is needed despite the ``async_`` naming convention used by Home Assistant's
registry helpers.
"""

import logging
from typing import Any, Optional

from ..const import UPSTREAM_VERSION_SENSOR
from ..firmware.tasmota.version import extract_version

_LOGGER = logging.getLogger(__name__)

_UNKNOWN_STATES = {"", "unknown", "unavailable"}


class HaDeviceLookup:
    """Gateway to Home Assistant's device/entity registries, bound to one ``hass``.

    Groups the MAC → ``DeviceEntry`` resolution and the firmware-version
    comparison helpers that all read from the same Home Assistant instance, so
    callers construct it once (``HaDeviceLookup(hass)``) instead of threading
    ``hass`` through every free-standing call.
    """

    def __init__(self, hass: Any) -> None:
        """Bind the lookup to a Home Assistant instance."""
        self._hass = hass

    def get_device(self, mac: str) -> Optional[Any]:
        """Return the HA ``DeviceEntry`` matching *mac*, or ``None`` if not found.

        Supports standard network MAC addresses (Tasmota, ESPHome, …) and Zigbee
        IEEE addresses stored as ``0x00124b0025156aca``.
        """
        try:
            from homeassistant.helpers import device_registry as dr  # type: ignore[import]
        except Exception:
            return None

        device_reg = dr.async_get(self._hass)
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

    def get_sw_version(self, mac: str) -> Optional[str]:
        """Return the live firmware version (``sw_version``) HA reports for *mac*.

        Returns ``None`` when the device isn't registered in HA or has no
        reported firmware version. This value is never persisted locally — it is
        fetched live from HA's device registry on every call.
        """
        ha_device = self.get_device(mac)
        if ha_device is None:
            return None
        sw_version = ha_device.sw_version
        return str(sw_version) if sw_version is not None else None

    def get_upstream_version(self) -> Optional[str]:
        """Return the raw state of the upstream Tasmota version sensor, or ``None``.

        Reads the ``sensor.tasmota_version_upstream`` entity state (the latest
        published Tasmota release). Returns ``None`` when the sensor is missing or
        carries no meaningful value (``unknown`` / ``unavailable`` / empty).
        """
        state = self._hass.states.get(UPSTREAM_VERSION_SENSOR)
        if state is None:
            return None
        value = state.state
        if value is None or str(value).lower() in _UNKNOWN_STATES:
            return None
        return str(value)

    def get_sw_up_to_date(self, sw_version: Optional[str]) -> Optional[bool]:
        """Return whether *sw_version* matches the latest upstream Tasmota release.

        Both the device firmware string and the upstream sensor state are cleaned
        down to their ``X.Y.Z`` form before comparison, so surrounding text such as
        ``"Tasmota v15.5.0 Sylvan"`` or a ``"(release)"`` suffix is ignored.

        Returns:
            ``True`` when both resolve to the same ``X.Y.Z`` (up to date),
            ``False`` when they differ (outdated), or ``None`` when the comparison
            can't be made (missing device version, missing upstream sensor, or a
            value with no parseable ``X.Y.Z``).
        """
        if not sw_version:
            return None
        latest_raw = self.get_upstream_version()
        if not latest_raw:
            return None
        current = extract_version(str(sw_version))
        latest = extract_version(latest_raw)
        if not current or not latest:
            return None
        return current == latest
