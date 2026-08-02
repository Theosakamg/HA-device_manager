"""Auto-provision the upstream Tasmota version reference sensor.

The device list flags each device green (up to date) or orange (different) by
comparing its live firmware version against the latest published Tasmota
release. That reference is read from the ``sensor.tasmota_version_upstream``
entity's state.

When the entity is missing (the user has not defined it themselves), this
module creates it by fetching the latest release from GitHub and refreshes it
once a day. When the entity already exists it is left untouched, so a
user-provided sensor always takes precedence.
"""

import logging
from datetime import timedelta
from typing import Any, Callable, Optional

import aiohttp

from ..const import UPSTREAM_VERSION_SENSOR

_LOGGER = logging.getLogger(__name__)

_GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/arendst/Tasmota/releases/latest"
)
_REFRESH_INTERVAL = timedelta(hours=24)
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_FRIENDLY_NAME = "Last Release of Tasmota Version"


class UpstreamVersionSensor:
    """Auto-provisions and refreshes ``sensor.tasmota_version_upstream``.

    Bound to a single Home Assistant instance. :meth:`async_ensure` creates the
    reference sensor from the latest GitHub release and schedules a daily
    refresh, but only when the entity doesn't already exist so a user-provided
    sensor always takes precedence.
    """

    def __init__(self, hass: Any) -> None:
        """Bind the provisioner to a Home Assistant instance."""
        self._hass = hass

    async def _fetch_latest_release(self) -> Optional[dict]:
        """Fetch the latest Tasmota release metadata from GitHub, or ``None`` on error.

        Network, timeout and JSON errors are swallowed and logged as warnings: a
        transient failure must never break integration startup.
        """
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(self._hass)
        try:
            async with session.get(
                _GITHUB_LATEST_RELEASE_URL, timeout=_REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Tasmota upstream version fetch failed: HTTP %s", resp.status
                    )
                    return None
                payload: dict = await resp.json()
                return payload
        except Exception as exc:  # noqa: BLE001 - never fatal, just skip this cycle
            _LOGGER.warning("Tasmota upstream version fetch error: %s", exc)
            return None

    async def _refresh_state(self, _now: Any = None) -> None:
        """Fetch the latest release and publish it as the upstream sensor state.

        Accepts an optional ``_now`` argument so it can be used directly as the
        :func:`async_track_time_interval` callback as well as invoked eagerly at
        setup time.
        """
        data = await self._fetch_latest_release()
        if not data:
            return
        name = data.get("name") or data.get("tag_name")
        if not name:
            return
        self._hass.states.async_set(
            UPSTREAM_VERSION_SENSOR,
            str(name),
            {
                "friendly_name": _FRIENDLY_NAME,
                "icon": "mdi:information",
                "tag_name": data.get("tag_name", ""),
            },
        )
        _LOGGER.debug("Set %s = %s", UPSTREAM_VERSION_SENSOR, name)

    async def async_ensure(self) -> Optional[Callable[[], None]]:
        """Create the upstream Tasmota version sensor if it doesn't already exist.

        Returns an unsubscribe callback for the daily refresh timer when this
        integration created the sensor, or ``None`` when the entity already
        existed (provided by the user or another integration) and was left
        untouched.
        """
        if self._hass.states.get(UPSTREAM_VERSION_SENSOR) is not None:
            _LOGGER.debug(
                "%s already exists; not auto-creating", UPSTREAM_VERSION_SENSOR
            )
            return None

        await self._refresh_state()

        from homeassistant.helpers.event import async_track_time_interval

        unsub: Callable[[], None] = async_track_time_interval(
            self._hass, self._refresh_state, _REFRESH_INTERVAL
        )
        return unsub
