"""Tests for the Tasmota runtime migration.

Covers:
  * numeric version comparison (``firmware.tasmota.version``) — the legacy naive
    string comparison bug;
  * the shared HTTP/MQTT-topic helpers (``firmware.tasmota.shared``),
    including the critical self-referencing Referer header;
  * the ``firmware.tasmota`` maintenance/update treatments (restart, status,
    upgrade, firmware batch) with the network and DB layers mocked. In
    particular a regression test asserting that ``upgrade_device`` sends
    ``Upgrade`` (never the legacy inverted ``curlMode`` / restart path) and
    always sends the Referer header.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import helpers  # provided via sys.path by run_tests.py

assert_raises = helpers.assert_raises

# ---------------------------------------------------------------------------
# Pure module: version_compare (no HA / no relative imports)
# ---------------------------------------------------------------------------

_version_compare = helpers.load_module("firmware/tasmota/version.py")
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
    "custom_components.device_manager.persistence",
    "custom_components.device_manager.persistence.models",
    "custom_components.device_manager.firmware",
    "custom_components.device_manager.firmware.tasmota",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

# Register the numeric version module where update.py expects it (`.version`).
sys.modules["custom_components.device_manager.firmware.tasmota.version"] = _version_compare

_case_convert = helpers.load_module("utils/case_convert.py")
_utils_pkg_mod = types.ModuleType("custom_components.device_manager.utils")
_utils_pkg_mod.case_convert = _case_convert  # type: ignore[attr-defined]
sys.modules.setdefault("custom_components.device_manager.utils", _utils_pkg_mod)
sys.modules.setdefault(
    "custom_components.device_manager.utils.case_convert", _case_convert
)

_models_base = helpers.load_module(
    "persistence/models/base.py",
    package="custom_components.device_manager.persistence.models",
)
sys.modules["custom_components.device_manager.persistence.models.base"] = _models_base
_models_device = helpers.load_module(
    "persistence/models/device.py",
    package="custom_components.device_manager.persistence.models",
)
sys.modules["custom_components.device_manager.persistence.models.device"] = _models_device

_tasmota_shared = helpers.load_module(
    "firmware/tasmota/shared.py",
    package="custom_components.device_manager.firmware.tasmota",
)
sys.modules[
    "custom_components.device_manager.firmware.tasmota.shared"
] = _tasmota_shared


def test_referer_header_is_self_referencing():
    headers = _tasmota_shared.referer_headers("10.0.0.5")
    assert headers == {"Referer": "http://10.0.0.5/"}


def test_build_url_sanitizes_data():
    url = _tasmota_shared.build_url("10.0.0.5", "cmnd", "Backlog Restart 1")
    assert url.startswith("http://10.0.0.5/cmnd?")
    assert " " not in url


# ---------------------------------------------------------------------------
# Runtime treatments: firmware/tasmota/{client,maintenance,update}.py
# (network + DB mocked)
# ---------------------------------------------------------------------------

# Stub the heavy persistence dependencies pulled in by client.py so the
# treatment modules import without a real DB / repositories / HA.
_repos_stub = types.ModuleType("custom_components.device_manager.persistence.repositories")
_repos_stub.DeviceRepository = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.persistence.repositories"] = _repos_stub

_db_stub = types.ModuleType(
    "custom_components.device_manager.persistence.database_manager"
)
_db_stub.DatabaseManager = object  # type: ignore[attr-defined]
sys.modules[
    "custom_components.device_manager.persistence.database_manager"
] = _db_stub

_client = helpers.load_module(
    "firmware/tasmota/client.py",
    package="custom_components.device_manager.firmware.tasmota",
    module_name="tasmota_client_module",
)
sys.modules["custom_components.device_manager.firmware.tasmota.client"] = _client

_maintenance = helpers.load_module(
    "firmware/tasmota/maintenance.py",
    package="custom_components.device_manager.firmware.tasmota",
    module_name="tasmota_maintenance_module",
)

_update = helpers.load_module(
    "firmware/tasmota/update.py",
    package="custom_components.device_manager.firmware.tasmota",
    module_name="tasmota_update_module",
)


def _fake_device(mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.5"):
    dev = MagicMock()
    dev.mac = mac
    dev.ip = ip
    return dev


def test_restart_device_http_sends_referer():
    """restart_device over HTTP must send the self-referencing Referer header."""
    dev = _fake_device()
    with patch.object(_client, "open_db", return_value=MagicMock()), \
         patch.object(_client, "close_db"), \
         patch.object(_client, "load_device_by_mac", return_value=dev), \
         patch.object(_client.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        result = _maintenance.restart_device(
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
    with patch.object(_client, "open_db", return_value=MagicMock()), \
         patch.object(_client, "close_db"), \
         patch.object(_client, "load_device_by_mac", return_value=dev), \
         patch.object(_client.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        _update.upgrade_device("/tmp/x.sqlite", dev.mac, {}, use_mqtt=False)

    url = mock_get.call_args[0][0]
    assert "Upgrade" in url
    assert "Restart" not in url


def test_get_status_offline_on_error():
    dev = _fake_device()
    with patch.object(_client, "open_db", return_value=MagicMock()), \
         patch.object(_client, "close_db"), \
         patch.object(_client, "load_device_by_mac", return_value=dev), \
         patch.object(
             _client, "http_get",
             side_effect=_client.TasmotaRuntimeError("boom"),
         ):
        result = _maintenance.get_status("/tmp/x.sqlite", dev.mac, {})

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

    with patch.object(_client, "open_db", return_value=MagicMock()), \
         patch.object(_client, "close_db"), \
         patch.object(_client, "load_all_devices", return_value=[dev]), \
         patch.object(_client, "http_get", side_effect=fake_http):
        result = _update.update_firmware_batch(
            "/tmp/x.sqlite", {}, target_version="14.5.0"
        )

    assert dev.mac in result["skipped"]
    assert dev.mac not in result["upgraded"]
    assert "Upgrade%201" not in calls


def test_filter_devices_by_mac():
    d1 = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    d2 = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")
    d3 = _fake_device("AA:BB:CC:DD:EE:03", None)  # no IP -> excluded
    out = _client.filter_devices([d1, d2, d3], ["aa:bb:cc:dd:ee:02"])
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
