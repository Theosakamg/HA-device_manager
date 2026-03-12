"""Case conversion utilities shared across models and controllers.

Provides snake_case ↔ camelCase conversion for strings and dictionaries.
This is the **single source of truth** — all other modules import from here.
"""

import re
from typing import Any


def to_camel_case(snake_str: str) -> str:
    """Convert a snake_case string to camelCase.

    Args:
        snake_str: The snake_case string to convert.

    Returns:
        The camelCase equivalent.

    Example:
        >>> to_camel_case("room_id")
        'roomId'
    """
    parts = snake_str.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_snake_case(camel_str: str) -> str:
    """Convert a camelCase string to snake_case.

    Args:
        camel_str: The camelCase string to convert.

    Returns:
        The snake_case equivalent.

    Example:
        >>> to_snake_case("roomId")
        'room_id'
    """
    s = re.sub(r"([A-Z])", r"_\1", camel_str).lower()
    return s.lstrip("_")


def to_camel_case_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Convert a dict with snake_case keys to camelCase keys.

    Args:
        data: Dict with snake_case keys.

    Returns:
        New dict with camelCase keys.
    """
    return {to_camel_case(k): v for k, v in data.items()}


def to_snake_case_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Convert a dict with camelCase keys to snake_case keys.

    Args:
        data: Dict with camelCase keys.

    Returns:
        New dict with snake_case keys.
    """
    return {to_snake_case(k): v for k, v in data.items()}
