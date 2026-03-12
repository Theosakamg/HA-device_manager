"""Migration 0001: make dm_devices.ip column nullable (NULL default instead of '')."""

import aiosqlite

# Schema snapshot at migration time
_DEVICES_DDL = """
    CREATE TABLE IF NOT EXISTS dm_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac TEXT UNIQUE DEFAULT '',
        ip TEXT UNIQUE DEFAULT NULL,
        enabled BOOLEAN NOT NULL DEFAULT 1,
        position_name TEXT DEFAULT '',
        position_slug TEXT DEFAULT '',
        mode TEXT DEFAULT '',
        interlock TEXT DEFAULT '',
        ha_device_class TEXT DEFAULT '',
        extra TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        room_id INTEGER NOT NULL,
        model_id INTEGER NOT NULL,
        firmware_id INTEGER NOT NULL,
        function_id INTEGER NOT NULL,
        target_id INTEGER,
        FOREIGN KEY (room_id) REFERENCES dm_rooms(id)
            ON DELETE CASCADE,
        FOREIGN KEY (model_id) REFERENCES dm_device_models(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (firmware_id)
            REFERENCES dm_device_firmwares(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (function_id)
            REFERENCES dm_device_functions(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (target_id) REFERENCES dm_devices(id)
            ON DELETE SET NULL
    )
"""


async def run(db: aiosqlite.Connection) -> None:
    """Recreate dm_devices if ip column has wrong non-NULL default."""
    cursor = await db.execute("PRAGMA table_info(dm_devices)")
    columns = await cursor.fetchall()
    if not columns:
        return

    for col in columns:
        col_dict = dict(col)
        if col_dict["name"] == "ip" and col_dict["dflt_value"] == "''":
            await db.execute(
                "ALTER TABLE dm_devices RENAME TO _dm_devices_old"
            )
            await db.execute(_DEVICES_DDL)
            await db.execute("""
                INSERT INTO dm_devices
                SELECT
                    id, mac, NULLIF(ip, ''),
                    enabled, position_name,
                    position_slug, mode,
                    interlock, ha_device_class,
                    extra, created_at,
                    updated_at, room_id,
                    model_id, firmware_id,
                    function_id, target_id
                FROM _dm_devices_old
            """)
            await db.execute("DROP TABLE _dm_devices_old")
            await db.commit()
            return
