"""API controller for HA group generation from the Device Manager hierarchy.

In HA 2026.x, typed groups (``light.home_lvl0_kitchen_lights``, …) are created
via the built-in "group" config entry flow::

    1. hass.config_entries.flow.async_init("group", context={"source": "user"})
    2. async_configure(flow_id, {"next_step_id": domain})
    3. async_configure(flow_id, {"name": object_id, "entities": [...], ...})

Member entity IDs are resolved from the HA device registry + entity registry
looking up each device by its MAC address.  This guarantees only entities that
actually exist in HA are included in each group.

For domains not supported by the config entry flow (climate, …), the fallback
uses the ``group.set`` service.

Display name: ``Building > Floor > Room > Lights``
"""

import logging
import re
from typing import Any

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# function_name → HA domain (member entity IDs)
# ---------------------------------------------------------------------------

_FUNCTION_TO_HA_DOMAIN: dict[str, str] = {
    "light": "light",
    "shutter": "cover",
    "heater": "climate",
    "tv": "media_player",
    "button": "binary_sensor",
    "door": "binary_sensor",
    "doorbell": "binary_sensor",
    "window": "binary_sensor",
    "motion": "binary_sensor",
    "presence": "binary_sensor",
    "sensor": "sensor",
    "energy": "sensor",
    "thermal": "sensor",
    "water": "sensor",
    "gaz": "sensor",
    "ir": "switch",
    "infra": "switch",
}

_DEFAULT_HA_DOMAIN = "switch"

_FUNCTION_PLURAL: dict[str, str] = {
    "light": "lights",
    "shutter": "shutters",
    "heater": "heaters",
    "tv": "tvs",
    "button": "buttons",
    "door": "doors",
    "doorbell": "doorbells",
    "window": "windows",
    "motion": "motions",
    "presence": "presences",
    "sensor": "sensors",
    "energy": "energies",
    "thermal": "thermals",
    "water": "waters",
    "gaz": "gazs",
    "ir": "irs",
    "infra": "infras",
}

# Domains that have a dedicated group type in the "group" config entry flow.
# See homeassistant/components/group/config_flow.py::GROUP_TYPES
_TYPED_DOMAINS = frozenset({
    "binary_sensor", "cover", "fan", "light", "lock", "media_player", "switch",
})

# Some domains require extra boolean fields in the form step
_DOMAIN_FLOW_EXTRA: dict[str, dict[str, Any]] = {
    "binary_sensor": {"all": False},
    "light": {"all": False},
    "switch": {"all": False},
}

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _ha_domain(function_name: str) -> str:
    return _FUNCTION_TO_HA_DOMAIN.get(function_name.lower(), _DEFAULT_HA_DOMAIN)


def _plural(function_name: str) -> str:
    fn = function_name.lower()
    return _FUNCTION_PLURAL.get(fn, fn + "s")


def _device_entity_id(
    ha_domain: str,
    building_slug: str,
    floor_slug: str,
    room_slug: str,
    function_slug: str,
    position_slug: str,
) -> str:
    """``{domain}.{building}_{floor}_{room}_{function}_{position}``"""
    parts = "_".join(
        _slugify(s)
        for s in [building_slug, floor_slug, room_slug, function_slug, position_slug]
        if s
    )
    return f"{ha_domain}.{parts}"


