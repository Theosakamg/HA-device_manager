"""Repository for DmDeviceFunction entities."""

from .base import BaseRepository
from ..models.device_function import DmDeviceFunction


class DeviceFunctionRepository(BaseRepository[DmDeviceFunction]):
    """Repository for DmDeviceFunction records.

    Manages CRUD operations on the dm_device_functions table.
    """

    table_name = "dm_device_functions"
    allowed_columns = {"enabled", "name"}
