"""Provisioning manager coordinates device loading and deployment.

Replaces the legacy GlobalManager and DevicesManager.
"""

import logging
from typing import List, Optional

from ...services.database_manager import DatabaseManager
from ...repositories import DeviceRepository, DeviceFirmwareRepository
from ...models.device import DmDevice

logger = logging.getLogger(__name__)


class ProvisioningManager:
    """Manages device loading and coordinates provisioning operations.

    This class replaces the legacy GlobalManager, providing a clean interface
    for loading devices from the database and accessing configuration settings.
    The database connection is provided at initialization and reused for all
    operations to avoid constant open/close cycles.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the manager.

        Args:
            db: DatabaseManager instance (must be already initialized).
        """
        self.db = db
        self._devices: List[DmDevice] = []
        self._settings: dict = {}

    async def load_devices(
        self,
        mac_filter: Optional[List[str]] = None,
        enabled_only: bool = True,
        states_filter: Optional[List[str]] = None
    ) -> List[DmDevice]:
        """Load devices from the database.

        Args:
            mac_filter: Optional list of MAC addresses to filter by.
            enabled_only: If True, only load enabled devices.
            states_filter: Optional list of states to include
                          (e.g. ['deployed', 'deployed_hot']).

        Returns:
            List of DmDevice instances with populated transient fields.
        """
        repo = DeviceRepository(self.db)

        try:
            # Load all devices with joins (transient fields populated)
            devices = await repo.find_all()

            # Apply filters
            if enabled_only:
                devices = [d for d in devices if d.enabled]

            if states_filter:
                devices = [d for d in devices if d.state in states_filter]

            if mac_filter:
                mac_filter_lower = [m.lower().strip() for m in mac_filter]
                devices = [d for d in devices if d.mac.lower() in mac_filter_lower]

            self._devices = devices
            logger.debug(f"Loaded {len(self._devices)} devices from database")

            return self._devices

        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            return []

    def load_devices_sync(
        self,
        mac_filter: Optional[List[str]] = None,
        enabled_only: bool = True,
        states_filter: Optional[List[str]] = None
    ) -> List[DmDevice]:
        """Synchronous wrapper for load_devices.

        Note: Prefer using async version when possible.

        Args:
            mac_filter: Optional list of MAC addresses to filter by.
            enabled_only: If True, only load enabled devices.
            states_filter: Optional list of states to include
                          (e.g. ['deployed', 'deployed_hot']).

        Returns:
            List of DmDevice instances.
        """
        import asyncio
        return asyncio.run(self.load_devices(mac_filter, enabled_only, states_filter))

    def get_devices(self) -> List[DmDevice]:
        """Get previously loaded devices.

        Returns:
            List of DmDevice instances.
        """
        return self._devices

    async def load_settings(self) -> dict:
        """Load application settings from the database.

        Returns:
            Dictionary of settings.
        """
        try:
            from ...repositories import SettingsRepository
            repo = SettingsRepository(self.db)
            self._settings = await repo.get_all()
            logger.debug(f"Loaded {len(self._settings)} settings")
            return self._settings
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return {}

    def get_settings(self) -> dict:
        """Get previously loaded settings.

        Returns:
            Dictionary of settings.
        """
        return self._settings

    def get_setting(self, key: str, default=None):
        """Get a specific setting value.

        Args:
            key: Setting key.
            default: Default value if key not found.

        Returns:
            Setting value or default.
        """
        return self._settings.get(key, default)

    async def load_deployable_firmwares(self) -> List[str]:
        """Load deployable firmware types from the database.

        Returns:
            List of firmware names that are enabled and deployable.
        """
        try:
            repo = DeviceFirmwareRepository(self.db)
            firmwares = await repo.find_all()

            # Filter for enabled and deployable firmwares
            deployable = [
                fw.name.lower()
                for fw in firmwares
                if fw.enabled and fw.deployable and fw.name
            ]

            logger.debug(f"Loaded {len(deployable)} deployable firmwares from database: {deployable}")
            return deployable

        except Exception as e:
            logger.error(f"Failed to load deployable firmwares: {e}")
            return []

    def load_deployable_firmwares_sync(self) -> List[str]:
        """Synchronous wrapper for load_deployable_firmwares.

        Note: Prefer using async version when possible.

        Returns:
            List of firmware names.
        """
        import asyncio
        return asyncio.run(self.load_deployable_firmwares())
