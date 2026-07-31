"""Migration 0005: fix empty slugs in hierarchy tables.

This migration ensures all slugs in dm_buildings, dm_floors, and dm_rooms
are non-empty by generating slugs from the name field where needed.
"""

import aiosqlite
import re


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    if not text:
        return "unknown"
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-') or "unknown"


async def run(db: aiosqlite.Connection) -> None:
    """Fix empty slugs in hierarchy tables."""

    tables = [
        ('dm_buildings', 'id', 'name', 'slug'),
        ('dm_floors', 'id', 'name', 'slug'),
        ('dm_rooms', 'id', 'name', 'slug'),
    ]

    for table, id_col, name_col, slug_col in tables:
        # Find records with empty slugs
        cursor = await db.execute(
            f"SELECT {id_col}, {name_col}, {slug_col} FROM {table} "
            f"WHERE {slug_col} = '' OR {slug_col} IS NULL"
        )
        empty_slugs = list(await cursor.fetchall())

        if not empty_slugs:
            continue

        print(f"Fixing {len(empty_slugs)} empty slugs in {table}")

        for row in empty_slugs:
            entity_id, name, current_slug = row
            # Generate slug from name
            new_slug = _slugify(name)

            # Ensure uniqueness by checking for conflicts
            base_slug = new_slug
            counter = 1
            while True:
                check_cursor = await db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {slug_col} = ? AND {id_col} != ?",
                    (new_slug, entity_id)
                )
                count_row = await check_cursor.fetchone()
                count = count_row[0] if count_row is not None else 0
                if count == 0:
                    break
                new_slug = f"{base_slug}-{counter}"
                counter += 1

            # Update the slug
            await db.execute(
                f"UPDATE {table} SET {slug_col} = ? WHERE {id_col} = ?",
                (new_slug, entity_id)
            )
            print(f"  {table} ID {entity_id}: '{name}' -> slug '{new_slug}'")

    await db.commit()
