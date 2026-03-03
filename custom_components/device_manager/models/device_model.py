"""DmDeviceModel dataclass model.

Represents a device model (hardware reference / template) in the device manager.
"""

from dataclasses import dataclass
from typing import Optional

from .base import SerializableMixin


@dataclass
class DmDeviceModel(SerializableMixin):
    """Dataclass representing a device model.

    Attributes:
        id: Primary key (auto-increment). None for new records.
        enabled: Whether this device model is active.
        name: Display name of the device model.
        template: Template content associated with the model.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    enabled: bool = True
    name: str = ""
    template: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
