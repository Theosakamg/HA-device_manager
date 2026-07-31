"""Repository for dashboard statistics aggregations.

This repository owns the read-only aggregation SQL for the dashboard. It
spans several tables (buildings, floors, rooms, devices, models, firmwares,
functions), so it does not extend the generic single-table
:class:`BaseRepository`. It returns plain dicts/lists that the API layer maps
into the :class:`StatsDto` boundary object — keeping every SQL statement inside
the sealed persistence layer.
"""

import logging
from typing import Any

from ..database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class StatsRepository:
    """Compute dashboard statistics with server-side SQL aggregation."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize with a shared DatabaseManager.

        Args:
            db_manager: The database manager providing the shared connection.
        """
        self.db = db_manager

    async def _count(self, sql: str) -> int:
        """Run a single ``SELECT COUNT(*) AS n`` query and return the count.

        The ``sql`` argument is always a static literal supplied by this class
        (never user input), so there is no injection surface.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(sql)
        row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    async def count_hierarchy(self) -> dict[str, int]:
        """Return the row counts for buildings, floors, rooms and devices."""
        return {
            "buildings": await self._count("SELECT COUNT(*) AS n FROM dm_buildings"),
            "floors": await self._count("SELECT COUNT(*) AS n FROM dm_floors"),
            "rooms": await self._count("SELECT COUNT(*) AS n FROM dm_rooms"),
            "devices": await self._count("SELECT COUNT(*) AS n FROM dm_devices"),
        }

    async def count_settings(self) -> dict[str, int]:
        """Return the row counts for models, firmwares and functions."""
        return {
            "models": await self._count("SELECT COUNT(*) AS n FROM dm_device_models"),
            "firmwares": await self._count("SELECT COUNT(*) AS n FROM dm_device_firmwares"),
            "functions": await self._count("SELECT COUNT(*) AS n FROM dm_device_functions"),
        }

    async def devices_by_firmware(self) -> list[dict[str, Any]]:
        """Return device counts grouped by firmware name.

        Uses a LEFT JOIN so devices without a firmware are reported under
        ``'Unknown'`` instead of being dropped.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute("""
            SELECT COALESCE(df.name, 'Unknown') AS name,
                   COUNT(*) AS cnt
            FROM dm_devices d
            LEFT JOIN dm_device_firmwares df ON d.firmware_id = df.id
            GROUP BY df.id
            ORDER BY cnt DESC
            """)
        return [{"name": row["name"], "count": int(row["cnt"])} for row in await cursor.fetchall()]

    async def devices_by_model(self) -> list[dict[str, Any]]:
        """Return device counts grouped by model name (LEFT JOIN, NULL-safe)."""
        conn = await self.db.get_connection()
        cursor = await conn.execute("""
            SELECT COALESCE(dm.name, 'Unknown') AS name,
                   COUNT(*) AS cnt
            FROM dm_devices d
            LEFT JOIN dm_device_models dm ON d.model_id = dm.id
            GROUP BY dm.id
            ORDER BY cnt DESC
            """)
        return [{"name": row["name"], "count": int(row["cnt"])} for row in await cursor.fetchall()]

    async def deployment_totals(self) -> dict[str, int]:
        """Return global deployment counters (total / success / fail).

        ``SUM(CASE ...)`` yields ``NULL`` when no device has a deploy status,
        so the results are coalesced to ``0`` to keep the endpoint robust on a
        freshly initialized database.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN last_deploy_status = 'done' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN last_deploy_status = 'fail' THEN 1 ELSE 0 END) AS fail
            FROM dm_devices
            WHERE last_deploy_status IS NOT NULL
            """)
        row = await cursor.fetchone()
        if row is None:
            return {"total": 0, "success": 0, "fail": 0}
        return {
            "total": int(row["total"] or 0),
            "success": int(row["success"] or 0),
            "fail": int(row["fail"] or 0),
        }

    async def deployment_by_firmware(self) -> list[dict[str, Any]]:
        """Return deployment counters grouped by firmware name."""
        conn = await self.db.get_connection()
        cursor = await conn.execute("""
            SELECT
                COALESCE(df.name, 'Unknown') AS name,
                COUNT(*) AS total,
                SUM(CASE WHEN d.last_deploy_status = 'done' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN d.last_deploy_status = 'fail' THEN 1 ELSE 0 END) AS fail
            FROM dm_devices d
            LEFT JOIN dm_device_firmwares df ON d.firmware_id = df.id
            WHERE d.last_deploy_status IS NOT NULL
            GROUP BY df.id
            ORDER BY total DESC
            """)
        return [
            {
                "name": row["name"],
                "total": int(row["total"] or 0),
                "success": int(row["success"] or 0),
                "fail": int(row["fail"] or 0),
            }
            for row in await cursor.fetchall()
        ]

    async def deployment_by_model(self) -> list[dict[str, Any]]:
        """Return deployment counters grouped by model name.

        Ordered by ascending success rate (worst first) then by volume, so the
        dashboard can surface the least reliable models at the top.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute("""
            SELECT
                COALESCE(dm.name, 'Unknown') AS name,
                COUNT(*) AS total,
                SUM(CASE WHEN d.last_deploy_status = 'done' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN d.last_deploy_status = 'fail' THEN 1 ELSE 0 END) AS fail,
                CAST(SUM(CASE WHEN d.last_deploy_status = 'done' THEN 1 ELSE 0 END) AS FLOAT)
                    / COUNT(*) AS success_rate
            FROM dm_devices d
            LEFT JOIN dm_device_models dm ON d.model_id = dm.id
            WHERE d.last_deploy_status IS NOT NULL
            GROUP BY dm.id
            ORDER BY success_rate ASC, total DESC
            """)
        return [
            {
                "name": row["name"],
                "total": int(row["total"] or 0),
                "success": int(row["success"] or 0),
                "fail": int(row["fail"] or 0),
            }
            for row in await cursor.fetchall()
        ]
