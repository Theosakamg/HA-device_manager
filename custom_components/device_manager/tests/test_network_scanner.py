"""Tests for NetworkScanner error propagation.

Verifies that scan failures raise NetworkScanError instead of silently
returning an empty dict, so callers can handle errors explicitly.
"""

import asyncio
import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

import helpers  # provided via sys.path by run_tests.py

# Re-export assert_raises from helpers so existing test code using it works
assert_raises = helpers.assert_raises

# ---------------------------------------------------------------------------
# Bootstrap: load scanner module without importing the full HA package
# ---------------------------------------------------------------------------

# Stub out all transitive dependencies
_yaml_stub = types.ModuleType("yaml")
_yaml_stub.safe_load = lambda s: {}  # type: ignore[attr-defined]

class _YAMLError(Exception):
    pass

_yaml_stub.YAMLError = _YAMLError  # type: ignore[attr-defined]

helpers.stub_ha_modules()

for _mod_name, _mod in [
    ("yaml", _yaml_stub),
]:
    sys.modules.setdefault(_mod_name, _mod)

# Stub services.database_manager
_db_manager_stub = types.ModuleType("custom_components.device_manager.services.database_manager")
_db_manager_stub.DatabaseManager = object  # type: ignore[attr-defined]

# Stub repositories
_repos_stub = types.ModuleType("custom_components.device_manager.repositories")
_repos_stub.DeviceRepository = object  # type: ignore[attr-defined]

# Stub provisioning.utility
_prov_utility_stub = types.ModuleType("custom_components.device_manager.provisioning.utility")
_prov_utility_stub.get_config = lambda key, default='': default  # type: ignore[attr-defined]

for _k, _v in [
    ("custom_components", types.ModuleType("custom_components")),
    ("custom_components.device_manager", types.ModuleType("custom_components.device_manager")),
    ("custom_components.device_manager.services", types.ModuleType("custom_components.device_manager.services")),
    ("custom_components.device_manager.services.database_manager", _db_manager_stub),
    ("custom_components.device_manager.repositories", _repos_stub),
    ("custom_components.device_manager.provisioning", types.ModuleType("custom_components.device_manager.provisioning")),
    ("custom_components.device_manager.provisioning.utility", _prov_utility_stub),
]:
    sys.modules.setdefault(_k, _v)

# Load scanner module
_scanner_module = helpers.load_module(
    "provisioning/core/scanner.py",
    package="custom_components.device_manager.provisioning.core",
    module_name="scanner_module",
)

NetworkScanner = _scanner_module.NetworkScanner  # type: ignore[attr-defined]
NetworkScanError = _scanner_module.NetworkScanError  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scanner():
    """Return a NetworkScanner with a dummy DB."""
    return NetworkScanner(db=MagicMock())


# ---------------------------------------------------------------------------
# Tests — run_network_scan() error propagation
# ---------------------------------------------------------------------------

def test_missing_scan_script_raises():
    """NetworkScanError raised when SCAN_SCRIPT_CONTENT is not configured."""
    scanner = _make_scanner()
    with patch.object(_scanner_module, "get_config", return_value=""):
        with assert_raises(NetworkScanError, match="SCAN_SCRIPT_CONTENT is not configured"):
            scanner.run_network_scan()


def test_timeout_raises():
    """NetworkScanError raised when the scan script times out."""
    scanner = _make_scanner()
    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\nsleep 999"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="bash", timeout=300)):
            with assert_raises(NetworkScanError, match="timed out"):
                scanner.run_network_scan()


def test_subprocess_exception_raises():
    """NetworkScanError raised when subprocess.run itself fails."""
    scanner = _make_scanner()
    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\necho ok"):
        with patch("subprocess.run", side_effect=OSError("no such file")):
            with assert_raises(NetworkScanError, match="Failed to execute scan script"):
                scanner.run_network_scan()


