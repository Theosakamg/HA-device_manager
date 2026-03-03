"""DmDevice dataclass model.

Represents a physical device in the device manager.  This is the most complex
model, holding foreign keys to room, model, firmware, function and an optional
self-referencing target device.  Transient fields (prefixed with ``_``) are
populated by repository JOIN queries and are **not** persisted.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..utils.case_convert import to_camel_case, to_snake_case
from .base import SerializableMixin


@dataclass
class DmDevice(SerializableMixin):
    """Dataclass representing a physical device.

    Attributes:
        id: Primary key (auto-increment). None for new records.
        mac: Unique MAC address of the device.
        ip: Optional unique IP address of the device (NULL allowed).
        enabled: Whether the device is active.
        position_name: Human-readable position name.
        position_slug: URL-friendly position identifier.
        mode: Operating mode of the device.
        interlock: Interlock configuration string.
        ha_device_class: Home Assistant device class identifier.
        extra: JSON string with additional data.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
        room_id: Foreign key to ``DmRoom``.
        model_id: Foreign key to ``DmDeviceModel``.
        firmware_id: Foreign key to ``DmDeviceFirmware``.
        function_id: Foreign key to ``DmDeviceFunction``.
        target_id: Optional foreign key to another ``DmDevice`` (self-ref).
    """

    mac: str = ""
    ip: Optional[str] = None
    enabled: bool = True
    position_name: str = ""
    position_slug: str = ""
    mode: str = ""
    interlock: str = ""
    ha_device_class: str = ""
    extra: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    room_id: Optional[int] = None
    model_id: Optional[int] = None
    firmware_id: Optional[int] = None
    function_id: Optional[int] = None
    target_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Transient fields – populated by repository JOINs, not persisted.
    # ------------------------------------------------------------------
    _room_slug: str = field(default="", repr=False)
    _room_name: str = field(default="", repr=False)
    _floor_number: int = field(default=0, repr=False)
    _floor_slug: str = field(default="", repr=False)
    _function_name: str = field(default="", repr=False)
    _model_name: str = field(default="", repr=False)
    _firmware_name: str = field(default="", repr=False)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    # to_dict() and to_camel_dict() are inherited from SerializableMixin.

    def to_camel_dict_full(
        self,
        settings: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Serialize all data including computed and transient fields.

        Transient fields are included **without** the leading underscore so
        they can be consumed directly by API clients.  Computed properties
        (``link``, ``mqttTopic``, ``hostname``, ``fqdn``) are also added.

        Args:
            settings: Optional dict of application settings.  Recognised
                keys: ``ip_prefix``, ``dns_suffix``, ``mqtt_topic_prefix``.
                When ``None`` the compiled-in defaults are used.

        Returns:
            A complete camelCase dictionary with computed values.
        """
        data = self.to_camel_dict()

        # Include transient fields without leading underscore.
        transient: Dict[str, Any] = {
            "room_slug": self._room_slug,
            "room_name": self._room_name,
            "floor_number": self._floor_number,
            "floor_slug": self._floor_slug,
            "function_name": self._function_name,
            "model_name": self._model_name,
            "firmware_name": self._firmware_name,
        }
        for key, value in transient.items():
            data[to_camel_case(key)] = value

        # Extract configurable prefixes/suffixes from settings.
        s = settings or {}
        ip_prefix = s.get("ip_prefix", "192.168.0")
        mqtt_prefix = s.get("mqtt_topic_prefix", "home")
        dns_suffix = s.get("dns_suffix", "domo.local")

        # Include computed properties.
        data["link"] = self.link(ip_prefix=ip_prefix)
        data["mqttTopic"] = self.mqtt_topic(mqtt_prefix=mqtt_prefix)
        data["hostname"] = self.hostname()
        data["fqdn"] = self.fqdn(dns_suffix=dns_suffix)

        return data

    # ------------------------------------------------------------------
    # Computed methods
    # ------------------------------------------------------------------

    def link(self, ip_prefix: str = "192.168.0") -> Optional[str]:
        """Return the device URL based on its IP address.

        If *ip* is a plain integer it is treated as the last octet of an
        ``{ip_prefix}.X`` address.  A full dotted IP is used as-is.

        Args:
            ip_prefix: Network prefix for numeric-only IPs.

        Returns:
            The URL string or ``None`` when no IP is available.
        """
        if not self.ip:
            return None

        if self.ip.isdigit():
            return f"http://{ip_prefix}.{self.ip}"

        return f"http://{self.ip}"

    def mqtt_topic(self, mqtt_prefix: str = "home") -> Optional[str]:
        """Return the MQTT topic for this device.

        Format: ``{mqtt_prefix}/l{floor}/{room_slug}/{function}/{position_slug}``

        Args:
            mqtt_prefix: First segment of the MQTT topic.

        Returns:
            The MQTT topic string or ``None``.
        """
        if not self._floor_slug or not self._room_slug or not self._function_name:
            return None

        function_slug = self._function_name.lower().replace(" ", "_")
        return (
            f"{mqtt_prefix}/{self._floor_slug}/{self._room_slug}"
            f"/{function_slug}/{self.position_slug}"
        )

    def hostname(self) -> Optional[str]:
        """Return the hostname for this device.

        Format: ``{floor_slug}_{room_slug}_{function}_{position_slug}``

        Returns:
            The hostname string or ``None`` when transient data is missing.
        """
        if not self._floor_slug or not self._room_slug or not self._function_name:
            return None

        function_slug = self._function_name.lower().replace(" ", "_")
        return (
            f"{self._floor_slug}_{self._room_slug}"
            f"_{function_slug}_{self.position_slug}"
        )

    def fqdn(self, dns_suffix: str = "domo.local") -> Optional[str]:
        """Return the fully-qualified domain name for this device.

        Format: ``{hostname}.{dns_suffix}``

        Args:
            dns_suffix: Domain suffix appended to the hostname.

        Returns:
            The FQDN string or ``None`` when hostname cannot be computed.
        """
        host = self.hostname()
        if host is None:
            return None
        return f"{host}.{dns_suffix}"

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DmDevice":
        """Create an instance from a dictionary.

        Handles both snake_case and camelCase keys transparently.  Transient
        fields can be supplied with or without the leading underscore.

        Args:
            data: Input dictionary with field values.

        Returns:
            A new ``DmDevice`` instance.
        """
        normalized: Dict[str, Any] = {}
        for key, value in data.items():
            normalized[to_snake_case(key)] = value

        # Normalize empty-string ip to None (DB expects NULL for missing IP)
        raw_ip = normalized.get("ip")
        ip_value = None if not raw_ip or (isinstance(raw_ip, str) and raw_ip.strip() == "") else raw_ip

        return cls(
            id=normalized.get("id"),
            mac=normalized.get("mac", ""),
            ip=ip_value,
            enabled=normalized.get("enabled", True),
            position_name=normalized.get("position_name", ""),
            position_slug=normalized.get("position_slug", ""),
            mode=normalized.get("mode", ""),
            interlock=normalized.get("interlock", ""),
            ha_device_class=normalized.get("ha_device_class", ""),
            extra=normalized.get("extra", ""),
            created_at=normalized.get("created_at"),
            updated_at=normalized.get("updated_at"),
            room_id=normalized.get("room_id"),
            model_id=normalized.get("model_id"),
            firmware_id=normalized.get("firmware_id"),
            function_id=normalized.get("function_id"),
            target_id=normalized.get("target_id"),
            # Transient fields.
            _room_slug=normalized.get("room_slug", ""),
            _room_name=normalized.get("room_name", ""),
            _floor_number=normalized.get("floor_number", 0),
            _floor_slug=normalized.get("floor_slug", ""),
            _function_name=normalized.get("function_name", ""),
            _model_name=normalized.get("model_name", ""),
            _firmware_name=normalized.get("firmware_name", ""),
        )
