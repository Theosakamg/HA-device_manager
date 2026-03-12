"""Generic CRUD controller views for Device Manager.

Provides ``CrudListView`` and ``CrudDetailView`` base classes that handle
the repetitive GET-list / POST / GET-by-id / PUT / DELETE boilerplate.
Entity-specific controllers only declare configuration attributes.
"""

import logging
from typing import Any, Callable, Optional

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect
from ..models.base import SerializableMixin
from ..utils.case_convert import to_snake_case_dict

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


def _validate_slug(data: dict[str, Any]) -> str | None:
    """Check that slug field is non-empty if present.

    Returns an error message if validation fails, None otherwise.
    """
    if "slug" in data:
        slug = data.get("slug", "")
        if not slug or (isinstance(slug, str) and slug.strip() == ""):
            return "Field 'slug' cannot be empty"
    return None


def _validate_state(data: dict[str, Any]) -> str | None:
    """Check that state field has a valid value if present.

    Returns an error message if validation fails, None otherwise.
    """
    if "state" in data:
        state = data.get("state", "")
        valid_states = ("deployed", "parking", "out_of_order", "deployed_hot")
        if state not in valid_states:
            return f"Field 'state' must be one of {valid_states}, got '{state}'"
    return None


# ------------------------------------------------------------------
# Helper utilities
# ------------------------------------------------------------------


async def _get_or_404(
    view: BaseView,
    repos: dict,
    repo_key: str,
    entity_id: int,
    entity_name: str,
) -> Any | web.Response:
    """Fetch an entity model by ID or return a 404 JSON response.

    Args:
        view: The current view (provides ``self.json``).
        repos: Repository dict.
        repo_key: Key in repo dict.
        entity_id: Integer PK.
        entity_name: Human readable name for the error message.

    Returns:
        A model instance if found, or an ``aiohttp.web.Response`` (404).
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
                _LOGGER.exception("Failed to %s %s", action, entity_name, exc_info=err)
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


class CrudListView(BaseView):
    """Generic list + create endpoint.

    Subclasses **must** set:
        * ``url``        – e.g. ``"/api/device_manager/homes"``
        * ``name``       – e.g. ``"api:device_manager:homes"``
        * ``repo_key``   – e.g. ``"home"``
        * ``entity_name``– e.g. ``"Home"``

    Optional overrides:
        * ``normalize_data``    – pre-process incoming data before create.
        * ``filter_param``      – query-string key used for optional filtering.
        * ``filter_method``     – repo method name when the filter is present.
        * ``_serialize_entity`` – override to customise serialization output.
    """

    repo_key: str = ""
    entity_name: str = ""
    normalize_data: Optional[Callable[[dict], dict]] = None
    filter_param: Optional[str] = None
    filter_method: Optional[str] = None

    def _serialize_entity(self, entity: SerializableMixin) -> dict[str, Any]:
        """Serialize a model instance to a camelCase dict for the API response.

        Override in subclasses for custom serialization (e.g. computed fields).

        Args:
            entity: A typed model instance returned by the repository.

        Returns:
            A camelCase dict suitable for JSON serialization.
        """
        return entity.to_camel_dict()

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
                return self.json([self._serialize_entity(i) for i in items])
        items = await repos[self.repo_key].find_all()
        return self.json([self._serialize_entity(i) for i in items])

    @_handle_errors("entity")
    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        """Create a new entity from the JSON body."""
        repos = get_repos(request)
        data = await request.json()
        snake_data = to_snake_case_dict(data)
        # Validate string lengths
        length_err = _validate_string_lengths(snake_data)
        if length_err:
            return self.json({"error": length_err}, status_code=400)
        # Validate slug is non-empty
        slug_err = _validate_slug(snake_data)
        if slug_err:
            return self.json({"error": slug_err}, status_code=400)
        # Validate state has valid value
        state_err = _validate_state(snake_data)
        if state_err:
            return self.json({"error": state_err}, status_code=400)
        if self.normalize_data:
            snake_data = self.normalize_data(snake_data)
        new_id = await repos[self.repo_key].create(snake_data)
        entity = await repos[self.repo_key].find_by_id(new_id)
        return self.json(self._serialize_entity(entity), status_code=201)


class CrudDetailView(BaseView):
    """Generic get / update / delete endpoint for a single entity.

    Subclasses **must** set:
        * ``url``         – e.g. ``"/api/device_manager/homes/{entity_id}"``
        * ``name``        – e.g. ``"api:device_manager:home"``
        * ``repo_key``    – e.g. ``"home"``
        * ``entity_name`` – e.g. ``"Home"``

    Optional overrides:
        * ``normalize_data``    – pre-process incoming data before update.
        * ``_serialize_entity`` – override to customise serialization output.
    """

    repo_key: str = ""
    entity_name: str = ""
    normalize_data: Optional[Callable[[dict], dict]] = None

    def _serialize_entity(self, entity: SerializableMixin) -> dict[str, Any]:
        """Serialize a model instance to a camelCase dict for the API response.

        Override in subclasses for custom serialization (e.g. computed fields).

        Args:
            entity: A typed model instance returned by the repository.

        Returns:
            A camelCase dict suitable for JSON serialization.
        """
        return entity.to_camel_dict()

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
        return self.json(self._serialize_entity(result))

    @_handle_errors("entity")
    @csrf_protect
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
        # Validate slug is non-empty
        slug_err = _validate_slug(snake_data)
        if slug_err:
            return self.json({"error": slug_err}, status_code=400)
        # Validate state has valid value
        state_err = _validate_state(snake_data)
        if state_err:
            return self.json({"error": state_err}, status_code=400)
        if self.normalize_data:
            snake_data = self.normalize_data(snake_data)
        await repos[self.repo_key].update(eid, snake_data)
        updated = await repos[self.repo_key].find_by_id(eid)
        return self.json(self._serialize_entity(updated))

    @_handle_errors("entity")
    @csrf_protect
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
