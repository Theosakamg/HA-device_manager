#!/usr/bin/env python3
"""Run all tests without requiring Home Assistant installation.

This loads test modules directly via importlib to avoid importing
the package __init__.py which requires homeassistant.

Usage:
    python3 custom_components/device_manager/run_tests.py
"""
import sys
from pathlib import Path
import importlib.util

# Expose tests/ so test modules can do: import helpers
_tests_dir = Path(__file__).resolve().parent / "tests"
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))


def _load_test_module(module_name: str):
    """Load a test module by file path to avoid package imports."""
    test_path = _tests_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, str(test_path))
    assert spec is not None, f"Cannot find spec for {module_name}"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, f"Spec has no loader for {module_name}"
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_TEST_MODULES = [
    "test_device",
    "test_import",
    "test_dm_device_computed",
    "test_identifier_validation",
    "test_ha_groups",
    "test_ha_floors",
    "test_ha_rooms",
    "test_crud_fk_diff",
    "test_mosquitto_config",
    "test_init_unload",
    "test_network_scanner",
]


def run() -> None:
    """Run all tests and display results."""
    failures = 0
    total_tests = 0

    print("=" * 70)
    print(" HA Device Manager - Test Suite")
    print("=" * 70)

    for module_name in _TEST_MODULES:
        mod = _load_test_module(module_name)
        suite_label: str = getattr(mod, "SUITE_LABEL", module_name)
        suite: list = getattr(mod, "TEST_SUITE", [])

        print(f"\n{suite_label}")
        for test_name, test_func in suite:
            total_tests += 1
            try:
                test_func()
                print(f"  ✓ {test_name}")
            except AssertionError as e:
                failures += 1
                print(f"  ✗ {test_name}")
                print(f"    {e}")
            except Exception as e:
                failures += 1
                print(f"  ✗ {test_name} (ERROR)")
                print(f"    {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    if failures:
        print(f"❌ {failures}/{total_tests} test(s) failed")
        sys.exit(1)
    print(f"✅ All {total_tests} tests passed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run()
