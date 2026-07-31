"""DmFloor dataclass model.

Represents a floor belonging to a building in the device manager hierarchy.
"""

from dataclasses import dataclass
from typing import Optional

from .base import SerializableMixin


@dataclass
class DmFloor(SerializableMixin):
    """Dataclass representing a floor within a building.

    Attributes:
        building_id: Foreign key referencing the parent ``DmBuilding``. Required.
        name: Display name of the floor.
        slug: URL-friendly identifier.
        description: Short description (max 255 characters).
        image: Path or URL to an image representing the floor.
        id: Primary key (auto-increment). None for new records.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    building_id: int = 0
    name: str = ""
    slug: str = ""
    description: str = ""
    image: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
