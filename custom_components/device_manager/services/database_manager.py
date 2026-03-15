"""Database manager for Device Manager integration."""

import importlib.util
import logging
from pathlib import Path
from typing import Optional

import aiosqlite

_LOGGER = logging.getLogger(__name__)

_BUILDINGS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_buildings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT '',
        slug TEXT NOT NULL DEFAULT '' CHECK(length(slug) > 0),
        description TEXT DEFAULT '',
        image TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_FLOORS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_floors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT '',
        slug TEXT NOT NULL DEFAULT '' CHECK(length(slug) > 0),
        description TEXT DEFAULT '',
        image TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        building_id INTEGER NOT NULL,
        FOREIGN KEY (building_id) REFERENCES dm_buildings(id)
            ON DELETE CASCADE
    )
"""

_ROOMS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT '',
        slug TEXT NOT NULL DEFAULT '' CHECK(length(slug) > 0),
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
"""

_DEVICE_MODELS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_device_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enabled INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL DEFAULT '',
        template TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_DEVICE_FIRMWARES_DDL = """
    CREATE TABLE IF NOT EXISTS dm_device_firmwares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enabled INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL DEFAULT '',
        deployable INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_DEVICE_FUNCTIONS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_device_functions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enabled INTEGER NOT NULL DEFAULT 1,
        name TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_DEVICES_DDL = """
    CREATE TABLE IF NOT EXISTS dm_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT UNIQUE DEFAULT '',
        ip TEXT UNIQUE DEFAULT NULL,
        enabled BOOLEAN NOT NULL DEFAULT 1,
        state TEXT NOT NULL DEFAULT 'deployed' CHECK(state IN ('deployed', 'parking', 'out_of_order', 'deployed_hot')),
        position_name TEXT DEFAULT '',
        position_slug TEXT DEFAULT '',
        mode TEXT DEFAULT '',
        interlock TEXT DEFAULT '',
        ha_device_class TEXT DEFAULT '',
        extra TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_deploy_at TIMESTAMP DEFAULT NULL,
        last_deploy_status TEXT DEFAULT NULL,
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

_SETTINGS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    )
"""

_MIGRATIONS_DDL = """
    CREATE TABLE IF NOT EXISTS dm_migrations (
        name TEXT PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

_ACTIVITY_LOG_DDL = """
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
            await db.execute(_BUILDINGS_DDL)

            # 2. Floors
            await db.execute(_FLOORS_DDL)

            # 3. Rooms
            await db.execute(_ROOMS_DDL)

            # 4. Device Models
            await db.execute(_DEVICE_MODELS_DDL)

            # 5. Device Firmwares
            await db.execute(_DEVICE_FIRMWARES_DDL)

            # 6. Device Functions
            await db.execute(_DEVICE_FUNCTIONS_DDL)

            # 7. Devices
            await db.execute(_DEVICES_DDL)

            # 8. Settings (key/value pairs for user-configurable constants)
            await db.execute(_SETTINGS_DDL)

            # 9. Activity log
            await db.execute(_ACTIVITY_LOG_DDL)

            await db.commit()

            await self._run_migrations(db)

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

    async def _run_migrations(self, db: aiosqlite.Connection) -> None:
        """Discover and apply pending migrations from the migrations/ folder.

        Each migration is a Python module exposing an async ``run(db)``
        function.  Applied migrations are tracked in ``dm_migrations`` so
        they are never executed twice.
        """
        await db.execute(_MIGRATIONS_DDL)
        await db.commit()

        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            return

        cursor = await db.execute("SELECT name FROM dm_migrations")
        applied = {row[0] for row in await cursor.fetchall()}

        files = sorted(
            f for f in migrations_dir.glob("[0-9]*.py")
        )

        for mig_file in files:
            if mig_file.name in applied:
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    mig_file.stem, mig_file
                )
                module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
                spec.loader.exec_module(module)  # type: ignore[union-attr]
                await module.run(db)
                await db.execute(
                    "INSERT INTO dm_migrations (name) VALUES (?)",
                    (mig_file.name,),
                )
                await db.commit()
                _LOGGER.info("Applied migration: %s", mig_file.name)
            except Exception as err:
                _LOGGER.warning(
                    "Migration %s skipped: %s", mig_file.name, err
                )
