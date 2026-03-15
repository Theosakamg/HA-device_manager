"""API controller for HA floor registry synchronization.

Synchronizes Device Manager floors to the Home Assistant native floor registry
(available since HA 2024.4).

Each DmFloor becomes an HA floor with:
- name  = floor.name
- level = index of the floor in the list sorted by floor_slug ASC (0-based)

The synchronization is atomic: if any floor fails, all previously applied
changes are rolled back before returning an error.
"""

import logging
from typing import Any

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect

_LOGGER = logging.getLogger(__name__)


async def _get_floor_registry(hass: Any) -> Any | None:
    """Return the HA floor registry, or None if unavailable (HA < 2024.4)."""
    try:
        from homeassistant.helpers import floor_registry as fr  # type: ignore[import]
        return fr.async_get(hass)
    except Exception as err:
        _LOGGER.warning("[ha_floors] floor_registry unavailable: %s", err)
        return None


class HaFloorsSyncAPIView(BaseView):
    """Synchronize Device Manager floors to the HA native floor registry.

    POST /api/device_manager/ha_floors/sync

    For each floor (sorted by slug ASC), creates or updates the matching entry
    in the HA floor registry.  The operation is atomic: on failure, all changes
    that were already applied during the current request are rolled back.
    """

    url = "/api/device_manager/ha_floors/sync"
    name = "api:device_manager:ha_floors:sync"
    requires_auth = True

    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        repos = get_repos(request)
        hass = request.app["hass"]
        _LOGGER.info("=== HA Floors synchronization started ===")

        registry = await _get_floor_registry(hass)
        if registry is None:
            return self.json(
                {
                    "error": (
                        "HA floor registry is unavailable. "
                        "Requires Home Assistant 2024.4 or later."
                    )
                },
                status_code=503,
            )

        try:
            # Process floors building by building so that level indices are
            # reset for each building (0-based within each building).
            buildings = await repos["building"].find_all()
            _LOGGER.info("[ha_floors] %d building(s) found", len(buildings))

            synced: list[dict] = []
            # Track what was changed for rollback: list of (action, ha_floor_id, original_entry)
            applied: list[tuple[str, str, Any]] = []

            for building in buildings:
                floors = await repos["floor"].find_by_building(building.id)
                # Floors are already sorted by slug ASC by the repository.
                _LOGGER.info(
                    "[ha_floors] building '%s': %d floor(s)", building.name, len(floors)
                )

                for idx, floor in enumerate(floors):
                    level = idx  # 0-based index within this building
                    ha_floor_id: str | None = None
                    # Prefix with building name so HA floor names are globally unique.
                    ha_name = f"{building.name} - {floor.name}"

                    try:
                        existing = registry.async_get_floor_by_name(ha_name)

                        if existing is not None:
                            ha_floor_id = existing.floor_id
                            registry.async_update(
                                ha_floor_id,
                                name=ha_name,
                                level=level,
                            )
                            applied.append(("update", ha_floor_id, existing))
                            _LOGGER.info(
                                "[ha_floors] ✓ updated '%s' (id=%s level=%d)",
                                ha_name, ha_floor_id, level,
                            )
                        else:
                            entry = registry.async_create(
                                ha_name,
                                level=level,
                            )
                            ha_floor_id = entry.floor_id
                            applied.append(("create", ha_floor_id, None))
                            _LOGGER.info(
                                "[ha_floors] ✓ created '%s' (id=%s level=%d)",
                                ha_name, ha_floor_id, level,
                            )

                        synced.append(
                            {
                                "floorId": ha_floor_id,
                                "name": ha_name,
                                "level": level,
                                "slug": floor.slug,
                                "buildingName": building.name,
                            }
                        )

                    except Exception as err:
                        _LOGGER.error(
                            "[ha_floors] failed to sync '%s' (id=%s): %s",
                            ha_name, ha_floor_id, err,
                        )
                        self._rollback(registry, applied)
                        return self.json(
                            {
                                "error": (
                                    f"Sync failed on floor '{ha_name}': {err}. "
                                    "All changes rolled back."
                                )
                            },
                            status_code=500,
                        )

        except Exception as err:
            _LOGGER.exception("[ha_floors] unexpected error during sync", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)

        _LOGGER.info(
            "=== HA Floors synchronization done: %d floor(s) ===", len(synced)
        )
        return self.json({"floors": synced, "total": len(synced)})

    def _rollback(
        self, registry: Any, applied: list[tuple[str, str, Any]]
    ) -> None:
        """Roll back all floor registry changes applied in this request."""
        _LOGGER.warning(
            "[ha_floors] rolling back %d change(s)", len(applied)
        )
        for action, ha_floor_id, original in reversed(applied):
            try:
                if action == "create":
                    registry.async_delete(ha_floor_id)
                    _LOGGER.debug(
                        "[ha_floors] rollback: deleted '%s'", ha_floor_id
                    )
                elif action == "update" and original is not None:
                    registry.async_update(
                        ha_floor_id,
                        name=original.name,
                        level=original.level,
                    )
                    _LOGGER.debug(
                        "[ha_floors] rollback: restored '%s'", ha_floor_id
                    )
            except Exception as rb_err:
                _LOGGER.warning(
                    "[ha_floors] rollback failed for '%s': %s",
                    ha_floor_id, rb_err,
                )
