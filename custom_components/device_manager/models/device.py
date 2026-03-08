"""DmDevice dataclass model.

Represents a physical device in the device manager.  This is the most complex
model, holding foreign keys to room, model, firmware, function and an optional
self-referencing target device.  Transient fields (prefixed with ``_``) are
populated by repository JOIN queries and are **not** persisted.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..utils.case_convert import to_snake_case
from .base import SerializableMixin


# ---------------------------------------------------------------------------
# Transient reference sub-objects — populated by JOIN queries, never stored.
# ---------------------------------------------------------------------------

@dataclass
class DeviceRoomRef:
    """Transient room info joined alongside a device."""
    name: str = ""
    slug: str = ""


@dataclass
class DeviceFloorRef:
    """Transient floor info joined alongside a device."""
    name: str = ""
    slug: str = ""
    number: int = 0


@dataclass
class DeviceBuildingRef:
    """Transient building info joined alongside a device."""
    name: str = ""
    slug: str = ""


@dataclass
class DeviceLinkedRefs:
    """Transient reference names for model, firmware, function and target."""
    model_name: str = ""
    firmware_name: str = ""
    function_name: str = ""
    target_mac: str = ""


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
    last_deploy_at: Optional[str] = None
    last_deploy_status: Optional[str] = None
    room_id: Optional[int] = None
    model_id: Optional[int] = None
    firmware_id: Optional[int] = None
    function_id: Optional[int] = None
    target_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Transient fields – populated by repository JOINs, not persisted.
    # ------------------------------------------------------------------
    _room: DeviceRoomRef = field(default_factory=DeviceRoomRef, repr=False)
    _floor: DeviceFloorRef = field(default_factory=DeviceFloorRef, repr=False)
    _building: DeviceBuildingRef = field(default_factory=DeviceBuildingRef, repr=False)
    _refs: DeviceLinkedRefs = field(default_factory=DeviceLinkedRefs, repr=False)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    # to_dict() and to_camel_dict() are inherited from SerializableMixin.

    def to_camel_dict_full(
        self,
        settings: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Serialize all data including computed and transient fields.

        Transient sub-objects are serialised as nested dicts under ``room``,
        ``floor``, ``building`` and ``refs`` keys.  Computed properties
        (``link``, ``mqttTopic``, ``hostname``, ``fqdn``) are also added.

        Args:
            settings: Optional dict of application settings.  Recognised
                keys: ``ip_prefix``, ``dns_suffix``, ``mqtt_topic_prefix``.
                When ``None`` the compiled-in defaults are used.

        Returns:
            A complete camelCase dictionary with computed values.
        """
        data = self.to_camel_dict()

        # Include transient sub-objects as nested dicts.
        data["room"] = {"name": self._room.name, "slug": self._room.slug}
        data["floor"] = {
            "name": self._floor.name,
            "slug": self._floor.slug,
            "number": self._floor.number,
        }
        data["building"] = {
            "name": self._building.name,
            "slug": self._building.slug
        }
        data["refs"] = {
            "modelName": self._refs.model_name,
            "firmwareName": self._refs.firmware_name,
            "functionName": self._refs.function_name,
            "targetMac": self._refs.target_mac,
        }

        # Extract configurable prefixes/suffixes from settings.
        s = settings or {}
        ip_prefix = s.get("ip_prefix", "192.168.0")
        dns_suffix = s.get("dns_suffix", "domo.local")

        # Include computed properties.
        data["link"] = self.link(ip_prefix=ip_prefix)
        data["mqttTopic"] = self.mqtt_topic()
        data["hostname"] = self.hostname()
        data["fqdn"] = self.fqdn(dns_suffix=dns_suffix)
        data["displayName"] = self.display_name()

        return data

    # ------------------------------------------------------------------
    # Computed methods
    # ------------------------------------------------------------------

    def display_name(self) -> str:
        """Return a short human-readable label for this device.

        Format: ``Building > Floor > Room > Function > Position``

        Parts that are empty are omitted so the result is always non-empty.
        Falls back to the MAC address when no hierarchy data is available.

        Returns:
            A ``>``-separated string identifying the device location and role.
        """
        sep = " > "
        parts = [
            self._building.name or self._building.slug.capitalize(),
            self._floor.name or self._floor.slug.capitalize(),
            self._room.name or self._room.slug.capitalize(),
            self._refs.function_name,
            self.position_name or self.position_slug.capitalize(),
        ]
        label = sep.join(p for p in parts if p)
        return label or self.mac

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

    def mqtt_topic(self) -> Optional[str]:
        """Return the MQTT topic for this device.

        Format: ``{building_slug}/{floor_slug}/{room_slug}/{function_slug}/{position_slug}``

        Returns:
            The MQTT topic string or ``None`` when required transient data is missing.
        """
        if (
            not self._building.slug
            or not self._floor.slug
            or not self._room.slug
            or not self._refs.function_name
        ):
            return None

        function_slug = self._refs.function_name.lower().replace(" ", "_")
        return (
            f"{self._building.slug}"
            f"/{self._floor.slug}"
            f"/{self._room.slug}"
            f"/{function_slug}"
            f"/{self.position_slug}"
        ).lower()

    def hostname(self) -> Optional[str]:
        """Return the hostname for this device.

        Format: ``{building_slug}_{floor_slug}_{room_slug}_{function_slug}_{position_slug}``

        Returns:
            The hostname string or ``None`` when required transient data is missing.
        """
        if (
            not self._building.slug
            or not self._floor.slug
            or not self._room.slug
            or not self._refs.function_name
        ):
            return None

        function_slug = self._refs.function_name.lower().replace(" ", "_")
        return (
            f"{self._building.slug}"
            f"_{self._floor.slug}"
            f"_{self._room.slug}"
            f"_{function_slug}"
            f"_{self.position_slug}"
        ).lower()

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
            last_deploy_at=normalized.get("last_deploy_at"),
            last_deploy_status=normalized.get("last_deploy_status"),
            room_id=normalized.get("room_id"),
            model_id=normalized.get("model_id"),
            firmware_id=normalized.get("firmware_id"),
            function_id=normalized.get("function_id"),
            target_id=normalized.get("target_id"),
            # Transient sub-objects built from JOIN columns.
            _room=DeviceRoomRef(
                name=normalized.get("room_name", ""),
                slug=normalized.get("room_slug", ""),
            ),
            _floor=DeviceFloorRef(
                name=normalized.get("floor_name", ""),
                slug=normalized.get("floor_slug", ""),
                number=normalized.get("floor_number", 0),
            ),
            _building=DeviceBuildingRef(
                name=normalized.get("building_name", ""),
                slug=normalized.get("building_slug", ""),
            ),
            _refs=DeviceLinkedRefs(
                model_name=normalized.get("model_name", ""),
                firmware_name=normalized.get("firmware_name", ""),
                function_name=normalized.get("function_name", ""),
                target_mac=normalized.get("target_mac", ""),
            ),
        )
