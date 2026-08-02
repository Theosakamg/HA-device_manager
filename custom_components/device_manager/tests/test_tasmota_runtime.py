"""Tests for the Tasmota runtime migration.

Covers:
  * numeric version comparison (``firmware.tasmota.version``) — the legacy naive
    string comparison bug;
  * the common HTTP/MQTT-topic helpers (``firmware.tasmota.common``),
    including the critical self-referencing Referer header;
  * the ``firmware.tasmota`` maintenance/update treatments (restart, status,
    upgrade, firmware batch), which now receive already-loaded ``DmDevice``
    objects (device loading lives in ``managers.device_loader``) so only the
    network layer is mocked. In particular a regression test asserting that
    ``upgrade_device`` sends ``Upgrade`` (never the legacy inverted
    ``curlMode`` / restart path) and always sends the Referer header;
  * ``managers.device_loader.filter_devices`` device selection (has-IP + MAC
    filter).
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
extract_version = _version_compare.extract_version


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


def test_extract_version_from_surrounding_text():
    assert extract_version("Tasmota v15.5.0 Sylvan") == "15.5.0"
    assert extract_version("15.5.0(release)") == "15.5.0"
    assert extract_version("v14.5.0") == "14.5.0"
    # First X.Y.Z match wins.
    assert extract_version("1.2.3 then 4.5.6") == "1.2.3"


def test_extract_version_returns_empty_when_absent():
    assert extract_version("") == ""
    assert extract_version("no version here") == ""
    # A full X.Y.Z triple is required (partial versions do not match).
    assert extract_version("14.5") == ""


# ---------------------------------------------------------------------------
# Common helpers: firmware/tasmota/common.py (needs DmDevice)
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

_tasmota_common = helpers.load_module(
    "firmware/tasmota/common.py",
    package="custom_components.device_manager.firmware.tasmota",
)
sys.modules[
    "custom_components.device_manager.firmware.tasmota.common"
] = _tasmota_common


def test_referer_header_is_self_referencing():
    headers = _tasmota_common.referer_headers("10.0.0.5")
    assert headers == {"Referer": "http://10.0.0.5/"}


def test_build_url_sanitizes_data():
    url = _tasmota_common.build_url("10.0.0.5", "cmnd", "Backlog Restart 1")
    assert url.startswith("http://10.0.0.5/cmnd?")
    assert " " not in url


def test_build_command_url_uses_cm_endpoint():
    """Commands target /cm?cmnd=<command>, matching the working deploy path."""
    url = _tasmota_common.build_command_url("10.0.0.5", "Restart 1")
    assert url == "http://10.0.0.5/cm?cmnd=Restart%201"
    assert "/cmnd?" not in url
    assert " " not in url


# ---------------------------------------------------------------------------
# Runtime treatments: firmware/tasmota/{client,maintenance,update}.py
# (network mocked; devices passed in directly by the manager layer)
# ---------------------------------------------------------------------------

# Stub the heavy persistence dependencies pulled in by managers.device_loader
# (the manager layer that now owns device loading) so it imports without a real
# DB / repositories. The firmware treatments themselves are persistence-free.
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

# Stub firmware.base.config (client.device_password reads DEVICE_PASS from it;
# the real module imports python-dotenv which isn't needed in these tests).
sys.modules.setdefault(
    "custom_components.device_manager.firmware.base",
    types.ModuleType("custom_components.device_manager.firmware.base"),
)
_config_stub = types.ModuleType(
    "custom_components.device_manager.firmware.base.config"
)
_config_stub.get_config = lambda key, default=None: default  # type: ignore[attr-defined]
sys.modules[
    "custom_components.device_manager.firmware.base.config"
] = _config_stub

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

# The maintenance/update treatments are now stateless classes; instantiate one
# backend of each and drive the tests through these instances.
_maintenance_backend = _maintenance.TasmotaMaintenance()
_update_backend = _update.TasmotaUpdate()

# managers.device_loader now owns device loading (open/close DB, find_by_mac,
# find_all and the has-IP/MAC filter). Load it against the persistence stubs
# registered above.
sys.modules.setdefault(
    "custom_components.device_manager.managers",
    types.ModuleType("custom_components.device_manager.managers"),
)
_device_loader = helpers.load_module(
    "managers/device_loader.py",
    package="custom_components.device_manager.managers",
    module_name="managers_device_loader_module",
)


def _fake_device(mac="AA:BB:CC:DD:EE:FF", ip="10.0.0.5"):
    dev = MagicMock()
    dev.mac = mac
    dev.ip = ip
    return dev


def test_restart_device_http_sends_referer():
    """restart_device over HTTP must send the self-referencing Referer header."""
    dev = _fake_device()
    with patch.object(_client.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        result = _maintenance_backend.restart_device(dev, {}, use_mqtt=False)

    assert result["ok"] is True
    assert result["transport"] == "http"
    _, kwargs = mock_get.call_args
    assert kwargs["headers"] == {"Referer": "http://10.0.0.5/"}
    # Command URL must contain Restart, not Upgrade.
    assert "Restart" in mock_get.call_args[0][0]


def test_upgrade_device_sends_upgrade_not_restart():
    """Regression: upgrade must send Upgrade (never the inverted restart path)."""
    dev = _fake_device()
    with patch.object(_client.requests, "get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        _update_backend.upgrade_device(dev, {}, use_mqtt=False)

    url = mock_get.call_args[0][0]
    assert "Upgrade" in url
    assert "Restart" not in url


def test_get_status_offline_on_error():
    dev = _fake_device()
    with patch.object(
        _client, "http_get",
        side_effect=_client.TasmotaRuntimeError("boom"),
    ):
        result = _maintenance_backend.get_status(dev, {})

    assert result["online"] is False
    assert result["status"] == {}


def test_update_firmware_batch_skips_up_to_date():
    """Devices already at/above the target version must be skipped, not upgraded."""
    dev = _fake_device()
    calls = []

    def fake_http(ip, command, settings):
        calls.append(command)
        if command == "Status 2":
            return {"StatusFWR": {"Version": "14.10.0"}}
        return {}

    with patch.object(_client, "http_get", side_effect=fake_http):
        result = _update_backend.update_firmware_batch([dev], {}, target_version="14.5.0")

    assert dev.mac in result["skipped"]
    assert dev.mac not in result["upgraded"]
    assert "Upgrade 1" not in calls


def test_restart_batch_restarts_each_device():
    """restart_batch sends Restart to every targeted device over HTTP."""
    d1 = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    d2 = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")
    calls = []

    def fake_http(ip, command, settings):
        calls.append(command)
        return {}

    with patch.object(_client, "http_get", side_effect=fake_http):
        result = _maintenance_backend.restart_batch([d1, d2], {})

    assert result["total"] == 2
    assert d1.mac in result["restarted"]
    assert d2.mac in result["restarted"]
    assert result["failed"] == []
    assert calls == ["Restart 1", "Restart 1"]


def test_restart_batch_collects_failures():
    """A per-device failure is collected instead of aborting the batch."""
    ok = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    bad = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")

    def fake_http(ip, command, settings):
        if ip == "10.0.0.2":
            raise _client.TasmotaRuntimeError("boom")
        return {}

    with patch.object(_client, "http_get", side_effect=fake_http):
        result = _maintenance_backend.restart_batch([ok, bad], {})

    assert result["total"] == 2
    assert ok.mac in result["restarted"]
    assert bad.mac in result["failed"]


def test_upgrade_batch_upgrades_all_unconditionally():
    """upgrade_batch sends Upgrade to every device without version gating."""
    d1 = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    d2 = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")
    calls = []

    def fake_http(ip, command, settings):
        calls.append(command)
        return {}

    with patch.object(_client, "http_get", side_effect=fake_http):
        result = _update_backend.upgrade_batch([d1, d2], {})

    assert result["total"] == 2
    assert d1.mac in result["upgraded"]
    assert d2.mac in result["upgraded"]
    # Unconditional: no Status query, always Upgrade for each device.
    assert calls == ["Upgrade 1", "Upgrade 1"]
    assert "Status 2" not in calls


def test_filter_devices_by_mac():
    d1 = _fake_device("AA:BB:CC:DD:EE:01", "10.0.0.1")
    d2 = _fake_device("AA:BB:CC:DD:EE:02", "10.0.0.2")
    d3 = _fake_device("AA:BB:CC:DD:EE:03", None)  # no IP -> excluded
    out = _device_loader.filter_devices([d1, d2, d3], ["aa:bb:cc:dd:ee:02"])
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
    ("version: extract from text", test_extract_version_from_surrounding_text),
    ("version: extract empty when absent", test_extract_version_returns_empty_when_absent),
    ("common: referer self-referencing", test_referer_header_is_self_referencing),
    ("common: build_url sanitizes", test_build_url_sanitizes_data),
    ("common: build_command_url uses /cm", test_build_command_url_uses_cm_endpoint),
    ("restart: sends Referer over HTTP", test_restart_device_http_sends_referer),
    ("upgrade: sends Upgrade not Restart", test_upgrade_device_sends_upgrade_not_restart),
    ("status: offline on error", test_get_status_offline_on_error),
    ("firmware batch: skips up-to-date", test_update_firmware_batch_skips_up_to_date),
    ("restart batch: restarts each device", test_restart_batch_restarts_each_device),
    ("restart batch: collects failures", test_restart_batch_collects_failures),
    ("upgrade batch: unconditional upgrade", test_upgrade_batch_upgrades_all_unconditionally),
    ("filter: by mac + drops no-ip", test_filter_devices_by_mac),
]
