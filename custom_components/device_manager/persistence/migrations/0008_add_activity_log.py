"""Migration 0008: create dm_activity_log table.

Adds the audit / activity log table for tracking configuration changes
and triggered actions within the integration.
"""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Create dm_activity_log table if it doesn't exist."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS dm_activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            user       TEXT NOT NULL DEFAULT 'system',
            event_type TEXT NOT NULL DEFAULT 'action'
                       CHECK(event_type IN ('config_change', 'action')),
            entity_type TEXT NOT NULL DEFAULT '',
            entity_id  INTEGER DEFAULT NULL,
            message    TEXT NOT NULL DEFAULT '',
            result     TEXT DEFAULT NULL,
            severity   TEXT NOT NULL DEFAULT 'info'
                       CHECK(severity IN ('info', 'warning', 'error'))
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp "
        "ON dm_activity_log (timestamp DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_activity_log_event_type "
        "ON dm_activity_log (event_type)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_activity_log_entity_type "
        "ON dm_activity_log (entity_type)"
    )
    await db.commit()
