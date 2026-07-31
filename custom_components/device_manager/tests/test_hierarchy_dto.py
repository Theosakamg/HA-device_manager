"""Tests for :class:`HierarchyDto` / :class:`HierarchyNodeDto` serialization.

Loads the DTO module directly by file path (it has no package-relative
imports) so the test needs no Home Assistant stubs.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_dto_path = Path(__file__).resolve().parent.parent / "dto" / "hierarchy_dto.py"
_spec = importlib.util.spec_from_file_location("hierarchy_dto", str(_dto_path))
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
HierarchyDto = _module.HierarchyDto
HierarchyNodeDto = _module.HierarchyNodeDto


def _entity(**kw):
    base = {
        "id": 1,
        "name": "n",
        "slug": "s",
        "description": "d",
        "image": "i",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-02",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_from_entity_flattens_and_adds_computed_fields():
    """from_entity renames timestamps and adds type / deviceCount / children."""
    node = HierarchyNodeDto.from_entity("room", _entity(id=7), 3, [])
    payload = node.to_api_dict()
    assert payload["type"] == "room"
    assert payload["id"] == 7
    assert payload["deviceCount"] == 3
    assert payload["createdAt"] == "2026-01-01"
    assert payload["updatedAt"] == "2026-01-02"
    assert payload["children"] == []
    assert "created_at" not in payload
    assert "building_id" not in payload


def test_nodes_nest_recursively():
    """Children are serialized recursively under their parent node."""
    room = HierarchyNodeDto.from_entity("room", _entity(id=3), 2, [])
    floor = HierarchyNodeDto.from_entity("floor", _entity(id=2), 2, [room])
    building = HierarchyNodeDto.from_entity("building", _entity(id=1), 2, [floor])
    payload = building.to_api_dict()
    assert payload["children"][0]["type"] == "floor"
    assert payload["children"][0]["children"][0]["type"] == "room"
    assert payload["children"][0]["children"][0]["id"] == 3


def test_tree_wraps_buildings_and_total():
    """HierarchyDto emits buildings + camelCase totalDevices."""
    building = HierarchyNodeDto.from_entity("building", _entity(id=1), 5, [])
    payload = HierarchyDto(buildings=[building], total_devices=5).to_api_dict()
    assert set(payload.keys()) == {"buildings", "totalDevices"}
    assert payload["totalDevices"] == 5
    assert payload["buildings"][0]["id"] == 1


def test_empty_tree_defaults():
    """A default tree serializes to an empty building list and zero total."""
    payload = HierarchyDto().to_api_dict()
    assert payload == {"buildings": [], "totalDevices": 0}


SUITE_LABEL = "HierarchyDto (dto/hierarchy_dto.py)"
TEST_SUITE = [
    ("from_entity flattens and adds computed fields", test_from_entity_flattens_and_adds_computed_fields),
    ("nodes nest recursively", test_nodes_nest_recursively),
    ("tree wraps buildings and total", test_tree_wraps_buildings_and_total),
    ("empty tree defaults", test_empty_tree_defaults),
]
