"""The HA Device Manager integration."""

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DB_NAME, DOMAIN
from .controllers import ALL_VIEWS
from .repositories import (
    BuildingRepository,
    FloorRepository,
    RoomRepository,
    DeviceRepository,
    DeviceModelRepository,
    DeviceFirmwareRepository,
    DeviceFunctionRepository,
    SettingsRepository,
)
from .services.database_manager import DatabaseManager
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
    """Set up the Device Manager component.

    Initializes the database, creates repository instances, and registers
    all API views and the sidebar panel.
    """
    _LOGGER.info("Setting up Device Manager")

    hass.data.setdefault(DOMAIN, {})

    # Initialize database
    db_path = Path(hass.config.config_dir) / DB_NAME
    db_manager = DatabaseManager(db_path)
    await db_manager.initialize()
    hass.data[DOMAIN]["db"] = db_manager

    # Load or generate symmetric encryption key (stored next to the DB)
    key_path = Path(hass.config.config_dir) / ".device_manager.key"
    crypto_key = await hass.async_add_executor_job(_load_or_create_key, key_path)
    _LOGGER.debug("Encryption key ready (path: %s)", key_path)

    # Create repositories
    repos = {
        "building": BuildingRepository(db_manager),
        "floor": FloorRepository(db_manager),
        "room": RoomRepository(db_manager, crypto_key=crypto_key),
        "device": DeviceRepository(db_manager),
        "device_model": DeviceModelRepository(db_manager),
        "device_firmware": DeviceFirmwareRepository(db_manager),
        "device_function": DeviceFunctionRepository(db_manager),
        "settings": SettingsRepository(db_manager),
    }
    hass.data[DOMAIN]["repos"] = repos

    # Register all API views
    for view_class in ALL_VIEWS:
        hass.http.register_view(view_class())

    # Register sidebar panel as a native HA custom panel (web component)
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Device Manager",
        sidebar_icon="mdi:devices",
        frontend_url_path="device_manager",
        config={
            "_panel_custom": {
                "name": "dm-app-shell",
                "module_url": "/device_manager_static/device-manager.js",
            }
        },
        require_admin=False,
    )

    _LOGGER.info("Device Manager setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Device Manager from a config entry."""
    _LOGGER.info("Setting up Device Manager config entry")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Device Manager config entry")
    # Close database connection
    db_manager = hass.data.get(DOMAIN, {}).get("db")
    if db_manager:
        await db_manager.close()
    return True
