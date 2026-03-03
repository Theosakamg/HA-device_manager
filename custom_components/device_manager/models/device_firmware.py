"""DmDeviceFirmware dataclass model.

Represents a device firmware version in the device manager.
"""

from dataclasses import dataclass
from typing import Optional

from .base import SerializableMixin


@dataclass
class DmDeviceFirmware(SerializableMixin):
    """Dataclass representing a device firmware entry.

    Attributes:
        id: Primary key (auto-increment). None for new records.
        enabled: Whether this firmware version is active.
        name: Display name of the firmware.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    enabled: bool = True
    name: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
