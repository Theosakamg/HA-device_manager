"""Tests for :class:`StatsRepository` aggregation queries.

Loads the repository and DatabaseManager directly by file path (no Home
Assistant install required) and seeds a small, FK-consistent dataset so the
GROUP BY / deployment aggregations can be asserted deterministically.
"""

import asyncio
import sys
import tempfile
import types
from pathlib import Path

import helpers  # provided via sys.path by run_tests.py

# ---------------------------------------------------------------------------
# Bootstrap: load DatabaseManager + StatsRepository without importing HA
# ---------------------------------------------------------------------------

database_manager_module = helpers.load_module("persistence/database_manager.py")
DatabaseManager = database_manager_module.DatabaseManager  # type: ignore[attr-defined]

_cm = sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
_dm = sys.modules.setdefault(
    "custom_components.device_manager",
    types.ModuleType("custom_components.device_manager"),
)
_persist = sys.modules.setdefault(
    "custom_components.device_manager.persistence",
    types.ModuleType("custom_components.device_manager.persistence"),
)
_persist.database_manager = database_manager_module  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.persistence.database_manager"] = database_manager_module

stats_repo_module = helpers.load_module(
    "persistence/repositories/stats_repository.py",
    package="custom_components.device_manager.persistence.repositories",
)
StatsRepository = stats_repo_module.StatsRepository  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# firmware ids: Tasmota=1, WLED=2 | model ids: ModelA=1, ModelB=2
# device layout (mac, room, model, firmware, function, deploy_status):
_DEVICES = [
    ("AA:01", 1, 1, 1, 1, "done"),
    ("AA:02", 1, 1, 1, 1, "fail"),
    ("AA:03", 1, 2, 1, 1, "done"),
    ("AA:04", 1, 2, 2, 1, None),  # never deployed → excluded from deploy stats
    ("AA:05", 1, 2, 2, 1, "done"),
]


async def _seed(db) -> None:
    """Insert a small FK-consistent dataset for aggregation assertions."""
    conn = await db.get_connection()
    await conn.execute("INSERT INTO dm_buildings (name, slug) VALUES ('B1', 'b1')")
    await conn.execute("INSERT INTO dm_floors (name, slug, building_id) VALUES ('F1', 'l0', 1)")
    await conn.executemany(
        "INSERT INTO dm_rooms (name, slug, floor_id) VALUES (?, ?, ?)",
        [("R1", "r1", 1), ("R2", "r2", 1)],
    )
    await conn.executemany(
        "INSERT INTO dm_device_models (name) VALUES (?)",
        [("ModelA",), ("ModelB",)],
    )
    await conn.executemany(
        "INSERT INTO dm_device_firmwares (name) VALUES (?)",
        [("Tasmota",), ("WLED",)],
    )
    await conn.execute("INSERT INTO dm_device_functions (name) VALUES ('Switch')")
    await conn.executemany(
        "INSERT INTO dm_devices"
        " (mac, room_id, model_id, firmware_id, function_id, last_deploy_status)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        _DEVICES,
    )
    await conn.commit()


async def _close(db) -> None:
    """Close the shared connection so the temp DB file can be removed cleanly."""
    if db._connection is not None:
        await db._connection.close()
        db._connection = None


async def _seeded(td: str):
    """Return a (db, repo) pair backed by a freshly seeded temp database."""
    db = DatabaseManager(Path(td) / "stats.db")
    await db.initialize()
    await _seed(db)
    return db, StatsRepository(db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_count_hierarchy_and_settings():
    """Hierarchy and settings counters reflect the seeded rows."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db, repo = await _seeded(td)
            try:
                assert await repo.count_hierarchy() == {
                    "buildings": 1,
                    "floors": 1,
                    "rooms": 2,
                    "devices": 5,
                }
                assert await repo.count_settings() == {
                    "models": 2,
                    "firmwares": 2,
                    "functions": 1,
                }
            finally:
                await _close(db)

    asyncio.run(coro())


def test_devices_grouping():
    """Devices are grouped by firmware and model, ordered by count DESC."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db, repo = await _seeded(td)
            try:
                assert await repo.devices_by_firmware() == [
                    {"name": "Tasmota", "count": 3},
                    {"name": "WLED", "count": 2},
                ]
                assert await repo.devices_by_model() == [
                    {"name": "ModelB", "count": 3},
                    {"name": "ModelA", "count": 2},
                ]
            finally:
                await _close(db)

    asyncio.run(coro())


def test_deployment_stats():
    """Deployment counters exclude never-deployed devices and group correctly."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db, repo = await _seeded(td)
            try:
                assert await repo.deployment_totals() == {
                    "total": 4,
                    "success": 3,
                    "fail": 1,
                }
                assert await repo.deployment_by_firmware() == [
                    {"name": "Tasmota", "total": 3, "success": 2, "fail": 1},
                    {"name": "WLED", "total": 1, "success": 1, "fail": 0},
                ]
                assert await repo.deployment_by_model() == [
                    {"name": "ModelA", "total": 2, "success": 1, "fail": 1},
                    {"name": "ModelB", "total": 2, "success": 2, "fail": 0},
                ]
            finally:
                await _close(db)

    asyncio.run(coro())


def test_deployment_totals_empty_db_is_zeroed():
    """On a fresh DB the SUM(CASE ...) NULLs are coalesced to 0 (no crash)."""

    async def coro():
        with tempfile.TemporaryDirectory() as td:
            db = DatabaseManager(Path(td) / "empty.db")
            await db.initialize()
            try:
                repo = StatsRepository(db)
                assert await repo.deployment_totals() == {
                    "total": 0,
                    "success": 0,
                    "fail": 0,
                }
                assert await repo.devices_by_firmware() == []
            finally:
                await _close(db)

    asyncio.run(coro())


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "📊 Stats Repository Tests"
TEST_SUITE = [
    ("hierarchy and settings counts", test_count_hierarchy_and_settings),
    ("devices grouped by firmware/model", test_devices_grouping),
    ("deployment statistics", test_deployment_stats),
    ("deployment totals on empty db", test_deployment_totals_empty_db_is_zeroed),
]
