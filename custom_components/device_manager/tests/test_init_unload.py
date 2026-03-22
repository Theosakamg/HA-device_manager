"""Tests for async_unload_entry in __init__.py.

Ensures the frontend panel is properly removed on unload so that a subsequent
reload (or HA restart) can re-register it without raising
ValueError: Overwriting panel device_manager (issue #36).
"""

import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


DATA_KEY_DB = "db"  # mirrors const.DATA_KEY_DB — resolved at load time


def _build_hass_stub(domain: str, db_manager=None):
    """Return a minimal fake hass object."""
    hass = MagicMock()
    hass.data = {domain: {DATA_KEY_DB: db_manager} if db_manager else {}}
    hass.config.config_dir = "/tmp"
    return hass


def _build_ha_stubs(domain: str):
    """Inject the minimal homeassistant stub modules required by __init__.py."""
    # homeassistant top-level
    ha_mod = types.ModuleType("homeassistant")

    # homeassistant.components.frontend
    frontend_mod = types.ModuleType("homeassistant.components.frontend")
    frontend_mod.async_register_built_in_panel = MagicMock()  # type: ignore[attr-defined]
    frontend_mod.async_remove_panel = MagicMock()  # type: ignore[attr-defined]

    ha_components = types.ModuleType("homeassistant.components")
    ha_components.frontend = frontend_mod  # type: ignore[attr-defined]

    # homeassistant.config_entries
    config_entries_mod = types.ModuleType("homeassistant.config_entries")
    config_entries_mod.ConfigEntry = MagicMock  # type: ignore[attr-defined]
    config_entries_mod.SOURCE_IMPORT = "import"  # type: ignore[attr-defined]

    # homeassistant.core
    core_mod = types.ModuleType("homeassistant.core")
    core_mod.HomeAssistant = MagicMock  # type: ignore[attr-defined]

    # homeassistant.helpers.typing
    helpers_mod = types.ModuleType("homeassistant.helpers")
    helpers_typing_mod = types.ModuleType("homeassistant.helpers.typing")
    helpers_typing_mod.ConfigType = dict  # type: ignore[attr-defined]

    sys.modules.setdefault("homeassistant", ha_mod)
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.frontend"] = frontend_mod
    sys.modules["homeassistant.config_entries"] = config_entries_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.helpers"] = helpers_mod
    sys.modules["homeassistant.helpers.typing"] = helpers_typing_mod

    return frontend_mod


