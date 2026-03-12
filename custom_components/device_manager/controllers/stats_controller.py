"""API controller for dashboard statistics.

All aggregations are computed directly in SQLite (GROUP BY queries) so that
only a handful of numbers are transported to the UI instead of the full
device list.
"""

import logging

from aiohttp import web

from .base import BaseView, get_repos

_LOGGER = logging.getLogger(__name__)


class StatsAPIView(BaseView):
    """Return pre-computed statistics for the dashboard.

    Response shape::

        {
            "buildings": 2,
            "floors": 6,
            "rooms": 18,
            "devices": 42,
            "byFirmware": [{"name": "Tasmota", "count": 30}, ...],
            "byModel":    [{"name": "Shelly 1",  "count": 15}, ...],
            "settingsCounts": {
                "models": 5,
                "firmwares": 3,
                "functions": 8
            }
        }

    All counts are computed with SQL aggregation on the server side;
    the client never receives the full device list.
    """

    url = "/api/device_manager/stats"
    name = "api:device_manager:stats"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Compute and return dashboard statistics."""
        try:
            repos = get_repos(request)
            db = repos["device"].db
            conn = await db.get_connection()

            # ── Hierarchy counts (three cheap COUNT(*) queries) ──────────────
            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_buildings")
            row = await cursor.fetchone()
            total_buildings = int(row["n"]) if row else 0

            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_floors")
            row = await cursor.fetchone()
            total_floors = int(row["n"]) if row else 0

            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_rooms")
            row = await cursor.fetchone()
            total_rooms = int(row["n"]) if row else 0

            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_devices")
            row = await cursor.fetchone()
            total_devices = int(row["n"]) if row else 0

            # ── Devices grouped by firmware (LEFT JOIN to keep NULL) ─────────
            cursor = await conn.execute(
                """
                SELECT COALESCE(df.name, 'Unknown') AS name,
                       COUNT(*) AS cnt
                FROM dm_devices d
                LEFT JOIN dm_device_firmwares df ON d.firmware_id = df.id
                GROUP BY df.id
                ORDER BY cnt DESC
                """
            )
            by_firmware = [
                {"name": row["name"], "count": int(row["cnt"])}
                for row in await cursor.fetchall()
            ]

            # ── Devices grouped by model ─────────────────────────────────────
            cursor = await conn.execute(
                """
                SELECT COALESCE(dm.name, 'Unknown') AS name,
                       COUNT(*) AS cnt
                FROM dm_devices d
                LEFT JOIN dm_device_models dm ON d.model_id = dm.id
                GROUP BY dm.id
                ORDER BY cnt DESC
                """
            )
            by_model = [
                {"name": row["name"], "count": int(row["cnt"])}
                for row in await cursor.fetchall()
            ]

            # ── Settings counts (models, firmwares, functions) ───────────────
            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_device_models")
            row = await cursor.fetchone()
            models_count = int(row["n"]) if row else 0

            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_device_firmwares")
            row = await cursor.fetchone()
            firmwares_count = int(row["n"]) if row else 0

            cursor = await conn.execute("SELECT COUNT(*) AS n FROM dm_device_functions")
            row = await cursor.fetchone()
            functions_count = int(row["n"]) if row else 0

            # ── Deployment statistics (global) ────────────────────────────────
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN last_deploy_status = 'done' THEN 1 ELSE 0 END) AS success,
                    SUM(CASE WHEN last_deploy_status = 'fail' THEN 1 ELSE 0 END) AS fail
                FROM dm_devices
                WHERE last_deploy_status IS NOT NULL
                """
            )
            row = await cursor.fetchone()
            deploy_stats = {
                "total": int(row["total"]) if row else 0,
                "success": int(row["success"]) if row else 0,
                "fail": int(row["fail"]) if row else 0,
            }

            # ── Deployment statistics by firmware ─────────────────────────────
            cursor = await conn.execute(
                """
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
                """
            )
            deploy_by_firmware = [
                {
                    "name": row["name"],
                    "total": int(row["total"]),
                    "success": int(row["success"]),
                    "fail": int(row["fail"]),
                }
                for row in await cursor.fetchall()
            ]

            # ── Deployment statistics by model ────────────────────────────────
            cursor = await conn.execute(
                """
                SELECT
                    COALESCE(dm.name, 'Unknown') AS name,
                    COUNT(*) AS total,
                    SUM(CASE WHEN d.last_deploy_status = 'done' THEN 1 ELSE 0 END) AS success,
                    SUM(CASE WHEN d.last_deploy_status = 'fail' THEN 1 ELSE 0 END) AS fail,
                    CAST(SUM(CASE WHEN d.last_deploy_status = 'done' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS success_rate
                FROM dm_devices d
                LEFT JOIN dm_device_models dm ON d.model_id = dm.id
                WHERE d.last_deploy_status IS NOT NULL
                GROUP BY dm.id
                ORDER BY success_rate ASC, total DESC
                """
            )
            deploy_by_model = [
                {
                    "name": row["name"],
                    "total": int(row["total"]),
                    "success": int(row["success"]),
                    "fail": int(row["fail"]),
                }
                for row in await cursor.fetchall()
            ]

            return self.json({
                "buildings": total_buildings,
                "floors": total_floors,
                "rooms": total_rooms,
                "devices": total_devices,
                "byFirmware": by_firmware,
                "byModel": by_model,
                "settingsCounts": {
                    "models": models_count,
                    "firmwares": firmwares_count,
                    "functions": functions_count,
                },
                "deployment": deploy_stats,
                "deploymentByFirmware": deploy_by_firmware,
                "deploymentByModel": deploy_by_model,
            })

        except Exception as err:
            _LOGGER.exception("Failed to compute stats", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)
