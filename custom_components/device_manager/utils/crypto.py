"""Symmetric encryption utilities using Fernet (AES-128-CBC + HMAC-SHA256).

Fernet guarantees that any message encrypted cannot be manipulated or read
without the key. Encryption is reversible using the same key.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(Exception):
    """Raised when a plaintext value cannot be encrypted (invalid key or internal error)."""


class DecryptionError(Exception):
    """Raised when a Fernet token cannot be decrypted (wrong key or corrupted data)."""

_LOGGER = logging.getLogger(__name__)


def generate_key() -> str:
    """Generate a new URL-safe base64-encoded Fernet key (44 chars).

    Returns:
        A 44-character URL-safe base64 string suitable for Fernet.
    """
    return str(Fernet.generate_key().decode())


def encrypt(plain: str, key: str) -> str:
    """Encrypt a plaintext string using Fernet (AES-128-CBC + HMAC-SHA256).

    Args:
        plain: The plaintext string to encrypt.
        key: The Fernet key – URL-safe base64, 44 characters.

    Returns:
        A Fernet token (base64-encoded) or ``""`` if *plain* is empty.

    Raises:
        EncryptionError: When *plain* is non-empty but encryption fails
            (invalid key, etc.).  The exception is raised so callers fail
            explicitly rather than silently persisting a blank value.
    """
    if not plain:
        return ""
    try:
        f = Fernet(key.encode())
        return str(f.encrypt(plain.encode()).decode())
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Encryption failed: %s", err)
        raise EncryptionError(str(err)) from err


def decrypt(cipher: str, key: str) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext.

    Args:
        cipher: The Fernet token to decrypt.
        key: The Fernet key – URL-safe base64, 44 characters.

    Returns:
        The original plaintext, or ``""`` when *cipher* is empty
        (field was never set / blank value).

    Raises:
        DecryptionError: When *cipher* is non-empty but cannot be decrypted
            (wrong key, corrupted token, or any other Fernet error).
            This is distinct from an empty/unset value so callers can
            surface the error appropriately.
    """
    if not cipher:
        return ""
    try:
        f = Fernet(key.encode())
        return str(f.decrypt(cipher.encode()).decode())
    except InvalidToken as exc:
        _LOGGER.warning("Decryption failed: invalid token (bad key or corrupted data)")
        raise DecryptionError("Invalid Fernet token – bad key or corrupted data") from exc
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Decryption failed: %s", err)
        raise DecryptionError(str(err)) from err
