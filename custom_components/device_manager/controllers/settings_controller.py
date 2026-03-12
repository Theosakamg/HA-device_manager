"""API controller for user-configurable settings."""

import logging
import re

from aiohttp import web

from .base import BaseView, get_repos, csrf_protect
from ..const import DEFAULT_SETTINGS

_LOGGER = logging.getLogger(__name__)

# Validation patterns for specific settings
_SETTING_VALIDATORS: dict[str, re.Pattern] = {
    "ip_prefix": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "dns_suffix": re.compile(r"^[a-zA-Z0-9._-]+$"),
    "mqtt_topic_prefix": re.compile(r"^[a-zA-Z0-9/_-]+$"),
    "default_building_name": re.compile(r"^.{1,100}$"),
    # Provisioning validators (all allow empty string for optional fields)
    "scan_ssh_user": re.compile(r"^[a-zA-Z0-9._-]*$"),
    "scan_ssh_host": re.compile(r"^[a-zA-Z0-9._:-]*$"),
    "scan_ssh_key_file": re.compile(r"^[a-zA-Z0-9._/-]*$"),
    "scan_script_content": re.compile(r"^[\s\S]*$"),
    "bus_port": re.compile(r"^\d{1,5}$|^$"),
    "bus_host": re.compile(r"^[a-zA-Z0-9._:-]*$"),
    "bus_username": re.compile(r"^[a-zA-Z0-9.@_-]*$"),
    "ntp_server1": re.compile(r"^[a-zA-Z0-9._-]*$"),
    "bridge_host": re.compile(r"^[a-zA-Z0-9@._:-]*$"),
}

# Maximum length for any setting value
_MAX_SETTING_LENGTH = 255

# Exceptions for settings that need larger limits
_MAX_SETTING_LENGTH_EXCEPTIONS: dict[str, int] = {
    "scan_script_content": 10000,  # Bash script can be several lines
}


class SettingsAPIView(BaseView):
    """GET / PUT endpoint for application settings."""

    url = "/api/device_manager/settings"
    name = "api:device_manager:settings"

    async def get(self, request: web.Request) -> web.Response:
        """Return all settings as a JSON object.

        Missing keys are seeded from DEFAULT_SETTINGS automatically.
        """
        try:
            repo = get_repos(request)["settings"]
            settings = await repo.get_all()
            return self.json(settings)
        except Exception as err:
            _LOGGER.exception("Failed to load settings", exc_info=err)
            return self.json(
                {"error": "Internal server error"},
                status_code=500,
            )

    @csrf_protect
    async def put(self, request: web.Request) -> web.Response:
        """Update one or more settings.

        Expects a JSON body with ``{key: value}`` pairs.  Only known
        setting keys (those in ``DEFAULT_SETTINGS``) are accepted.

        Returns the full settings dict after update.
        """
        try:
            body = await request.json()
        except Exception:
            return self.json(
                {"error": "Invalid JSON body"}, status_code=400
            )

        # Filter to known keys only
        allowed = set(DEFAULT_SETTINGS.keys())
        filtered = {
            k: str(v) for k, v in body.items() if k in allowed
        }
        if not filtered:
            return self.json(
                {"error": "No valid setting keys provided"},
                status_code=400,
            )

        # Validate setting values
        for key, val in filtered.items():
            max_len = _MAX_SETTING_LENGTH_EXCEPTIONS.get(key, _MAX_SETTING_LENGTH)
            if len(val) > max_len:
                return self.json(
                    {"error": f"Setting '{key}' exceeds maximum length"},
                    status_code=400,
                )
            pattern = _SETTING_VALIDATORS.get(key)
            if pattern and not pattern.match(val):
                return self.json(
                    {"error": f"Invalid format for setting '{key}'"},
                    status_code=400,
                )

        # Security audit logging for scan_script_content changes
        if "scan_script_content" in filtered:
            import hashlib
            script_hash = hashlib.sha256(filtered["scan_script_content"].encode()).hexdigest()
            _LOGGER.warning(
                "SECURITY: scan_script_content modified (length: %d, hash: %s)",
                len(filtered["scan_script_content"]),
                script_hash[:16]
            )

        try:
            repo = get_repos(request)["settings"]
            result = await repo.set_many(filtered)
            _LOGGER.info("Settings updated: %s", list(filtered.keys()))
            return self.json(result)
        except Exception as err:
            _LOGGER.exception("Failed to update settings", exc_info=err)
            return self.json(
                {"error": "Internal server error"},
                status_code=500,
            )
