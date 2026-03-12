"""Tests for device identifier validation (_is_valid_identifier).

Covers all accepted identifier formats:
  - Ethernet MAC colon-separated   (AA:BB:CC:DD:EE:FF)
  - Ethernet MAC hyphen-separated  (AA-BB-CC-DD-EE-FF)
  - Ethernet MAC compact           (AABBCCDDEEFF)
  - EUI-64 colon-separated         (AA:BB:CC:DD:EE:FF:00:11)
  - Zigbee EUI-64 with 0x prefix   (0x00124b0025156aca)
"""

import sys
import types
import importlib.util
from pathlib import Path


def _load_device_controller():
    """Load device_controller.py with all HA/aiohttp dependencies mocked."""
    base_dir = Path(__file__).resolve().parents[1]

    # Mock aiohttp
    aiohttp_mod = types.ModuleType("aiohttp")
    web_mod = types.ModuleType("aiohttp.web")
    web_mod.Request = object  # type: ignore[attr-defined]
    web_mod.Response = object  # type: ignore[attr-defined]
    aiohttp_mod.web = web_mod  # type: ignore[attr-defined]
    sys.modules.setdefault("aiohttp", aiohttp_mod)
    sys.modules.setdefault("aiohttp.web", web_mod)

    # Ensure package namespace exists
    for pkg in (
        "custom_components",
        "custom_components.device_manager",
        "custom_components.device_manager.controllers",
        "custom_components.device_manager.models",
        "custom_components.device_manager.utils",
    ):
        sys.modules.setdefault(pkg, types.ModuleType(pkg))

    # Mock .crud
    crud_mod = types.ModuleType("custom_components.device_manager.controllers.crud")
    crud_mod.CrudListView = type("CrudListView", (), {})  # type: ignore[attr-defined]
    crud_mod.CrudDetailView = type("CrudDetailView", (), {})  # type: ignore[attr-defined]
    crud_mod._handle_errors = lambda name: (lambda f: f)  # type: ignore[attr-defined]
    sys.modules["custom_components.device_manager.controllers.crud"] = crud_mod

    # Mock .base
    base_ctrl_mod = types.ModuleType("custom_components.device_manager.controllers.base")
    base_ctrl_mod.get_repos = lambda r: {}  # type: ignore[attr-defined]
    sys.modules["custom_components.device_manager.controllers.base"] = base_ctrl_mod

    # Mock ..models.base
    models_base_mod = types.ModuleType("custom_components.device_manager.models.base")
    models_base_mod.SerializableMixin = object  # type: ignore[attr-defined]
    sys.modules["custom_components.device_manager.models.base"] = models_base_mod

    # Mock ..models.device
    models_device_mod = types.ModuleType("custom_components.device_manager.models.device")
    models_device_mod.DmDevice = object  # type: ignore[attr-defined]
    sys.modules["custom_components.device_manager.models.device"] = models_device_mod

    # Mock ..utils.case_convert
    case_convert_mod = types.ModuleType("custom_components.device_manager.utils.case_convert")
    case_convert_mod.to_snake_case_dict = lambda d: d  # type: ignore[attr-defined]
    sys.modules["custom_components.device_manager.utils.case_convert"] = case_convert_mod

    controller_path = base_dir / "controllers" / "device_controller.py"
    spec = importlib.util.spec_from_file_location(
        "custom_components.device_manager.controllers.device_controller",
        str(controller_path),
    )
    assert spec is not None and spec.loader is not None, "Cannot load device_controller"
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "custom_components.device_manager.controllers"
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_ctrl = _load_device_controller()
_is_valid_identifier = _ctrl._is_valid_identifier


# ---------------------------------------------------------------------------
# Valid formats
# ---------------------------------------------------------------------------

def test_mac_colon_uppercase():
    assert _is_valid_identifier("7C:2C:67:D7:DF:E8")
    assert _is_valid_identifier("AA:BB:CC:DD:EE:FF")


def test_mac_colon_lowercase():
    assert _is_valid_identifier("aa:bb:cc:dd:ee:ff")
    assert _is_valid_identifier("7c:2c:67:d7:df:e8")


def test_mac_hyphen():
    assert _is_valid_identifier("7C-2C-67-D7-DF-E8")
    assert _is_valid_identifier("AA-BB-CC-DD-EE-FF")
    assert _is_valid_identifier("aa-bb-cc-dd-ee-ff")


def test_mac_compact():
    assert _is_valid_identifier("7C2C67D7DFE8")
    assert _is_valid_identifier("aabbccddeeff")
    assert _is_valid_identifier("AABBCCDDEEFF")


def test_eui64_colon():
    assert _is_valid_identifier("00:12:4B:00:25:15:6A:CA")
    assert _is_valid_identifier("aa:bb:cc:dd:ee:ff:00:11")


def test_zigbee_eui64_hex_prefix():
    """Zigbee EUI-64 in 0x... form as seen in fixtures."""
    assert _is_valid_identifier("0x00124b0025156aca")
    assert _is_valid_identifier("0xAABBCCDDEEFF0011")
    assert _is_valid_identifier("0xaabbccddeeff0011")


# ---------------------------------------------------------------------------
# Invalid formats
# ---------------------------------------------------------------------------

def test_empty_string_rejected():
    assert not _is_valid_identifier("")


def test_plain_text_rejected():
    assert not _is_valid_identifier("zigbee")
    assert not _is_valid_identifier("not-a-mac")


def test_non_hex_chars_rejected():
    assert not _is_valid_identifier("ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")
    assert not _is_valid_identifier("GG-GG-GG-GG-GG-GG")


def test_ip_address_rejected():
    assert not _is_valid_identifier("192.168.1.1")


def test_short_mac_rejected():
    assert not _is_valid_identifier("AA:BB:CC:DD:EE")          # only 5 bytes


def test_short_eui64_rejected():
    assert not _is_valid_identifier("0x00124b")                 # too short


def test_eui64_wrong_prefix_rejected():
    assert not _is_valid_identifier("00124b0025156aca")         # 16 hex but no 0x prefix
