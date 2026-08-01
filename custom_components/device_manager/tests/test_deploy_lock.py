"""Tests for the deploy()/scan() concurrency lock in managers/deploy_manager.py.

Verifies that a second deploy() or scan() call raises DeployInProgressError
immediately (instead of racing with an in-progress run on the same SQLite
DB file) and that the lock is always released afterwards, including when
the underlying implementation raises.
"""

import sys
import types
from unittest.mock import patch

import helpers  # provided via sys.path by run_tests.py

assert_raises = helpers.assert_raises

# ---------------------------------------------------------------------------
# Bootstrap: load managers/deploy_manager.py with its heavier dependencies
# (ProvisioningManager, FirmwareFactory, NetworkScanner, DatabaseManager,
# DeviceRepository, Initializer) stubbed out, since this test only exercises
# the module-level concurrency lock, not the actual deploy/scan logic.
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()

for _name in (
    "custom_components",
    "custom_components.device_manager",
    "custom_components.device_manager.managers",
    "custom_components.device_manager.persistence",
    "custom_components.device_manager.firmware",
    "custom_components.device_manager.firmware.base",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_provision_manager_stub = types.ModuleType("custom_components.device_manager.managers.provision_manager")
_provision_manager_stub.ProvisioningManager = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.managers.provision_manager"] = _provision_manager_stub

_factory_stub = types.ModuleType("custom_components.device_manager.firmware.base.firmware_factory")
_factory_stub.FirmwareFactory = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.firmware.base.firmware_factory"] = _factory_stub

_scanner_stub = types.ModuleType("custom_components.device_manager.managers.network_scanner")
_scanner_stub.NetworkScanner = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.managers.network_scanner"] = _scanner_stub

_config_stub = types.ModuleType("custom_components.device_manager.firmware.base.config")
_config_stub.Initializer = object  # type: ignore[attr-defined]
_config_stub.get_config = lambda key, default='': default  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.firmware.base.config"] = _config_stub

_db_manager_stub = types.ModuleType("custom_components.device_manager.persistence.database_manager")
_db_manager_stub.DatabaseManager = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.persistence.database_manager"] = _db_manager_stub

_repos_stub = types.ModuleType("custom_components.device_manager.persistence.repositories")
_repos_stub.DeviceRepository = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.persistence.repositories"] = _repos_stub

# Module under test.
_deploy_module = helpers.load_module(
    "managers/deploy_manager.py",
    package="custom_components.device_manager.managers",
    module_name="deploy_module",
)

DeployManager = _deploy_module.DeployManager
DeployInProgressError = _deploy_module.DeployInProgressError
_DEPLOY_LOCK = DeployManager._DEPLOY_LOCK


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_deploy_raises_when_already_in_progress():
    """A second deploy() call while one is running raises DeployInProgressError."""
    assert _DEPLOY_LOCK.acquire(blocking=False), "test setup: lock should be free"
    try:
        with assert_raises(DeployInProgressError):
            DeployManager("/tmp/dm-test.sqlite").deploy()
    finally:
        _DEPLOY_LOCK.release()


def test_scan_raises_when_deploy_in_progress():
    """scan() shares deploy()'s lock: rejected while a deploy is running."""
    assert _DEPLOY_LOCK.acquire(blocking=False), "test setup: lock should be free"
    try:
        with assert_raises(DeployInProgressError):
            DeployManager("/tmp/dm-test.sqlite").scan()
    finally:
        _DEPLOY_LOCK.release()


def test_deploy_releases_lock_on_success():
    """deploy() releases the lock after a successful run and forwards args."""
    with patch.object(DeployManager, "_deploy_impl") as mock_impl:
        DeployManager("/tmp/dm-test.sqlite").deploy(firmware_types=["Tasmota"])

    mock_impl.assert_called_once_with(["Tasmota"], None)
    assert not _DEPLOY_LOCK.locked(), "lock must be released after a successful deploy"


def test_deploy_releases_lock_even_if_impl_raises():
    """deploy() releases the lock even if the underlying implementation raises."""
    with patch.object(DeployManager, "_deploy_impl", side_effect=RuntimeError("boom")):
        with assert_raises(RuntimeError, match="boom"):
            DeployManager("/tmp/dm-test.sqlite").deploy()

    assert not _DEPLOY_LOCK.locked(), "lock must be released even after a failed deploy"


def test_scan_releases_lock_on_success():
    """scan() releases the lock after a successful run and returns _scan_impl's result."""
    with patch.object(DeployManager, "_scan_impl", return_value={"total": 0}) as mock_impl:
        result = DeployManager("/tmp/dm-test.sqlite").scan()

    mock_impl.assert_called_once_with()
    assert result == {"total": 0}
    assert not _DEPLOY_LOCK.locked(), "lock must be released after a successful scan"


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "🔒 Deploy/Scan Concurrency Lock Tests"
TEST_SUITE = [
    ("deploy() raises when already in progress", test_deploy_raises_when_already_in_progress),
    ("scan() raises when deploy in progress", test_scan_raises_when_deploy_in_progress),
    ("deploy() releases lock on success", test_deploy_releases_lock_on_success),
    ("deploy() releases lock even if impl raises", test_deploy_releases_lock_even_if_impl_raises),
    ("scan() releases lock on success", test_scan_releases_lock_on_success),
]
