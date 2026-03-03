"""Repository for DmDeviceFunction entities."""

from .base import BaseRepository


class DeviceFunctionRepository(BaseRepository):
    """Repository for DmDeviceFunction records.

    Manages CRUD operations on the dm_device_functions table.
    """

    table_name = "dm_device_functions"
    allowed_columns = {"enabled", "name"}
