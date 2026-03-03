"""Base controller utilities for Device Manager API views."""

import logging
from typing import Any

from aiohttp import web

from ..const import DOMAIN
from ..utils.case_convert import to_camel_case_dict, to_snake_case_dict

_LOGGER = logging.getLogger(__name__)


# Re-export for backward compatibility with existing controller imports.
__all__ = ["to_camel_case_dict", "to_snake_case_dict", "get_repos"]


def get_repos(request: web.Request) -> dict:
    """Get the repository dict from the request's hass data.

    Args:
        request: The aiohttp request.

    Returns:
        Dict of repository instances.
    """
    hass = request.app["hass"]
    return hass.data[DOMAIN]["repos"]
