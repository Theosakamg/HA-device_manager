"""Repository for DmDevice entities."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .base import BaseRepository
from ..models.device import DmDevice

_LOGGER = logging.getLogger(__name__)


class DeviceRepository(BaseRepository[DmDevice]):
    """Repository for managing DmDevice records in dm_devices table.

    Provides enriched queries with JOINs to include related entity names
    for display purposes.
    """

    table_name = "dm_devices"
    model_class = DmDevice
    allowed_columns = {
        "mac", "ip", "enabled", "state", "position_name", "position_slug",
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
            h.slug AS building_slug,
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

    def _row_to_model(self, row: dict[str, Any]) -> DmDevice:
        """Hydrate a JOIN row into a fully-populated DmDevice instance.

        The JOIN columns are mapped to the transient ``_*`` fields of
        DmDevice so that ``to_camel_dict_full()`` exposes them to API clients.
        Also derives ``_floor_number`` from the ``floor_slug`` (e.g. ``l2`` → 2).
        """
        # Derive floor_number from floor_slug (e.g. "l0" -> 0)
        floor_slug = row.get("floor_slug") or ""
        try:
            floor_number = int(floor_slug.lstrip("l")) if floor_slug else 0
        except (ValueError, AttributeError):
            floor_number = 0
        row["floor_number"] = floor_number
        return DmDevice.from_dict(row)

    async def find_all(self) -> list[DmDevice]:
        """Retrieve all devices with joined related entity names.

        Returns:
            A list of DmDevice instances including transient JOIN fields.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(f"{self._JOIN_SELECT} ORDER BY d.id ASC")
        rows = await cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def find_by_id(self, entity_id: int) -> Optional[DmDevice]:
        """Retrieve a single device by ID with joined names.

        Args:
            entity_id: The device ID.

        Returns:
            A DmDevice instance or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.id = ?", (entity_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_model(dict(row)) if row else None

    async def find_by_room(self, room_id: int) -> list[DmDevice]:
        """Find all devices in a specific room.

        Args:
            room_id: The room ID to filter by.

        Returns:
            A list of DmDevice instances.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.room_id = ? ORDER BY d.id ASC",
            (room_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(dict(row)) for row in rows]

    async def find_by_mac(self, mac: str) -> Optional[DmDevice]:
        """Find a device by its MAC address.

        Args:
            mac: The MAC address string.

        Returns:
            A DmDevice instance or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.mac = ?", (mac,)
        )
        row = await cursor.fetchone()
        return self._row_to_model(dict(row)) if row else None

    async def find_by_ip(self, ip: str) -> Optional[DmDevice]:
        """Find a device by its IP address.

        Args:
            ip: The IP address string.

        Returns:
            A DmDevice instance or None.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"{self._JOIN_SELECT} WHERE d.ip = ?", (ip,)
        )
        row = await cursor.fetchone()
        return self._row_to_model(dict(row)) if row else None

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

    async def update_deploy_status(
        self, device_id: int, status: str
    ) -> None:
        """Update last_deploy_at and last_deploy_status for a device.

        This method bypasses the ``allowed_columns`` whitelist because these
        fields are set exclusively by the deploy process, not via the CRUD API.

        Args:
            device_id: The device primary key.
            status:    ``'done'`` or ``'fail'``.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn = await self.db.get_connection()
        await conn.execute(
            "UPDATE dm_devices"
            " SET last_deploy_at = ?, last_deploy_status = ?"
            " WHERE id = ?",
            (now, status, device_id),
        )
        await conn.commit()
        _LOGGER.debug(
            "Deploy status updated: device_id=%d status=%s", device_id, status
        )
