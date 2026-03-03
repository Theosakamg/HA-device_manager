"""Generic CRUD controller views for Device Manager.

Provides ``CrudListView`` and ``CrudDetailView`` base classes that handle
the repetitive GET-list / POST / GET-by-id / PUT / DELETE boilerplate.
Entity-specific controllers only declare configuration attributes.
"""

import logging
from typing import Any, Callable, Optional

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .base import get_repos
from ..utils.case_convert import to_camel_case_dict, to_snake_case_dict

_LOGGER = logging.getLogger(__name__)

# Maximum allowed length for string fields to prevent abuse
_MAX_FIELD_LENGTH = 5_000


def _safe_int(value: str, field_name: str = "id") -> int | None:
    """Convert a string to int, returning None if invalid."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _validate_string_lengths(
    data: dict[str, Any], max_length: int = _MAX_FIELD_LENGTH
) -> str | None:
    """Check that all string values are within max_length.

    Returns an error message if validation fails, None otherwise.
    """
    for key, val in data.items():
        if isinstance(val, str) and len(val) > max_length:
            return f"Field '{key}' exceeds maximum length ({max_length})"
    return None


# ------------------------------------------------------------------
# Helper utilities
# ------------------------------------------------------------------


async def _get_or_404(
    view: HomeAssistantView,
    repos: dict,
    repo_key: str,
    entity_id: int,
    entity_name: str,
) -> Any | web.Response:
    """Fetch an entity by ID or return a 404 JSON response.

    Args:
        view: The current view (provides ``self.json``).
        repos: Repository dict.
        repo_key: Key in repo dict.
        entity_id: Integer PK.
        entity_name: Human readable name for the error message.

    Returns:
        The entity dict if found, or an ``aiohttp.web.Response`` (404).
    """
    entity = await repos[repo_key].find_by_id(entity_id)
    if not entity:
        return view.json({"error": f"{entity_name} not found"}, status_code=404)
    return entity


def _handle_errors(entity_name: str):
    """Decorator that wraps a handler in try/except with logging.

    Args:
        entity_name: Used in the log message prefix.
    """

    def decorator(func):
        async def wrapper(self, request, *args, **kwargs):
            try:
                return await func(self, request, *args, **kwargs)
            except Exception as err:
                action = func.__name__  # get / post / put / delete
                _LOGGER.exception("Failed to %s %s", action, entity_name)
                return self.json(
                    {"error": "Internal server error"},
                    status_code=500,
                )

        # Preserve the method name so that aiohttp routing works.
        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    return decorator


# ------------------------------------------------------------------
# Generic CRUD views
# ------------------------------------------------------------------


class CrudListView(HomeAssistantView):
    """Generic list + create endpoint.

    Subclasses **must** set:
        * ``url``        – e.g. ``"/api/device_manager/homes"``
        * ``name``       – e.g. ``"api:device_manager:homes"``
        * ``repo_key``   – e.g. ``"home"``
        * ``entity_name``– e.g. ``"Home"``

    Optional overrides:
        * ``normalize_data``  – pre-process incoming data before create.
        * ``filter_param``    – query-string key used for optional filtering.
        * ``filter_method``   – repo method name when the filter is present.
    """

    requires_auth = True
    repo_key: str = ""
    entity_name: str = ""
    normalize_data: Optional[Callable[[dict], dict]] = None
    filter_param: Optional[str] = None
    filter_method: Optional[str] = None

    @_handle_errors("entities")
    async def get(self, request: web.Request) -> web.Response:
        """Return all entities, with optional parent filtering."""
        repos = get_repos(request)
        if self.filter_param and self.filter_method:
            parent_id = request.query.get(self.filter_param)
            if parent_id:
                parent_id_int = _safe_int(parent_id, self.filter_param)
                if parent_id_int is None:
                    return self.json(
                        {"error": f"Invalid {self.filter_param} format"},
                        status_code=400,
                    )
                items = await getattr(repos[self.repo_key], self.filter_method)(
                    parent_id_int
                )
                return self.json([to_camel_case_dict(i) for i in items])
        items = await repos[self.repo_key].find_all()
        return self.json([to_camel_case_dict(i) for i in items])

    @_handle_errors("entity")
    async def post(self, request: web.Request) -> web.Response:
        """Create a new entity from the JSON body."""
        repos = get_repos(request)
        data = await request.json()
        snake_data = to_snake_case_dict(data)
        # Validate string lengths
        length_err = _validate_string_lengths(snake_data)
        if length_err:
            return self.json({"error": length_err}, status_code=400)
        if self.normalize_data:
            snake_data = self.normalize_data(snake_data)
        new_id = await repos[self.repo_key].create(snake_data)
        entity = await repos[self.repo_key].find_by_id(new_id)
        return self.json(to_camel_case_dict(entity), status_code=201)


class CrudDetailView(HomeAssistantView):
    """Generic get / update / delete endpoint for a single entity.

    Subclasses **must** set:
        * ``url``         – e.g. ``"/api/device_manager/homes/{entity_id}"``
        * ``name``        – e.g. ``"api:device_manager:home"``
        * ``repo_key``    – e.g. ``"home"``
        * ``entity_name`` – e.g. ``"Home"``

    Optional overrides:
        * ``normalize_data`` – pre-process incoming data before update.
    """

    requires_auth = True
    repo_key: str = ""
    entity_name: str = ""
    normalize_data: Optional[Callable[[dict], dict]] = None

    @_handle_errors("entity")
    async def get(self, request: web.Request, entity_id: str) -> web.Response:
        """Get a single entity by ID."""
        repos = get_repos(request)
        eid = _safe_int(entity_id)
        if eid is None:
            return self.json({"error": "Invalid ID format"}, status_code=400)
        result = await _get_or_404(self, repos, self.repo_key, eid, self.entity_name)
        if isinstance(result, web.Response):
            return result
        return self.json(to_camel_case_dict(result))

    @_handle_errors("entity")
    async def put(self, request: web.Request, entity_id: str) -> web.Response:
        """Update an entity by ID."""
        repos = get_repos(request)
        eid = _safe_int(entity_id)
        if eid is None:
            return self.json({"error": "Invalid ID format"}, status_code=400)
        result = await _get_or_404(self, repos, self.repo_key, eid, self.entity_name)
        if isinstance(result, web.Response):
            return result
        data = await request.json()
        snake_data = to_snake_case_dict(data)
        # Validate string lengths
        length_err = _validate_string_lengths(snake_data)
        if length_err:
            return self.json({"error": length_err}, status_code=400)
        if self.normalize_data:
            snake_data = self.normalize_data(snake_data)
        await repos[self.repo_key].update(eid, snake_data)
        updated = await repos[self.repo_key].find_by_id(eid)
        return self.json(to_camel_case_dict(updated))

    @_handle_errors("entity")
    async def delete(self, request: web.Request, entity_id: str) -> web.Response:
        """Delete an entity by ID."""
        repos = get_repos(request)
        eid = _safe_int(entity_id)
        if eid is None:
            return self.json({"error": "Invalid ID format"}, status_code=400)
        result = await _get_or_404(self, repos, self.repo_key, eid, self.entity_name)
        if isinstance(result, web.Response):
            return result
        await repos[self.repo_key].delete(eid)
        return self.json({"result": "ok"})
