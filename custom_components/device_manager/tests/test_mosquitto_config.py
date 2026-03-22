"""Tests for the Mosquitto config generation logic.

These tests import ``generate_mosquitto_files`` directly from the
production controller so they exercise the real code path instead of
a local copy.
"""

import io
import sys
import types
import zipfile

import helpers  # provided via sys.path by run_tests.py

# ---------------------------------------------------------------------------
# Bootstrap: load maintenance_controller without importing the full HA package
# ---------------------------------------------------------------------------

helpers.stub_ha_modules()
helpers.stub_aiohttp()

_base_stub = types.ModuleType("custom_components.device_manager.controllers.base")
_base_stub.BaseView = object  # type: ignore[attr-defined]
_base_stub.rate_limit = lambda **_kw: (lambda f: f)  # type: ignore[attr-defined]
_base_stub.csrf_protect = lambda f: f  # type: ignore[attr-defined]
_base_stub.get_repos = lambda r: {}  # type: ignore[attr-defined]
_base_stub.emit_activity_log = lambda *a, **kw: None  # type: ignore[attr-defined]

_const_stub = types.ModuleType("custom_components.device_manager.const")
_const_stub.DOMAIN = "device_manager"  # type: ignore[attr-defined]
_const_stub.DATA_KEY_DB = "db"  # type: ignore[attr-defined]
_const_stub.SETTING_MQTT_PREFIX = "mqtt_topic_prefix"  # type: ignore[attr-defined]
_const_stub.SETTING_BUS_USERNAME = "bus_username"  # type: ignore[attr-defined]
_const_stub.SETTING_BUS_PASSWORD = "bus_password"  # type: ignore[attr-defined]

for _mod_name, _mod in [
    ("custom_components", types.ModuleType("custom_components")),
    ("custom_components.device_manager", types.ModuleType("custom_components.device_manager")),
    ("custom_components.device_manager.controllers", types.ModuleType("custom_components.device_manager.controllers")),
    ("custom_components.device_manager.controllers.base", _base_stub),
    ("custom_components.device_manager.const", _const_stub),
]:
    sys.modules.setdefault(_mod_name, _mod)  # type: ignore[arg-type]

_ctrl_module = helpers.load_module(
    "controllers/maintenance_controller.py",
    package="custom_components.device_manager.controllers",
    module_name="maintenance_controller",
)

# The real production function under test
generate_mosquitto_files = _ctrl_module.generate_mosquitto_files  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_passwd_contains_room_credentials():
    """Rooms with login+password appear in the passwd file."""
    data = [
        ("home", "ground", "living_user", "s3cr3t", "living"),
        ("home", "ground", "kitchen_user", "p@ss", "kitchen"),
    ]
    passwd, _, _ = generate_mosquitto_files(data, "myprefix", "admin", "adminpass")
    assert "living_user:s3cr3t" in passwd
    assert "kitchen_user:p@ss" in passwd


def test_passwd_contains_admin():
    """Admin credentials appear in passwd when both user and password are set."""
    passwd, _, _ = generate_mosquitto_files([], "home", "admin", "secret123")
    assert "admin:secret123" in passwd


def test_acl_room_topic_format():
    """ACL entry for a room uses the correct hierarchical topic."""
    data = [("bldg", "floor1", "user1", "pw", "room1")]
    _, acl, _ = generate_mosquitto_files(data, "home", "admin", "")
    assert "user user1" in acl
    assert "topic readwrite home/bldg/floor1/room1/#" in acl


def test_acl_admin_full_access():
    """Admin user gets 'topic readwrite #' when password is set."""
    _, acl, _ = generate_mosquitto_files([], "home", "admin", "pw")
    assert "user admin\ntopic readwrite #" in acl


def test_room_without_credentials_skipped():
    """Rooms without login or password are not included."""
    data = [
        ("bldg", "f1", "", "pw", "room1"),    # no login
        ("bldg", "f1", "user2", "", "room2"),  # no password
        ("bldg", "f1", None, None, "room3"),   # None
    ]
    passwd, acl, _ = generate_mosquitto_files(data, "home", "admin", "")
    assert "room1" not in passwd
    assert "room2" not in passwd
    assert "room3" not in passwd
    assert "user2" not in acl


def test_mosquitto_conf_references_correct_paths():
    """mosquitto.conf references /mosquitto/config/passwd and acl."""
    _, _, conf = generate_mosquitto_files([], "home", "admin", "")
    assert "password_file /mosquitto/config/passwd" in conf
    assert "acl_file /mosquitto/config/acl" in conf


def test_zip_contains_three_files():
    """The ZIP archive must contain exactly passwd, acl, mosquitto.conf."""
    data = [("bldg", "f1", "user1", "pw1", "room1")]
    passwd, acl, conf = generate_mosquitto_files(data, "home", "admin", "adminpw")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("passwd", passwd)
        zf.writestr("acl", acl)
        zf.writestr("mosquitto.conf", conf)
    buf.seek(0)

    with zipfile.ZipFile(buf) as zf:
        names = set(zf.namelist())
    assert names == {"passwd", "acl", "mosquitto.conf"}


def test_mqtt_prefix_leading_slash_stripped():
    """Leading/trailing slashes in mqtt_prefix are stripped."""
    data = [("b", "f", "u", "p", "r")]
    _, acl, _ = generate_mosquitto_files(data, "/home/", "admin", "")
    assert "topic readwrite home/b/f/r/#" in acl


def test_empty_hierarchy_only_admin():
    """With no rooms, only admin appears in passwd when password is set."""
    passwd, acl, _ = generate_mosquitto_files([], "home", "superadmin", "securepass")
    lines = [line for line in passwd.split("\n") if line]
    assert lines == ["superadmin:securepass"]
    assert "user superadmin\ntopic readwrite #" in acl


def test_no_admin_password_skips_admin_entry():
    """Admin entry is skipped when password is empty (security: no empty-pass admin)."""
    data = [("b", "f", "u", "p", "r")]
    passwd, acl, _ = generate_mosquitto_files(data, "home", "admin", "")
    lines = [line for line in passwd.split("\n") if line]
    assert lines == ["u:p"]
    assert "topic readwrite #" not in acl


def test_room_with_none_password_skipped():
    """Rooms whose password is None (decryption failure) are skipped."""
    data = [
        ("b", "f", "user_ok", "pass_ok", "room_ok"),
        ("b", "f", "user_bad", None, "room_bad"),  # decryption failure
    ]
    passwd, acl, _ = generate_mosquitto_files(data, "home", "admin", "adminpw")
    assert "user_ok:pass_ok" in passwd
    assert "user_bad" not in passwd
    assert "room_bad" not in acl


# ---------------------------------------------------------------------------
# Test suite registration
# ---------------------------------------------------------------------------

SUITE_LABEL = "📡 Mosquitto Config Generation Tests"
TEST_SUITE = [
    ("passwd contains room credentials", test_passwd_contains_room_credentials),
    ("passwd contains admin", test_passwd_contains_admin),
    ("acl room topic format", test_acl_room_topic_format),
    ("acl admin full access", test_acl_admin_full_access),
    ("room without credentials skipped", test_room_without_credentials_skipped),
    ("mosquitto.conf references correct paths", test_mosquitto_conf_references_correct_paths),
    ("zip contains three files", test_zip_contains_three_files),
    ("mqtt prefix leading slash stripped", test_mqtt_prefix_leading_slash_stripped),
    ("empty hierarchy only admin", test_empty_hierarchy_only_admin),
    ("no admin password skips admin entry", test_no_admin_password_skips_admin_entry),
    ("room with None password skipped", test_room_with_none_password_skipped),
]