def _resolve_device_entities(hass: Any, mac: str, domain: str) -> list[str]:
    """Return real HA entity IDs for the given device MAC and domain.

    Queries the HA device registry by MAC (network or Zigbee IEEE address),
    then the entity registry filtered by domain.  Only enabled entities are
    returned.  Returns an empty list when the device is not registered in HA.
    """
    try:
        from homeassistant.helpers import device_registry as dr, entity_registry as er  # type: ignore[import]
    except Exception:
        return []

    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    ha_device = None

    # Standard network MAC (Tasmota, ESPHome, …)
    try:
        normalized = dr.format_mac(mac)
        ha_device = device_reg.async_get_device(
            connections={(dr.CONNECTION_NETWORK_MAC, normalized)}
        )
    except Exception:
        pass

    # Zigbee IEEE address: DM stores "0x00124b0025156aca" → "00:12:4b:00:25:15:6a:ca"
    if ha_device is None and isinstance(mac, str) and mac.lower().startswith("0x"):
        try:
            raw = mac[2:].lower().zfill(16)
            ieee = ":".join(raw[i:i+2] for i in range(0, 16, 2))
            ha_device = device_reg.async_get_device(
                connections={(dr.CONNECTION_ZIGBEE, ieee)}
            )
        except Exception:
            pass

    if ha_device is None:
        _LOGGER.debug("[resolve] mac=%s → not found in HA device registry", mac)
        return []

    entries = er.async_entries_for_device(entity_reg, ha_device.id)
    found = [
        e.entity_id
        for e in entries
        if e.domain == domain and not e.disabled_by
    ]
    _LOGGER.debug(
        "[resolve] mac=%s domain=%s → device '%s' → entities: %s",
        mac, domain, ha_device.name_by_user or ha_device.name, found,
    )
    return found

def _group_object_id(*parts: str) -> str:
    """``{p1}_{p2}_...`` slugified — used as entity_id suffix."""
    return "_".join(_slugify(p) for p in parts if p)


async def _remove_all_group_entries(hass: Any) -> int:
    """Delete ALL 'group' config entries (typed groups). Returns count removed."""
    entries = hass.config_entries.async_entries("group")
    for entry in list(entries):
        await hass.config_entries.async_remove(entry.entry_id)
    return len(entries)


async def _create_typed_group(
    hass: Any, domain: str, object_id: str, members: list[str], pretty_name: str
) -> str | None:
    """Create a typed group via the HA 'group' config entry flow."""
    _LOGGER.debug("[create_group] %s.%s  members=%s", domain, object_id, members)
    try:
        result = await hass.config_entries.flow.async_init(
            "group", context={"source": "user"}
        )
        flow_id = result["flow_id"]
        _LOGGER.debug("[create_group] flow_id=%s  step1_result type=%s", flow_id, result.get("type"))

        result = await hass.config_entries.flow.async_configure(
            flow_id, {"next_step_id": domain}
        )
        _LOGGER.debug("[create_group] step2 type=%s", result.get("type"))

        user_input: dict[str, Any] = {
            "name": object_id,
            "entities": members,
            "hide_members": False,
            **_DOMAIN_FLOW_EXTRA.get(domain, {}),
        }
        result = await hass.config_entries.flow.async_configure(flow_id, user_input)
        _LOGGER.debug("[create_group] step3 type=%s  result=%s", result.get("type"), result)

        if result.get("type") == "create_entry":
            entity_id = f"{domain}.{object_id}"
            await hass.async_block_till_done()
            try:
                from homeassistant.helpers import entity_registry as er  # type: ignore[import]
                registry = er.async_get(hass)
                reg_entry = registry.async_get(entity_id)
                if reg_entry:
                    registry.async_update_entity(entity_id, name=pretty_name)
                    _LOGGER.debug("[create_group] friendly name set: %s → %s", entity_id, pretty_name)
                else:
                    _LOGGER.warning("[create_group] entity not in registry after creation: %s", entity_id)
            except Exception as err:
                _LOGGER.debug("[create_group] could not set friendly name for %s: %s", entity_id, err)
            _LOGGER.info("[create_group] ✓ created %s  (%s)", entity_id, pretty_name)
            return entity_id

        _LOGGER.warning(
            "[create_group] unexpected flow result for %s.%s: %s", domain, object_id, result
        )
        return None
    except Exception as err:
        _LOGGER.warning("[create_group] failed %s.%s: %s", domain, object_id, err)
        return None


# ---------------------------------------------------------------------------
# API View
# ---------------------------------------------------------------------------


