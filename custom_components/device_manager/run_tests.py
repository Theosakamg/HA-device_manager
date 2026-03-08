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


def load_test_module(module_name: str):
    """Load a test module by file path to avoid package imports."""
    test_path = Path(__file__).resolve().parent / 'tests' / f'{module_name}.py'
    spec = importlib.util.spec_from_file_location(module_name, str(test_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load test modules
test_device = load_test_module('test_device')
test_import = load_test_module('test_import')
test_dm_device_computed = load_test_module('test_dm_device_computed')

# Import test functions from test_device
test_compute_derived_fields_from_fixtures = (
    test_device.test_compute_derived_fields_from_fixtures
)

# Import test functions from test_import
test_csv_import_to_db = test_import.test_csv_import_to_db

# Import test functions from test_dm_device_computed
test_mqtt_topic_format = (
    test_dm_device_computed.test_mqtt_topic_format
)
test_mqtt_topic_returns_none_when_missing_building = (
    test_dm_device_computed.test_mqtt_topic_returns_none_when_missing_building
)
test_mqtt_topic_structure = (
    test_dm_device_computed.test_mqtt_topic_structure
)
test_hostname_format = test_dm_device_computed.test_hostname_format
test_hostname_returns_none_when_missing_building = (
    test_dm_device_computed.test_hostname_returns_none_when_missing_building
)
test_fqdn_format = test_dm_device_computed.test_fqdn_format
test_fqdn_custom_suffix = test_dm_device_computed.test_fqdn_custom_suffix
test_display_name_full = test_dm_device_computed.test_display_name_full
test_display_name_fallback_to_mac = (
    test_dm_device_computed.test_display_name_fallback_to_mac
)
test_link_with_full_ip = test_dm_device_computed.test_link_with_full_ip
test_link_with_numeric_ip = test_dm_device_computed.test_link_with_numeric_ip
test_to_camel_dict_full_includes_computed = (
    test_dm_device_computed.test_to_camel_dict_full_includes_computed
)


def run():
    """Run all tests and display results."""
    failures = 0
    total_tests = 0

    print("=" * 70)
    print(" HA Device Manager - Test Suite")
    print("=" * 70)

    # Legacy DmDevice tests with fixtures
    print("\n📦 Device Model Tests (Legacy Fixtures)")
    device_tests = [
        ("compute derived fields from fixtures", test_compute_derived_fields_from_fixtures),
    ]

    for test_name, test_func in device_tests:
        total_tests += 1
        try:
            test_func()
            print(f'  ✓ {test_name}')
        except AssertionError as e:
            failures += 1
            print(f'  ✗ {test_name}')
            print(f'    {e}')
        except Exception as e:
            failures += 1
            print(f'  ✗ {test_name} (ERROR)')
            print(f'    {type(e).__name__}: {e}')

    # CSV Import tests
    print("\n📥 CSV Import Tests")
    import_tests = [
        ("csv import to database", test_csv_import_to_db),
    ]

    for test_name, test_func in import_tests:
        total_tests += 1
        try:
            test_func()
            print(f'  ✓ {test_name}')
        except AssertionError as e:
            failures += 1
            print(f'  ✗ {test_name}')
            print(f'    {e}')
        except Exception as e:
            failures += 1
            print(f'  ✗ {test_name} (ERROR)')
            print(f'    {type(e).__name__}: {e}')

    # DmDevice computed methods tests
    print("\n🔧 DmDevice Computed Methods Tests")
    computed_tests = [
        ("mqtt_topic format & lowercase", test_mqtt_topic_format),
        ("mqtt_topic None when missing building", test_mqtt_topic_returns_none_when_missing_building),
        ("mqtt_topic structure (5 segments)", test_mqtt_topic_structure),
        ("hostname format & lowercase", test_hostname_format),
        ("hostname None when missing building", test_hostname_returns_none_when_missing_building),
        ("fqdn format & lowercase", test_fqdn_format),
        ("fqdn custom suffix", test_fqdn_custom_suffix),
        ("display_name full hierarchy", test_display_name_full),
        ("display_name fallback to MAC", test_display_name_fallback_to_mac),
        ("link with full IP", test_link_with_full_ip),
        ("link with numeric IP", test_link_with_numeric_ip),
        ("to_camel_dict_full includes computed fields", test_to_camel_dict_full_includes_computed),
    ]

    for test_name, test_func in computed_tests:
        total_tests += 1
        try:
            test_func()
            print(f'  ✓ {test_name}')
        except AssertionError as e:
            failures += 1
            print(f'  ✗ {test_name}')
            print(f'    {e}')
        except Exception as e:
            failures += 1
            print(f'  ✗ {test_name} (ERROR)')
            print(f'    {type(e).__name__}: {e}')

    # Summary
    print("\n" + "=" * 70)
    if failures:
        print(f"❌ {failures}/{total_tests} test(s) failed")
        sys.exit(1)
    print(f'✅ All {total_tests} tests passed')
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run()
