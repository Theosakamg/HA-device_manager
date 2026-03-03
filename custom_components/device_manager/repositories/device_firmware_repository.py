"""Repository for DmDeviceFirmware entities."""

from .base import BaseRepository


class DeviceFirmwareRepository(BaseRepository):
    """Repository for DmDeviceFirmware records.

    Manages CRUD operations on the dm_device_firmwares table.
    """

    table_name = "dm_device_firmwares"
    allowed_columns = {"enabled", "name"}
