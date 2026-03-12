"""Migration 0003: add last_deploy_at and last_deploy_status to dm_devices."""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Add last_deploy_at and last_deploy_status columns to dm_devices if missing."""
    cursor = await db.execute("PRAGMA table_info(dm_devices)")
    columns = {row["name"] for row in await cursor.fetchall()}

    for col, definition in (
        ("last_deploy_at", "TIMESTAMP DEFAULT NULL"),
        ("last_deploy_status", "TEXT DEFAULT NULL"),
    ):
        if col not in columns:
            await db.execute(
                f"ALTER TABLE dm_devices ADD COLUMN {col} {definition}"
            )
            await db.commit()
