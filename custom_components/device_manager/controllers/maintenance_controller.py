"""API controller for maintenance operations."""

import io
import logging
import zipfile

from aiohttp import web

from .base import BaseView, rate_limit, csrf_protect, get_repos, emit_activity_log
from ..const import DOMAIN, SETTING_MQTT_PREFIX, SETTING_BUS_USERNAME, SETTING_BUS_PASSWORD

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
            await emit_activity_log(
                request,
                event_type="action",
                entity_type="maintenance",
                message="Database cleaned (DELETE ALL DATA confirmed)",
                result=str(counts),
                severity="warning",
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
            await emit_activity_log(
                request,
                event_type="action",
                entity_type="maintenance",
                message=f"IP cache cleared: {updated} device(s) updated",
            )
            return self.json({"success": True, "updated": updated})
        except Exception as err:
            _LOGGER.exception("Clear IP cache failed", exc_info=err)
            return self.json(
                {"error": "Clear IP cache failed. Check server logs."},
                status_code=500,
            )


class MaintenanceMosquittoConfigAPIView(BaseView):
    """API endpoint to generate Mosquitto MQTT broker configuration files.

    Returns a ZIP archive containing:
    - ``passwd``:        Cleartext credentials (one ``user:password`` per line).
    - ``acl``:           ACL rules (per-room restrictions + admin full access).
    - ``mosquitto.conf``: Minimal broker config referencing the above files.

    Only rooms that have **both** ``login`` and ``password`` set receive a
    dedicated ACL entry.  The admin user (read from the ``bus_username``
    setting) always gets full ``readwrite #`` access.
    """

    url = "/api/device_manager/maintenance/generate-mosquitto-config"
    name = "api:device_manager:maintenance:generate_mosquitto_config"

    @rate_limit(requests=20, window=60)
    async def get(self, request: web.Request) -> web.Response:
        """Generate and download the Mosquitto configuration ZIP archive.

        Returns:
            Binary ZIP response with ``Content-Disposition: attachment``.
        """
        try:
            repos = get_repos(request)
            settings = await repos["settings"].get_all()

            mqtt_prefix = settings.get(SETTING_MQTT_PREFIX, "home").strip("/")
            admin_user = settings.get(SETTING_BUS_USERNAME, "admin")
            admin_pass = settings.get(SETTING_BUS_PASSWORD, "")

            # Collect credentials and ACL entries across the full hierarchy
            passwd_lines: list[str] = []
            acl_blocks: list[str] = []

            buildings = await repos["building"].find_all()
            for building in buildings:
                floors = await repos["floor"].find_by_building(building.id)
                for floor in floors:
                    rooms = await repos["room"].find_by_floor(floor.id)
                    for room in rooms:
                        if not (room.login and room.password):
                            continue
                        # Passwords may be None when decryption fails; skip
                        if room.password is None:
                            _LOGGER.warning(
                                "Room %s has an encrypted password that could not"
                                " be decrypted — skipping from Mosquitto config",
                                room.name,
                            )
                            continue

                        topic = (
                            f"{mqtt_prefix}/"
                            f"{building.slug}/{floor.slug}/{room.slug}"
                        )
                        passwd_lines.append(f"{room.login}:{room.password}")
                        acl_blocks.append(
                            f"user {room.login}\ntopic readwrite {topic}/#\n"
                        )

            # Admin entry always present
            if admin_user:
                passwd_lines.append(f"{admin_user}:{admin_pass}")
                acl_blocks.append(f"user {admin_user}\ntopic readwrite #\n")

            passwd_content = "\n".join(passwd_lines) + "\n" if passwd_lines else ""
            acl_content = "\n".join(acl_blocks)
            mosquitto_conf = (
                "# Generated by Device Manager\n"
                "listener 1883\n"
                "allow_anonymous false\n"
                "password_file /mosquitto/config/passwd\n"
                "acl_file /mosquitto/config/acl\n"
            )

            # Build ZIP in memory
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("passwd", passwd_content)
                zf.writestr("acl", acl_content)
                zf.writestr("mosquitto.conf", mosquitto_conf)
            zip_bytes = buf.getvalue()

            _LOGGER.info(
                "Mosquitto config generated: %d room credentials",
                len(passwd_lines) - (1 if admin_user else 0),
            )
            await emit_activity_log(
                request,
                event_type="action",
                entity_type="maintenance",
                message="Mosquitto configuration files generated",
            )

            return web.Response(
                body=zip_bytes,
                status=200,
                headers={
                    "Content-Type": "application/zip",
                    "Content-Disposition": 'attachment; filename="mosquitto-config.zip"',
                    "X-Content-Type-Options": "nosniff",
                },
            )

        except Exception as err:
            _LOGGER.exception("Mosquitto config generation failed", exc_info=err)
            return self.json(
                {"error": "Mosquitto config generation failed. Check server logs."},
                status_code=500,
            )
