"""Controller layer (API views) for Device Manager."""

from .static_controller import StaticView
from .building_controller import BuildingsAPIView, BuildingAPIView
from .floor_controller import FloorsAPIView, FloorAPIView
from .room_controller import RoomsAPIView, RoomAPIView
from .device_controller import DevicesAPIView, DeviceAPIView
from .device_model_controller import DeviceModelsAPIView, DeviceModelAPIView
from .device_firmware_controller import DeviceFirmwaresAPIView, DeviceFirmwareAPIView
from .device_function_controller import DeviceFunctionsAPIView, DeviceFunctionAPIView
from .hierarchy_controller import HierarchyAPIView
from .import_controller import CSVImportAPIView
from .export_controller import ExportAPIView
from .maintenance_controller import MaintenanceCleanDBAPIView, MaintenanceClearIPCacheAPIView
from .settings_controller import SettingsAPIView
from .deploy_controller import DeployAPIView, DevicesScanAPIView
from .ssh_key_controller import SSHKeyUploadAPIView
from .stats_controller import StatsAPIView
from .db_backup_controller import SQLiteExportAPIView, SQLiteImportAPIView
from .ha_groups_controller import HaGroupsSyncAPIView
from .ha_floors_controller import HaFloorsSyncAPIView
from .ha_rooms_controller import HaRoomsSyncAPIView
from .activity_log_controller import ActivityLogAPIView, ActivityLogExportAPIView, ActivityLogPurgeAPIView

ALL_VIEWS = [
    StaticView,
    BuildingsAPIView,
    BuildingAPIView,
    FloorsAPIView,
    FloorAPIView,
    RoomsAPIView,
    RoomAPIView,
    DevicesAPIView,
    DeviceAPIView,
    DeviceModelsAPIView,
    DeviceModelAPIView,
    DeviceFirmwaresAPIView,
    DeviceFirmwareAPIView,
    DeviceFunctionsAPIView,
    DeviceFunctionAPIView,
    HierarchyAPIView,
    CSVImportAPIView,
    ExportAPIView,
    SQLiteExportAPIView,
    SQLiteImportAPIView,
    MaintenanceCleanDBAPIView,
    MaintenanceClearIPCacheAPIView,
    SettingsAPIView,
    DeployAPIView,
    DevicesScanAPIView,
    SSHKeyUploadAPIView,
    StatsAPIView,
    HaGroupsSyncAPIView,
    HaFloorsSyncAPIView,
    HaRoomsSyncAPIView,
    ActivityLogAPIView,
    ActivityLogExportAPIView,
    ActivityLogPurgeAPIView,
]
