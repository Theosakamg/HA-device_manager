"""The HA Device Manager integration."""

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CRYPTO_KEY_FILENAME,
    DATA_KEY_CRYPTO,
    DATA_KEY_DB,
    DB_NAME,
    DOMAIN,
    FRONTEND_JS_FILENAME,
    PANEL_COMPONENT_NAME,
    STATIC_URL_BASE,
)
from .api import ALL_VIEWS
from .persistence.database_manager import DatabaseManager
from .utils.crypto import generate_key

_LOGGER = logging.getLogger(__name__)


def _load_or_create_key(key_path: Path) -> str:
    """Load the encryption key from disk, or generate and persist a new one.

    Runs in a thread-pool executor to avoid blocking the event loop.
    """
    if key_path.exists():
        key = key_path.read_text().strip()
        key_path.chmod(0o600)
        return key
    key = generate_key()
    key_path.write_text(key)
    key_path.chmod(0o600)
    return key


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Auto-create the config entry if none exists (system integration, no user input needed)."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Device Manager from a config entry.

    Initializes the database, creates repository instances, and registers
    all API views and the sidebar panel.
    """
    _LOGGER.info("Setting up Device Manager")

    hass.data.setdefault(DOMAIN, {})

    # Initialize database
    db_path = Path(hass.config.config_dir) / DB_NAME
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    hass.data[DOMAIN][DATA_KEY_DB] = db_manager

    # Load or generate symmetric encryption key (stored next to the DB)
    key_path = Path(hass.config.config_dir) / CRYPTO_KEY_FILENAME
    crypto_key = await hass.async_add_executor_job(_load_or_create_key, key_path)
    _LOGGER.debug("Encryption key ready (path: %s)", key_path)

    # Store the encryption key so request handlers can build repositories on demand.
    hass.data[DOMAIN][DATA_KEY_CRYPTO] = crypto_key

    # Register all API views
    for view_class in ALL_VIEWS:
        hass.http.register_view(view_class())

    # Register Tasmota runtime services (restart, upgrade, status, ...)
    from .ha.service_registration import async_register_services

    async_register_services(hass)

    # Register sidebar panel as a native HA custom panel (web component)
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Device Manager",
        sidebar_icon="mdi:devices",
        frontend_url_path="device_manager",
        config={
            "_panel_custom": {
                "name": PANEL_COMPONENT_NAME,
                "module_url": f"{STATIC_URL_BASE}/{FRONTEND_JS_FILENAME}",
            }
        },
        require_admin=False,
    )

    _LOGGER.info("Device Manager setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Device Manager config entry")
    # Unregister Tasmota runtime services
    from .ha.service_registration import async_unregister_services

    async_unregister_services(hass)
    # Remove the sidebar panel so it can be re-registered on reload
    frontend.async_remove_panel(hass, "device_manager")
    # Close database connection
    db_manager = hass.data.get(DOMAIN, {}).get(DATA_KEY_DB)
    if db_manager:
        await db_manager.close()
    hass.data.pop(DOMAIN, None)
    return True
