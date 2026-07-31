"""Tests for :class:`MaintenanceRepository` and ``DatabaseManager.checkpoint``.

Exercises the destructive maintenance SQL (full wipe with autoincrement reset,
IP-cache clearing) and the WAL checkpoint helper, all loaded directly by file
path without a Home Assistant install.
"""

import asyncio
import sys
import tempfile
import types
from pathlib import Path

import helpers  # provided via sys.path by run_tests.py

# ---------------------------------------------------------------------------
# Bootstrap: load DatabaseManager + MaintenanceRepository without importing HA
# ---------------------------------------------------------------------------

database_manager_module = helpers.load_module("persistence/database_manager.py")
DatabaseManager = database_manager_module.DatabaseManager  # type: ignore[attr-defined]

sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
sys.modules.setdefault(
    "custom_components.device_manager",
    types.ModuleType("custom_components.device_manager"),
)
_persist = sys.modules.setdefault(
    "custom_components.device_manager.persistence",
    types.ModuleType("custom_components.device_manager.persistence"),
)
_persist.database_manager = database_manager_module  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.persistence.database_manager"] = database_manager_module

maintenance_repo_module = helpers.load_module(
    "persistence/repositories/maintenance_repository.py",
    package="custom_components.device_manager.persistence.repositories",
)
MaintenanceRepository = maintenance_repo_module.MaintenanceRepository  # type: ignore[attr-defined]

_COUNT_SQL = (
    "SELECT COUNT(*) AS n FROM dm_devices",
    "SELECT COUNT(*) AS n FROM dm_rooms",
    "SELECT COUNT(*) AS n FROM dm_floors",
    "SELECT COUNT(*) AS n FROM dm_buildings",
    "SELECT COUNT(*) AS n FROM dm_device_models",
    "SELECT COUNT(*) AS n FROM dm_device_firmwares",
    "SELECT COUNT(*) AS n FROM dm_device_functions",
)


async def _seed_chain(conn) -> None:
    """Insert one row in each parent table (all ids resolve to 1)."""
    await conn.execute("INSERT INTO dm_buildings (name, slug) VALUES ('B1', 'b1')")
    await conn.execute("INSERT INTO dm_floors (name, slug, building_id) VALUES ('F1', 'l0', 1)")
    await conn.execute("INSERT INTO dm_rooms (name, slug, floor_id) VALUES ('R1', 'r1', 1)")
    await conn.execute("INSERT INTO dm_device_models (name) VALUES ('ModelA')")
    await conn.execute("INSERT INTO dm_device_firmwares (name) VALUES ('Tasmota')")
    await conn.execute("INSERT INTO dm_device_functions (name) VALUES ('Switch')")


async def _close(db) -> None:
    """Close the shared connection so the temp DB file can be removed cleanly."""
    if db._connection is not None:
        await db._connection.close()
        db._connection = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wipe_all_data_empties_tables_and_resets_sequence():
    """wipe_all_data deletes every row and restarts autoincrement at 1."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db = DatabaseManager(Path(td) / "wipe.db")
            await db.initialize()
            try:
                conn = await db.get_connection()
                await _seed_chain(conn)
                await conn.execute(
                    "INSERT INTO dm_devices"
                    " (mac, room_id, model_id, firmware_id, function_id)"
                    " VALUES ('AA:01', 1, 1, 1, 1)"
                )
                await conn.commit()

                counts = await MaintenanceRepository(db).wipe_all_data()
                assert counts == {
                    "dm_devices": 1,
                    "dm_rooms": 1,
                    "dm_floors": 1,
                    "dm_buildings": 1,
                    "dm_device_models": 1,
                    "dm_device_firmwares": 1,
                    "dm_device_functions": 1,
                }

                for sql in _COUNT_SQL:
                    cursor = await conn.execute(sql)
                    assert (await cursor.fetchone())["n"] == 0

                # sqlite_sequence was cleared → next building id restarts at 1
                await conn.execute("INSERT INTO dm_buildings (name, slug) VALUES ('New', 'new')")
                await conn.commit()
                cursor = await conn.execute("SELECT id FROM dm_buildings")
                assert (await cursor.fetchone())["id"] == 1
            finally:
                await _close(db)

    asyncio.run(coro())


def test_clear_ip_cache_nulls_only_populated_ips():
    """clear_ip_cache resets non-NULL IPs and returns the updated count."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db = DatabaseManager(Path(td) / "ip.db")
            await db.initialize()
            try:
                conn = await db.get_connection()
                await _seed_chain(conn)
                await conn.executemany(
                    "INSERT INTO dm_devices"
                    " (mac, ip, room_id, model_id, firmware_id, function_id)"
                    " VALUES (?, ?, 1, 1, 1, 1)",
                    [
                        ("AA:01", "10.0.0.1"),
                        ("AA:02", "10.0.0.2"),
                        ("AA:03", None),
                    ],
                )
                await conn.commit()

                updated = await MaintenanceRepository(db).clear_ip_cache()
                assert updated == 2

                cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_devices WHERE ip IS NOT NULL")
                assert (await cursor.fetchone())["n"] == 0
            finally:
                await _close(db)

    asyncio.run(coro())


def test_checkpoint_preserves_data():
    """checkpoint() flushes the WAL without losing committed rows."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db = DatabaseManager(Path(td) / "ckpt.db")
            await db.initialize()
            try:
                conn = await db.get_connection()
                await conn.execute("INSERT INTO dm_buildings (name, slug) VALUES ('B1', 'b1')")
                await conn.commit()

                await db.checkpoint()

                cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_buildings")
                assert (await cursor.fetchone())["n"] == 1
            finally:
                await _close(db)

    asyncio.run(coro())


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "🧹 Maintenance Repository Tests"
TEST_SUITE = [
    ("wipe all data resets tables and sequence", test_wipe_all_data_empties_tables_and_resets_sequence),
    ("clear ip cache nulls populated ips", test_clear_ip_cache_nulls_only_populated_ips),
    ("checkpoint preserves committed data", test_checkpoint_preserves_data),
]
