"""Migration 0007: add scan_script_content setting to dm_settings.

This migration adds the scan_script_content key to the settings table
with the default script for querying a Kea DHCP server via SSH.

The script is stored in the database instead of using an external file,
allowing users to customize the network scanning logic via the web UI.
"""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Add scan_script_content setting to dm_settings if missing."""
    # Check if the key already exists
    cursor = await db.execute(
        "SELECT COUNT(*) FROM dm_settings WHERE key = ?",
        ("scan_script_content",),
    )
    row = await cursor.fetchone()
    exists = row[0] > 0 if row else False

    if not exists:
        # Default script: queries Kea DHCP server via SSH and outputs YAML
        default_script = (
            r"""SSH_USER=$SCAN_SCRIPT_SSH_USER
SSH_HOST=$SCAN_SCRIPT_SSH_HOST
PRIVATE_KEY_FILE=$SCAN_SCRIPT_PRIVATE_KEY_FILE

if [ -z "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SCAN_SCRIPT_PRIVATE_KEY_FILE is not set" >&2
    exit 1
fi

if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SSH key file not found: $PRIVATE_KEY_FILE" >&2
    exit 1
fi

ssh -T -i "$PRIVATE_KEY_FILE" """
            r"""-o BatchMode=yes -o LogLevel=ERROR -o StrictHostKeyChecking=no """
            r""""$SSH_USER@$SSH_HOST" | """
            r"""jq -r '.arguments.leases[] | "\(."ip-address"): \(."hw-address")"' """
            r"""2>/dev/null"""
        )

        await db.execute(
            "INSERT INTO dm_settings (key, value) VALUES (?, ?)",
            ("scan_script_content", default_script),
        )
        await db.commit()
        print("Migration 0007: Added scan_script_content setting to dm_settings")
