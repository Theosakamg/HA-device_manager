"""Repository for DmDevice entities."""

import logging
from typing import Any, Optional

from .base import BaseRepository

_LOGGER = logging.getLogger(__name__)


class DeviceRepository(BaseRepository):
    """Repository for managing DmDevice records in dm_devices table.

    Provides enriched queries with JOINs to include related entity names
    for display purposes.
    """

    table_name = "dm_devices"
    allowed_columns = {
        "mac", "ip", "enabled", "position_name", "position_slug",
        "mode", "interlock", "ha_device_class", "extra",
        "room_id", "model_id", "firmware_id", "function_id", "target_id",
    }
    parent_column = "room_id"

    _JOIN_SELECT = """
        SELECT
            d.*,
            r.name AS room_name,
            r.slug AS room_slug,
            l.name AS floor_name,
            l.slug AS floor_slug,
            h.name AS building_name,
            dm.name AS model_name,
            df.name AS firmware_name,
            dfn.name AS function_name,
            t.mac AS target_mac
        FROM dm_devices d
        LEFT JOIN dm_rooms r ON d.room_id = r.id
        LEFT JOIN dm_floors l ON r.floor_id = l.id
        LEFT JOIN dm_buildings h ON l.building_id = h.id
        LEFT JOIN dm_device_models dm ON d.model_id = dm.id
        LEFT JOIN dm_device_firmwares df ON d.firmware_id = df.id
        LEFT JOIN dm_device_functions dfn ON d.function_id = dfn.id
        LEFT JOIN dm_devices t ON d.target_id = t.id
    """

    async def find_all(self) -> list[dict[str, Any]]:
        """Retrieve all devices with joined related entity names.

        Returns:
            A list of device dicts including room_name, level_name, etc.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(f"{self._JOIN_SELECT} ORDER BY d.id ASC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def find_by_id(self, entity_id: int) -> Optional[dict[str, Any]]:
        """Retrieve a single device by ID with joined names.

        Args:
            entity_id: The device ID.

        Returns:
            A device dict or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.id = ?", (entity_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def find_by_room(self, room_id: int) -> list[dict[str, Any]]:
        """Find all devices in a specific room.

        Args:
            room_id: The room ID to filter by.

        Returns:
            A list of device dicts.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.room_id = ? ORDER BY d.id ASC",
            (room_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def find_by_mac(self, mac: str) -> Optional[dict[str, Any]]:
        """Find a device by its MAC address.

        Args:
            mac: The MAC address string.

        Returns:
            A device dict or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.mac = ?", (mac,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def find_by_ip(self, ip: str) -> Optional[dict[str, Any]]:
        """Find a device by its IP address.

        Args:
            ip: The IP address string.

        Returns:
            A device dict or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.ip = ?", (ip,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def count_by_room(self, room_id: int) -> int:
        """Count devices in a specific room.

        Args:
            room_id: The room ID.

        Returns:
            The device count.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM dm_devices WHERE room_id = ?",
            (room_id,),
        )
        row = await cursor.fetchone()
        return int(row["cnt"]) if row else 0

    async def count_all_by_room(self) -> dict[int, int]:
        """Count devices grouped by room_id in a single query.

        Returns:
            A dict mapping room_id to device count.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            "SELECT room_id, COUNT(*) as cnt FROM dm_devices GROUP BY room_id"
        )
        rows = await cursor.fetchall()
        return {int(row["room_id"]): int(row["cnt"]) for row in rows}
