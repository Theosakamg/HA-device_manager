"""Scan report Data Transfer Object.

Composite boundary object for the network-scan result. Unlike entity DTOs
(e.g. :class:`DeviceDto`) it does not wrap a persistence model: it captures the
aggregated statistics produced by ``managers.network_scanner`` and exposes the
explicit camelCase shape consumed by the frontend, so the boundary contract is
defined in one place instead of relying on implicit key camelization.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ScanReportDto:
    """Aggregated statistics of a network scan at the API boundary."""

    total: int = 0
    mapped: int = 0
    not_found: int = 0
    errors: int = 0
    error_details: List[str] = field(default_factory=list)

    @classmethod
    def from_stats(cls, stats: Dict[str, Any]) -> "ScanReportDto":
        """Build a DTO from the raw scanner statistics dict (snake_case keys)."""
        return cls(
            total=int(stats.get("total", 0)),
            mapped=int(stats.get("mapped", 0)),
            not_found=int(stats.get("not_found", 0)),
            errors=int(stats.get("errors", 0)),
            error_details=list(stats.get("error_details", []) or []),
        )

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to the explicit camelCase API payload."""
        return {
            "total": self.total,
            "mapped": self.mapped,
            "notFound": self.not_found,
            "errors": self.errors,
            "errorDetails": list(self.error_details),
        }
