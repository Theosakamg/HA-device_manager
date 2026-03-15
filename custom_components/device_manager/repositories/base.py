"""Base repository with generic CRUD operations."""

import logging
import re
from typing import Any, Generic, Optional, Type, TypeVar, get_args

from ..models.base import SerializableMixin
from ..services.database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)

# Whitelist of valid table names — defence-in-depth against SQL injection.
_VALID_TABLE_NAMES = frozenset({
    "dm_buildings",
    "dm_floors",
    "dm_rooms",
    "dm_devices",
    "dm_device_models",
    "dm_device_firmwares",
    "dm_device_functions",
    "dm_settings",
    "dm_activity_log",
})

# Regex for safe SQL identifiers (column names)
_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

M = TypeVar("M", bound=SerializableMixin)


def _resolve_model_class(cls: type) -> Optional[Type[SerializableMixin]]:
    """Inspect ``__orig_bases__`` to extract the concrete M type argument.

    When a subclass is defined as ``class FooRepository(BaseRepository[Foo])``,
    Python stores the parameterised base as an entry in ``__orig_bases__``.
    We walk those bases looking for the first generic argument that is a
    concrete subclass of :class:`SerializableMixin`.
    """
    for base in getattr(cls, "__orig_bases__", ()):
        args = get_args(base)
        if args:
            candidate = args[0]
            if isinstance(candidate, type) and issubclass(candidate, SerializableMixin):
                return candidate
    return None


