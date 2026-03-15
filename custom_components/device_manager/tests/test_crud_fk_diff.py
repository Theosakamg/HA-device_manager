"""Tests for _build_update_diff FK entity resolution (issue #24).

Verifies that FK fields (ending with _id) display the entity name alongside
the raw ID, that non-FK fields keep their raw value, that sensitive fields
are masked, and that graceful fallback works when a repo or entity is missing.
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal stub setup — load only crud.py under test
# ---------------------------------------------------------------------------

base_dir = Path(__file__).resolve().parents[1]

# Stub aiohttp
aiohttp_module = types.ModuleType("aiohttp")
web_module = types.ModuleType("aiohttp.web")
web_module.Request = object  # type: ignore[attr-defined]
web_module.Response = object  # type: ignore[attr-defined]
aiohttp_module.web = web_module  # type: ignore[attr-defined]
sys.modules.setdefault("aiohttp", aiohttp_module)
sys.modules.setdefault("aiohttp.web", web_module)

# Stub homeassistant
for mod_name in [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.http",
]:
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

ha_http = sys.modules["homeassistant.components.http"]


class _FakeHAView:
    requires_auth = True


ha_http.HomeAssistantView = _FakeHAView  # type: ignore[attr-defined]

# Stub custom_components packages
for pkg in (
    "custom_components",
    "custom_components.device_manager",
    "custom_components.device_manager.controllers",
    "custom_components.device_manager.models",
    "custom_components.device_manager.utils",
):
    sys.modules.setdefault(pkg, types.ModuleType(pkg))

# Stub .base controller
base_ctrl_stub = types.ModuleType("custom_components.device_manager.controllers.base")


class _BaseView(_FakeHAView):
    def json(self, result, status_code=200):
        return {"result": result, "status": status_code}


base_ctrl_stub.BaseView = _BaseView  # type: ignore[attr-defined]
base_ctrl_stub.get_repos = lambda req: {}  # type: ignore[attr-defined]
base_ctrl_stub.csrf_protect = lambda f: f  # type: ignore[attr-defined]
base_ctrl_stub.rate_limit = lambda **kw: (lambda f: f)  # type: ignore[attr-defined]
base_ctrl_stub.emit_activity_log = lambda *a, **kw: None  # type: ignore[attr-defined]
base_ctrl_stub.fmt_entity_label = lambda t, n, i, s="": f"{t} - {n} [id={i}]"  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.controllers.base"] = base_ctrl_stub

# Stub models.base
models_base_stub = types.ModuleType("custom_components.device_manager.models.base")
models_base_stub.SerializableMixin = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.models.base"] = models_base_stub

# Stub utils.case_convert
case_convert_stub = types.ModuleType("custom_components.device_manager.utils.case_convert")
case_convert_stub.to_snake_case_dict = lambda d: d  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.utils.case_convert"] = case_convert_stub

# Load the actual crud module
crud_path = base_dir / "controllers" / "crud.py"
spec = importlib.util.spec_from_file_location(
    "custom_components.device_manager.controllers.crud", str(crud_path)
)
assert spec is not None and spec.loader is not None
crud_mod = importlib.util.module_from_spec(spec)
crud_mod.__package__ = "custom_components.device_manager.controllers"
spec.loader.exec_module(crud_mod)  # type: ignore[union-attr]

_build_update_diff = crud_mod._build_update_diff
_resolve_fk_label = crud_mod._resolve_fk_label
_escape_md = crud_mod._escape_md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _make_room(entity_id: int, name: str):
    entity = types.SimpleNamespace()
    entity.id = entity_id
    entity.name = name
    entity.slug = name.lower().replace(" ", "-")
    return entity


def _make_device(entity_id: int, display: str):
    entity = types.SimpleNamespace()
    entity.id = entity_id
    entity.display_name = lambda: display
    return entity


# ---------------------------------------------------------------------------
# Tests for _resolve_fk_label
# ---------------------------------------------------------------------------


class TestResolveFkLabel:
    """Unit tests for the _resolve_fk_label helper."""

    def test_none_value_returns_none_marker(self):
        result = run(_resolve_fk_label("room_id", None, {}))
        assert result == "_(none)_"

    def test_unknown_field_returns_raw(self):
        result = run(_resolve_fk_label("custom_field_id", 7, {}))
        assert result == "`7`"

    def test_repo_not_in_repos_returns_raw(self):
        # room_id is in FK_REPO_MAP but repos dict is empty
        result = run(_resolve_fk_label("room_id", 3, {}))
        assert result == "`3`"

    def test_entity_not_found_returns_raw(self):
        async def _not_found(eid):
            return None

        repos = {"room": types.SimpleNamespace(find_by_id=_not_found)}
        result = run(_resolve_fk_label("room_id", 99, repos))
        assert result == "`99`"

    def test_entity_found_with_name(self):
        room = _make_room(3, "Living Room")

        async def _find(eid):
            return room if eid == 3 else None

        repos = {"room": types.SimpleNamespace(find_by_id=_find)}
        result = run(_resolve_fk_label("room_id", 3, repos))
        assert result == '"Living Room" (3)'

    def test_entity_found_with_display_name(self):
        device = _make_device(5, "Sonoff TH16")

        async def _find(eid):
            return device if eid == 5 else None

        repos = {"device": types.SimpleNamespace(find_by_id=_find)}
        result = run(_resolve_fk_label("target_id", 5, repos))
        assert result == '"Sonoff TH16" (5)'

    def test_repo_raises_returns_raw(self):
        async def _broken(eid):
            raise RuntimeError("DB error")

        repos = {"room": types.SimpleNamespace(find_by_id=_broken)}
        result = run(_resolve_fk_label("room_id", 3, repos))
        assert result == "`3`"

    def test_entity_name_with_markdown_chars_is_escaped(self):
        room = _make_room(7, "Living*Room_[Main]")

        async def _find(eid):
            return room if eid == 7 else None

        repos = {"room": types.SimpleNamespace(find_by_id=_find)}
        result = run(_resolve_fk_label("room_id", 7, repos))
        # The name portion (between the outer quotes) must have escaped metacharacters
        safe_name = result.split('"')[1]
        assert "\\*" in safe_name, "asterisk must be escaped"
        assert "\\_" in safe_name, "underscore must be escaped"
        assert "(7)" in result, "raw_id must be preserved unescaped"


# ---------------------------------------------------------------------------
# Tests for _build_update_diff
# ---------------------------------------------------------------------------


class TestBuildUpdateDiffFk:
    """Tests that FK fields display entity names in the diff."""

    def _make_repos(self):
        room_a = _make_room(3, "Living Room")
        room_b = _make_room(5, "Kitchen")

        async def _find_room(eid):
            return {3: room_a, 5: room_b}.get(eid)

        return {"room": types.SimpleNamespace(find_by_id=_find_room)}

    def test_fk_field_shows_entity_names(self):
        repos = self._make_repos()
        result = run(_build_update_diff("Device - foo", {"room_id": 3}, {"room_id": 5}, repos))
        assert '"Living Room" (3)' in result
        assert '"Kitchen" (5)' in result
        assert "room_id" in result

    def test_non_fk_field_shows_raw(self):
        result = run(_build_update_diff("Room - bar", {"name": "old"}, {"name": "new"}, {}))
        assert "`old`" in result
        assert "`new`" in result

    def test_sensitive_field_is_masked(self):
        result = run(_build_update_diff("Device - x", {"password": "abc"}, {"password": "xyz"}, {}))
        assert "`***`" in result
        assert "abc" not in result
        assert "xyz" not in result

    def test_no_changes_returns_header_only(self):
        result = run(_build_update_diff("Room - foo", {"name": "same"}, {"name": "same"}, {}))
        assert result == "Updated Room - foo"
        assert "\n" not in result

    def test_skip_fields_ignored(self):
        result = run(_build_update_diff(
            "Room - foo",
            {"name": "a", "updated_at": "2024-01-01"},
            {"name": "a", "updated_at": "2024-06-01"},
            {},
        ))
        assert result == "Updated Room - foo"

    def test_fk_none_to_value(self):
        room_b = _make_room(5, "Kitchen")

        async def _find_room(eid):
            return room_b if eid == 5 else None

        repos = {"room": types.SimpleNamespace(find_by_id=_find_room)}
        result = run(_build_update_diff("Device - foo", {"room_id": None}, {"room_id": 5}, repos))
        assert "_(none)_" in result
        assert '"Kitchen" (5)' in result

    def test_fk_fallback_when_repos_empty(self):
        # FK field but no repos — must fallback gracefully
        result = run(_build_update_diff("Device - foo", {"room_id": 1}, {"room_id": 2}, {}))
        assert "`1`" in result
        assert "`2`" in result
