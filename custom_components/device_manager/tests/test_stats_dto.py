"""Tests for :class:`StatsDto` boundary serialization.

Loads the DTO module directly by file path (it has no package-relative
imports) so the test needs no Home Assistant stubs.
"""

import importlib.util
from pathlib import Path

_dto_path = Path(__file__).resolve().parent.parent / "dto" / "stats_dto.py"
_spec = importlib.util.spec_from_file_location("stats_dto", str(_dto_path))
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
StatsDto = _module.StatsDto


def _sample():
    return StatsDto(
        buildings=1,
        floors=2,
        rooms=3,
        devices=4,
        by_firmware=[{"name": "Tasmota", "count": 4}],
        by_model=[{"name": "Shelly 1", "count": 2}],
        models_count=5,
        firmwares_count=6,
        functions_count=7,
        deployment={"total": 4, "success": 3, "fail": 1},
        deployment_by_firmware=[{"name": "Tasmota", "total": 4, "success": 3, "fail": 1}],
        deployment_by_model=[{"name": "Shelly 1", "total": 2, "success": 2, "fail": 0}],
    )


def test_flat_counters_nested_under_settings_counts():
    """The flat *_count fields are nested under settingsCounts."""
    payload = _sample().to_api_dict()
    assert payload["settingsCounts"] == {"models": 5, "firmwares": 6, "functions": 7}
    assert "models_count" not in payload
    assert "modelsCount" not in payload


def test_top_level_keys_are_camel_case():
    """The assembled payload exposes the expected camelCase top-level keys."""
    payload = _sample().to_api_dict()
    assert set(payload.keys()) == {
        "buildings", "floors", "rooms", "devices",
        "byFirmware", "byModel", "settingsCounts",
        "deployment", "deploymentByFirmware", "deploymentByModel",
    }


def test_lists_pass_through_unchanged():
    """List items keep their single-word keys untouched."""
    payload = _sample().to_api_dict()
    assert payload["byFirmware"] == [{"name": "Tasmota", "count": 4}]
    assert payload["deploymentByModel"] == [
        {"name": "Shelly 1", "total": 2, "success": 2, "fail": 0}
    ]


def test_defaults_produce_empty_shape():
    """A default DTO still yields the full nested shape with zeros/empties."""
    payload = StatsDto().to_api_dict()
    assert payload["settingsCounts"] == {"models": 0, "firmwares": 0, "functions": 0}
    assert payload["deployment"] == {"total": 0, "success": 0, "fail": 0}
    assert payload["byFirmware"] == []
    assert payload["deploymentByModel"] == []


SUITE_LABEL = "StatsDto (dto/stats_dto.py)"
TEST_SUITE = [
    ("flat counters nested under settingsCounts", test_flat_counters_nested_under_settings_counts),
    ("top-level keys are camelCase", test_top_level_keys_are_camel_case),
    ("lists pass through unchanged", test_lists_pass_through_unchanged),
    ("defaults produce full empty shape", test_defaults_produce_empty_shape),
]
