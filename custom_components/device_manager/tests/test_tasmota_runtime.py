"""Tests for the Tasmota runtime migration.

Covers:
  * numeric version comparison (``utils.version_compare``) — the legacy naive
    string comparison bug;
  * the shared HTTP/MQTT-topic helpers (``provisioning.core.tasmota_shared``),
    including the critical self-referencing Referer header;
  * ``services.tasmota_runtime`` single-device and batch operations, with the
    network and DB layers mocked. In particular a regression test asserting
    that ``upgrade_device`` sends ``Upgrade`` (never the legacy inverted
    ``curlMode`` / restart path) and always sends the Referer header.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import helpers  # provided via sys.path by run_tests.py

assert_raises = helpers.assert_raises

# ---------------------------------------------------------------------------
# Pure module: version_compare (no HA / no relative imports)
# ---------------------------------------------------------------------------

_version_compare = helpers.load_module("utils/version_compare.py")
parse_tasmota_version = _version_compare.parse_tasmota_version
is_newer = _version_compare.is_newer


def test_parse_strips_suffix_and_prefix():
    assert parse_tasmota_version("v14.5.0(release)") == (14, 5, 0)
    assert parse_tasmota_version("14.5.0(tasmota)") == (14, 5, 0)
    assert parse_tasmota_version("14.5.0") == (14, 5, 0)


def test_parse_handles_garbage():
    assert parse_tasmota_version("") == ()
    assert parse_tasmota_version("14.5.0-dev") == (14, 5, 0)


def test_is_newer_numeric_not_lexicographic():
    # The legacy string comparison wrongly reports 14.5.1 > 14.10.0.
    assert is_newer("14.10.0", "14.5.1") is True
    assert is_newer("14.5.1", "14.10.0") is False


def test_is_newer_pads_missing_components():
    assert is_newer("14.5", "14.5.0") is False
    assert is_newer("14.5.1", "14.5") is True


# ---------------------------------------------------------------------------
# Shared helpers: provisioning/core/tasmota_shared.py (needs DmDevice)
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()

for _name in (
    "custom_components",
    "custom_components.device_manager",
    "custom_components.device_manager.models",
    "custom_components.device_manager.provisioning",
    "custom_components.device_manager.provisioning.core",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_case_convert = helpers.load_module("utils/case_convert.py")
_utils_pkg_mod = types.ModuleType("custom_components.device_manager.utils")
_utils_pkg_mod.case_convert = _case_convert  # type: ignore[attr-defined]
_utils_pkg_mod.version_compare = _version_compare  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components.device_manager.utils", _utils_pkg_mod)
sys.modules.setdefault(
    "custom_components.device_manager.utils.case_convert", _case_convert
)
sys.modules.setdefault(
    "custom_components.device_manager.utils.version_compare", _version_compare
)

_models_base = helpers.load_module(
    "models/base.py", package="custom_components.device_manager.models"
)
sys.modules["custom_components.device_manager.models.base"] = _models_base
_models_device = helpers.load_module(
    "models/device.py", package="custom_components.device_manager.models"
)
sys.modules["custom_components.device_manager.models.device"] = _models_device

_tasmota_shared = helpers.load_module(
    "provisioning/core/tasmota_shared.py",
    package="custom_components.device_manager.provisioning.core",
)
sys.modules[
    "custom_components.device_manager.provisioning.core.tasmota_shared"
] = _tasmota_shared


def test_referer_header_is_self_referencing():
    headers = _tasmota_shared.referer_headers("10.0.0.5")
    assert headers == {"Referer": "http://10.0.0.5/"}


def test_build_url_sanitizes_data():
    url = _tasmota_shared.build_url("10.0.0.5", "cmnd", "Backlog Restart 1")
    assert url.startswith("http://10.0.0.5/cmnd?")
    assert " " not in url


# ---------------------------------------------------------------------------
# Runtime service: services/tasmota_runtime.py (network + DB mocked)
# ---------------------------------------------------------------------------

# Stub the heavy relative dependencies pulled in by tasmota_runtime so it can
# be imported without a real DB / repositories / HA.
_repos_stub = types.ModuleType("custom_components.device_manager.repositories")
_repos_stub.DeviceRepository = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.repositories"] = _repos_stub

_db_stub = types.ModuleType(
    "custom_components.device_manager.services.database_manager"
)
_db_stub.DatabaseManager = object  # type: ignore[attr-defined]
sys.modules.setdefault(
    "custom_components.device_manager.services", types.ModuleType(
        "custom_components.device_manager.services"
    )
)
sys.modules[
    "custom_components.device_manager.services.database_manager"
] = _db_stub

_tasmota_runtime = helpers.load_module(
    "services/tasmota_runtime.py",
    package="custom_components.device_manager.services",
    module_name="tasmota_runtime_module",
)


def _fake_device(mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.5"):
    dev = MagicMock()
    dev.mac = mac
    dev.ip = ip
    return dev


def test_restart_device_http_sends_referer():
    """restart_device over HTTP must send the self-referencing Referer header."""
    dev = _fake_device()
    with patch.object(_tasmota_runtime, "_open_db", return_value=MagicMock()), \
         patch.object(_tasmota_runtime, "_close_db"), \
         patch.object(_tasmota_runtime, "_load_device_by_mac", return_value=dev), \
         patch.object(_tasmota_runtime.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        result = _tasmota_runtime.restart_device(
            "/tmp/x.sqlite", dev.mac, {}, use_mqtt=False
        )

    assert result["ok"] is True
    assert result["transport"] == "http"
    _, kwargs = mock_get.call_args
    assert kwargs["headers"] == {"Referer": "http://10.0.0.5/"}
    # Command URL must contain Restart, not Upgrade.
    assert "Restart" in mock_get.call_args[0][0]


def test_upgrade_device_sends_upgrade_not_restart():
    """Regression: upgrade must send Upgrade (never the inverted restart path)."""
    dev = _fake_device()
    with patch.object(_tasmota_runtime, "_open_db", return_value=MagicMock()), \
         patch.object(_tasmota_runtime, "_close_db"), \
         patch.object(_tasmota_runtime, "_load_device_by_mac", return_value=dev), \
         patch.object(_tasmota_runtime.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        _tasmota_runtime.upgrade_device("/tmp/x.sqlite", dev.mac, {}, use_mqtt=False)

    url = mock_get.call_args[0][0]
    assert "Upgrade" in url
    assert "Restart" not in url


def test_get_status_offline_on_error():
    dev = _fake_device()
    with patch.object(_tasmota_runtime, "_open_db", return_value=MagicMock()), \
         patch.object(_tasmota_runtime, "_close_db"), \
         patch.object(_tasmota_runtime, "_load_device_by_mac", return_value=dev), \
         patch.object(
             _tasmota_runtime, "_http_get",
             side_effect=_tasmota_runtime.TasmotaRuntimeError("boom"),
         ):
        result = _tasmota_runtime.get_status("/tmp/x.sqlite", dev.mac, {})

    assert result["online"] is False
    assert result["status"] == {}


def test_update_firmware_batch_skips_up_to_date():
    """Devices already at/above the target version must be skipped, not upgraded."""
    dev = _fake_device()
    calls = []

    def fake_http(ip, cmd, password, data=None):
        calls.append(data)
        if data == "Status%202":
            return {"StatusFWR": {"Version": "14.10.0"}}
        return {}

    with patch.object(_tasmota_runtime, "_open_db", return_value=MagicMock()), \
         patch.object(_tasmota_runtime, "_close_db"), \
         patch.object(_tasmota_runtime, "_load_all_devices", return_value=[dev]), \
         patch.object(_tasmota_runtime, "_http_get", side_effect=fake_http):
        result = _tasmota_runtime.update_firmware_batch(
            "/tmp/x.sqlite", {}, target_version="14.5.0"
        )

    assert dev.mac in result["skipped"]
    assert dev.mac not in result["upgraded"]
    assert "Upgrade%201" not in calls


def test_filter_devices_by_mac():
    d1 = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    d2 = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")
    d3 = _fake_device("AA:BB:CC:DD:EE:03", None)  # no IP -> excluded
    out = _tasmota_runtime._filter_devices([d1, d2, d3], ["aa:bb:cc:dd:ee:02"])
    assert out == [d2]


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "📡 Tasmota Runtime Tests"
TEST_SUITE = [
    ("version: strips suffix/prefix", test_parse_strips_suffix_and_prefix),
    ("version: handles garbage", test_parse_handles_garbage),
    ("version: numeric not lexicographic", test_is_newer_numeric_not_lexicographic),
    ("version: pads missing components", test_is_newer_pads_missing_components),
    ("shared: referer self-referencing", test_referer_header_is_self_referencing),
    ("shared: build_url sanitizes", test_build_url_sanitizes_data),
    ("restart: sends Referer over HTTP", test_restart_device_http_sends_referer),
    ("upgrade: sends Upgrade not Restart", test_upgrade_device_sends_upgrade_not_restart),
    ("status: offline on error", test_get_status_offline_on_error),
    ("firmware batch: skips up-to-date", test_update_firmware_batch_skips_up_to_date),
    ("filter: by mac + drops no-ip", test_filter_devices_by_mac),
]