class BaseRepository(Generic[M]):
    """Base repository providing generic CRUD operations for a SQLite table.

    Subclasses must define:
        - table_name:      str      – The SQL table name.
        - allowed_columns: set[str] – Whitelist of column names for
                                      insert/update.

    ``model_class`` is **inferred automatically** from the generic type
    parameter (e.g. ``class FooRepo(BaseRepository[Foo])`` → ``Foo``).
    Subclasses may still declare it explicitly to override the inference.

    Optional hooks (override in subclasses):
        - _decode_row(row):     post-process a raw dict after reading.
        - _encode_row(data):    pre-process a dict before writing.
        - _row_to_model(row):   convert a decoded dict to a model instance.
                                Default implementation calls
                                ``model_class.from_dict(row)``.
    """

    table_name: str = ""
    model_class: Optional[Type[M]] = None  # type: ignore[assignment]
    allowed_columns: set[str] = set()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-resolve model_class from the generic type parameter."""
        super().__init_subclass__(**kwargs)
        # Only set when not already explicitly declared on this class.
        if "model_class" not in cls.__dict__:
            resolved = _resolve_model_class(cls)
            if resolved is not None:
                cls.model_class = resolved  # type: ignore[assignment]

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize with a shared DatabaseManager.

        Args:
            db_manager: The database manager providing the shared connection.

        Raises:
            ValueError: If table_name is not in the allowed whitelist.
        """
        if self.table_name and self.table_name not in _VALID_TABLE_NAMES:
            raise ValueError(
                f"Invalid table name '{self.table_name}'. "
                f"Must be one of {_VALID_TABLE_NAMES}"
            )
        self.db = db_manager

    # ------------------------------------------------------------------
    # Row transformation hooks (override in subclasses)
    # ------------------------------------------------------------------

    def _decode_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Post-process a raw dict after reading from the DB.

        Override to decrypt fields or enrich the dict.  Default is identity.
        """
        return row

    def _encode_row(self, data: dict[str, Any]) -> dict[str, Any]:
        """Pre-process data before writing to the DB.

        Override to encrypt fields or transform values.  Default is identity.
        """
        return data

    def _row_to_model(self, row: dict[str, Any]) -> M:
        """Convert a decoded DB row dict to a typed model instance.

        The default implementation delegates to ``model_class.from_dict()``.
        Override in subclasses when additional logic is needed (e.g. JOIN
        column mapping).

        Args:
            row: A fully decoded dict from ``_decode_row()``.

        Returns:
            A typed model instance.

        Raises:
            NotImplementedError: If ``model_class`` is not set.
        """
        if self.model_class is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define 'model_class'"
            )
        return self.model_class.from_dict(row)  # type: ignore[return-value]

    async def find_all(self) -> list[M]:
        """Retrieve all rows from the table, ordered by id ASC.

        Returns:
            A list of typed model instances.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT * FROM {self.table_name} ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(self._decode_row(dict(row))) for row in rows]

    async def find_by_id(self, entity_id: int) -> Optional[M]:
        """Retrieve a single row by its primary key.

        Args:
            entity_id: The integer primary key.

        Returns:
            A typed model instance, or None if not found.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"SELECT * FROM {self.table_name} WHERE id = ?", (entity_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_model(self._decode_row(dict(row))) if row else None

    async def create(self, data: dict[str, Any]) -> int:
        """Insert a new row and return its auto-generated ID.

        Only columns listed in `allowed_columns` are written.

        Args:
            data: A dict of column names to values.

        Returns:
            The integer ID of the newly created row.

        Raises:
            ValueError: If the insert fails to produce an ID.
        """
        filtered = {k: v for k, v in data.items() if k in self.allowed_columns}
        if not filtered:
            conn = await self.db.get_connection()
            cursor = await conn.execute(
                f"INSERT INTO {self.table_name} DEFAULT VALUES"
            )
            await conn.commit()
            if cursor.lastrowid is None:
                raise ValueError("Failed to get ID after insert")
            return int(cursor.lastrowid)

        filtered = self._encode_row(filtered)

        cols = list(filtered.keys())
        # Validate column names are safe identifiers
        for col in cols:
            if not _SAFE_IDENTIFIER_RE.match(col):
                raise ValueError(f"Invalid column name: {col}")
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        values = [filtered[c] for c in cols]

        conn = await self.db.get_connection()
        sql = (
            f"INSERT INTO {self.table_name}"
            f" ({col_list}) VALUES ({placeholders})"
        )
        cursor = await conn.execute(sql, tuple(values))
        await conn.commit()
        if cursor.lastrowid is None:
            raise ValueError("Failed to get ID after insert")
        _LOGGER.debug("Created %s (ID: %d)", self.table_name, cursor.lastrowid)
        return int(cursor.lastrowid)

    async def update(self, entity_id: int, data: dict[str, Any]) -> bool:
        """Update an existing row by ID.

        Only columns listed in `allowed_columns` are modified.
        Automatically sets updated_at to CURRENT_TIMESTAMP.

        Args:
            entity_id: The integer primary key.
            data: A dict of column names to new values.

        Returns:
            True if the update was applied, False if no valid columns provided.
        """
        filtered = {k: v for k, v in data.items() if k in self.allowed_columns}
        if not filtered:
            return False

        filtered = self._encode_row(filtered)

        # Validate column names are safe identifiers
        for k in filtered:
            if not _SAFE_IDENTIFIER_RE.match(k):
                raise ValueError(f"Invalid column name: {k}")

        sets = [f"{k} = ?" for k in filtered]
        sets.append("updated_at = CURRENT_TIMESTAMP")
        values = list(filtered.values())
        values.append(entity_id)

        conn = await self.db.get_connection()
        await conn.execute(
            f"UPDATE {self.table_name} SET {', '.join(sets)} WHERE id = ?",
            tuple(values),
        )
        await conn.commit()
        _LOGGER.debug("Updated %s (ID: %d)", self.table_name, entity_id)
        return True

    async def delete(self, entity_id: int) -> bool:
        """Delete a row by ID.

        Args:
            entity_id: The integer primary key.

        Returns:
            True if a row was deleted, False otherwise.
        """
        conn = await self.db.get_connection()
        cursor = await conn.execute(
            f"DELETE FROM {self.table_name} WHERE id = ?", (entity_id,)
        )
        await conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            _LOGGER.debug("Deleted %s (ID: %d)", self.table_name, entity_id)
        return deleted

    async def find_by_parent(self, parent_id: int) -> list[M]:
        """Find rows by parent FK. Subclasses should override parent_column.

        Args:
            parent_id: The parent foreign key value.

        Returns:
            A list of typed model instances.
        """
        parent_column = getattr(self, "parent_column", None)
        if not parent_column:
            return []
        conn = await self.db.get_connection()
        sql = (
            f"SELECT * FROM {self.table_name}"
            f" WHERE {parent_column} = ?"
            " ORDER BY id ASC"
        )
        cursor = await conn.execute(sql, (parent_id,))
        rows = await cursor.fetchall()
        return [self._row_to_model(self._decode_row(dict(row))) for row in rows]