def test_nonzero_exit_raises():
    """NetworkScanError raised when the scan script exits with a non-zero code."""
    scanner = _make_scanner()
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b"permission denied"
    mock_result.stdout = b""

    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\nexit 1"):
        with patch("subprocess.run", return_value=mock_result):
            with assert_raises(NetworkScanError, match="exit 1"):
                scanner.run_network_scan()


def test_invalid_yaml_raises():
    """NetworkScanError raised when the scan output is not valid YAML."""
    scanner = _make_scanner()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = b""
    mock_result.stdout = b": invalid: yaml: ["

    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\necho ok"):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(_scanner_module, "yaml") as mock_yaml:
                mock_yaml.safe_load = MagicMock(side_effect=_YAMLError("bad yaml"))
                mock_yaml.YAMLError = _YAMLError
                with assert_raises(NetworkScanError, match="Failed to parse scan script output"):
                    scanner.run_network_scan()


def test_non_dict_output_raises():
    """NetworkScanError raised when scan output is valid YAML but not a dict."""
    scanner = _make_scanner()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = b""
    mock_result.stdout = b"- item1\n- item2\n"

    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\necho ok"):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(_scanner_module, "yaml") as mock_yaml:
                mock_yaml.safe_load = MagicMock(return_value=["item1", "item2"])
                mock_yaml.YAMLError = _YAMLError
                with assert_raises(NetworkScanError, match="Unexpected scan output format"):
                    scanner.run_network_scan()


def test_successful_scan_returns_dict():
    """A successful scan returns a MAC-to-IP dict and stores results."""
    scanner = _make_scanner()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = b""
    mock_result.stdout = b"192.168.1.1: aa:bb:cc:dd:ee:ff\n"

    with patch.object(_scanner_module, "get_config", return_value="#!/bin/bash\necho ok"):
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(_scanner_module, "yaml") as mock_yaml:
                mock_yaml.safe_load = MagicMock(return_value={"192.168.1.1": "aa:bb:cc:dd:ee:ff"})
                mock_yaml.YAMLError = _YAMLError
                result = scanner.run_network_scan()

    assert result == {"aa:bb:cc:dd:ee:ff": "192.168.1.1"}
    assert scanner._scan_results == {"aa:bb:cc:dd:ee:ff": "192.168.1.1"}


# ---------------------------------------------------------------------------
# Tests — update_device_ips() with None vs empty scan results
# ---------------------------------------------------------------------------

def test_update_device_ips_without_scan_returns_error():
    """update_device_ips returns an error dict when scan was never run."""
    scanner = _make_scanner()
    # _scan_results is None by default (never scanned)
    result = asyncio.run(scanner.update_device_ips())
    assert result["errors"] == 1
    assert result["total"] == 0
    assert "No scan results available" in result["error_details"][0]


def test_update_device_ips_with_empty_scan_proceeds():
    """update_device_ips processes normally when scan found 0 devices."""
    scanner = _make_scanner()
    scanner._scan_results = {}  # scan ran, found nothing

    repo_mock = MagicMock()

    async def _async_find_all():
        return []

    repo_mock.find_all = _async_find_all

    with patch.object(_scanner_module, "DeviceRepository", return_value=repo_mock):
        result = asyncio.run(scanner.update_device_ips())

    assert result["errors"] == 0
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "📡 Network Scanner Error Propagation Tests"
TEST_SUITE = [
    ("missing script config raises", test_missing_scan_script_raises),
    ("timeout raises NetworkScanError", test_timeout_raises),
    ("subprocess exception raises", test_subprocess_exception_raises),
    ("nonzero exit code raises", test_nonzero_exit_raises),
    ("invalid YAML output raises", test_invalid_yaml_raises),
    ("non-dict output raises", test_non_dict_output_raises),
    ("successful scan returns dict", test_successful_scan_returns_dict),
    ("update_device_ips without scan returns error", test_update_device_ips_without_scan_returns_error),
    ("update_device_ips with empty scan proceeds", test_update_device_ips_with_empty_scan_proceeds),
]
