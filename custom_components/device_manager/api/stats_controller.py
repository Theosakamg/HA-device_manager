"""API controller for dashboard statistics.

All aggregations are computed server-side by :class:`StatsRepository` (the
persistence layer owns the SQL). The controller only orchestrates the repo
calls and assembles the :class:`StatsDto`, so a handful of numbers are
transported to the UI instead of the full device list.
"""

import logging

from aiohttp import web

from .base import BaseView, get_repos
from ..dto import StatsDto

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
            stats = get_repos(request)["stats"]

            hierarchy = await stats.count_hierarchy()
            settings = await stats.count_settings()

            return self.json(
                StatsDto(
                    buildings=hierarchy["buildings"],
                    floors=hierarchy["floors"],
                    rooms=hierarchy["rooms"],
                    devices=hierarchy["devices"],
                    by_firmware=await stats.devices_by_firmware(),
                    by_model=await stats.devices_by_model(),
                    models_count=settings["models"],
                    firmwares_count=settings["firmwares"],
                    functions_count=settings["functions"],
                    deployment=await stats.deployment_totals(),
                    deployment_by_firmware=await stats.deployment_by_firmware(),
                    deployment_by_model=await stats.deployment_by_model(),
                ).to_api_dict()
            )

        except Exception as err:
            _LOGGER.exception("Failed to compute stats", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)
