"""Migration 0006: add state column to dm_devices.

This migration adds a state column to track device deployment context:
- deployed: Device is deployed and operational in the house
- parking: Device is in stock (spare/upgrade)
- out_of_order: Device is broken/not functional
- deployed_hot: Deployed but manual configuration only (excluded from deploy all)

The state field is complementary to enabled (bool):
- enabled: Technical status (active/inactive)
- state: Business context (why this status)
"""

import aiosqlite


async def run(db: aiosqlite.Connection) -> None:
    """Add state column to dm_devices table."""

    # Add state column with default value 'deployed'
    await db.execute(
        "ALTER TABLE dm_devices ADD COLUMN state TEXT NOT NULL DEFAULT 'deployed'"
    )

    # Migrate existing data based on enabled status
    # enabled=1 -> state='deployed' (conservative: assume deployed)
    await db.execute(
        "UPDATE dm_devices SET state = 'deployed' WHERE enabled = 1"
    )

    # enabled=0 -> state='parking' (conservative: assume in stock)
    await db.execute(
        "UPDATE dm_devices SET state = 'parking' WHERE enabled = 0"
    )

    await db.commit()

    print(f"Migration 0006: Added state column to dm_devices")
    print(f"  - Devices with enabled=1 migrated to state='deployed'")
    print(f"  - Devices with enabled=0 migrated to state='parking'")
    print(f"  - Users can manually adjust state values as needed")
