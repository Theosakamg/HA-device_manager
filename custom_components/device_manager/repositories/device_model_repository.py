"""Repository for DmDeviceModel entities."""

from .base import BaseRepository
from ..models.device_model import DmDeviceModel


class DeviceModelRepository(BaseRepository[DmDeviceModel]):
    """Repository for DmDeviceModel records.

    Manages CRUD operations on the dm_device_models table.
    """

    table_name = "dm_device_models"
    allowed_columns = {"enabled", "name", "template"}
