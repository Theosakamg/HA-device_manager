"""Repository for DmBuilding entities."""

from .base import BaseRepository


class BuildingRepository(BaseRepository):
    """Repository for managing DmBuilding records in dm_buildings table."""

    table_name = "dm_buildings"
    allowed_columns = {"name", "slug", "description", "image"}