class HaGroupsGenerateAPIView(BaseView):
    """Generate typed HA groups for ALL buildings.

    POST /api/device_manager/ha_groups/generate
    Body: ignored — always regenerates the complete room→floor→building stack.
    """

    url = "/api/device_manager/ha_groups/generate"
    name = "api:device_manager:ha_groups:generate"
    requires_auth = True

    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        repos = get_repos(request)
        hass = request.app["hass"]
        _LOGGER.info("=== HA Groups generation started ===")

        try:
            buildings = await repos["building"].find_all()
            _LOGGER.info("[phase1] %d building(s) found", len(buildings))

            settings_all = await repos["settings"].get_all()
            allow_empty = settings_all.get("ha_groups_empty_groups", "false") == "true"
            _LOGGER.debug("[phase1] allow_empty=%s", allow_empty)

            # Phase 1: collect all group definitions using HA registries
            all_groups: list[dict] = []
            for building in buildings:
                await self._collect_building(hass, repos, building.id, all_groups, allow_empty)
            _LOGGER.info("[phase1] %d group(s) collected total", len(all_groups))

            # Phase 2: remove all existing typed group config entries (clean slate)
            removed = await _remove_all_group_entries(hass)
            _LOGGER.info("[phase2] removed %d existing group config entries", removed)

            # Phase 3: create groups
            created_typed: list[dict] = []
            created_fallback: list[dict] = []

            for g in all_groups:
                domain = g["domain"]
                object_id = g["objectId"]
                members = g["members"]

                if domain in _TYPED_DOMAINS:
                    entity_id = await _create_typed_group(hass, domain, object_id, members, g["name"])
                    if entity_id:
                        g["entityId"] = entity_id
                        created_typed.append(g)
                        continue

                # Fallback: group.set service → group.dm_xxx
                fb_entity_id = f"group.{object_id}"
                try:
                    await hass.services.async_call(
                        "group",
                        "set",
                        {
                            "object_id": object_id,
                            "name": g["name"],
                            "entities": members,
                        },
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.warning("group.set failed for %s: %s", object_id, err)
                    # Last resort: write state directly
                    hass.states.async_set(
                        fb_entity_id,
                        "on",
                        {"entity_id": members, "friendly_name": g["name"]},
                    )
                g["entityId"] = fb_entity_id
                created_fallback.append(g)

            _LOGGER.info(
                "[phase3] ==> %d typed (%s), %d fallback (group.set)",
                len(created_typed),
                ", ".join(sorted({g["domain"] for g in created_typed})),
                len(created_fallback),
            )
            _LOGGER.info("=== HA Groups generation done ===")

        except Exception as err:
            _LOGGER.exception("Failed to generate HA groups", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)

        result = [
            {
                "entityId": g["entityId"],
                "name": g["name"],
                "memberCount": g["memberCount"],
                "scope": g["scope"],
            }
            for g in all_groups
        ]
        return self.json({"groups": result, "total": len(result)})

    # ------------------------------------------------------------------
    # Collection helpers — build all_groups list without creating entities yet
    # ------------------------------------------------------------------

    async def _collect_room(self, hass: Any, repos: dict, room_id: int, all_groups: list[dict], allow_empty: bool = False) -> list[dict]:
        """Collect room-level group definitions.

        Member entity IDs are resolved from the HA registries (by device MAC)
        so only entities that actually exist in HA are included.
        """
        room = await repos["room"].find_by_id(room_id)
        if room is None:
            return []

        devices = await repos["device"].find_by_room(room_id)
        if not devices:
            return []

        sample = devices[0]
        building_slug = sample._building.slug if sample._building else ""
        building_name = sample._building.name if sample._building else ""
        floor_slug = sample._floor.slug if sample._floor else ""
        floor_name = sample._floor.name if sample._floor else ""

        by_function: dict[str, list] = {}
        for device in devices:
            fn = (device._refs.function_name or "").strip()
            if fn:
                by_function.setdefault(fn, []).append(device)

        added: list[dict] = []
        for fn_name, fn_devices in by_function.items():
            domain = _ha_domain(fn_name)
            plural = _plural(fn_name)

            # Resolve real entity IDs from HA registries
            members: list[str] = []
            for d in fn_devices:
                entity_ids = _resolve_device_entities(hass, d.mac, domain)
                if entity_ids:
                    members.extend(entity_ids)
                else:
                    _LOGGER.debug(
                        "[room:%s] fn=%s domain=%s mac=%s → no HA entity found",
                        room.slug, fn_name, domain, d.mac,
                    )

            if not members:
                if not allow_empty:
                    _LOGGER.debug("[room:%s] fn=%s → skipped (no members resolved)", room.slug, fn_name)
                    continue
                _LOGGER.debug("[room:%s] fn=%s → creating empty group (allow_empty=True)", room.slug, fn_name)

            object_id = _group_object_id(building_slug, floor_slug, room.slug, plural)
            pretty_name = f"{building_name} > {floor_name} > {room.name} > {plural.capitalize()}"

            _LOGGER.info(
                "[room:%s] queued %s.%s  members=%s",
                room.slug, domain, object_id, members,
            )
            entry = {
                "objectId": object_id,
                "entityId": f"{domain}.{object_id}",  # tentative, updated after creation
                "name": pretty_name,
                "memberCount": len(members),
                "scope": "room",
                "domain": domain,
                "plural": plural,
                "members": members,
            }
            all_groups.append(entry)
            added.append(entry)
            _LOGGER.debug("Queued room group %s.%s (%d members)", domain, object_id, len(members))

        return added

    async def _collect_floor(self, hass: Any, repos: dict, floor_id: int, all_groups: list[dict], allow_empty: bool = False) -> list[dict]:
        floor = await repos["floor"].find_by_id(floor_id)
        if floor is None:
            return []

        rooms = await repos["room"].find_by_floor(floor_id)
        room_entries: list[dict] = []
        for room in rooms:
            room_entries.extend(await self._collect_room(hass, repos, room.id, all_groups, allow_empty))

        # Group room entries by (domain, plural)
        fn_to_rooms: dict[tuple, list[str]] = {}
        for g in room_entries:
            key = (g["domain"], g["plural"])
            fn_to_rooms.setdefault(key, []).append(g["entityId"])

        building_slug, building_name = "", ""
        for room in rooms:
            devices = await repos["device"].find_by_room(room.id)
            if devices:
                building_slug = devices[0]._building.slug or ""
                building_name = devices[0]._building.name or ""
                break

        added: list[dict] = []
        for (domain, plural), room_ids in fn_to_rooms.items():
            object_id = _group_object_id(building_slug, floor.slug, plural)
            pretty_name = f"{building_name} > {floor.name} > {plural.capitalize()}"
            entry = {
                "objectId": object_id,
                "entityId": f"{domain}.{object_id}",
                "name": pretty_name,
                "memberCount": len(room_ids),
                "scope": "floor",
                "domain": domain,
                "plural": plural,
                "members": room_ids,
            }
            all_groups.append(entry)
            added.append(entry)
            _LOGGER.debug("Queued floor group %s.%s (%d members)", domain, object_id, len(room_ids))

        return added

    async def _collect_building(self, hass: Any, repos: dict, building_id: int, all_groups: list[dict], allow_empty: bool = False) -> list[dict]:
        building = await repos["building"].find_by_id(building_id)
        if building is None:
            return []

        floors = await repos["floor"].find_by_building(building_id)
        floor_entries: list[dict] = []
        for floor in floors:
            floor_entries.extend(await self._collect_floor(hass, repos, floor.id, all_groups, allow_empty))

        fn_to_floors: dict[tuple, list[str]] = {}
        for g in floor_entries:
            key = (g["domain"], g["plural"])
            fn_to_floors.setdefault(key, []).append(g["entityId"])

        added: list[dict] = []
        for (domain, plural), floor_ids in fn_to_floors.items():
            object_id = _group_object_id(building.slug, plural)
            pretty_name = f"{building.name} > {plural.capitalize()}"
            entry = {
                "objectId": object_id,
                "entityId": f"{domain}.{object_id}",
                "name": pretty_name,
                "memberCount": len(floor_ids),
                "scope": "building",
                "domain": domain,
                "plural": plural,
                "members": floor_ids,
            }
            all_groups.append(entry)
            added.append(entry)
            _LOGGER.debug("Queued building group %s.%s (%d members)", domain, object_id, len(floor_ids))

        return added
