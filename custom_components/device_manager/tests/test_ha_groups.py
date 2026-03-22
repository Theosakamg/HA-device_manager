"""Tests for HA groups controller helper functions.

Validates entity ID generation, slugification, domain mapping and group naming
without requiring a live Home Assistant instance.
"""

import sys
import types

import helpers  # provided via sys.path by run_tests.py

# ---------------------------------------------------------------------------
# Minimal stub setup — load only the controller module under test
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()
helpers.stub_aiohttp()

class _FakeHAView:
    requires_auth = True


ha_http = sys.modules["homeassistant.components.http"]
ha_http.HomeAssistantView = _FakeHAView  # type: ignore[attr-defined]

# Stub the base controller module
base_ctrl_stub = types.ModuleType(
    "custom_components.device_manager.controllers.base"
)

class _BaseView(_FakeHAView):
    pass

base_ctrl_stub.BaseView = _BaseView  # type: ignore[attr-defined]
base_ctrl_stub.get_repos = lambda req: {}  # type: ignore[attr-defined]
base_ctrl_stub.csrf_protect = lambda f: f  # type: ignore[attr-defined]

async def _noop_emit(*args, **kwargs):
    pass


base_ctrl_stub.emit_activity_log = _noop_emit  # type: ignore[attr-defined]

sys.modules["custom_components"] = types.ModuleType("custom_components")
sys.modules["custom_components.device_manager"] = types.ModuleType(
    "custom_components.device_manager"
)
sys.modules[
    "custom_components.device_manager.controllers"
] = types.ModuleType("custom_components.device_manager.controllers")
sys.modules[
    "custom_components.device_manager.controllers.base"
] = base_ctrl_stub

# Now load the actual module under test
ctrl_module = helpers.load_module(
    "controllers/ha_groups_controller.py",
    package="custom_components.device_manager.controllers",
    module_name="ha_groups_controller",
)

# Grab helpers
_slugify = ctrl_module._slugify
_ha_domain = ctrl_module._ha_domain
_plural = ctrl_module._plural
_device_entity_id = ctrl_module._device_entity_id
_room_group_object_id = lambda b, f, r, p: ctrl_module._group_object_id(b, f, r, p)
_floor_group_object_id = lambda b, f, p: ctrl_module._group_object_id(b, f, p)
_building_group_object_id = lambda b, p: ctrl_module._group_object_id(b, p)


# ---------------------------------------------------------------------------
# Tests as plain functions for run_tests.py compatibility
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert _slugify("Home") == "home"

def test_slugify_spaces():
    assert _slugify("Floor 0") == "floor_0"

def test_slugify_special_chars():
    assert _slugify("Bed-Room!") == "bed_room"

def test_slugify_multiple_separators():
    assert _slugify("A  B--C") == "a_b_c"

def test_ha_domain_light():
    assert _ha_domain("light") == "light"

def test_ha_domain_shutter():
    assert _ha_domain("shutter") == "cover"

def test_ha_domain_heater():
    assert _ha_domain("heater") == "climate"

def test_ha_domain_tv():
    assert _ha_domain("tv") == "media_player"

def test_ha_domain_button():
    assert _ha_domain("button") == "binary_sensor"

def test_ha_domain_energy():
    assert _ha_domain("energy") == "sensor"

def test_ha_domain_unknown_defaults_to_switch():
    assert _ha_domain("unknown_function") == "switch"

def test_ha_domain_case_insensitive():
    assert _ha_domain("Light") == "light"
    assert _ha_domain("SHUTTER") == "cover"

def test_plural_light():
    assert _plural("light") == "lights"

def test_plural_shutter():
    assert _plural("shutter") == "shutters"

def test_plural_unknown_appends_s():
    assert _plural("widget") == "widgets"

def test_device_entity_id_standard():
    eid = _device_entity_id("light", "home", "lvl0", "bed", "light", "door")
    assert eid == "light.home_lvl0_bed_light_door"

def test_device_entity_id_matches_hostname_pattern():
    # Canonical example from the issue description
    eid = _device_entity_id("light", "home", "lvl0", "bed", "light", "door")
    assert eid == "light.home_lvl0_bed_light_door"

def test_device_entity_id_uppercase_building():
    eid = _device_entity_id("cover", "Home", "L0", "Living Room", "shutter", "main")
    assert eid == "cover.home_l0_living_room_shutter_main"

def test_device_entity_id_empty_position_omitted():
    eid = _device_entity_id("switch", "home", "l0", "kit", "ir", "")
    assert eid == "switch.home_l0_kit_ir"

def test_room_group_entity_id():
    obj = _room_group_object_id("home", "lvl0", "kitchen", "lights")
    assert obj == "home_lvl0_kitchen_lights"
    assert f"group.{obj}" == "group.home_lvl0_kitchen_lights"

def test_floor_group_entity_id():
    obj = _floor_group_object_id("home", "lvl1", "shutters")
    assert obj == "home_lvl1_shutters"
    assert f"group.{obj}" == "group.home_lvl1_shutters"

def test_building_group_entity_id():
    obj = _building_group_object_id("home", "lights")
    assert obj == "home_lights"
    assert f"group.{obj}" == "group.home_lights"

def test_room_group_special_chars():
    obj = _room_group_object_id("Home", "Floor 0", "Living Room", "lights")
    assert obj == "home_floor_0_living_room_lights"

def test_floor_group_has_building_prefix():
    obj = _floor_group_object_id("home", "lvl0", "lights")
    assert obj.startswith("home_")

def test_building_group_has_building_prefix():
    obj = _building_group_object_id("myHome", "shutters")
    assert obj.startswith("my")


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "🏠 HA Groups Controller Tests"
TEST_SUITE = [
    ("slugify basic", test_slugify_basic),
    ("slugify spaces", test_slugify_spaces),
    ("slugify special chars", test_slugify_special_chars),
    ("slugify multiple separators", test_slugify_multiple_separators),
    ("ha_domain light", test_ha_domain_light),
    ("ha_domain shutter → cover", test_ha_domain_shutter),
    ("ha_domain heater → climate", test_ha_domain_heater),
    ("ha_domain tv → media_player", test_ha_domain_tv),
    ("ha_domain button → binary_sensor", test_ha_domain_button),
    ("ha_domain energy → sensor", test_ha_domain_energy),
    ("ha_domain unknown → switch", test_ha_domain_unknown_defaults_to_switch),
    ("ha_domain case insensitive", test_ha_domain_case_insensitive),
    ("plural light", test_plural_light),
    ("plural shutter", test_plural_shutter),
    ("plural unknown appends s", test_plural_unknown_appends_s),
    ("device entity_id standard", test_device_entity_id_standard),
    ("device entity_id matches hostname pattern", test_device_entity_id_matches_hostname_pattern),
    ("device entity_id uppercase building", test_device_entity_id_uppercase_building),
    ("device entity_id empty position omitted", test_device_entity_id_empty_position_omitted),
    ("room group entity_id", test_room_group_entity_id),
    ("floor group entity_id", test_floor_group_entity_id),
    ("building group entity_id", test_building_group_entity_id),
    ("room group special chars", test_room_group_special_chars),
    ("floor group has building prefix", test_floor_group_has_building_prefix),
    ("building group has building prefix", test_building_group_has_building_prefix),
]
