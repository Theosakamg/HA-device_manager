"""API controllers for SQLite database backup (export) and restore (import)."""

import asyncio
import logging
import shutil
from datetime import datetime

from aiohttp import web
from aiohttp.web_request import FileField

from .base import BaseView, rate_limit, csrf_protect
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Maximum database upload size: 200 MB
_MAX_DB_SIZE = 200 * 1024 * 1024

# SQLite file magic header (first 16 bytes of every valid SQLite3 file)
_SQLITE_MAGIC = b"SQLite format 3\x00"


class SQLiteExportAPIView(BaseView):
    """Export the live SQLite database as a binary file download.

    Before reading the file the WAL is fully checkpointed so that the
    downloaded ``.db`` contains the latest committed state.
    """

    url = "/api/device_manager/export/db"
    name = "api:device_manager:export:db"
    requires_auth = True

    @rate_limit(requests=10, window=60)
    async def get(self, request: web.Request) -> web.Response:
        """Download the SQLite database file.

        Returns:
            Binary response with ``Content-Disposition: attachment``.
        """
        try:
            hass = request.app["hass"]
            db_manager = hass.data[DOMAIN]["db"]
            db_path = db_manager.db_path

            # Flush all pending WAL frames to the main file so the snapshot is
            # complete and consistent.
            conn = await db_manager.get_connection()
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            # Read the database file outside the event loop to avoid blocking.
            loop = asyncio.get_event_loop()
            data: bytes = await loop.run_in_executor(None, db_path.read_bytes)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"device_manager_{timestamp}.db"

            _LOGGER.info(
                "SQLite DB exported: %d bytes → %s", len(data), filename
            )
            return web.Response(
                body=data,
                content_type="application/octet-stream",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except Exception as err:
            _LOGGER.exception("SQLite export failed", exc_info=err)
            return self.json(
                {"error": "Database export failed. Check server logs."},
                status_code=500,
            )


class SQLiteImportAPIView(BaseView):
    """Replace the live SQLite database with an uploaded ``.db`` file.

    The current database is backed up before replacement so that the
    operation can be undone manually if needed.
    """

    url = "/api/device_manager/import/db"
    name = "api:device_manager:import:db"
    requires_auth = True

    @rate_limit(requests=3, window=3600)
    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        """Replace the database with the uploaded file.

        Expects ``multipart/form-data`` with a ``file`` field containing
        a valid SQLite3 database.

        Returns:
            JSON ``{"success": true, "backup": "<path>"}`` on success.
        """
        try:
            hass = request.app["hass"]
            db_manager = hass.data[DOMAIN]["db"]
            db_path = db_manager.db_path

            post = await request.post()
            file_field = post.get("file")

            if not file_field or not isinstance(file_field, FileField):
                return self.json({"error": "No file provided"}, status_code=400)

            raw = file_field.file.read(_MAX_DB_SIZE + 1)
            if len(raw) > _MAX_DB_SIZE:
                return self.json(
                    {"error": "File too large (max 200 MB)"},
                    status_code=413,
                )

            # Validate SQLite magic header to reject obviously wrong files.
            if len(raw) < 16 or raw[:16] != _SQLITE_MAGIC:
                return self.json(
                    {"error": "Invalid file: not a SQLite3 database"},
                    status_code=400,
                )

            # Create a timestamped backup of the current database before
            # replacing it so the user can recover if something goes wrong.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.with_suffix(f".{timestamp}.bak")

            loop = asyncio.get_event_loop()

            def _replace_db() -> str:
                if db_path.exists():
                    shutil.copy2(db_path, backup_path)
                db_path.write_bytes(raw)
                # Remove stale WAL / SHM sidecar files so SQLite opens cleanly.
                for suffix in ("-wal", "-shm"):
                    sidecar = db_path.parent / (db_path.name + suffix)
                    if sidecar.exists():
                        sidecar.unlink()
                return str(backup_path)

            # Close the shared connection before touching the file.
            await db_manager.close()

            backup_str = await loop.run_in_executor(None, _replace_db)

            # Re-open the connection and re-apply any pending migrations so
            # the manager is ready for the next request.
            await db_manager.initialize()

            _LOGGER.warning(
                "SQLite DB replaced (backup: %s, new size: %d bytes)",
                backup_str,
                len(raw),
            )
            return self.json({"success": True, "backup": backup_str})

        except Exception as err:
            _LOGGER.exception("SQLite import failed", exc_info=err)
            # Best-effort: try to re-initialize the connection if it was closed.
            try:
                hass = request.app["hass"]
                await hass.data[DOMAIN]["db"].initialize()
            except Exception:
                pass
            return self.json(
                {"error": "Database import failed. Check server logs."},
                status_code=500,
            )
