"""Static content controller for Device Manager frontend."""

import logging
from pathlib import Path

from aiohttp import web

from .base import BaseView

_LOGGER = logging.getLogger(__name__)

# Pre-computed dist directory (resolved once at import time)
_COMPONENT_PATH = Path(__file__).parent.parent
_DIST_DIR = (_COMPONENT_PATH / "frontend" / "dist").resolve()


class StaticView(BaseView):
    """Serve static frontend files from the dist directory."""

    url = "/device_manager_static/{filename}"
    name = "api:device_manager:static"
    requires_auth = False

    # Allowed file extensions for static assets
    _ALLOWED_EXTENSIONS = {".js", ".css", ".html", ".map", ".svg", ".png", ".ico"}

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Serve a static file by name.

        Validates that the resolved path stays within the dist directory
        to prevent path traversal attacks.

        Args:
            request: The aiohttp request.
            filename: Name of the static file to serve.

        Returns:
            The file content with appropriate content type.
        """
        try:
            # Validate filename: reject hidden files and path separators
            if not filename or filename.startswith(".") or "/" in filename or "\\" in filename:
                return web.Response(status=400, text="Invalid filename")

            # Validate extension
            ext = Path(filename).suffix.lower()
            if ext not in self._ALLOWED_EXTENSIONS:
                return web.Response(status=403, text="Forbidden file type")

            # Resolve and verify the path stays within dist/
            static_path = (_DIST_DIR / filename).resolve()
            if not str(static_path).startswith(str(_DIST_DIR)):
                _LOGGER.warning("Path traversal attempt blocked: %s", filename)
                return web.Response(status=403, text="Forbidden")

            if not static_path.exists():
                return web.Response(status=404, text="File not found")

            hass = request.app["hass"]
            content = await hass.async_add_executor_job(
                lambda: static_path.read_bytes()
            )

            content_type = "application/javascript"
            if ext == ".css":
                content_type = "text/css"
            elif ext == ".html":
                content_type = "text/html"
            elif ext == ".svg":
                content_type = "image/svg+xml"
            elif ext == ".png":
                content_type = "image/png"
            elif ext == ".ico":
                content_type = "image/x-icon"

            return web.Response(
                body=content,
                content_type=content_type,
                headers={
                    "Cache-Control": "no-cache",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except Exception as err:
            _LOGGER.error("Failed to serve static file %s: %s", filename, err)
            return web.Response(status=500, text="Internal server error")
