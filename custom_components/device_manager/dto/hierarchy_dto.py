"""Hierarchy tree Data Transfer Objects.

Composite boundary objects for the building/floor/room tree. A tree node is not
a 1:1 mirror of a persistence model: it drops foreign-key columns, flattens
``created_at`` / ``updated_at`` to camelCase, and adds the computed ``type``,
``deviceCount`` and recursive ``children`` fields. That model-to-node mapping
lives here (via :meth:`HierarchyNodeDto.from_entity`) instead of in the
controller, which only supplies the counts and child ordering.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class HierarchyNodeDto:
    """A single building/floor/room node in the hierarchy tree."""

    type: str
    id: int
    name: str
    slug: str
    description: Any
    image: Any
    created_at: Any
    updated_at: Any
    device_count: int
    children: List["HierarchyNodeDto"] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        node_type: str,
        entity: Any,
        device_count: int,
        children: List["HierarchyNodeDto"],
    ) -> "HierarchyNodeDto":
        """Build a node from a persistence entity plus computed fields."""
        return cls(
            type=node_type,
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            description=entity.description,
            image=entity.image,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            device_count=device_count,
            children=children,
        )

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize the node (and its children) to the camelCase API payload."""
        return {
            "type": self.type,
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image": self.image,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "deviceCount": self.device_count,
            "children": [child.to_api_dict() for child in self.children],
        }


@dataclass
class HierarchyDto:
    """Full hierarchy tree at the API boundary."""

    buildings: List[HierarchyNodeDto] = field(default_factory=list)
    total_devices: int = 0

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize the tree to the camelCase API payload."""
        return {
            "buildings": [node.to_api_dict() for node in self.buildings],
            "totalDevices": self.total_devices,
        }
