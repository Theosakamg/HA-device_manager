"""Tests for :class:`HaSyncResultDto` boundary serialization.

Loads the DTO module directly by file path (it has no package-relative
imports) so the test needs no Home Assistant stubs.
"""

import importlib.util
from pathlib import Path

_dto_path = Path(__file__).resolve().parent.parent / "dto" / "ha_sync_result_dto.py"
_spec = importlib.util.spec_from_file_location("ha_sync_result_dto", str(_dto_path))
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
HaSyncResultDto = _module.HaSyncResultDto


def test_total_is_derived_from_item_count():
    """total is computed from the item list length, not passed in."""
    items = [{"floorId": "a"}, {"floorId": "b"}, {"floorId": "c"}]
    payload = HaSyncResultDto("floors", items).to_api_dict()
    assert payload["total"] == 3
    assert payload["floors"] == items


def test_collection_key_is_parameterized():
    """The collection key names the item list (floors / rooms / groups)."""
    assert set(HaSyncResultDto("rooms", []).to_api_dict().keys()) == {"rooms", "total"}
    assert set(HaSyncResultDto("groups", []).to_api_dict().keys()) == {"groups", "total"}


def test_items_pass_through_unchanged():
    """Already-camelCase item dicts are emitted as-is."""
    items = [{"areaId": "x", "name": "Kitchen", "floorId": "f1"}]
    payload = HaSyncResultDto("rooms", items).to_api_dict()
    assert payload["rooms"][0] == {"areaId": "x", "name": "Kitchen", "floorId": "f1"}


def test_empty_result_has_zero_total():
    """An empty sync yields an empty list and total 0."""
    payload = HaSyncResultDto("groups").to_api_dict()
    assert payload == {"groups": [], "total": 0}


SUITE_LABEL = "HaSyncResultDto (dto/ha_sync_result_dto.py)"
TEST_SUITE = [
    ("total derived from item count", test_total_is_derived_from_item_count),
    ("collection key is parameterized", test_collection_key_is_parameterized),
    ("items pass through unchanged", test_items_pass_through_unchanged),
    ("empty result has zero total", test_empty_result_has_zero_total),
]
