"""Repository for DmDeviceModel entities."""

from .base import BaseRepository


class DeviceModelRepository(BaseRepository):
    """Repository for DmDeviceModel records.

    Manages CRUD operations on the dm_device_models table.
    """

    table_name = "dm_device_models"
    allowed_columns = {"enabled", "name", "template"}
