"""Repository for user-configurable settings (key/value store)."""

import logging
from typing import Any

from ..const import DEFAULT_SETTINGS, TABLE_SETTINGS
from ..services.database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class SettingsRepository:
    """Key/value repository backed by the dm_settings table.

    Settings are seeded from ``DEFAULT_SETTINGS`` the first time they are
    requested.  The table uses ``key TEXT PRIMARY KEY`` so there is no
    auto-increment id.
    """

    table_name = TABLE_SETTINGS

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_all(self) -> dict[str, str]:
        """Return all settings as a ``{key: value}`` dict.

        Missing keys are seeded from ``DEFAULT_SETTINGS`` automatically.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT key, value FROM {self.table_name}"  # noqa: S608
        )
        rows = await cursor.fetchall()
        stored = {row["key"]: row["value"] for row in rows}

        # Seed missing defaults
        for key, default_val in DEFAULT_SETTINGS.items():
            if key not in stored:
                await self._insert(key, default_val)
                stored[key] = default_val

        return stored

    async def get(self, key: str) -> str:
        """Return a single setting value, falling back to its default."""
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT value FROM {self.table_name} WHERE key = ?",  # noqa: S608
            (key,),
        )
        row = await cursor.fetchone()
        if row:
            return row["value"]

        # Key not in DB yet → seed it
        default = DEFAULT_SETTINGS.get(key, "")
        await self._insert(key, default)
        return default

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def set(self, key: str, value: str) -> None:
        """Create or update a single setting."""
        conn = await self.db.get_connection()
        await conn.execute(
            f"INSERT INTO {self.table_name} (key, value) VALUES (?, ?)"  # noqa: S608
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await conn.commit()
        _LOGGER.debug("Setting saved: %s = %s", key, value)

    async def set_many(self, data: dict[str, str]) -> dict[str, str]:
        """Bulk-update settings and return the final state."""
        for key, value in data.items():
            await self.set(key, value)
        return await self.get_all()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _insert(self, key: str, value: str) -> None:
        """Insert a setting without overwriting existing values."""
        conn = await self.db.get_connection()
        await conn.execute(
            f"INSERT OR IGNORE INTO {self.table_name} (key, value)"  # noqa: S608
            " VALUES (?, ?)",
            (key, value),
        )
        await conn.commit()
