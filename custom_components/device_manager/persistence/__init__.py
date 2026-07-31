"""Sealed persistence layer for Device Manager.

This package is the single boundary to the SQLite database: DB models,
repositories, the database manager and schema migrations. It stays watertight
- nothing here imports from ``firmware``, ``managers``, ``api``, ``ha`` or
``dto``. The persistence layer is depended upon; it never depends upward.
"""

from .database_manager import DatabaseManager
from .repositories import (
    ActivityLogRepository,
    BuildingRepository,
    DeviceFirmwareRepository,
    DeviceFunctionRepository,
    DeviceModelRepository,
    DeviceRepository,
    FloorRepository,
    RoomRepository,
    SettingsRepository,
)

__all__ = [
    "DatabaseManager",
    "ActivityLogRepository",
    "BuildingRepository",
    "DeviceFirmwareRepository",
    "DeviceFunctionRepository",
    "DeviceModelRepository",
    "DeviceRepository",
    "FloorRepository",
    "RoomRepository",
    "SettingsRepository",
]
