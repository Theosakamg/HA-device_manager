"""API controller for activity log operations."""

import logging

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect, rate_limit  # noqa: F401 get_repos used at runtime

_LOGGER = logging.getLogger(__name__)

# Safe upper bound for purge age (in days)
_MAX_PURGE_DAYS = 3650  # 10 years


def _safe_int(value: str, default: int) -> int:
    """Convert a string to int, returning default if invalid."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class ActivityLogAPIView(BaseView):
    """GET /api/device_manager/activity_log — paginated, filterable list."""

    url = "/api/device_manager/activity_log"
    name = "api:device_manager:activity_log"
    requires_auth = True

    @rate_limit(requests=60, window=60)
    async def get(self, request: web.Request) -> web.Response:
        """Return a paginated list of activity log entries with optional filters.

        Query parameters (all optional):
            date_from   ISO 8601 datetime string (>=)
            date_to     ISO 8601 datetime string (<=)
            event_type  'config_change' or 'action'
            entity_type e.g. 'device', 'room', …
            user        HA user display name
            severity    'info', 'warning', or 'error'
            page        Page number (default 1)
            page_size   Items per page (default 50, max 200)
        """
        repos = get_repos(request)
        q = request.query

        try:
            result = await repos["activity_log"].list_entries(
                date_from=q.get("date_from") or None,
                date_to=q.get("date_to") or None,
                event_type=q.get("event_type") or None,
                entity_type=q.get("entity_type") or None,
                user=q.get("user") or None,
                severity=q.get("severity") or None,
                page=_safe_int(q.get("page", "1"), 1),
                page_size=_safe_int(q.get("page_size", "50"), 50),
            )
            return self.json(result)
        except Exception as err:
            _LOGGER.exception("Failed to list activity log", exc_info=err)
            return self.json({"error": "Internal server error"}, status_code=500)


class ActivityLogExportAPIView(BaseView):
    """GET /api/device_manager/activity_log/export — CSV or JSON export."""

    url = "/api/device_manager/activity_log/export"
    name = "api:device_manager:activity_log:export"
    requires_auth = True

    @rate_limit(requests=10, window=60)
    async def get(self, request: web.Request) -> web.Response:
        """Export all activity log entries as CSV or JSON.

        Query parameters:
            format  'csv' or 'json' (default 'json')
        """
        import csv
        import io
        import json

        fmt = request.query.get("format", "json").lower()
        if fmt not in ("csv", "json"):
            return self.json({"error": "Invalid format. Use 'csv' or 'json'."}, status_code=400)

        repos = get_repos(request)
        try:
            # Fetch all entries (no pagination for export)
            result = await repos["activity_log"].list_entries(page_size=200)
            all_items = result["items"]
            # Fetch remaining pages if needed
            total_pages = result["pages"]
            for p in range(2, total_pages + 1):
                more = await repos["activity_log"].list_entries(page=p, page_size=200)
                all_items.extend(more["items"])
        except Exception as err:
            _LOGGER.exception("Failed to export activity log", exc_info=err)
            return self.json({"error": "Export failed"}, status_code=500)

        if fmt == "json":
            body = json.dumps(all_items, ensure_ascii=False, indent=2)
            return web.Response(
                status=200,
                body=body.encode("utf-8"),
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Disposition": 'attachment; filename="activity_log.json"',
                    **self._SECURITY_HEADERS,
                },
            )

        # CSV export
        fieldnames = ["id", "timestamp", "user", "eventType", "entityType",
                      "entityId", "message", "result", "severity"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
        writer.writeheader()
        for item in all_items:
            # Sanitize formula injection
            safe_item = {}
            for k, v in item.items():
                val = str(v) if v is not None else ""
                if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
                    val = "'" + val
                safe_item[k] = val
            writer.writerow(safe_item)

        return web.Response(
            status=200,
            body=buf.getvalue().encode("utf-8"),
            headers={
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": 'attachment; filename="activity_log.csv"',
                **self._SECURITY_HEADERS,
            },
        )


class ActivityLogPurgeAPIView(BaseView):
    """POST /api/device_manager/activity_log/purge — purge old entries."""

    url = "/api/device_manager/activity_log/purge"
    name = "api:device_manager:activity_log:purge"
    requires_auth = True

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request: web.Request) -> web.Response:
        """Delete activity log entries older than N days.

        Expects JSON body:
            { "older_than_days": 90 }
        """
        try:
            body = await request.json()
        except Exception:
            body = {}

        older_than_days = body.get("older_than_days")
        if not isinstance(older_than_days, int) or older_than_days < 1:
            return self.json(
                {"error": "older_than_days must be a positive integer"},
                status_code=400,
            )
        if older_than_days > _MAX_PURGE_DAYS:
            return self.json(
                {"error": f"older_than_days must be <= {_MAX_PURGE_DAYS}"},
                status_code=400,
            )

        repos = get_repos(request)
        try:
            deleted = await repos["activity_log"].purge(older_than_days)
            return self.json({"success": True, "deleted": deleted})
        except Exception as err:
            _LOGGER.exception("Activity log purge failed", exc_info=err)
            return self.json({"error": "Purge failed"}, status_code=500)
