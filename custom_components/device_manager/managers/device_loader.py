"""Synchronous device-loading helpers for the runtime treatment managers.

The maintenance / update managers run synchronously inside Home Assistant
executor threads (see ``ha.service_registration`` and the Tasmota runtime API
controllers). Before handing work to the firmware treatment layer - which must
stay persistence-free - they load the target device(s) from the local database
*here*. This module owns the short-lived ``DatabaseManager`` lifecycle and the
``DeviceRepository`` access on the managers' behalf, keeping every database
call inside the ``managers`` layer as mandated by the project layering
(``managers`` -> ``firmware``; only ``managers`` / ``api`` touch persistence).
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from ..persistence.database_manager import DatabaseManager
from ..persistence.models.device import DmDevice
from ..persistence.repositories import DeviceRepository

logger = logging.getLogger(__name__)


def _open_db(db_path: Path) -> DatabaseManager:
    """Open and initialize a DatabaseManager (sync wrapper)."""
    db = DatabaseManager(db_path)
    asyncio.run(db.initialize())
    return db


def _close_db(db: DatabaseManager) -> None:
    """Close a DatabaseManager (sync wrapper); never raises."""
    try:
        asyncio.run(db.close())
    except Exception as e:  # noqa: BLE001 - closing must never break a treatment
        logger.debug("Error closing DB: %s", e)


def filter_devices(
    devices: List[DmDevice], mac_filter: Optional[List[str]]
) -> List[DmDevice]:
    """Return devices that have an IP, optionally restricted to *mac_filter*.

    A device without an IP address cannot be reached over HTTP, so it is always
    dropped. When *mac_filter* is provided, only devices whose MAC is listed
    (case-insensitive) are kept.
    """
    result = [d for d in devices if getattr(d, "ip", None)]
    if mac_filter:
        wanted = {m.upper() for m in mac_filter}
        result = [d for d in result if d.mac.upper() in wanted]
    return result


def get_device(db_path: Path, mac: str) -> Optional[DmDevice]:
    """Load a single hydrated device by MAC from *db_path*.

    Opens a short-lived connection, resolves the device via
    ``DeviceRepository.find_by_mac`` and closes the connection before returning.

    Args:
        db_path: Path to the SQLite database.
        mac: Target device MAC address.

    Returns:
        The hydrated ``DmDevice`` or ``None`` when no device matches *mac*.
    """
    db = _open_db(db_path)
    try:

        async def _find() -> Optional[DmDevice]:
            return await DeviceRepository(db).find_by_mac(mac)

        return asyncio.run(_find())
    finally:
        _close_db(db)


def get_devices(
    db_path: Path, mac_filter: Optional[List[str]] = None
) -> List[DmDevice]:
    """Load every reachable (has-IP) device from *db_path*.

    Opens a short-lived connection, loads all hydrated devices, closes the
    connection and returns those with an IP address, optionally restricted to
    *mac_filter*.

    Args:
        db_path: Path to the SQLite database.
        mac_filter: Optional list of MACs to restrict the result to.

    Returns:
        The list of reachable hydrated devices.
    """
    db = _open_db(db_path)
    try:

        async def _all() -> List[DmDevice]:
            return await DeviceRepository(db).find_all()

        devices = asyncio.run(_all())
    finally:
        _close_db(db)
    return filter_devices(devices, mac_filter)
