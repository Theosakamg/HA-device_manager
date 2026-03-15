"""DmActivityLog dataclass model.

Represents a single audit/activity log entry persisted in dm_activity_log.
"""

from dataclasses import dataclass, field
from typing import Optional

from .base import SerializableMixin


@dataclass
class DmActivityLog(SerializableMixin):
    """A single audit log entry recording a config change or triggered action.

    Fields:
        id:          Auto-increment primary key.
        timestamp:   UTC timestamp string (ISO 8601).
        user:        HA display name of the user who triggered the event.
        event_type:  'config_change' or 'action'.
        entity_type: Affected entity kind (device, room, floor, building,
                     device_model, device_firmware, device_function,
                     setting, import, deploy, scan, maintenance, ha_sync).
        entity_id:   FK to the affected record (nullable).
        message:     Human-readable description (supports Markdown).
        result:      Raw output / error log (nullable).
        severity:    'info', 'warning', or 'error'.
    """

    id: Optional[int] = field(default=None)
    timestamp: str = field(default="")
    user: str = field(default="system")
    event_type: str = field(default="action")
    entity_type: str = field(default="")
    entity_id: Optional[int] = field(default=None)
    message: str = field(default="")
    result: Optional[str] = field(default=None)
    severity: str = field(default="info")
