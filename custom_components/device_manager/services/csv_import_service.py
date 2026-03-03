"""CSV import service for Device Manager."""

import csv
import io
import logging
import re
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


def _sanitize_slug(value: str) -> str:
    """Convert a string to a URL-safe slug.

    Args:
        value: The string to slugify.

    Returns:
        A lowercase slug with only alphanumeric chars, dashes,
        underscores and dots.
    """
    if not value:
        return ""
    s = str(value).strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-_.]", "", s)
    return s


def _titleize(value: str) -> str:
    """Convert a slug or raw value to Title Case.

    Args:
        value: The string to titleize.

    Returns:
        A title-cased string with underscores/dashes replaced by spaces.
    """
    if not value:
        return ""
    v = str(value).strip()
    if not v:
        return ""
    v = v.replace("_", " ").replace("-", " ")
    return " ".join(p.capitalize() for p in v.split())


# CSV header to semantic field mapping
HEADER_MAP = {
    "Check": None,
    "MAC": "mac",
    "State": "state",
    "Level": "level",
    "Room FR": "room_fr",
    "Position FR": "position_fr",
    "Function": "function",
    "Room SLUG": "room_slug",
    "Position SLUG": "position_slug",
    "Firmware": "firmware",
    "Model": "model",
    "IP": "ip",
    "Interlock": "interlock",
    "Mode": "mode",
    "Target": "target",
    "HA_device_class": "ha_device_class",
    "Extra": "extra",
    "Link": None,         # computed, not imported
    "MQTT": None,         # computed, not imported
    "Hostname": None,     # computed, not imported
    "DNS": None,          # computed, not imported
    "count_topic": None,  # computed, not imported
    "Notes": None,        # not in new schema
    "Bat": None,          # not in new schema
}


