"""Tests for DmDevice model using legacy fixtures.

These tests verify that the new DmDevice model correctly computes
the same derived fields as the legacy Device class.
"""

import json
from pathlib import Path
import importlib.util
import sys
import types

# Load modules by file path to avoid importing package __init__
# (which requires homeassistant)
base_dir = Path(__file__).resolve().parents[1]

# Load case_convert utility
case_convert_path = base_dir / 'utils' / 'case_convert.py'
spec = importlib.util.spec_from_file_location('case_convert', str(case_convert_path))
assert spec is not None and spec.loader is not None, "Cannot load case_convert"
case_convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case_convert)  # type: ignore[union-attr]

# Create mock parent package modules for relative imports
custom_components_module = types.ModuleType('custom_components')
device_manager_module = types.ModuleType('device_manager')
utils_module = types.ModuleType('utils')
utils_module.case_convert = case_convert  # type: ignore[attr-defined]

sys.modules['custom_components'] = custom_components_module
sys.modules['custom_components.device_manager'] = device_manager_module
sys.modules['custom_components.device_manager.utils'] = utils_module
sys.modules['custom_components.device_manager.utils.case_convert'] = case_convert

# Load base module
base_path = base_dir / 'models' / 'base.py'
spec = importlib.util.spec_from_file_location('base_module', str(base_path))
assert spec is not None and spec.loader is not None, "Cannot load base model"
base_module = importlib.util.module_from_spec(spec)
base_module.__package__ = 'custom_components.device_manager.models'
spec.loader.exec_module(base_module)  # type: ignore[union-attr]

# Load device module
device_path = base_dir / 'models' / 'device.py'
spec = importlib.util.spec_from_file_location('device_module', str(device_path))
assert spec is not None and spec.loader is not None, "Cannot load device model"
device_module = importlib.util.module_from_spec(spec)
device_module.__package__ = 'custom_components.device_manager.models'
sys.modules['custom_components.device_manager.models.base'] = base_module
spec.loader.exec_module(device_module)  # type: ignore[union-attr]

DmDevice = device_module.DmDevice
DeviceRoomRef = device_module.DeviceRoomRef
DeviceFloorRef = device_module.DeviceFloorRef
DeviceBuildingRef = device_module.DeviceBuildingRef
DeviceLinkedRefs = device_module.DeviceLinkedRefs

FIXTURES = Path(__file__).parent / "fixtures" / "devices.json"


def load_fixtures():
    """Load test fixtures from JSON file."""
    return json.loads(FIXTURES.read_text(encoding='utf8'))


def test_compute_derived_fields_from_fixtures():
    """Test that DmDevice computed properties match legacy expectations.

    Note: The new DmDevice model has a different format than the legacy Device:
    - Legacy: home/l0/office/button/lunch
    - New: building_slug/l0/office/button/lunch

    This test adapts expectations to the new format.
    """
    fixtures = load_fixtures()
    for f in fixtures:
        # Extract fixture data
        mac = f.get('mac')
        ip = f.get('ip')
        room_slug = f.get('room_slug', '')
        position_slug = f.get('position_slug', '')
        function_name = f.get('function', '')

        # Create DmDevice with transient data
        device = DmDevice(
            mac=mac,
            ip=str(ip) if ip is not None else None,
            position_slug=position_slug,
            position_name=f.get('position_fr', '') or position_slug.capitalize(),
            enabled=f.get('state') == 'Enable',
            _room=DeviceRoomRef(slug=room_slug),
            _floor=DeviceFloorRef(slug='l0', number=0),
            _building=DeviceBuildingRef(slug='main'),
            _refs=DeviceLinkedRefs(
                function_name=function_name,
                model_name=f.get('model', ''),
                firmware_name=f.get('firmware', ''),
            ),
        )

        # Get expected values from fixture
        exp = f.get('expected', {})

        # Test hostname (format changed: removed building from legacy format)
        if exp.get('hostname'):
            hostname = device.hostname()
            # Legacy: l0_office_button_lunch
            # New: main_l0_office_button_lunch
            expected_hostname = f"main_{exp['hostname']}"
            assert hostname == expected_hostname, (
                f"Hostname mismatch for {mac}: "
                f"expected {expected_hostname}, got {hostname}"
            )

        # Test mqtt_topic (format changed: building instead of 'home')
        if exp.get('mqtt_topic'):
            mqtt_topic = device.mqtt_topic()
            # Legacy: home/l0/office/button/lunch
            # New: main/l0/office/button/lunch
            expected_mqtt = exp['mqtt_topic'].replace('home/', 'main/')
            assert mqtt_topic == expected_mqtt, (
                f"MQTT topic mismatch for {mac}: "
                f"expected {expected_mqtt}, got {mqtt_topic}"
            )

        # Test link (unchanged)
        if exp.get('link'):
            link = device.link()
            assert link == exp['link'], (
                f"Link mismatch for {mac}: "
                f"expected {exp['link']}, got {link}"
            )

        # Test fqdn (replaces 'dns' in legacy fixtures)
        if exp.get('dns'):
            fqdn = device.fqdn()
            # Legacy: l0_office_button_lunch.domo.local
            # New: main_l0_office_button_lunch.domo.local
            expected_fqdn = f"main_{exp['dns']}"
            assert fqdn == expected_fqdn, (
                f"FQDN mismatch for {mac}: "
                f"expected {expected_fqdn}, got {fqdn}"
            )
