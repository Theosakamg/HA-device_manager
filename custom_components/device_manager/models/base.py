"""Base mixin for serializable dataclass models.

Provides generic ``to_dict``, ``to_camel_dict``, ``from_dict`` and ``get``
methods so that individual model files only need to declare their fields.
"""

import dataclasses
from typing import Any, Dict

from ..utils.case_convert import to_camel_case, to_snake_case

_MISSING = object()  # Sentinel for .get() default detection


class SerializableMixin:
    """Mixin providing generic serialization for ``@dataclass`` models.

    Conventions used by the mixin:

    * Fields whose name starts with ``_`` are considered **transient** and
      are excluded from ``to_dict`` (they are populated by repository JOINs
      and not persisted).
    * The ``id`` field is omitted from ``to_dict`` when its value is ``None``
      (new records that have not yet been inserted).
    * ``from_dict`` normalises incoming keys from camelCase to snake_case
      so that API payloads and DB rows are handled transparently.
    """

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the instance to a dict with snake_case keys.

        Fields starting with ``_`` (transient) are excluded.  The ``id`` key
        is omitted when its value is ``None``.

        Returns:
            A dictionary representation suitable for persistence.
        """
        data: Dict[str, Any] = {}
        for f in dataclasses.fields(self):  # type: ignore[arg-type]
            if f.name.startswith("_"):
                continue
            value = getattr(self, f.name)
            if f.name == "id" and value is None:
                continue
            data[f.name] = value
        return data

    def to_camel_dict(self) -> Dict[str, Any]:
        """Serialize the instance to a dict with camelCase keys.

        Suitable for JSON API responses.  Transient fields are excluded.

        Returns:
            A dictionary with camelCase keys.
        """
        return {to_camel_case(k): v for k, v in self.to_dict().items()}

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerializableMixin":
        """Create an instance from a dictionary.

        Handles both snake_case and camelCase keys transparently.  Transient
        fields (prefixed with ``_``) can be supplied with or without the
        leading underscore.

        Args:
            data: Input dictionary with field values.

        Returns:
            A new instance of the model.
        """
        # Normalize all incoming keys to snake_case.
        normalized: Dict[str, Any] = {}
        for key, value in data.items():
            normalized[to_snake_case(key)] = value

        # Build kwargs by inspecting declared dataclass fields.
        kwargs: Dict[str, Any] = {}
        for f in dataclasses.fields(cls):  # type: ignore[arg-type]
            # Transient fields are stored as ``_foo`` but supplied as ``foo``.
            lookup_key = f.name.lstrip("_") if f.name.startswith("_") else f.name

            if lookup_key in normalized:
                kwargs[f.name] = normalized[lookup_key]
            elif f.default is not dataclasses.MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                kwargs[f.name] = f.default_factory()  # type: ignore[misc]

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # dict-like access (smooth internal API)
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return attribute *key*, with transparent transient-field lookup.

        Mirrors the ``dict.get()`` interface so that code can be migrated
        incrementally from raw dicts to model instances.  Transient fields
        (stored as ``_<key>``) are accessible without the leading underscore.

        Args:
            key: Attribute name (with or without leading ``_``).
            default: Value returned when the attribute is not found.

        Returns:
            The attribute value, or *default*.
        """
        val = getattr(self, key, _MISSING)
        if val is not _MISSING:
            return val
        # Try transient field with underscore prefix.
        val = getattr(self, f"_{key}", _MISSING)
        if val is not _MISSING:
            return val
        return default
