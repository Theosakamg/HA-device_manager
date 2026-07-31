"""Tests for :class:`ImportResultDto` boundary serialization.

Loads the DTO module directly by file path (it has no package-relative
imports) so the test needs no Home Assistant stubs.
"""

import importlib.util
from pathlib import Path

_dto_path = Path(__file__).resolve().parent.parent / "dto" / "import_result_dto.py"
_spec = importlib.util.spec_from_file_location("import_result_dto", str(_dto_path))
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
ImportResultDto = _module.ImportResultDto


_RAW = {
    "total": 5,
    "created": 4,
    "updated": 0,
    "skipped": 1,
    "target_resolved": 3,
    "target_failed": 1,
    "errors": ["Row 2: boom"],
    "logs": [{"row": 1, "status": "created", "message": "ok", "id": 7, "mac": "AA"}],
}


def test_from_result_maps_all_fields():
    """from_result copies every snake_case counter from the raw dict."""
    dto = ImportResultDto.from_result(_RAW)
    assert dto.total == 5
    assert dto.created == 4
    assert dto.skipped == 1
    assert dto.target_resolved == 3
    assert dto.target_failed == 1
    assert dto.errors == ["Row 2: boom"]
    assert dto.logs[0]["mac"] == "AA"


def test_to_api_dict_uses_camel_case():
    """to_api_dict renames the diverging target counters to camelCase."""
    payload = ImportResultDto.from_result(_RAW).to_api_dict()
    assert set(payload.keys()) == {
        "total", "created", "updated", "skipped",
        "targetResolved", "targetFailed", "errors", "logs",
    }
    assert payload["targetResolved"] == 3
    assert payload["targetFailed"] == 1
    assert "target_resolved" not in payload
    assert "target_failed" not in payload


def test_logs_pass_through_unchanged():
    """Log entries keep their single-word keys untouched."""
    payload = ImportResultDto.from_result(_RAW).to_api_dict()
    assert payload["logs"][0] == {
        "row": 1, "status": "created", "message": "ok", "id": 7, "mac": "AA",
    }


def test_from_result_defaults_missing_keys():
    """Missing keys fall back to zero / empty list instead of raising."""
    dto = ImportResultDto.from_result({})
    assert dto.total == 0
    assert dto.target_resolved == 0
    assert dto.target_failed == 0
    assert dto.errors == []
    assert dto.logs == []


SUITE_LABEL = "ImportResultDto (dto/import_result_dto.py)"
TEST_SUITE = [
    ("from_result maps all fields", test_from_result_maps_all_fields),
    ("to_api_dict uses camelCase keys", test_to_api_dict_uses_camel_case),
    ("logs pass through unchanged", test_logs_pass_through_unchanged),
    ("from_result defaults missing keys", test_from_result_defaults_missing_keys),
]
