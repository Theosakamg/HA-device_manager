"""Tests for :class:`ScanReportDto` boundary serialization.

Loads the DTO module directly by file path (it has no package-relative
imports) so the test needs no Home Assistant stubs.
"""

import importlib.util
from pathlib import Path

_dto_path = Path(__file__).resolve().parent.parent / "dto" / "scan_report_dto.py"
_spec = importlib.util.spec_from_file_location("scan_report_dto", str(_dto_path))
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
ScanReportDto = _module.ScanReportDto


def test_from_stats_maps_all_fields():
    """from_stats copies every snake_case field from the raw stats dict."""
    dto = ScanReportDto.from_stats(
        {
            "total": 10,
            "mapped": 7,
            "not_found": 2,
            "errors": 1,
            "error_details": ["boom"],
        }
    )
    assert dto.total == 10
    assert dto.mapped == 7
    assert dto.not_found == 2
    assert dto.errors == 1
    assert dto.error_details == ["boom"]


def test_to_api_dict_uses_camel_case():
    """to_api_dict emits explicit camelCase keys for the frontend."""
    payload = ScanReportDto.from_stats(
        {"total": 3, "mapped": 1, "not_found": 2, "errors": 0, "error_details": []}
    ).to_api_dict()
    assert set(payload.keys()) == {"total", "mapped", "notFound", "errors", "errorDetails"}
    assert payload["notFound"] == 2
    assert payload["errorDetails"] == []


def test_from_stats_defaults_missing_keys():
    """Missing keys fall back to zero / empty list instead of raising."""
    dto = ScanReportDto.from_stats({})
    assert dto.total == 0
    assert dto.mapped == 0
    assert dto.not_found == 0
    assert dto.errors == 0
    assert dto.error_details == []


def test_from_stats_tolerates_none_error_details():
    """A None error_details value is normalized to an empty list."""
    dto = ScanReportDto.from_stats({"error_details": None})
    assert dto.error_details == []
    assert dto.to_api_dict()["errorDetails"] == []


SUITE_LABEL = "ScanReportDto (dto/scan_report_dto.py)"
TEST_SUITE = [
    ("from_stats maps all fields", test_from_stats_maps_all_fields),
    ("to_api_dict uses camelCase keys", test_to_api_dict_uses_camel_case),
    ("from_stats defaults missing keys", test_from_stats_defaults_missing_keys),
    ("from_stats tolerates None error_details", test_from_stats_tolerates_none_error_details),
]
