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
    assert spec is not None, f"Cannot find spec for {module_name}"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, f"Spec has no loader for {module_name}"
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# Load test modules
test_device = load_test_module('test_device')
test_import = load_test_module('test_import')
test_dm_device_computed = load_test_module('test_dm_device_computed')
test_identifier_validation = load_test_module('test_identifier_validation')
test_ha_groups = load_test_module('test_ha_groups')
test_ha_floors = load_test_module('test_ha_floors')
test_ha_rooms = load_test_module('test_ha_rooms')

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

# Import test functions from test_identifier_validation
test_mac_colon_uppercase = test_identifier_validation.test_mac_colon_uppercase
test_mac_colon_lowercase = test_identifier_validation.test_mac_colon_lowercase
test_mac_hyphen = test_identifier_validation.test_mac_hyphen
test_mac_compact = test_identifier_validation.test_mac_compact
test_eui64_colon = test_identifier_validation.test_eui64_colon
test_zigbee_eui64_hex_prefix = test_identifier_validation.test_zigbee_eui64_hex_prefix
test_empty_string_rejected = test_identifier_validation.test_empty_string_rejected
test_plain_text_rejected = test_identifier_validation.test_plain_text_rejected
test_non_hex_chars_rejected = test_identifier_validation.test_non_hex_chars_rejected
test_ip_address_rejected = test_identifier_validation.test_ip_address_rejected
test_short_mac_rejected = test_identifier_validation.test_short_mac_rejected
test_short_eui64_rejected = test_identifier_validation.test_short_eui64_rejected
test_eui64_wrong_prefix_rejected = test_identifier_validation.test_eui64_wrong_prefix_rejected


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

    # Identifier validation tests
    print("\n🔒 Identifier Validation Tests")
    identifier_tests = [
        ("MAC colon uppercase", test_mac_colon_uppercase),
        ("MAC colon lowercase", test_mac_colon_lowercase),
        ("MAC hyphen", test_mac_hyphen),
        ("MAC compact", test_mac_compact),
        ("EUI-64 colon", test_eui64_colon),
        ("Zigbee EUI-64 (0x...)", test_zigbee_eui64_hex_prefix),
        ("empty string rejected", test_empty_string_rejected),
        ("plain text rejected", test_plain_text_rejected),
        ("non-hex chars rejected", test_non_hex_chars_rejected),
        ("IP address rejected", test_ip_address_rejected),
        ("short MAC rejected", test_short_mac_rejected),
        ("short EUI-64 rejected", test_short_eui64_rejected),
        ("EUI-64 without 0x rejected", test_eui64_wrong_prefix_rejected),
    ]

    for test_name, test_func in identifier_tests:
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

    # HA Groups tests
    print("\n🏠 HA Groups Controller Tests")
    ha_groups_tests = [
        ("slugify basic", test_ha_groups.test_slugify_basic),
        ("slugify spaces", test_ha_groups.test_slugify_spaces),
        ("slugify special chars", test_ha_groups.test_slugify_special_chars),
        ("slugify multiple separators", test_ha_groups.test_slugify_multiple_separators),
        ("ha_domain light", test_ha_groups.test_ha_domain_light),
        ("ha_domain shutter → cover", test_ha_groups.test_ha_domain_shutter),
        ("ha_domain heater → climate", test_ha_groups.test_ha_domain_heater),
        ("ha_domain tv → media_player", test_ha_groups.test_ha_domain_tv),
        ("ha_domain button → binary_sensor", test_ha_groups.test_ha_domain_button),
        ("ha_domain energy → sensor", test_ha_groups.test_ha_domain_energy),
        ("ha_domain unknown → switch", test_ha_groups.test_ha_domain_unknown_defaults_to_switch),
        ("ha_domain case insensitive", test_ha_groups.test_ha_domain_case_insensitive),
        ("plural light", test_ha_groups.test_plural_light),
        ("plural shutter", test_ha_groups.test_plural_shutter),
        ("plural unknown appends s", test_ha_groups.test_plural_unknown_appends_s),
        ("device entity_id standard", test_ha_groups.test_device_entity_id_standard),
        ("device entity_id matches hostname pattern", test_ha_groups.test_device_entity_id_matches_hostname_pattern),
        ("device entity_id uppercase building", test_ha_groups.test_device_entity_id_uppercase_building),
        ("device entity_id empty position omitted", test_ha_groups.test_device_entity_id_empty_position_omitted),
        ("room group entity_id", test_ha_groups.test_room_group_entity_id),
        ("floor group entity_id", test_ha_groups.test_floor_group_entity_id),
        ("building group entity_id", test_ha_groups.test_building_group_entity_id),
        ("room group special chars", test_ha_groups.test_room_group_special_chars),
        ("floor group has building prefix", test_ha_groups.test_floor_group_has_building_prefix),
        ("building group has building prefix", test_ha_groups.test_building_group_has_building_prefix),
    ]

    for test_name, test_func in ha_groups_tests:
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

    # HA Floors tests
    print("\n🏢 HA Floors Controller Tests")
    ha_floors_tests = [
        ("registry create auto-generates floor_id", test_ha_floors.test_registry_create_auto_generates_id),
        ("registry get_floor_by_name found", test_ha_floors.test_registry_get_floor_by_name_found),
        ("registry get_floor_by_name missing", test_ha_floors.test_registry_get_floor_by_name_missing),
        ("rollback deletes created floors", test_ha_floors.test_rollback_deletes_created_floors),
        ("rollback restores updated floors", test_ha_floors.test_rollback_restores_updated_floors),
        ("rollback is reversed order", test_ha_floors.test_rollback_is_reversed_order),
        ("rollback skips update without original", test_ha_floors.test_rollback_skips_update_without_original),
        ("rollback tolerates registry error", test_ha_floors.test_rollback_tolerates_registry_error),
        ("create entry floor_id is accessible", test_ha_floors.test_create_entry_floor_id_is_accessible),
        ("ha name per building is unique", test_ha_floors.test_ha_name_per_building_is_unique),
        ("level resets per building", test_ha_floors.test_level_resets_per_building),
    ]

    for test_name, test_func in ha_floors_tests:
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

    # HA Rooms tests
    print("\n🚪 HA Rooms Controller Tests")
    ha_rooms_tests = [
        ("registry create auto-generates area id", test_ha_rooms.test_registry_create_auto_generates_id),
        ("registry create with floor_id", test_ha_rooms.test_registry_create_with_floor_id),
        ("registry get_area_by_name missing", test_ha_rooms.test_registry_get_area_by_name_missing),
        ("rollback deletes created areas", test_ha_rooms.test_rollback_deletes_created_areas),
        ("rollback restores updated areas", test_ha_rooms.test_rollback_restores_updated_areas),
        ("rollback is reversed order", test_ha_rooms.test_rollback_is_reversed_order),
        ("rollback skips update without original", test_ha_rooms.test_rollback_skips_update_without_original),
        ("rollback multiple rooms reversed", test_ha_rooms.test_rollback_multiple_rooms_reversed),
        ("compute_area_id basic", test_ha_rooms.test_compute_area_id_basic),
        ("slugify fallback ascii", test_ha_rooms.test_slugify_fallback_ascii),
        ("compute_area_id special chars", test_ha_rooms.test_compute_area_id_special_chars),
        ("registry create then update name keeps id", test_ha_rooms.test_registry_create_then_update_name_keeps_id),
        ("compute_area_id matches registry create id", test_ha_rooms.test_compute_area_id_matches_registry_create_id),
        ("registry get_area by id found", test_ha_rooms.test_registry_get_area_by_id_found),
        ("registry get_area missing", test_ha_rooms.test_registry_get_area_missing),
        ("duplicate name detection", test_ha_rooms.test_duplicate_name_detection),
        ("unique name not marked duplicate", test_ha_rooms.test_unique_name_not_marked_duplicate),
    ]

    for test_name, test_func in ha_rooms_tests:
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
