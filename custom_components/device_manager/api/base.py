"""Base controller utilities for Device Manager API views."""

import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Any


from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from ..const import DATA_KEY_DB, DATA_KEY_REPOS, DOMAIN
from ..utils.case_convert import to_camel_case_dict, to_snake_case_dict

_LOGGER = logging.getLogger(__name__)


# Re-export for backward compatibility with existing controller imports.
__all__ = ["to_camel_case_dict", "to_snake_case_dict", "get_repos", "get_db_path", "rate_limit", "csrf_protect", "fmt_entity_label"]

# ---------------------------------------------------------------------------
# In-memory rate limiter
# ---------------------------------------------------------------------------

# Store: {(endpoint_key, client_id): [request_timestamp, ...]}
_rate_limit_store: dict[tuple, list[float]] = defaultdict(list)


def rate_limit(requests: int = 60, window: int = 60):
    """Decorator to enforce a sliding-window rate limit on an aiohttp handler.

    Args:
        requests: Maximum number of requests allowed per ``window`` seconds.
        window:   Time window in seconds (default: 60).

    Returns HTTP 429 with a ``Retry-After`` header when the limit is exceeded.
    The client is identified by the first value of ``X-Forwarded-For`` (if set
    by a trusted reverse proxy) or the raw remote address — keeping things
    simple and dependency-free while still blocking bulk abuse.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request: web.Request, *args, **kwargs) -> web.Response:
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            client_id = forwarded_for.split(",")[0].strip() if forwarded_for else (request.remote or "unknown")
            key = (func.__qualname__, client_id)

            now = time.monotonic()
            cutoff = now - window

            # Evict expired timestamps and check limit (no async lock needed — GIL
            # guarantees list mutation atomicity for CPython; acceptable for HA)
            timestamps = _rate_limit_store[key]
            fresh = [t for t in timestamps if t > cutoff]

            if len(fresh) >= requests:
                _LOGGER.warning(
                    "Rate limit exceeded: endpoint=%s client=%s (%d/%d req in %ds)",
                    func.__qualname__, client_id, len(fresh), requests, window,
                )
                # Persist pruned list without the new timestamp
                if fresh:
                    _rate_limit_store[key] = fresh
                else:
                    _rate_limit_store.pop(key, None)
                return web.Response(
                    status=429,
                    headers={"Retry-After": str(window), "Content-Type": "application/json"},
                    text='{"error": "Too many requests. Please try again later."}',
                )

            fresh.append(now)
            _rate_limit_store[key] = fresh
            return await func(self, request, *args, **kwargs)  # type: ignore[no-any-return]

        return wrapper
    return decorator


def csrf_protect(func):
    """Decorator that enforces the anti-CSRF custom header on a handler.

    Blocks the request with HTTP 403 if ``X-Requested-With: XMLHttpRequest``
    is absent. Browsers cannot send custom headers in cross-origin requests
    without a CORS preflight (which HA denies for external origins), so
    presence of this header proves the request originates from same-origin
    JavaScript — not from a forged form submission on another site.

    Apply to all state-changing handlers (POST, PUT, DELETE).
    """
    @wraps(func)
    async def wrapper(self, request: web.Request, *args, **kwargs) -> web.Response:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            _LOGGER.warning(
                "CSRF check failed for %s: missing X-Requested-With header from %s",
                func.__qualname__,
                request.remote,
            )
            return web.Response(
                status=403,
                headers={"Content-Type": "application/json"},
                text='{"error": "Forbidden"}',
            )
        return await func(self, request, *args, **kwargs)  # type: ignore[no-any-return]

    # Preserve method name so aiohttp routing works correctly
    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    return wrapper


def get_repos(request: web.Request) -> dict[str, Any]:
    """Return the shared repository dict.

    Single coupling point between controllers and hass.data.  All
    controllers must go through this helper instead of accessing
    ``hass.data[DOMAIN]`` directly.
    """
    hass = request.app["hass"]
    repos: dict[str, Any] = hass.data[DOMAIN][DATA_KEY_REPOS]
    return repos


def get_db_path(request: web.Request):
    """Return the SQLite database Path from the app stack.

    Use this to pass a plain ``Path`` to executor jobs (provisioning
    layer) so they can open their own short-lived connection without
    any dependency on the HA event loop or the shared DatabaseManager.
    """
    hass = request.app["hass"]
    return hass.data[DOMAIN][DATA_KEY_DB].db_path


def get_request_user(request: web.Request) -> str:
    """Extract the HA user display name from the authenticated request.

    Falls back to 'system' when the user cannot be resolved (e.g. during
    automated calls or tests).

    Args:
        request: The incoming aiohttp request.

    Returns:
        The user's display name string.
    """
    try:
        user = request.get("hass_user")
        if user is not None:
            return user.name or "system"
    except Exception:
        pass
    return "system"


def fmt_entity_label(entity_type: str, name: str, eid: int | None = None, slug: str = "") -> str:
    """Return a standardised entity reference: 'Type - Name [id=N, slug=xxx]'."""
    parts = []
    if eid is not None:
        parts.append(f"id={eid}")
    if slug:
        parts.append(f"slug={slug}")
    meta = f" [{', '.join(parts)}]" if parts else ""
    return f"{entity_type} - {name}{meta}"


async def emit_activity_log(
    request: web.Request,
    event_type: str,
    entity_type: str,
    message: str,
    *,
    entity_id: Any = None,
    result: str | None = None,
    severity: str = "info",
) -> None:
    """Fire-and-forget wrapper to append an activity log entry.

    Any exception is caught and logged — a logging failure must never
    propagate and block the actual operation.

    Args:
        request:     The current aiohttp request (for repos + user resolution).
        event_type:  'config_change' or 'action'.
        entity_type: e.g. 'device', 'room', 'floor', …
        message:     Human-readable Markdown message.
        entity_id:   Optional numeric FK to the affected record.
        result:      Optional raw output / error string.
        severity:    'info', 'warning', or 'error'.
    """
    try:
        repos = get_repos(request)
        user = get_request_user(request)
        await repos["activity_log"].log_entry(
            user=user,
            event_type=event_type,
            entity_type=entity_type,
            message=message,
            entity_id=entity_id,
            result=result,
            severity=severity,
        )
    except Exception as exc:
        _LOGGER.debug("Activity log emission failed (non-critical): %s", exc)


class BaseView(HomeAssistantView):
    """Base view with common utilities for Device Manager API controllers."""

    requires_auth = True

    # Security headers added to every API response
    _SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
    }

    def json(self, result: Any, status_code: int = 200) -> web.Response:  # type: ignore[override]
        """Return a JSON response with security headers."""
        response: web.Response = super().json(result, status_code=status_code)  # type: ignore[assignment]
        response.headers.update(self._SECURITY_HEADERS)
        return response
