"""Shared, pure Tasmota HTTP/MQTT helpers.

Extracted from :class:`~custom_components.device_manager.provisioning.adapters.tasmota.TasmotaAdapter`
so that both the deploy-time adapter and the runtime services
(:mod:`custom_components.device_manager.services.tasmota_runtime`) share the
exact same, already-tested URL building / Referer-header / MQTT-topic logic
instead of duplicating (and re-introducing bugs already fixed once, e.g. the
missing Referer header that causes Tasmota to reject requests with
``HTTP: Referer '' denied``).

These functions take plain values (no ``self``/adapter/manager instance) so
they can be reused from any context.
"""

from typing import Dict, Optional

from requests.utils import requote_uri  # type: ignore[import-untyped]

from ...models.device import DmDevice

# MQTT FullTopic template Tasmota is configured with by the adapter's
# ``_configure_device()``: "{location}/%topic%/%prefix%/". %topic% is
# substituted with the device's Topic setting, %prefix% with "cmnd"/"stat"/
# "tele" depending on message direction.
MQTT_FULLTOPIC = "{}/%topic%/%prefix%/"

# URL template for the Tasmota HTTP API.
URL_BASE_TPL = "http://{IP_DEV}/{CMND}?"


def sanitize_data(data: str) -> str:
    """Sanitize command data for URL encoding.

    Args:
        data: Raw command data string.

    Returns:
        URL-safe encoded string.
    """
    data_safe = data.replace("%", "%25")
    data_safe = data_safe.replace("/", "%2F")
    data_safe = data_safe.replace("#", "%23")
    data_safe = data_safe.replace(" ", "%20")
    data_safe = data_safe.replace(";", "%3B")
    return data_safe


def build_url(ip: str, cmd: str, data: Optional[str] = None) -> str:
    """Build and sanitize a URL for the Tasmota HTTP API.

    Args:
        ip: Device IP address.
        cmd: Command type (e.g. ``"cm"``, ``"dl"``).
        data: Optional command data.

    Returns:
        Sanitized, request-ready URL string.
    """
    url_base = URL_BASE_TPL.format(IP_DEV=ip, CMND=cmd)

    if data:
        data_safe = sanitize_data(data)
        url_full = url_base + data_safe
    else:
        url_full = url_base

    return str(requote_uri(url_full))


def referer_headers(ip: Optional[str]) -> Dict[str, str]:
    """Build a self-referencing Referer header for Tasmota HTTP API calls.

    Tasmota rejects HTTP API requests with an empty/foreign Referer unless
    ``SetOption128 1`` is set or a Webpassword is configured (error:
    ``HTTP: Referer '' denied. Use 'SetOption128 1' ...``). This is enabled
    by default after a factory reset, which also clears any configured
    Webpassword - a chicken-and-egg lockout since we need HTTP access to
    reconfigure the device. Sending a same-origin Referer (as a browser
    hitting the device's own web UI would) is trusted by Tasmota regardless
    of SetOption128, so always set it. Do not remove.

    Args:
        ip: Device IP address.

    Returns:
        Headers dict with a self-referencing Referer.
    """
    return {"Referer": f"http://{ip}/"}


def mqtt_topic_location(device: DmDevice, mqtt_prefix: str) -> str:
    """Get the MQTT topic location part for a device.

    Args:
        device: Device instance.
        mqtt_prefix: Configured MQTT topic prefix (``mqtt_topic_prefix`` setting).

    Returns:
        Topic location string (e.g. ``"home/l0/room"``).
    """
    return f"{mqtt_prefix}/{device._floor.slug}/{device._room.slug}"


def mqtt_topic_device(device: DmDevice) -> str:
    """Get the MQTT topic device part for a device.

    Args:
        device: Device instance.

    Returns:
        Topic device string (e.g. ``"/function/position"``).
    """
    function_slug = device._refs.function_name.lower().replace(" ", "_")
    return f"/{function_slug}/{device.position_slug}"


def build_cmnd_topic(device: DmDevice, mqtt_prefix: str) -> str:
    """Build the full MQTT ``cmnd/`` topic Tasmota listens on for *device*.

    Deterministically derived from the same fields the adapter uses to
    configure the device's ``FullTopic``/``Topic`` at deploy time (see
    ``TasmotaAdapter._configure_device()``), so no dependency on the HA core
    ``tasmota`` integration's MQTT discovery data is needed (that data has
    already changed shape once across a HA core refactor and broke the
    original pyscript-based lookup).

    Args:
        device: Device instance.
        mqtt_prefix: Configured MQTT topic prefix (``mqtt_topic_prefix`` setting).

    Returns:
        Full command topic string (e.g. ``"home/l0/room/button/desk/cmnd/"``).
    """
    location = mqtt_topic_location(device, mqtt_prefix)
    topic_device = mqtt_topic_device(device).lstrip("/")
    full_topic = MQTT_FULLTOPIC.format(location)
    return full_topic.replace("%topic%", topic_device).replace("%prefix%", "cmnd")
