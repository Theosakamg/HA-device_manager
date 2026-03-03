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
    if key_path.exists():
        crypto_key = key_path.read_text().strip()
        key_path.chmod(0o600)  # enforce owner-only in case it was created with wider perms
        _LOGGER.debug("Loaded encryption key from %s", key_path)
    else:
        crypto_key = generate_key()
        key_path.write_text(crypto_key)
        key_path.chmod(0o600)
        _LOGGER.info("Generated new encryption key at %s", key_path)

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

    # Register sidebar panel
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Device Manager",
        sidebar_icon="mdi:devices",
        frontend_url_path="device_manager",
        config={"url": "/device_manager"},
        require_admin=False,
        config_panel_domain=DOMAIN,
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
