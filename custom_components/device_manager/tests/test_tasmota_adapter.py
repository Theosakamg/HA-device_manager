"""Tests for TasmotaAdapter GPIO template configuration.

Verifies that the device model's ``template`` (Tasmota Template/Module
GPIO mapping) is applied during deploy when defined, and silently skipped
(fail-soft, no exception) when the device has no model, the model has no
template, or the template JSON is malformed. Also verifies the template is
applied before any other device configuration.
"""

import sys
import types
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import helpers  # provided via sys.path by run_tests.py

if TYPE_CHECKING:
    # Only for static type-checking: the real classes are loaded dynamically
    # below via helpers.load_module() so MyPy can resolve their real types
    # without this import ever running (avoids needing homeassistant at runtime).
    from custom_components.device_manager.models.device import DmDevice as DmDeviceType
    from custom_components.device_manager.provisioning.adapters.tasmota import (
        TasmotaAdapter as TasmotaAdapterType,
    )

assert_raises = helpers.assert_raises

# ---------------------------------------------------------------------------
# Bootstrap: load DmDevice, FirmwareAdapter and TasmotaAdapter without
# importing the real homeassistant package or requiring a live HA install.
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()

for _name in (
    "custom_components",
    "custom_components.device_manager",
    "custom_components.device_manager.models",
    "custom_components.device_manager.provisioning",
    "custom_components.device_manager.provisioning.core",
    "custom_components.device_manager.provisioning.adapters",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

# utils.case_convert (dependency of models/base.py and models/device.py)
_case_convert = helpers.load_module("utils/case_convert.py")
_utils_pkg = sys.modules["custom_components.device_manager"]
_utils_pkg_mod = types.ModuleType("custom_components.device_manager.utils")
_utils_pkg_mod.case_convert = _case_convert  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components.device_manager.utils", _utils_pkg_mod)
sys.modules.setdefault("custom_components.device_manager.utils.case_convert", _case_convert)

# Real models.base + models.device modules, registered so relative imports
# from firmware_base.py / tasmota.py resolve correctly.
_models_base = helpers.load_module(
    "models/base.py",
    package="custom_components.device_manager.models",
)
sys.modules["custom_components.device_manager.models.base"] = _models_base

_models_device = helpers.load_module(
    "models/device.py",
    package="custom_components.device_manager.models",
)
sys.modules["custom_components.device_manager.models.device"] = _models_device

DmDevice = _models_device.DmDevice
DeviceRoomRef = _models_device.DeviceRoomRef
DeviceFloorRef = _models_device.DeviceFloorRef
DeviceBuildingRef = _models_device.DeviceBuildingRef
DeviceLinkedRefs = _models_device.DeviceLinkedRefs

# Stub provisioning.utility.get_config (reads env/settings in the real app).
_prov_utility_stub = types.ModuleType("custom_components.device_manager.provisioning.utility")
_prov_utility_stub.get_config = lambda key, default='': default  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.provisioning.utility"] = _prov_utility_stub

# Real firmware_base module (only depends on models.device, already stubbed above).
_firmware_base = helpers.load_module(
    "provisioning/core/firmware_base.py",
    package="custom_components.device_manager.provisioning.core",
)
sys.modules["custom_components.device_manager.provisioning.core.firmware_base"] = _firmware_base

# Module under test.
_tasmota_module = helpers.load_module(
    "provisioning/adapters/tasmota.py",
    package="custom_components.device_manager.provisioning.adapters",
    module_name="tasmota_module",
)
TasmotaAdapter = _tasmota_module.TasmotaAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(model_template: str = "", ip: str = "192.168.1.50") -> "DmDeviceType":
    """Build a minimal DmDevice suitable for adapter tests."""
    return DmDevice(  # type: ignore[no-any-return]
        mac="AA:BB:CC:DD:EE:FF",
        ip=ip,
        position_slug="desk",
        position_name="Desk",
        enabled=True,
        _room=DeviceRoomRef(slug="office"),
        _floor=DeviceFloorRef(slug="l0", number=0),
        _building=DeviceBuildingRef(slug="main"),
        _refs=DeviceLinkedRefs(
            model_name="Shelly Mini1PMG3",
            model_template=model_template,
            firmware_name="Tasmota",
            function_name="Button",
        ),
    )


def _make_adapter() -> "TasmotaAdapterType":
    """Build a TasmotaAdapter without touching the real filesystem."""
    with patch.object(TasmotaAdapter, "_create_backup_folder", lambda self: None):
        return TasmotaAdapter(manager=MagicMock())  # type: ignore[no-any-return]


_VALID_TEMPLATE = (
    '{"NAME":"Shelly Mini1PMG3","ARCH":"ESP32C3",'
    '"GPIO":[576,32,0,4736,0,224,3200,8161,0,0,192,0,0,0,0,0,0,0,0,0,0,0],'
    '"FLAG":0,"BASE":1}'
)


# ---------------------------------------------------------------------------
# Tests — _configure_template()
# ---------------------------------------------------------------------------

def test_valid_template_sends_template_and_module():
    """A valid template JSON is sent via Template + Module 0 commands."""
    adapter = _make_adapter()
    device = _make_device(model_template=_VALID_TEMPLATE)

    with patch.object(adapter, "_send_commands") as mock_send:
        adapter._configure_template(device)

    mock_send.assert_called_once_with(
        device, {"Template": _VALID_TEMPLATE, "Module": "0"}
    )


def test_empty_template_is_skipped():
    """No model template defined: no command is sent, no exception raised."""
    adapter = _make_adapter()
    device = _make_device(model_template="")

    with patch.object(adapter, "_send_commands") as mock_send:
        adapter._configure_template(device)

    mock_send.assert_not_called()


def test_no_model_assigned_is_skipped():
    """Device with no model assigned (default refs) behaves like empty template."""
    adapter = _make_adapter()
    device = _make_device()
    device._refs = DeviceLinkedRefs()  # simulate no model_id / no linked model

    with patch.object(adapter, "_send_commands") as mock_send:
        adapter._configure_template(device)

    mock_send.assert_not_called()


def test_invalid_json_template_is_skipped():
    """Malformed template JSON is logged and skipped, not raised."""
    adapter = _make_adapter()
    device = _make_device(model_template="{not valid json")

    with patch.object(adapter, "_send_commands") as mock_send:
        adapter._configure_template(device)  # must not raise

    mock_send.assert_not_called()


def test_whitespace_only_template_is_skipped():
    """A template consisting only of whitespace is treated as empty."""
    adapter = _make_adapter()
    device = _make_device(model_template="   ")

    with patch.object(adapter, "_send_commands") as mock_send:
        adapter._configure_template(device)

    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — _configure_device() ordering: template applied before anything else
# ---------------------------------------------------------------------------

def test_configure_device_applies_template_before_base_config():
    """The GPIO template must be sent before base/network configuration."""
    adapter = _make_adapter()
    device = _make_device(model_template=_VALID_TEMPLATE)

    with patch.object(adapter, "_send_commands") as mock_send, \
         patch.object(adapter, "_configure_interlock"), \
         patch.object(adapter, "_configure_by_function"):
        adapter._configure_device(device)

    assert mock_send.call_count >= 2, "Expected at least template + base_config calls"
    first_call_configs = mock_send.call_args_list[0].args[1]
    assert first_call_configs == {"Template": _VALID_TEMPLATE, "Module": "0"}, (
        f"Template must be the first _send_commands call, got: {first_call_configs}"
    )


def test_configure_device_without_template_skips_but_still_configures():
    """Regression: devices without a model template deploy exactly as before."""
    adapter = _make_adapter()
    device = _make_device(model_template="")

    with patch.object(adapter, "_send_commands") as mock_send, \
         patch.object(adapter, "_configure_interlock"), \
         patch.object(adapter, "_configure_by_function"):
        adapter._configure_device(device)

    sent_configs = [c.args[1] for c in mock_send.call_args_list]
    assert not any("Template" in cfg for cfg in sent_configs), (
        "No Template command should be sent when the model has no template"
    )
    assert len(sent_configs) == 2, "base_config and network_config should still be sent"


# ---------------------------------------------------------------------------
# Tests — Referer header (Tasmota Referer/CORS protection, see SetOption128)
# ---------------------------------------------------------------------------

def test_dump_config_sends_self_referencing_referer_header():
    """_dump_config() must send a self-referencing Referer header.

    Tasmota rejects HTTP API calls with an empty/foreign Referer unless
    SetOption128 1 is set or a Webpassword is configured - which is exactly
    the state right after a factory reset (Webpassword cleared). A
    same-origin Referer is trusted regardless, unblocking freshly-reset
    devices without needing console/serial access.
    """
    adapter = _make_adapter()
    device = _make_device(ip="192.168.1.77")
    adapter.backup_path = "/tmp"

    mock_response = MagicMock()
    mock_response.content = b"dummy-config-dump"

    with patch.object(_tasmota_module.requests, "get", return_value=mock_response) as mock_get, \
         patch("builtins.open", MagicMock()):
        adapter._dump_config(device)

    _, kwargs = mock_get.call_args
    assert kwargs.get("headers") == {"Referer": "http://192.168.1.77/"}


def test_send_commands_sends_self_referencing_referer_header():
    """_send_commands() must send a self-referencing Referer header."""
    adapter = _make_adapter()
    device = _make_device(ip="192.168.1.88")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Template": "Ok"}

    with patch.object(_tasmota_module.requests, "get", return_value=mock_response) as mock_get:
        adapter._send_commands(device, {"Template": "x"})

    _, kwargs = mock_get.call_args
    assert kwargs.get("headers") == {"Referer": "http://192.168.1.88/"}


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "🔌 Tasmota Adapter - GPIO Template Tests"
TEST_SUITE = [
    ("valid template sends Template+Module", test_valid_template_sends_template_and_module),
    ("empty template is skipped", test_empty_template_is_skipped),
    ("no model assigned is skipped", test_no_model_assigned_is_skipped),
    ("invalid JSON template is skipped", test_invalid_json_template_is_skipped),
    ("whitespace-only template is skipped", test_whitespace_only_template_is_skipped),
    ("template applied before base config", test_configure_device_applies_template_before_base_config),
    ("no template: deploy unaffected (regression)", test_configure_device_without_template_skips_but_still_configures),
    ("_dump_config sends self-referencing Referer header", test_dump_config_sends_self_referencing_referer_header),
    ("_send_commands sends self-referencing Referer header", test_send_commands_sends_self_referencing_referer_header),
]
