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
            "byModel":    [{"name": "Shelly 1",  "count": 15}, ...]
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

            return self.json({
                "buildings": total_buildings,
                "floors": total_floors,
                "rooms": total_rooms,
                "devices": total_devices,
                "byFirmware": by_firmware,
                "byModel": by_model,
            })

        except Exception as err:
            _LOGGER.exception("Failed to compute stats", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)
