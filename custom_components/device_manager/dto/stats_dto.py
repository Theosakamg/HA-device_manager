"""Dashboard statistics Data Transfer Object.

Composite boundary object for the dashboard statistics endpoint. It owns the
assembly of the aggregated payload (nesting the settings counters under
``settingsCounts`` and the deployment counters under ``deployment``) so the
controller only runs the queries while the payload shape lives in the DTO layer.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _default_deployment() -> Dict[str, int]:
    return {"total": 0, "success": 0, "fail": 0}


@dataclass
class StatsDto:
    """Aggregated dashboard statistics at the API boundary."""

    buildings: int = 0
    floors: int = 0
    rooms: int = 0
    devices: int = 0
    by_firmware: List[Dict[str, Any]] = field(default_factory=list)
    by_model: List[Dict[str, Any]] = field(default_factory=list)
    models_count: int = 0
    firmwares_count: int = 0
    functions_count: int = 0
    deployment: Dict[str, int] = field(default_factory=_default_deployment)
    deployment_by_firmware: List[Dict[str, Any]] = field(default_factory=list)
    deployment_by_model: List[Dict[str, Any]] = field(default_factory=list)

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to the nested camelCase API payload.

        The flat ``*_count`` fields are nested under ``settingsCounts``; list
        items (``byFirmware`` / ``deploymentByModel`` ...) already use
        single-word camelCase keys and pass through unchanged.
        """
        return {
            "buildings": self.buildings,
            "floors": self.floors,
            "rooms": self.rooms,
            "devices": self.devices,
            "byFirmware": list(self.by_firmware),
            "byModel": list(self.by_model),
            "settingsCounts": {
                "models": self.models_count,
                "firmwares": self.firmwares_count,
                "functions": self.functions_count,
            },
            "deployment": dict(self.deployment),
            "deploymentByFirmware": list(self.deployment_by_firmware),
            "deploymentByModel": list(self.deployment_by_model),
        }
