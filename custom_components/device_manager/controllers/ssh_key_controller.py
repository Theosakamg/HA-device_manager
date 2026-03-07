"""API controller for SSH private key upload."""

import logging
import os
import re
from pathlib import Path

from aiohttp import web

from .base import BaseView
from ..const import DOMAIN, SETTING_SCAN_SSH_KEY_FILE

_LOGGER = logging.getLogger(__name__)

# Directory (relative to HA config dir) where SSH keys are stored
SSH_KEY_DIR = "dm/keys"

# Restrict file names: alphanumeric, hyphen, underscore, dot — no path traversal
_VALID_FILENAME = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")

# Maximum allowed key file size (64 KiB — more than enough for any SSH key)
_MAX_KEY_SIZE = 65_536


class SSHKeyUploadAPIView(BaseView):
    """POST /api/device_manager/ssh-key/upload — upload a private key file.

    The file is saved to ``<ha_config>/dm/keys/<filename>`` with mode 0o600.
    The absolute path is then persisted in ``scan_ssh_key_file`` setting.
    """

    url = "/api/device_manager/ssh-key/upload"
    name = "api:device_manager:ssh_key_upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Handle multipart file upload."""
        hass = request.app["hass"]

        try:
            reader = await request.multipart()
        except Exception:
            return self.json({"error": "Expected multipart/form-data"}, status_code=400)

        field = await reader.next()
        if field is None or field.name != "file":
            return self.json({"error": "Missing 'file' field"}, status_code=400)

        # Sanitise filename — never trust the client-supplied name directly
        raw_name = (field.filename or "").strip()
        # Keep only the basename (no slashes)
        raw_name = os.path.basename(raw_name)
        if not _VALID_FILENAME.match(raw_name):
            return self.json(
                {"error": "Invalid filename. Use only letters, digits, dots, hyphens, underscores (max 64 chars)."},
                status_code=400,
            )

        # Read content with size cap
        chunks = []
        total = 0
        while True:
            chunk = await field.read_chunk(8192)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_KEY_SIZE:
                return self.json(
                    {"error": f"File too large (max {_MAX_KEY_SIZE // 1024} KiB)"},
                    status_code=413,
                )
            chunks.append(chunk)

        key_bytes = b"".join(chunks)
        if not key_bytes:
            return self.json({"error": "Empty file"}, status_code=400)

        # Basic sanity check: must look like a PEM key or OpenSSH key
        key_str = key_bytes.decode("utf-8", errors="replace")
        if not (
            "-----BEGIN" in key_str
            or "openssh-key-v1" in key_str.lower()
        ):
            return self.json(
                {"error": "File does not appear to be a valid PEM/OpenSSH private key"},
                status_code=400,
            )

        # Resolve destination directory resolving inside HA config dir
        config_dir = Path(hass.config.config_dir).resolve()
        key_dir = (config_dir / SSH_KEY_DIR).resolve()

        # Guard: ensure the resolved key_dir is still inside config_dir
        try:
            key_dir.relative_to(config_dir)
        except ValueError:
            _LOGGER.error("Path traversal attempt blocked: %s", key_dir)
            return self.json({"error": "Invalid destination path"}, status_code=400)

        dest = (key_dir / raw_name).resolve()

        # Guard: ensure dest file is inside key_dir
        try:
            dest.relative_to(key_dir)
        except ValueError:
            _LOGGER.error("Path traversal attempt blocked: %s", dest)
            return self.json({"error": "Invalid destination path"}, status_code=400)

        try:
            await hass.async_add_executor_job(_write_key_file, key_dir, dest, key_bytes)
        except OSError as err:
            _LOGGER.exception("Failed to write SSH key", exc_info=err)
            return self.json({"error": "Failed to write key file"}, status_code=500)

        # Persist the absolute path in settings DB
        repo = hass.data[DOMAIN]["repos"]["settings"]
        await repo.set(SETTING_SCAN_SSH_KEY_FILE, str(dest))

        _LOGGER.info("SSH key uploaded and stored: %s", dest)
        return self.json({
            "success": True,
            "path": str(dest),
            "filename": raw_name,
        })


def _write_key_file(key_dir: Path, dest: Path, content: bytes) -> None:
    """Create the key directory and write the key file with strict permissions.

    Runs in a thread-pool executor (blocking I/O).
    """
    key_dir.mkdir(parents=True, exist_ok=True)
    # Secure the directory itself
    key_dir.chmod(0o700)

    # Write atomically: write to a temp file, then rename
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        tmp.write_bytes(content)
        tmp.chmod(0o600)
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