class CSVImportService:
    """Service to import devices from a CSV file into the relational schema.

    Automatically creates reference entities (Building, Floor, Room, Model,
    Firmware, Function) if they do not already exist, then creates Device
    records with proper foreign keys.
    """

    def __init__(
        self,
        repositories: dict,
        settings: dict[str, str] | None = None,
    ) -> None:
        """Initialize the CSV import service.

        Args:
            repositories: Dict of repository instances keyed by name.
            settings: Optional dict of application settings.  Recognised
                keys: ``ip_prefix``, ``default_building_name``.
        """
        self.repos = repositories
        self._settings = settings or {}

    async def import_csv(self, csv_text: str) -> dict[str, Any]:
        """Import devices from CSV text.

        Args:
            csv_text: The raw CSV content as string.

        Returns:
            A dict with 'created' count and 'logs' list of per-row results.
        """
        reader = csv.DictReader(io.StringIO(csv_text))
        logs: list[dict[str, Any]] = []
        errors: list[str] = []
        created = 0
        total = 0
        max_rows = 10_000

        # Caches to avoid re-creating entities
        building_cache: dict[str, int] = {}
        floor_cache: dict[str, int] = {}
        room_cache: dict[str, int] = {}
        model_cache: dict[str, int] = {}
        firmware_cache: dict[str, int] = {}
        function_cache: dict[str, int] = {}

        for i, row in enumerate(reader, start=1):
            if i > max_rows:
                errors.append(f"Import limited to {max_rows} rows")
                break
            total = i
            try:
                # Extract fields from CSV
                parsed = self._parse_row(row)

                # 1. Ensure Building exists (use configured default name)
                building_key = self._settings.get(
                    "default_building_name", "Building"
                )
                if building_key not in building_cache:
                    building_id = await self._find_or_create_hierarchy(
                        "building", "name", building_key,
                        {"name": building_key, "slug": _sanitize_slug(building_key),
                         "description": "", "image": ""},
                    )
                    building_cache[building_key] = building_id

                # 2. Ensure Floor exists
                level_raw = str(parsed.get("level", "0")).strip() or "0"
                floor_name = f"Floor {level_raw}"
                floor_slug = f"l{level_raw}"
                floor_key = f"{building_cache[building_key]}:{floor_slug}"
                if floor_key not in floor_cache:
                    floor_id = await self._find_or_create_hierarchy(
                        "floor", "slug", floor_slug,
                        {"name": floor_name, "slug": floor_slug,
                         "description": "", "image": "",
                         "building_id": building_cache[building_key]},
                        parent_id=building_cache[building_key],
                    )
                    floor_cache[floor_key] = floor_id

                # 3. Ensure Room exists
                room_name = parsed.get("room_fr", "") or ""
                room_slug = _sanitize_slug(
                    parsed.get("room_slug", "") or room_name
                )
                if not room_name:
                    room_name = _titleize(room_slug) or "Unknown"
                room_key = f"{floor_cache[floor_key]}:{room_slug}"
                if room_key not in room_cache:
                    room_id = await self._find_or_create_hierarchy(
                        "room", "slug", room_slug,
                        {"name": room_name, "slug": room_slug,
                         "description": "", "image": "",
                         "floor_id": floor_cache[floor_key]},
                        parent_id=floor_cache[floor_key],
                    )
                    room_cache[room_key] = room_id

                # 4. Ensure DeviceModel exists
                model_name = parsed.get("model", "") or "Unknown"
                if model_name not in model_cache:
                    model_id = await self._find_or_create_ref(
                        self.repos["device_model"], model_name
                    )
                    model_cache[model_name] = model_id

                # 5. Ensure DeviceFirmware exists
                firmware_name = parsed.get("firmware", "") or "na"
                if firmware_name not in firmware_cache:
                    firmware_id = await self._find_or_create_ref(
                        self.repos["device_firmware"], firmware_name
                    )
                    firmware_cache[firmware_name] = firmware_id

                # 6. Ensure DeviceFunction exists
                function_name = parsed.get("function", "") or "sensor"
                if function_name not in function_cache:
                    function_id = await self._find_or_create_ref(
                        self.repos["device_function"], function_name
                    )
                    function_cache[function_name] = function_id

                # 7. Determine enabled status from state
                state_raw = parsed.get("state", "")
                enabled = self._parse_enabled(state_raw)

                # 8. Build IP: if the CSV value is a plain number,
                #    treat it as the last octet of {ip_prefix}.X
                ip_prefix = self._settings.get("ip_prefix", "192.168.0")
                raw_ip = (parsed.get("ip", "") or "").strip()
                if raw_ip:
                    if raw_ip.isdigit():
                        ip_value: str | None = f"{ip_prefix}.{raw_ip}"
                    else:
                        ip_value = raw_ip
                else:
                    ip_value = None

                # 9. Create the device
                device_data = {
                    "mac": parsed.get("mac", ""),
                    "ip": ip_value,
                    "enabled": enabled,
                    "position_name": parsed.get("position_fr", ""),
                    "position_slug": _sanitize_slug(
                        parsed.get("position_slug", "")
                        or parsed.get("position_fr", "")
                    ),
                    "mode": parsed.get("mode", ""),
                    "interlock": parsed.get("interlock", ""),
                    "ha_device_class": parsed.get("ha_device_class", ""),
                    "extra": parsed.get("extra", ""),
                    "room_id": room_cache[room_key],
                    "model_id": model_cache[model_name],
                    "firmware_id": firmware_cache[firmware_name],
                    "function_id": function_cache[function_name],
                    "target_id": None,
                }

                device_id = await self.repos["device"].create(device_data)
                created += 1
                logs.append({
                    "row": i,
                    "status": "created",
                    "message": f"Device created (MAC: {device_data['mac']})",
                    "id": device_id,
                    "mac": device_data["mac"],
                })

            except Exception as ex:
                _LOGGER.exception("Failed to import row %s", i)
                error_msg = str(ex)
                errors.append(f"Row {i}: {error_msg}")
                logs.append({
                    "row": i,
                    "status": "error",
                    "message": error_msg,
                })

        return {
            "total": total,
            "created": created,
            "updated": 0,
            "skipped": 0,
            "errors": errors,
            "logs": logs,
        }

    def _parse_row(self, row: dict) -> dict[str, str]:
        """Parse a CSV row using the header map.

        Args:
            row: A dict from csv.DictReader.

        Returns:
            A dict of semantic field names to stripped string values.
        """
        result: dict[str, str] = {}
        for csv_key, field_name in HEADER_MAP.items():
            if field_name and csv_key in row:
                val = (row[csv_key] or "").strip()
                result[field_name] = val
        return result

    def _parse_enabled(self, state: str) -> bool:
        """Convert a state string to a boolean enabled flag.

        Args:
            state: The raw state string from CSV
                   (e.g. 'Enable', 'Disable', etc.)

        Returns:
            True if the state indicates the device is enabled.
        """
        if not state:
            return False
        key = (
            state.strip()
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )
        return key in ("enable", "enable-hot")

    async def _find_or_create_hierarchy(
        self,
        repo_key: str,
        match_field: str,
        match_value: str,
        create_data: Dict[str, Any],
        parent_id: Optional[int] = None,
    ) -> int:
        """Find or create a hierarchical entity (building, floor, room).

        Args:
            repo_key: The repository key (e.g. "building", "floor", "room").
            match_field: The field to match on (e.g. "name", "slug").
            match_value: The value to match.
            create_data: Data dict for creation if not found.
            parent_id: Optional parent ID for child entities.

        Returns:
            The entity ID.
        """
        repo = self.repos[repo_key]
        if parent_id is not None:
            items = await repo.find_by_parent(parent_id)
        else:
            items = await repo.find_all()
        for item in items:
            if item.get(match_field) == match_value:
                return int(item["id"])
        return int(await repo.create(create_data))

    async def _find_or_create_ref(self, repo: Any, name: str) -> int:
        """Find or create a reference entity by name.

        Works for model, firmware, and function entities.

        Args:
            repo: The repository instance.
            name: The entity name.

        Returns:
            The entity ID.
        """
        items = await repo.find_all()
        for item in items:
            if item.get("name") == name:
                return int(item["id"])
        return int(await repo.create({"name": name, "enabled": True}))
