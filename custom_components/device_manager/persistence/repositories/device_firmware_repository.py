"""Repository for DmDeviceFirmware entities."""

from .base import BaseRepository
from ..models.device_firmware import DmDeviceFirmware


class DeviceFirmwareRepository(BaseRepository[DmDeviceFirmware]):
    """Repository for DmDeviceFirmware records.

    Manages CRUD operations on the dm_device_firmwares table.
    """

    table_name = "dm_device_firmwares"
    allowed_columns = {"enabled", "name", "deployable"}
