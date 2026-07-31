"""CSV import result Data Transfer Object.

Composite boundary object for the CSV import summary. It captures the counters
produced by ``managers.csv_import_service.CSVImportService.import_csv`` and
exposes the explicit camelCase shape consumed by the frontend, so keys that
diverge from a plain rename (``target_resolved`` -> ``targetResolved``,
``target_failed`` -> ``targetFailed``) are defined here instead of relying on
implicit key camelization.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ImportResultDto:
    """Summary of a CSV import run at the API boundary."""

    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    target_resolved: int = 0
    target_failed: int = 0
    errors: List[str] = field(default_factory=list)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_result(cls, result: Dict[str, Any]) -> "ImportResultDto":
        """Build a DTO from the raw import result dict (snake_case keys)."""
        return cls(
            total=int(result.get("total", 0)),
            created=int(result.get("created", 0)),
            updated=int(result.get("updated", 0)),
            skipped=int(result.get("skipped", 0)),
            target_resolved=int(result.get("target_resolved", 0)),
            target_failed=int(result.get("target_failed", 0)),
            errors=list(result.get("errors", []) or []),
            logs=list(result.get("logs", []) or []),
        )

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to the explicit camelCase API payload.

        ``logs`` entries already use single-word keys (row/status/message/id/mac)
        and are passed through unchanged.
        """
        return {
            "total": self.total,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "targetResolved": self.target_resolved,
            "targetFailed": self.target_failed,
            "errors": list(self.errors),
            "logs": list(self.logs),
        }
