"""Repository for DmFloor entities."""

from .base import BaseRepository
from ..models.floor import DmFloor


class FloorRepository(BaseRepository[DmFloor]):
    """Repository for managing DmFloor records in dm_floors table.

    Floors are always sorted by ``slug`` so that the natural floor
    order (l0, l1, l2 …) is preserved regardless of insertion order.
    """

    table_name = "dm_floors"
    allowed_columns = {"name", "slug", "description", "image", "building_id"}
    parent_column = "building_id"
    default_order = "slug ASC"

    async def find_all(self) -> list[DmFloor]:
        """Retrieve all floors ordered by slug.

        Returns:
            A list of DmFloor instances sorted by slug.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT * FROM {self.table_name}"
            f" ORDER BY {self.default_order}"
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def find_by_building(self, building_id: int) -> list[DmFloor]:
        """Find all floors belonging to a specific building.

        Args:
            building_id: The building ID to filter by.

        Returns:
            A list of DmFloor instances sorted by slug.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT * FROM {self.table_name}"
            f" WHERE {self.parent_column} = ?"
            f" ORDER BY {self.default_order}",
            (building_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]
