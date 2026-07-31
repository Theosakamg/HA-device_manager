"""Repository for destructive cross-table maintenance operations.

Owns the SQL behind the Maintenance admin page: wiping every managed table
and clearing the cached device IP addresses. Like :class:`StatsRepository`, it
spans several tables, so it is a standalone repository rather than a
:class:`BaseRepository` subclass. Keeping this SQL here preserves the
watertight persistence boundary — no ``DELETE``/``UPDATE`` statement lives in
the API layer.
"""

import logging

from ..database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class MaintenanceRepository:
    """Execute administrative wipe/reset operations across managed tables."""

    # Tables that may be wiped, ordered children-before-parents so foreign key
    # constraints are respected. This is a static whitelist interpolated into
    # DELETE statements; it must never contain user-controlled values.
    CLEANABLE_TABLES = (
        "dm_devices",
        "dm_rooms",
        "dm_floors",
        "dm_buildings",
        "dm_device_models",
        "dm_device_firmwares",
        "dm_device_functions",
    )

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize with a shared DatabaseManager.

        Args:
            db_manager: The database manager providing the shared connection.
        """
        self.db = db_manager

    async def wipe_all_data(self) -> dict[str, int]:
        """Delete every row from all cleanable tables and reset autoincrement.

        Rows are deleted in :attr:`CLEANABLE_TABLES` order to respect foreign
        key constraints, then the ``sqlite_sequence`` counters are cleared so
        primary keys restart from 1.

        Returns:
            Mapping of table name to the number of rows deleted.
        """
        conn = await self.db.get_connection()

        counts: dict[str, int] = {}
        for table in self.CLEANABLE_TABLES:
            cursor = await conn.execute(f"DELETE FROM {table}")  # noqa: S608 — table from static whitelist
            counts[table] = cursor.rowcount

        # Reset autoincrement counters (sqlite_sequence) for the wiped tables.
        for table in self.CLEANABLE_TABLES:
            await conn.execute(
                "DELETE FROM sqlite_sequence WHERE name = ?",
                (table,),
            )

        await conn.commit()
        _LOGGER.warning("Database wiped: %s", counts)
        return counts

    async def clear_ip_cache(self) -> int:
        """Reset every device IP address to ``NULL``.

        Returns:
            The number of devices whose IP was cleared.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute("UPDATE dm_devices SET ip = NULL WHERE ip IS NOT NULL")
        await conn.commit()
        _LOGGER.info("IP cache cleared: %d device(s) updated", cursor.rowcount)
        return cursor.rowcount
