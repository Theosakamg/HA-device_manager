"""DmDeviceFunction dataclass model.

Represents a device function (role / purpose) in the device manager.
"""

from dataclasses import dataclass
from typing import Optional

from .base import SerializableMixin


@dataclass
class DmDeviceFunction(SerializableMixin):
    """Dataclass representing a device function.

    Attributes:
        id: Primary key (auto-increment). None for new records.
        enabled: Whether this function is active.
        name: Display name of the function.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    enabled: bool = True
    name: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
