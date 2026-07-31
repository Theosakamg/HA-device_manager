"""Tasmota firmware version comparison helpers.

Tasmota reports its version in forms such as ``14.5.0``, ``14.5.0(release)``,
``14.5.0(tasmota)`` or ``v14.5.0``. The original pyscript compared these
strings lexicographically (``"14.5.1" > "14.10.0"`` evaluates to ``True`` even
though 14.10.0 is newer), which produced wrong upgrade decisions. This module
parses versions into numeric tuples so comparisons are numerically correct.
"""

from typing import Tuple


def parse_tasmota_version(version: str) -> Tuple[int, ...]:
    """Parse a Tasmota version string into a numeric tuple.

    Strips a leading ``v`` and any trailing ``(...)`` build/flavour suffix,
    then splits the dotted numeric parts. Non-numeric parts are treated as 0
    so a malformed value never raises.

    Args:
        version: Raw version string (e.g. ``"14.5.0(release)"``, ``"v14.5.0"``).

    Returns:
        Tuple of integers (e.g. ``(14, 5, 0)``). Empty input yields ``()``.
    """
    if not version:
        return ()

    cleaned = version.strip().lstrip("vV")

    # Drop any "(release)" / "(tasmota)" suffix.
    paren = cleaned.find("(")
    if paren != -1:
        cleaned = cleaned[:paren]

    cleaned = cleaned.strip()
    if not cleaned:
        return ()

    parts = []
    for chunk in cleaned.split("."):
        chunk = chunk.strip()
        # Keep only the leading digits of each chunk (e.g. "0-dev" -> 0).
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)

    return tuple(parts)


def is_newer(target: str, current: str) -> bool:
    """Return True when *target* is a strictly newer version than *current*.

    Missing minor/patch components are treated as 0 (so ``14.5`` == ``14.5.0``)
    by right-padding the shorter tuple before comparison.

    Args:
        target: Candidate target version (e.g. the latest available).
        current: The device's currently installed version.

    Returns:
        True if ``target`` > ``current`` numerically, else False.
    """
    t = parse_tasmota_version(target)
    c = parse_tasmota_version(current)

    length = max(len(t), len(c))
    t_padded = t + (0,) * (length - len(t))
    c_padded = c + (0,) * (length - len(c))

    return t_padded > c_padded
