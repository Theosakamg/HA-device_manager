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

        # Pending target resolution: list of (device_id, raw_target, room_id)
        pending_targets: list[tuple[int, str, int]] = []

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

                # 7. Parse state and enabled from State CSV column
                state_raw = parsed.get("state", "")
                state, enabled = self._parse_state_and_enabled(state_raw)

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
                    "state": state,
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

                # Queue target resolution for second pass
                raw_target = (parsed.get("target", "") or "").strip()
                if raw_target:
                    pending_targets.append(
                        (device_id, raw_target, room_cache[room_key])
                    )

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

        # ── Second pass: resolve target links ──────────────────────────
        # All devices are now created; resolve function/position references
        # within the same room.
        target_resolved = 0
        target_failed = 0
        for device_id, raw_target, room_id in pending_targets:
            resolved_id = await self._resolve_target(raw_target, room_id)
            if resolved_id is not None:
                await self.repos["device"].update(
                    device_id, {"target_id": resolved_id}
                )
                target_resolved += 1
                _LOGGER.debug(
                    "Target resolved: device %d → %d (raw: %s)",
                    device_id, resolved_id, raw_target,
                )
            else:
                target_failed += 1
                errors.append(
                    f"Device {device_id}: target '{raw_target}' not found"
                    f" in room {room_id}"
                )

        return {
            "total": total,
            "created": created,
            "updated": 0,
            "skipped": 0,
            "target_resolved": target_resolved,
            "target_failed": target_failed,
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

    def _parse_state_and_enabled(self, state_str: str) -> tuple[str, bool]:
        """Convert a State CSV value to (state, enabled) tuple.

        Args:
            state_str: The raw State string from CSV
                       (e.g. 'Enable', 'Disable', 'Enable-Hot', 'KO', 'NA').

        Returns:
            Tuple of (state, enabled) with proper mapping:
            - "Enable" → ("deployed", True)
            - "Disable" → ("parking", False)
            - "NA" → ("parking", False)
            - "Enable-Hot" → ("deployed_hot", True)
            - "KO" → ("out_of_order", False)
            - default → ("parking", False)
        """
        if not state_str:
            return ("parking", False)

        key = (
            state_str.strip()
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )

        mapping = {
            "enable": ("deployed", True),
            "disable": ("parking", False),
            "na": ("parking", False),
            "enable-hot": ("deployed_hot", True),
            "ko": ("out_of_order", False),
        }

        return mapping.get(key, ("parking", False))

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
            if getattr(item, match_field, None) == match_value:
                return int(item.id)
        return int(await repo.create(create_data))

    async def _resolve_target(
        self, raw_target: str, room_id: int
    ) -> Optional[int]:
        """Resolve a target string to a device ID within the same room.

        The target format is ``function_slug/position_slug``
        (e.g. ``light/ceiling``).  Only devices in ``room_id`` are
        considered — the security model restricts links to the same room.

        Args:
            raw_target: Raw target string from the CSV (e.g. ``light/ceiling``).
            room_id: The room ID of the source device.

        Returns:
            The target device ID, or None if no match is found.
        """
        if not raw_target or "/" not in raw_target:
            return None
        parts = raw_target.strip().lower().split("/", 1)
        target_function_slug = parts[0].strip()
        target_position_slug = parts[1].strip()
        if not target_function_slug or not target_position_slug:
            return None

        candidates = await self.repos["device"].find_by_room(room_id)
        for device in candidates:
            fn = (device._refs.function_name or "").strip().lower()
            ps = (device.position_slug or "").strip().lower()
            if fn == target_function_slug and ps == target_position_slug:
                return int(device.id)
        return None

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
            if item.name == name:
                return int(item.id)
        return int(await repo.create({"name": name, "enabled": True}))
