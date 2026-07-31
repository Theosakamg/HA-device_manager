"""Migration 0009: move the encryption key into the dm/ sub-folder.

Previously the encryption key was stored at:
    <config_dir>/.device_manager.key

It is now co-located with the database inside the dm/ sub-folder:
    <config_dir>/dm/.device_manager.key

This migration detects the old path and moves the file so that the
integration can find it on the next startup without forcing a key
regeneration (which would invalidate all encrypted room passwords).
"""

import logging
from pathlib import Path

import aiosqlite

_LOGGER = logging.getLogger(__name__)

_OLD_KEY_FILENAME = ".device_manager.key"
_NEW_KEY_FILENAME = "dm/.device_manager.key"


async def run(db: aiosqlite.Connection) -> None:
    """Move the crypto key from config_dir/ to config_dir/dm/ if needed."""
    # Derive config_dir from the database path via PRAGMA database_list.
    # The DB lives at <config_dir>/dm/device_manager.db, so two levels up
    # from the database file gives us config_dir.
    cursor = await db.execute("PRAGMA database_list")
    rows = list(await cursor.fetchall())
    if not rows:
        _LOGGER.warning("Migration 0009: could not determine DB path, skipping key move")
        return

    db_path = Path(rows[0][2])  # (seq, name, file)  — index 2 is the file path
    if not db_path.is_absolute():
        _LOGGER.warning(
            "Migration 0009: DB path is not absolute (%s), skipping key move", db_path
        )
        return

    config_dir = db_path.parent.parent  # config_dir/dm/device_manager.db -> config_dir
    old_key_path = config_dir / _OLD_KEY_FILENAME
    new_key_path = config_dir / _NEW_KEY_FILENAME

    if not old_key_path.exists():
        # Nothing to migrate — either already moved or fresh install.
        return

    if new_key_path.exists():
        # New location already has a key (e.g. manual copy); keep it and
        # remove the old file to avoid confusion.
        old_key_path.unlink()
        _LOGGER.info(
            "Migration 0009: new key already present at %s — removed stale old key at %s",
            new_key_path,
            old_key_path,
        )
        return

    # Ensure the destination directory exists (should already be created by
    # DatabaseManager.initialize, but be defensive).
    new_key_path.parent.mkdir(parents=True, exist_ok=True)

    old_key_path.rename(new_key_path)
    new_key_path.chmod(0o600)

    _LOGGER.info(
        "Migration 0009: encryption key moved from %s to %s",
        old_key_path,
        new_key_path,
    )
