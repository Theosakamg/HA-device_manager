"""Database manager for Device Manager integration."""

import logging
from pathlib import Path
from typing import Optional

import aiosqlite

_LOGGER = logging.getLogger(__name__)

_DEVICES_DDL = """
    CREATE TABLE IF NOT EXISTS dm_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT UNIQUE DEFAULT '',
        ip TEXT UNIQUE DEFAULT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        position_name TEXT DEFAULT '',
        position_slug TEXT DEFAULT '',
        mode TEXT DEFAULT '',
        interlock TEXT DEFAULT '',
        ha_device_class TEXT DEFAULT '',
        extra TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        room_id INTEGER NOT NULL,
        model_id INTEGER NOT NULL,
        firmware_id INTEGER NOT NULL,
        function_id INTEGER NOT NULL,
        target_id INTEGER,
        FOREIGN KEY (room_id) REFERENCES dm_rooms(id)
            ON DELETE CASCADE,
        FOREIGN KEY (model_id) REFERENCES dm_device_models(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (firmware_id)
            REFERENCES dm_device_firmwares(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (function_id)
            REFERENCES dm_device_functions(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (target_id) REFERENCES dm_devices(id)
            ON DELETE SET NULL
    )
"""


class DatabaseManager:
    """Manage the SQLite database lifecycle for Device Manager.

    Provides a shared connection pool and handles table creation
    for all 7 entity tables with proper foreign key constraints.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize database manager.

        Args:
            db_path: Absolute path to the SQLite database file.
        """
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
        _LOGGER.info("Database path: %s", self.db_path)

    async def get_connection(self) -> aiosqlite.Connection:
        """Get or create a shared database connection.

        Returns:
            An active aiosqlite connection with foreign keys enabled.
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    async def initialize(self) -> None:
        """Create all database tables if they do not exist.

        Creates tables in order respecting foreign key dependencies.
        """
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            db = await self.get_connection()

            # 1. Buildings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_buildings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    slug TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    image TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Floors
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_floors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    slug TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    image TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    building_id INTEGER NOT NULL,
                    FOREIGN KEY (building_id) REFERENCES dm_buildings(id)
                        ON DELETE CASCADE
                )
            """)

            # 3. Rooms
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    slug TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    image TEXT DEFAULT '',
                    login TEXT DEFAULT '',
                    password TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    floor_id INTEGER NOT NULL,
                    FOREIGN KEY (floor_id) REFERENCES dm_floors(id)
                        ON DELETE CASCADE
                )
            """)

            # 4. Device Models
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_device_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL DEFAULT '',
                    template TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Device Firmwares
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_device_firmwares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. Device Functions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_device_functions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. Devices
            await db.execute(_DEVICES_DDL)

            # 8. Settings (key/value pairs for user-configurable constants)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT ''
                )
            """)

            await db.commit()

            # Migration: recreate dm_devices if ip has wrong constraint
            # SQLite UNIQUE treats '' as a value, need NULL default
            try:
                await self._migrate_devices_ip_nullable(db)
            except Exception as mig_err:
                _LOGGER.warning("Device ip migration skipped: %s", mig_err)

            # Migration: add login/password columns to dm_rooms if missing
            try:
                await self._migrate_rooms_add_credentials(db)
            except Exception as mig_err:
                _LOGGER.warning("Room credentials migration skipped: %s", mig_err)

            _LOGGER.info(
                "Database initialized successfully with all tables"
            )
        except Exception as err:
            _LOGGER.error("Failed to initialize database: %s", err)
            raise

    async def close(self) -> None:
        """Close the shared database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            _LOGGER.info("Database connection closed")

    async def _migrate_devices_ip_nullable(
        self, db: aiosqlite.Connection
    ) -> None:
        """Migrate dm_devices table: make ip column nullable with NULL default.

        SQLite cannot ALTER COLUMN constraints, so we recreate the table
        if the ip column currently has a non-NULL default.
        """
        cursor = await db.execute("PRAGMA table_info(dm_devices)")
        columns = await cursor.fetchall()
        if not columns:
            return  # Table does not exist yet

        # Check if ip column default is '' (old schema)
        for col in columns:
            col_dict = dict(col)
            if col_dict["name"] == "ip" and col_dict["dflt_value"] == "''":
                _LOGGER.info(
                    "Migrating dm_devices: ip -> nullable"
                )
                await db.execute(
                    "ALTER TABLE dm_devices"
                    " RENAME TO _dm_devices_old"
                )
                await db.execute(_DEVICES_DDL)
                await db.execute("""
                    INSERT INTO dm_devices
                    SELECT
                        id, mac, NULLIF(ip, ''),
                        enabled, position_name,
                        position_slug, mode,
                        interlock, ha_device_class,
                        extra, created_at,
                        updated_at, room_id,
                        model_id, firmware_id,
                        function_id, target_id
                    FROM _dm_devices_old
                """)
                await db.execute(
                    "DROP TABLE _dm_devices_old"
                )
                await db.commit()
                _LOGGER.info(
                    "Migration complete: ip is now nullable"
                )
                return

    async def _migrate_rooms_add_credentials(
        self, db: aiosqlite.Connection
    ) -> None:
        """Migrate dm_rooms table: add login and password columns if missing.

        SQLite supports ``ALTER TABLE … ADD COLUMN`` which is safe to run
        even when the table already exists – it only fails when the column
        already exists.  We swallow that error gracefully.
        """
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
                _LOGGER.info("Migration: added dm_rooms.%s column", col)
