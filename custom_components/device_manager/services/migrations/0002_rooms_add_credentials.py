"""Migration 0002: add login and password columns to dm_rooms."""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Add login and password columns to dm_rooms if missing."""
    cursor = await db.execute("PRAGMA table_info(dm_rooms)")
    columns = {row["name"] for row in await cursor.fetchall()}

    for col, definition in (
        ("login", "TEXT DEFAULT ''"),
        ("password", "TEXT DEFAULT ''"),
    ):
        if col not in columns:
            await db.execute(
                f"ALTER TABLE dm_rooms ADD COLUMN {col} {definition}"
            )
            await db.commit()
