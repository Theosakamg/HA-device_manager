"""Device Data Transfer Object.

Boundary object between the sealed persistence model (:class:`DmDevice`) and the
camelCase JSON representation consumed by the frontend, so controllers never
expose the DB model directly. This is the reference implementation of the DTO
pattern; the remaining entities are migrated to dedicated DTOs incrementally.
"""

from dataclasses import dataclass
from typing import Any, Dict

from ..persistence.models.device import DmDevice
from ..utils.case_convert import to_snake_case_dict


@dataclass
class DeviceDto:
    """Transfer object wrapping a :class:`DmDevice` at the API boundary."""

    model: DmDevice

    @classmethod
    def from_model(cls, model: DmDevice) -> "DeviceDto":
        """Build a DTO from a persistence model."""
        return cls(model=model)

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to the full camelCase API payload (incl. computed fields)."""
        return self.model.to_camel_dict_full()

    @staticmethod
    def to_snake_from_api(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an incoming camelCase API payload to snake_case keys."""
        return to_snake_case_dict(data)
