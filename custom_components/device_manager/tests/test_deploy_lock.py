"""Tests for the deploy()/scan() concurrency lock in provisioning/deploy.py.

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
# Bootstrap: load provisioning/deploy.py with its heavier dependencies
# (ProvisioningManager, FirmwareFactory, NetworkScanner, DatabaseManager,
# DeviceRepository, Initializer) stubbed out, since this test only exercises
# the module-level concurrency lock, not the actual deploy/scan logic.
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()

for _name in (
    "custom_components",
    "custom_components.device_manager",
    "custom_components.device_manager.provisioning",
    "custom_components.device_manager.provisioning.core",
    "custom_components.device_manager.services",
):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_core_manager_stub = types.ModuleType("custom_components.device_manager.provisioning.core.manager")
_core_manager_stub.ProvisioningManager = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.provisioning.core.manager"] = _core_manager_stub

_core_factory_stub = types.ModuleType("custom_components.device_manager.provisioning.core.firmware_factory")
_core_factory_stub.FirmwareFactory = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.provisioning.core.firmware_factory"] = _core_factory_stub

_core_scanner_stub = types.ModuleType("custom_components.device_manager.provisioning.core.scanner")
_core_scanner_stub.NetworkScanner = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.provisioning.core.scanner"] = _core_scanner_stub

_prov_utility_stub = types.ModuleType("custom_components.device_manager.provisioning.utility")
_prov_utility_stub.Initializer = object  # type: ignore[attr-defined]
_prov_utility_stub.get_config = lambda key, default='': default  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.provisioning.utility"] = _prov_utility_stub

_db_manager_stub = types.ModuleType("custom_components.device_manager.services.database_manager")
_db_manager_stub.DatabaseManager = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.services.database_manager"] = _db_manager_stub

_repos_stub = types.ModuleType("custom_components.device_manager.repositories")
_repos_stub.DeviceRepository = object  # type: ignore[attr-defined]
sys.modules["custom_components.device_manager.repositories"] = _repos_stub

# Module under test.
_deploy_module = helpers.load_module(
    "provisioning/deploy.py",
    package="custom_components.device_manager.provisioning",
    module_name="deploy_module",
)

deploy = _deploy_module.deploy
scan = _deploy_module.scan
DeployInProgressError = _deploy_module.DeployInProgressError
_DEPLOY_LOCK = _deploy_module._DEPLOY_LOCK


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_deploy_raises_when_already_in_progress():
    """A second deploy() call while one is running raises DeployInProgressError."""
    assert _DEPLOY_LOCK.acquire(blocking=False), "test setup: lock should be free"
    try:
        with assert_raises(DeployInProgressError):
            deploy(db_path="/tmp/dm-test.sqlite")
    finally:
        _DEPLOY_LOCK.release()


def test_scan_raises_when_deploy_in_progress():
    """scan() shares deploy()'s lock: rejected while a deploy is running."""
    assert _DEPLOY_LOCK.acquire(blocking=False), "test setup: lock should be free"
    try:
        with assert_raises(DeployInProgressError):
            scan(db_path="/tmp/dm-test.sqlite")
    finally:
        _DEPLOY_LOCK.release()


def test_deploy_releases_lock_on_success():
    """deploy() releases the lock after a successful run and forwards args."""
    with patch.object(_deploy_module, "_deploy_impl") as mock_impl:
        deploy(db_path="/tmp/dm-test.sqlite", firmware_types=["Tasmota"])

    mock_impl.assert_called_once_with("/tmp/dm-test.sqlite", ["Tasmota"], None)
    assert not _DEPLOY_LOCK.locked(), "lock must be released after a successful deploy"


def test_deploy_releases_lock_even_if_impl_raises():
    """deploy() releases the lock even if the underlying implementation raises."""
    with patch.object(_deploy_module, "_deploy_impl", side_effect=RuntimeError("boom")):
        with assert_raises(RuntimeError, match="boom"):
            deploy(db_path="/tmp/dm-test.sqlite")

    assert not _DEPLOY_LOCK.locked(), "lock must be released even after a failed deploy"


def test_scan_releases_lock_on_success():
    """scan() releases the lock after a successful run and returns _scan_impl's result."""
    with patch.object(_deploy_module, "_scan_impl", return_value={"total": 0}) as mock_impl:
        result = scan(db_path="/tmp/dm-test.sqlite")

    mock_impl.assert_called_once_with("/tmp/dm-test.sqlite")
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
