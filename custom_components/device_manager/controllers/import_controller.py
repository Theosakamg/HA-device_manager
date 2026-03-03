"""API controller for CSV import."""

import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from ..const import DOMAIN
from .base import get_repos
from ..services.csv_import_service import CSVImportService

_LOGGER = logging.getLogger(__name__)

# Maximum CSV upload size: 10 MB
_MAX_CSV_SIZE = 10 * 1024 * 1024


class CSVImportAPIView(HomeAssistantView):
    """API endpoint for CSV device import."""

    url = "/api/device_manager/import"
    name = "api:device_manager:import"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Import devices from an uploaded CSV file.

        Expects multipart/form-data with a 'file' field containing
        the CSV data.

        Returns:
            JSON with import results (created/updated counts, errors).
        """
        try:
            repos = get_repos(request)
            post = await request.post()
            file_field = post.get("file")

            if not file_field:
                return self.json({"error": "No file provided"}, status_code=400)

            raw = file_field.file.read(_MAX_CSV_SIZE + 1)
            if len(raw) > _MAX_CSV_SIZE:
                return self.json(
                    {"error": "File too large (max 10 MB)"},
                    status_code=413,
                )
            try:
                text = raw.decode("utf-8")
            except Exception:
                text = raw.decode("latin-1", errors="replace")

            # Load user settings for IP prefix, default home name, etc.
            hass = request.app["hass"]
            settings_repo = hass.data[DOMAIN]["repos"].get("settings")
            settings = await settings_repo.get_all() if settings_repo else {}

            service = CSVImportService(repos, settings=settings)
            result = await service.import_csv(text)

            return self.json(result)
        except Exception as err:
            _LOGGER.exception("CSV import failed")
            return self.json(
                {"error": "Import failed. Check server logs."},
                status_code=500,
            )
