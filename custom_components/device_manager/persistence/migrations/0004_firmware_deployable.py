"""Migration 0004: add deployable column to dm_device_firmwares."""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Add deployable column to dm_device_firmwares if missing."""
    cursor = await db.execute("PRAGMA table_info(dm_device_firmwares)")
    columns = {row["name"] for row in await cursor.fetchall()}

    if "deployable" not in columns:
        await db.execute(
            "ALTER TABLE dm_device_firmwares ADD COLUMN deployable INTEGER NOT NULL DEFAULT 0"
        )
        await db.commit()
