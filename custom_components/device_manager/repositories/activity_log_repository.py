"""Repository for DmActivityLog entries."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .base import BaseRepository
from ..models.activity_log import DmActivityLog

_LOGGER = logging.getLogger(__name__)

# Maximum rows returned per page
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200


class ActivityLogRepository(BaseRepository[DmActivityLog]):
    """Repository for dm_activity_log table.

    Provides log emission, paginated + filtered listing, and optional purge.
    Does NOT subclass CRUD because activity log entries are append-only
    (no update / delete by ID in normal operation).
    """

    table_name = "dm_activity_log"
    model_class = DmActivityLog
    allowed_columns = {
        "timestamp", "user", "event_type", "entity_type",
        "entity_id", "message", "result", "severity",
    }

    def _validate_enum(self, field_name: str, value: str, allowed: tuple[str, ...]) -> str:
        """Return value if valid, else the first allowed value (safe fallback)."""
        if value in allowed:
            return value
        _LOGGER.warning(
            "[activity_log] Invalid %s='%s', defaulting to '%s'",
            field_name, value, allowed[0],
        )
        return allowed[0]

    async def log_entry(
        self,
        user: str,
        event_type: str,
        entity_type: str,
        message: str,
        *,
        entity_id: Optional[int] = None,
        result: Optional[str] = None,
        severity: str = "info",
    ) -> None:
        """Append a new activity log entry.

        This is fire-and-forget — callers should wrap in try/except so a
        logging failure never blocks the main operation.

        Args:
            user:        HA user display name.
            event_type:  'config_change' or 'action'.
            entity_type: Affected entity kind.
            message:     Human-readable Markdown message.
            entity_id:   Optional FK to the affected record.
            result:      Optional raw output / error log.
            severity:    'info', 'warning', or 'error'.
        """
        safe_event_type = self._validate_enum(
            "event_type", event_type, ("config_change", "action")
        )
        safe_severity = self._validate_enum(
            "severity", severity, ("info", "warning", "error")
        )

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = await self.db.get_connection()
        await conn.execute(
            """
            INSERT INTO dm_activity_log
                (timestamp, user, event_type, entity_type, entity_id,
                 message, result, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, user, safe_event_type, entity_type, entity_id,
             message, result, safe_severity),
        )
        await conn.commit()

    async def list_entries(
        self,
        *,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        user: Optional[str] = None,
        severity: Optional[str] = None,
        page: int = 1,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        """Return a paginated, filtered list of activity log entries.

        Returns:
            A dict with keys: items (list[dict]), total (int), page (int),
            page_size (int), pages (int).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
        offset = (page - 1) * page_size

        conditions: list[str] = []
        params: list[Any] = []

        if date_from:
            conditions.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("timestamp <= ?")
            params.append(date_to)
        if event_type and event_type in ("config_change", "action"):
            conditions.append("event_type = ?")
            params.append(event_type)
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if user:
            conditions.append("user = ?")
            params.append(user)
        if severity and severity in ("info", "warning", "error"):
            conditions.append("severity = ?")
            params.append(severity)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        conn = await self.db.get_connection()

        count_cursor = await conn.execute(
            f"SELECT COUNT(*) FROM dm_activity_log {where_clause}",
            params,
        )
        count_row = await count_cursor.fetchone()
        total = count_row[0] if count_row else 0

        cursor = await conn.execute(
            f"""
            SELECT * FROM dm_activity_log
            {where_clause}
            ORDER BY timestamp DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        )
        rows = await cursor.fetchall()

        items = [DmActivityLog.from_dict(dict(row)).to_camel_dict() for row in rows]
        pages = max(1, (total + page_size - 1) // page_size)

        return {
            "items": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "pages": pages,
        }

    async def purge(self, older_than_days: int) -> int:
        """Delete entries older than ``older_than_days`` days.

        Args:
            older_than_days: Entries with a timestamp older than this many
                             days will be deleted.  Must be >= 1.

        Returns:
            Number of rows deleted.
        """
        if older_than_days < 1:
            raise ValueError("older_than_days must be >= 1")

        conn = await self.db.get_connection()
        cursor = await conn.execute(
            """
            DELETE FROM dm_activity_log
            WHERE datetime(timestamp) < datetime('now', ? || ' days')
            """,
            (f"-{older_than_days}",),
        )
        await conn.commit()
        deleted = cursor.rowcount
        _LOGGER.info("[activity_log] Purged %d entries older than %d days", deleted, older_than_days)
        return deleted
