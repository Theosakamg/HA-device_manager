"""Common, pure Tasmota HTTP/MQTT helpers.

Extracted from :class:`~custom_components.device_manager.firmware.tasmota.provision.TasmotaAdapter`
so that both the deploy-time adapter and the runtime treatments
(:mod:`custom_components.device_manager.firmware.tasmota.maintenance` and
:mod:`custom_components.device_manager.firmware.tasmota.update`) share the
exact same, already-tested URL building / Referer-header / MQTT-topic logic
instead of duplicating (and re-introducing bugs already fixed once, e.g. the
missing Referer header that causes Tasmota to reject requests with
``HTTP: Referer '' denied``).

These functions take plain values (no ``self``/adapter/manager instance) so
they can be reused from any context.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

from requests.utils import requote_uri  # type: ignore[import-untyped]

from ...persistence.models.device import DmDevice

# MQTT FullTopic template Tasmota is configured with by the adapter's
# ``_configure_device()``: "{location}/%topic%/%prefix%/". %topic% is
# substituted with the device's Topic setting, %prefix% with "cmnd"/"stat"/
# "tele" depending on message direction.
MQTT_FULLTOPIC = "{}/%topic%/%prefix%/"

# URL template for the Tasmota HTTP API.
URL_BASE_TPL = "http://{IP_DEV}/{CMND}?"

# Tasmota HTTP *command* endpoint. Commands are sent as ``/cm?cmnd=<command>``.
CMND_ENDPOINT = "cm"

# ---------------------------------------------------------------------------
# Tasmota console commands
# ---------------------------------------------------------------------------
# Command *verbs*. Used both as the HTTP ``cmnd=`` command and, for MQTT, as
# the command-topic suffix (``cmnd/<topic>/Restart``).
CMD_RESTART = "Restart"
CMD_UPGRADE = "Upgrade"
CMD_STATUS = "Status"
CMD_AP = "AP"
# Batch prefix: run the following ``;``-separated commands back-to-back with no
# inter-command delay (``Backlog0 cmd1;cmd2;...``).
CMD_BACKLOG = "Backlog0"

# Command *payloads* (arguments).
PAYLOAD_ON = "1"                # Restart 1 / Upgrade 1 (also the MQTT payload)
PAYLOAD_STATUS_ALL = "0"        # Status 0 -> full status report
PAYLOAD_STATUS_FIRMWARE = "2"   # Status 2 -> firmware/version report


def build_command(verb: str, payload: str = "") -> str:
    """Compose a Tasmota console command string.

    Centralizes the ``"<verb> <payload>"`` convention so callers reference the
    named :data:`CMD_RESTART` / :data:`PAYLOAD_ON` constants instead of raw
    literals scattered across the runtime treatments.

    Args:
        verb: Command verb (e.g. :data:`CMD_RESTART`).
        payload: Optional command argument (e.g. :data:`PAYLOAD_ON`).

    Returns:
        The command string, e.g. ``"Restart 1"`` (or bare ``"Status"`` when no
        payload is given).
    """
    return f"{verb} {payload}" if payload else verb


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


def build_command_url(
    ip: str, command: str, params: Optional[Dict[str, str]] = None
) -> str:
    """Build a Tasmota HTTP *command* URL.

    Centralizes the ``/cm?cmnd=<command>`` convention so callers pass the raw
    command (e.g. ``"Restart 1"``, ``"Status 0"``, ``"Backlog0 Power1 0"``)
    plus optional extra query *params*, instead of hand-crafting and
    pre-encoding query strings. Values are URL-encoded (spaces -> ``%20``).

    Args:
        ip: Device IP address.
        command: Raw Tasmota command sent as the ``cmnd`` query parameter.
        params: Optional extra query parameters.

    Returns:
        Request-ready URL, e.g. ``"http://10.0.0.5/cm?cmnd=Restart%201"``.
    """
    query: Dict[str, str] = {"cmnd": command}
    if params:
        query.update(params)
    encoded = urlencode(query, quote_via=quote)
    url_base = URL_BASE_TPL.format(IP_DEV=ip, CMND=CMND_ENDPOINT)
    return str(requote_uri(url_base + encoded))


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


def build_cmnd_topic(device: DmDevice, settings: Dict[str, Any], command: str) -> str:
    """Build the full MQTT command topic Tasmota listens on for *command*.

    MQTT counterpart of :func:`build_command`: the HTTP path encodes the verb in
    the ``cmnd=`` query string, whereas MQTT encodes it as the command-topic
    suffix (``.../cmnd/<command>``) with the payload carried in the message
    body. Both are single-call builders, keeping the maintenance / update
    treatments symmetric across transports.

    The topic is deterministically derived from the same fields the adapter uses
    to configure the device's ``FullTopic``/``Topic`` at deploy time (see
    ``TasmotaAdapter._configure_device()``), so no dependency on the HA core
    ``tasmota`` integration's MQTT discovery data is needed (that data has
    already changed shape once across a HA core refactor and broke the original
    pyscript-based lookup).

    Args:
        device: Device instance.
        settings: Application settings dict (provides ``mqtt_topic_prefix``).
        command: Command verb appended as the topic suffix (e.g. :data:`CMD_RESTART`).

    Returns:
        Full command topic string (e.g. ``"home/l0/room/button/desk/cmnd/Restart"``).
    """
    mqtt_prefix = settings.get("mqtt_topic_prefix", "home")
    location = mqtt_topic_location(device, mqtt_prefix)
    topic_device = mqtt_topic_device(device).lstrip("/")
    full_topic = MQTT_FULLTOPIC.format(location)
    cmnd_prefix = full_topic.replace("%topic%", topic_device).replace("%prefix%", "cmnd")
    return f"{cmnd_prefix}{command}"