class TestAsyncUnloadEntry(unittest.TestCase):
    """Test that async_unload_entry removes the frontend panel."""

    def setUp(self):
        # Remove any previously cached version of the module under test
        for key in list(sys.modules.keys()):
            if "custom_components.device_manager" in key or key == "device_manager_init":
                del sys.modules[key]

        self.frontend_mod = _build_ha_stubs("device_manager")

        # Stub out internal sub-packages so __init__.py can be imported
        for mod_name in [
            "custom_components",
            "custom_components.device_manager",
            "custom_components.device_manager.const",
            "custom_components.device_manager.controllers",
            "custom_components.device_manager.repositories",
            "custom_components.device_manager.services",
            "custom_components.device_manager.services.database_manager",
            "custom_components.device_manager.utils",
            "custom_components.device_manager.utils.crypto",
        ]:
            if mod_name not in sys.modules:
                sys.modules[mod_name] = types.ModuleType(mod_name)

        # Provide the symbols imported by __init__.py
        _const = sys.modules["custom_components.device_manager.const"]
        _const.DB_NAME = "device_manager.db"  # type: ignore[attr-defined]
        _const.DOMAIN = "device_manager"  # type: ignore[attr-defined]
        _const.DATA_KEY_DB = DATA_KEY_DB  # type: ignore[attr-defined]
        _const.DATA_KEY_REPOS = "repos"  # type: ignore[attr-defined]
        _const.STATIC_URL_BASE = "/device_manager_static"  # type: ignore[attr-defined]
        _const.FRONTEND_JS_FILENAME = "device-manager.js"  # type: ignore[attr-defined]
        _const.PANEL_COMPONENT_NAME = "dm-app-shell"  # type: ignore[attr-defined]
        _const.CRYPTO_KEY_FILENAME = "dm/.device_manager.key"  # type: ignore[attr-defined]
        sys.modules["custom_components.device_manager.controllers"].ALL_VIEWS = []  # type: ignore[attr-defined]
        sys.modules["custom_components.device_manager.utils.crypto"].generate_key = lambda: "testkey"  # type: ignore[attr-defined]

        repo_names = [
            "BuildingRepository", "FloorRepository", "RoomRepository",
            "DeviceRepository", "DeviceModelRepository", "DeviceFirmwareRepository",
            "DeviceFunctionRepository", "SettingsRepository", "ActivityLogRepository",
        ]
        repos_mod = sys.modules["custom_components.device_manager.repositories"]
        for name in repo_names:
            setattr(repos_mod, name, MagicMock())

        db_manager_mod = sys.modules["custom_components.device_manager.services.database_manager"]
        db_manager_mod.DatabaseManager = MagicMock  # type: ignore[attr-defined]

        services_mod = sys.modules["custom_components.device_manager.services"]
        services_mod.database_manager = db_manager_mod  # type: ignore[attr-defined]

        # Import the module under test
        import importlib.util
        from pathlib import Path
        init_path = Path(__file__).resolve().parents[1] / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            "custom_components.device_manager", str(init_path)
        )
        assert spec and spec.loader
        self.init_module = importlib.util.module_from_spec(spec)
        self.init_module.__package__ = "custom_components.device_manager"
        spec.loader.exec_module(self.init_module)  # type: ignore[union-attr]

    def test_async_remove_panel_called_on_unload(self):
        """async_remove_panel must be called with 'device_manager' during unload."""
        db_manager = MagicMock()
        db_manager.close = AsyncMock()

        hass = _build_hass_stub("device_manager", db_manager)

        entry = MagicMock()

        asyncio.run(self.init_module.async_unload_entry(hass, entry))

        self.frontend_mod.async_remove_panel.assert_called_once_with(hass, "device_manager")

    def test_db_closed_on_unload(self):
        """The database manager must be closed during unload."""
        db_manager = MagicMock()
        db_manager.close = AsyncMock()

        hass = _build_hass_stub("device_manager", db_manager)
        entry = MagicMock()

        asyncio.run(self.init_module.async_unload_entry(hass, entry))

        db_manager.close.assert_awaited_once()

    def test_hass_data_cleared_on_unload(self):
        """hass.data[DOMAIN] must be removed during unload."""
        db_manager = MagicMock()
        db_manager.close = AsyncMock()

        hass = _build_hass_stub("device_manager", db_manager)
        entry = MagicMock()

        asyncio.run(self.init_module.async_unload_entry(hass, entry))

        self.assertNotIn("device_manager", hass.data)

    def test_unload_returns_true(self):
        """async_unload_entry must return True on success."""
        db_manager = MagicMock()
        db_manager.close = AsyncMock()

        hass = _build_hass_stub("device_manager", db_manager)
        entry = MagicMock()

        result = asyncio.run(self.init_module.async_unload_entry(hass, entry))

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

def _make_unload_test(method_name: str):
    """Wrap a TestAsyncUnloadEntry method so setUp() is called first."""
    def _run():
        inst = TestAsyncUnloadEntry()
        inst.setUp()
        getattr(inst, method_name)()
    return _run


SUITE_LABEL = "🔌 Integration Unload Tests"
TEST_SUITE = [
    ("async_remove_panel called on unload", _make_unload_test("test_async_remove_panel_called_on_unload")),
    ("db closed on unload", _make_unload_test("test_db_closed_on_unload")),
    ("hass.data cleared on unload", _make_unload_test("test_hass_data_cleared_on_unload")),
    ("unload returns True", _make_unload_test("test_unload_returns_true")),
]
