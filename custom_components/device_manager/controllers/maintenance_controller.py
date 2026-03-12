"""API controller for maintenance operations."""

import logging

from aiohttp import web

from .base import BaseView, rate_limit, csrf_protect
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Whitelist of tables that can be cleaned — protects against injection
# if the table list were ever made dynamic.
_CLEANABLE_TABLES = (
    "dm_devices",
    "dm_rooms",
    "dm_floors",
    "dm_buildings",
    "dm_device_models",
    "dm_device_firmwares",
    "dm_device_functions",
)


class MaintenanceCleanDBAPIView(BaseView):
    """API endpoint to wipe all data from the database."""

    url = "/api/device_manager/maintenance/clean-db"
    name = "api:device_manager:maintenance:clean_db"

    @rate_limit(requests=3, window=60)
    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        """Delete all data from every managed table.

        Expects JSON body with a 'confirmation' field set to
        'DELETE ALL DATA' to proceed.

        Returns:
            JSON with deletion counts per table.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}

        confirmation = body.get("confirmation", "")
        if confirmation != "DELETE ALL DATA":
            return self.json(
                {"error": "Invalid confirmation phrase"},
                status_code=400,
            )

        try:
            hass = request.app["hass"]
            db_mgr = hass.data[DOMAIN]["db"]
            conn = await db_mgr.get_connection()

            # Delete in order respecting FK constraints
            counts: dict[str, int] = {}
            for table in _CLEANABLE_TABLES:
                cursor = await conn.execute(
                    f"DELETE FROM {table}"  # noqa: S608 — table from whitelist
                )
                counts[table] = cursor.rowcount

            # Reset autoincrement counters (sqlite_sequence)
            for table in _CLEANABLE_TABLES:
                await conn.execute(
                    "DELETE FROM sqlite_sequence WHERE name = ?",
                    (table,),
                )

            await conn.commit()

            _LOGGER.warning(
                "Database cleaned: %s", counts
            )
            return self.json({
                "success": True,
                "deleted": counts,
            })
        except Exception as err:
            _LOGGER.exception("Database clean failed", exc_info=err)
            return self.json(
                {"error": "Database clean failed. Check server logs."},
                status_code=500,
            )


class MaintenanceClearIPCacheAPIView(BaseView):
    """API endpoint to reset all device IP addresses to NULL."""

    url = "/api/device_manager/maintenance/clear-ip-cache"
    name = "api:device_manager:maintenance:clear_ip_cache"

    @rate_limit(requests=10, window=60)
    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        """Set ip = NULL for every row in dm_devices.

        Returns:
            JSON with the number of devices updated.
        """
        try:
            hass = request.app["hass"]
            db_mgr = hass.data[DOMAIN]["db"]
            conn = await db_mgr.get_connection()

            cursor = await conn.execute(
                "UPDATE dm_devices SET ip = NULL WHERE ip IS NOT NULL"
            )
            updated = cursor.rowcount
            await conn.commit()

            _LOGGER.info("IP cache cleared: %d devices updated", updated)
            return self.json({"success": True, "updated": updated})
        except Exception as err:
            _LOGGER.exception("Clear IP cache failed", exc_info=err)
            return self.json(
                {"error": "Clear IP cache failed. Check server logs."},
                status_code=500,
            )
