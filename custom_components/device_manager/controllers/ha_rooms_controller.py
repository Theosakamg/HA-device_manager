"""API controller for HA area registry synchronization from Device Manager rooms.

Synchronizes Device Manager rooms to the Home Assistant native area registry.

For each DmRoom, an HA area is created or updated with:
- area.id   = slugified full path "{building} - {floor} - {room}" (stable,
              collision-free; derived via HA slugify when available, regex
              fallback otherwise).
- area.name = room.name only (unique rooms) or "{room} - {floor}" when the
              same room name appears in multiple floors, to satisfy HA's
              global display-name uniqueness constraint.
- floor_id  = HA floor ID previously synced for the parent DmFloor
              (looked up by name "{building} - {floor}"). Omitted when the
              HA floor has not been synced yet — run "Sync HA Floors" first.

The synchronization is atomic: if any area fails, all previously applied
changes are rolled back before returning an error.

Prerequisites:
  - HA area registry is available (HA 2023.x+)
  - HA floor registry is available (HA 2024.4+) for floor assignment;
    if a matching HA floor is not found, the area is still created without
    a floor assignment and a warning is logged.
"""

import logging
import re
from collections import Counter
from typing import Any

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect

_LOGGER = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Slugify a string using HA's own utility when available, regex fallback.

    HA's ``homeassistant.util.slugify`` handles non-ASCII characters (accents,
    etc.) via ``unicodedata.normalize`` before slugifying, which is required to
    match the area IDs that HA generates internally.  The regex fallback is
    kept for environments where HA utilities cannot be imported (e.g. tests).
    """
    try:
        from homeassistant.util import slugify  # type: ignore[import]
        return str(slugify(text, separator="_"))
    except Exception:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _compute_area_id(building_name: str, floor_name: str, room_name: str) -> str:
    """Compute the stable HA area ID from the full hierarchy path.

    Uses HA's own slugify (with regex fallback) so that the area ID matches
    what HA generates internally, including correct handling of non-ASCII
    characters (accents, etc.).  The ID is derived from the full path
    ``{building} - {floor} - {room}`` to be globally unique and stable across
    re-syncs, even after the display name has been updated.
    """
    full_name = f"{building_name} - {floor_name} - {room_name}"
    return _slugify(full_name)


async def _get_area_registry(hass: Any) -> Any | None:
    """Return the HA area registry, or None if unavailable."""
    try:
        from homeassistant.helpers import area_registry as ar  # type: ignore[import]
        return ar.async_get(hass)
    except Exception as err:
        _LOGGER.warning("[ha_rooms] area_registry unavailable: %s", err)
        return None


async def _get_floor_registry(hass: Any) -> Any | None:
    """Return the HA floor registry, or None if unavailable (HA < 2024.4)."""
    try:
        from homeassistant.helpers import floor_registry as fr  # type: ignore[import]
        return fr.async_get(hass)
    except Exception as err:
        _LOGGER.warning("[ha_rooms] floor_registry unavailable: %s", err)
        return None


class HaRoomsSyncAPIView(BaseView):
    """Synchronize Device Manager rooms to the HA native area registry.

    POST /api/device_manager/ha_rooms/sync

    For each room (building → floor → room), creates or updates the matching
    entry in the HA area registry, linking each area to its corresponding HA
    floor (previously synced by DM floor sync).  The operation is atomic:
    on failure, all changes that were already applied during the current
    request are rolled back.
    """

    url = "/api/device_manager/ha_rooms/sync"
    name = "api:device_manager:ha_rooms:sync"
    requires_auth = True

    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        repos = get_repos(request)
        hass = request.app["hass"]
        _LOGGER.info("=== HA Rooms synchronization started ===")

        area_reg = await _get_area_registry(hass)
        if area_reg is None:
            return self.json(
                {"error": "HA area registry is unavailable."},
                status_code=503,
            )

        floor_reg = await _get_floor_registry(hass)
        if floor_reg is None:
            _LOGGER.warning(
                "[ha_rooms] HA floor registry unavailable — rooms will be created "
                "without floor assignment (requires Home Assistant 2024.4+)."
            )

        try:
            buildings = await repos["building"].find_all()
            _LOGGER.info("[ha_rooms] %d building(s) found", len(buildings))

            # Pre-load hierarchy and detect duplicate room names so we can
            # disambiguate the HA display name when two rooms share the same name.
            building_data: list[tuple[Any, list[tuple[Any, list[Any]]]]] = []
            all_room_names: list[str] = []
            for building in buildings:
                floors = await repos["floor"].find_by_building(building.id)
                floor_data: list[tuple[Any, list[Any]]] = []
                for floor in floors:
                    rooms = await repos["room"].find_by_floor(floor.id)
                    floor_data.append((floor, rooms))
                    all_room_names.extend(r.name for r in rooms)
                building_data.append((building, floor_data))

            # Room names that appear more than once across the full dataset.
            # Use Counter for O(n) detection instead of O(n²) list.count().
            name_counts: Counter[str] = Counter(all_room_names)
            duplicate_names: set[str] = {
                name for name, count in name_counts.items() if count > 1
            }
            if duplicate_names:
                _LOGGER.info(
                    "[ha_rooms] %d duplicate room name(s) detected — "
                    "will use '<floor> - <room>' as display name: %s",
                    len(duplicate_names), sorted(duplicate_names),
                )

            synced: list[dict] = []
            # Track what was changed for rollback:
            # list of (action, ha_area_id, original_entry)
            applied: list[tuple[str, str, Any]] = []

            for building, floor_data in building_data:
                _LOGGER.info(
                    "[ha_rooms] building '%s': %d floor(s)", building.name, len(floor_data)
                )

                for floor, rooms in floor_data:
                    _LOGGER.info(
                        "[ha_rooms] floor '%s': %d room(s)", floor.name, len(rooms)
                    )

                    # Resolve the HA floor ID for this DM floor (if available)
                    ha_floor_id: str | None = None
                    if floor_reg is not None:
                        ha_floor_name = f"{building.name} - {floor.name}"
                        ha_floor_entry = floor_reg.async_get_floor_by_name(ha_floor_name)
                        if ha_floor_entry is not None:
                            ha_floor_id = ha_floor_entry.floor_id
                        else:
                            _LOGGER.warning(
                                "[ha_rooms] HA floor '%s' not found — room(s) in "
                                "floor '%s' will be created without floor assignment. "
                                "Run 'Sync HA Floors' first.",
                                ha_floor_name, floor.name,
                            )

                    for room in rooms:
                        # Unique full-path name → stable area ID
                        ha_area_full_name = f"{building.name} - {floor.name} - {room.name}"
                        ha_area_id_key = _compute_area_id(building.name, floor.name, room.name)
                        # Friendly name: just room.name when unique, else disambiguate
                        # with the floor name to satisfy HA's global uniqueness constraint.
                        ha_friendly_name = (
                            f"{room.name} - {floor.name}"
                            if room.name in duplicate_names
                            else room.name
                        )
                        ha_area_id: str | None = None

                        try:
                            existing = area_reg.async_get_area(ha_area_id_key)

                            if existing is not None:
                                ha_area_id = existing.id
                                # Only pass floor_id when resolved — passing None
                                # would clear an existing floor assignment.
                                update_kwargs: dict[str, Any] = {"name": ha_friendly_name}
                                if ha_floor_id is not None:
                                    update_kwargs["floor_id"] = ha_floor_id
                                area_reg.async_update(ha_area_id, **update_kwargs)
                                applied.append(("update", ha_area_id, existing))
                                _LOGGER.info(
                                    "[ha_rooms] ✓ updated '%s' (id=%s floor_id=%s)",
                                    ha_friendly_name, ha_area_id, ha_floor_id,
                                )
                            else:
                                # Create with unique full-path name to generate a
                                # stable, collision-free area ID, then immediately
                                # update the display name.
                                create_kwargs: dict[str, Any] = {}
                                if ha_floor_id is not None:
                                    create_kwargs["floor_id"] = ha_floor_id
                                entry = area_reg.async_create(
                                    ha_area_full_name,
                                    **create_kwargs,
                                )
                                ha_area_id = entry.id
                                # Track create before the name-update so rollback
                                # covers the area even if the update fails.
                                applied.append(("create", ha_area_id, None))
                                area_reg.async_update(ha_area_id, name=ha_friendly_name)
                                _LOGGER.info(
                                    "[ha_rooms] ✓ created '%s' (id=%s floor_id=%s)",
                                    ha_friendly_name, ha_area_id, ha_floor_id,
                                )

                            synced.append(
                                {
                                    "areaId": ha_area_id,
                                    "name": ha_friendly_name,
                                    "floorId": ha_floor_id,
                                    "roomSlug": room.slug,
                                    "floorSlug": floor.slug,
                                    "buildingName": building.name,
                                }
                            )

                        except Exception as err:
                            _LOGGER.error(
                                "[ha_rooms] failed to sync room '%s' (id=%s): %s",
                                room.name, ha_area_id, err,
                            )
                            self._rollback(area_reg, applied)
                            return self.json(
                                {
                                    "error": (
                                        f"Sync failed on room '{ha_area_full_name}': {err}. "
                                        "All changes rolled back."
                                    )
                                },
                                status_code=500,
                            )

        except Exception as err:
            _LOGGER.exception("[ha_rooms] unexpected error during sync", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)

        _LOGGER.info(
            "=== HA Rooms synchronization done: %d room(s) ===", len(synced)
        )
        return self.json({"rooms": synced, "total": len(synced)})

    def _rollback(
        self, area_reg: Any, applied: list[tuple[str, str, Any]]
    ) -> None:
        """Roll back all area registry changes applied in this request."""
        _LOGGER.warning(
            "[ha_rooms] rolling back %d change(s)", len(applied)
        )
        for action, ha_area_id, original in reversed(applied):
            try:
                if action == "create":
                    area_reg.async_delete(ha_area_id)
                    _LOGGER.debug(
                        "[ha_rooms] rollback: deleted '%s'", ha_area_id
                    )
                elif action == "update" and original is not None:
                    area_reg.async_update(
                        ha_area_id,
                        name=original.name,
                        floor_id=original.floor_id,
                    )
                    _LOGGER.debug(
                        "[ha_rooms] rollback: restored '%s'", ha_area_id
                    )
            except Exception as rb_err:
                _LOGGER.warning(
                    "[ha_rooms] rollback failed for '%s': %s",
                    ha_area_id, rb_err,
                )
