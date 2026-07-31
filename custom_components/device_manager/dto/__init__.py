"""Data Transfer Objects for Device Manager.

DTOs are Plain Old Python Objects used to move data across layer boundaries
(persistence -> managers/firmware -> api) without leaking the sealed DB models
outside the persistence layer. Each DTO knows how to build itself from a
persistence model and how to serialize to the camelCase JSON shape consumed by
the frontend.
"""

from .device_dto import DeviceDto
from .ha_sync_result_dto import HaSyncResultDto
from .hierarchy_dto import HierarchyDto, HierarchyNodeDto
from .import_result_dto import ImportResultDto
from .scan_report_dto import ScanReportDto
from .stats_dto import StatsDto

__all__ = [
    "DeviceDto",
    "HaSyncResultDto",
    "HierarchyDto",
    "HierarchyNodeDto",
    "ImportResultDto",
    "ScanReportDto",
    "StatsDto",
]
