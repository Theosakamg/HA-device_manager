"""Home Assistant registry sync result Data Transfer Object.

Composite boundary object shared by the floor / area / group sync endpoints.
It owns the ``{<collection>: [...], "total": N}`` envelope and derives ``total``
from the item count, so the three controllers no longer hand-write (and risk
desyncing) the length. The already-camelCase item dicts are passed through
unchanged.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class HaSyncResultDto:
    """Result envelope for a Home Assistant registry synchronization."""

    collection_key: str
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to ``{<collection_key>: items, "total": len(items)}``."""
        return {
            self.collection_key: list(self.items),
            "total": len(self.items),
        }
