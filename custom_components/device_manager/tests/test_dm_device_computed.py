"""Tests for DmDevice computed methods.

These tests ensure that computed methods (mqtt_topic, hostname, fqdn)
maintain their expected format and always return lowercase values.
"""

import helpers  # provided via sys.path by run_tests.py

# ---------------------------------------------------------------------------
# Bootstrap: load DmDevice model via shared helper
# ---------------------------------------------------------------------------

_m = helpers.load_device_model()
DmDevice = _m.DmDevice
DeviceRoomRef = _m.DeviceRoomRef
DeviceFloorRef = _m.DeviceFloorRef
DeviceBuildingRef = _m.DeviceBuildingRef
DeviceLinkedRefs = _m.DeviceLinkedRefs


def create_test_device(
    mac="AA:BB:CC:DD:EE:FF",
    ip="192.168.0.100",
    position_slug="main",
    room_name="Living Room",
    room_slug="living_room",
    floor_name="Ground Floor",
    floor_slug="l0",
    floor_number=0,
    building_name="Main Building",
    building_slug="main",
    function_name="Light Switch",
):
    """Create a test device with all required transient data."""
    return DmDevice(
        mac=mac,
        ip=ip,
        position_slug=position_slug,
        position_name="Main",
        _room=DeviceRoomRef(name=room_name, slug=room_slug),
        _floor=DeviceFloorRef(
            name=floor_name, slug=floor_slug, number=floor_number
        ),
        _building=DeviceBuildingRef(name=building_name, slug=building_slug),
        _refs=DeviceLinkedRefs(
            function_name=function_name,
            model_name="Test Model",
            firmware_name="Test Firmware",
        ),
    )


def test_mqtt_topic_format():
    """Test MQTT topic follows the correct format and is lowercase."""
    device = create_test_device(
        building_slug="MAIN",
        floor_slug="L1",
        room_slug="BedRoom",
        position_slug="LEFT",
        function_name="Light Switch",
    )
    result = device.mqtt_topic()
    expected = "main/l1/bedroom/light_switch/left"
    assert result == expected, f"Expected: {expected}, got: {result}"
    assert result == result.lower(), "MQTT topic must be lowercase"


def test_mqtt_topic_returns_none_when_missing_building():
    """Test MQTT topic returns None when building_slug is missing."""
    device = DmDevice(
        mac="AA:BB:CC:DD:EE:FF",
        position_slug="main",
        _floor=DeviceFloorRef(slug="L1"),
        _room=DeviceRoomRef(slug="room"),
        _refs=DeviceLinkedRefs(function_name="Light"),
    )
    result = device.mqtt_topic()
    assert result is None, f"Should return None when building_slug is missing, got: {result}"


def test_mqtt_topic_structure():
    """Test MQTT topic has exactly 5 segments."""
    device = create_test_device()
    result = device.mqtt_topic()
    assert result is not None, "mqtt_topic should not be None"
    segments = result.split("/")
    assert len(segments) == 5, f"Expected 5 segments, got {len(segments)}: {result}"


def test_hostname_format():
    """Test hostname follows the correct format, lowercase, and abbreviation mapping."""
    device = create_test_device(
        building_slug="HOUSE",
        floor_slug="L2",
        room_slug="BedRoom",
        position_slug="Main",
        function_name="Button",  # abbreviated: "button" -> "btn"
    )
    result = device.hostname()
    expected = "house_l2_bedroom_btn_main"
    assert result == expected, f"Expected: {expected}, got: {result}"
    assert result == result.lower(), "Hostname must be lowercase"


def test_hostname_returns_none_when_missing_building():
    """Test hostname returns None when building_slug is missing."""
    device = DmDevice(
        mac="AA:BB:CC:DD:EE:FF",
        position_slug="main",
        _floor=DeviceFloorRef(slug="L1"),
        _room=DeviceRoomRef(slug="room"),
        _refs=DeviceLinkedRefs(function_name="Light"),
    )
    result = device.hostname()
    assert result is None, f"Should return None when building_slug is missing, got: {result}"


def test_fqdn_format():
    """Test FQDN follows the correct format and is lowercase."""
    device = create_test_device(
        building_slug="main",
        floor_slug="l0",
        room_slug="kitchen",
        position_slug="center",
        function_name="Relay",
    )
    result = device.fqdn()
    expected = "main_l0_kitchen_relay_center.domo.local"
    assert result == expected, f"Expected: {expected}, got: {result}"
    assert result == result.lower(), "FQDN must be lowercase"


def test_fqdn_custom_suffix():
    """Test FQDN with custom DNS suffix."""
    device = create_test_device()
    result = device.fqdn(dns_suffix="home.lan")
    assert result.endswith(".home.lan"), f"Should end with .home.lan, got: {result}"


def test_display_name_full():
    """Test display_name with all components present."""
    device = create_test_device()
    result = device.display_name()
    expected = "Main Building > Ground Floor > Living Room > Light Switch > Main"
    assert result == expected, f"Expected: {expected}, got: {result}"


def test_display_name_fallback_to_mac():
    """Test display_name fallback to MAC when no hierarchy data."""
    device = DmDevice(mac="AA:BB:CC:DD:EE:FF")
    result = device.display_name()
    assert result == "AA:BB:CC:DD:EE:FF", f"Should fallback to MAC, got: {result}"


def test_link_with_full_ip():
    """Test link generation with full IP address."""
    device = create_test_device(ip="192.168.1.50")
    result = device.link()
    assert result == "http://192.168.1.50", f"Expected: http://192.168.1.50, got: {result}"


def test_link_with_numeric_ip():
    """Test link generation with numeric-only IP (last octet)."""
    device = create_test_device(ip="100")
    result = device.link()
    assert result == "http://192.168.0.100", f"Expected: http://192.168.0.100, got: {result}"


def test_to_camel_dict_full_includes_computed():
    """Test that to_camel_dict_full() includes all computed fields in lowercase."""
    device = create_test_device(
        building_slug="MAIN",
        floor_slug="L1",
        room_slug="ROOM",
        position_slug="POS",
        function_name="Light Switch",
    )
    result = device.to_camel_dict_full()

    assert "link" in result, "Should include 'link'"
    assert "mqttTopic" in result, "Should include 'mqttTopic'"
    assert "hostname" in result, "Should include 'hostname'"
    assert "fqdn" in result, "Should include 'fqdn'"
    assert "displayName" in result, "Should include 'displayName'"

    # Verify lowercase
    mqtt = result.get("mqttTopic")
    hostname = result.get("hostname")
    fqdn = result.get("fqdn")

    if mqtt:
        assert mqtt == mqtt.lower(), f"mqttTopic must be lowercase: {mqtt}"
    if hostname:
        assert hostname == hostname.lower(), f"hostname must be lowercase: {hostname}"
    if fqdn:
        assert fqdn == fqdn.lower(), f"fqdn must be lowercase: {fqdn}"


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "🔧 DmDevice Computed Methods Tests"
TEST_SUITE = [
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
