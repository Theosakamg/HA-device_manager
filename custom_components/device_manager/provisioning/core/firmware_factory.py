"""Factory for creating firmware adapters.

Responsible for creating and managing firmware adapter instances.
"""

import logging
from typing import List, Optional

from .firmware_base import FirmwareAdapter

logger = logging.getLogger(__name__)


class FirmwareFactory:
    """Factory for creating firmware adapter instances.

    Creates adapters based on requested firmware types and stores them
    for reuse during deployment.
    """

    def __init__(self, manager, firmware_types: Optional[List[str]] = None) -> None:
        """Initialize the factory.

        Args:
            manager: ProvisioningManager instance.
            firmware_types: List of firmware types to load. If None, loads all.
        """
        self._adapters: List[FirmwareAdapter] = []
        self._manager = manager

        if firmware_types is None:
            firmware_types = ['tasmota', 'wled', 'zigbee']

        for fw_type in firmware_types:
            adapter = self._create_adapter(fw_type)
            if adapter:
                self._adapters.append(adapter)

    def _create_adapter(self, firmware_type: str) -> Optional[FirmwareAdapter]:
        """Create an adapter for the specified firmware type.

        Args:
            firmware_type: Firmware type string (case-insensitive).

        Returns:
            Adapter instance or None if type is unknown.
        """
        fw_type_lower = firmware_type.lower()

        try:
            if fw_type_lower == 'tasmota':
                from ..adapters.tasmota import TasmotaAdapter
                logger.info("Loaded Tasmota adapter")
                return TasmotaAdapter(self._manager)

            elif fw_type_lower == 'wled':
                from ..adapters.wled import WLEDAdapter
                logger.info("Loaded WLED adapter")
                return WLEDAdapter(self._manager)

            elif fw_type_lower == 'zigbee':
                from ..adapters.zigbee import ZigbeeAdapter
                logger.info("Loaded Zigbee adapter")
                return ZigbeeAdapter(self._manager)

            else:
                logger.warning(f"Unknown firmware type: {firmware_type}")
                return None

        except ImportError as e:
            logger.error(f"Failed to import adapter for {firmware_type}: {e}")
            return None

    def get_adapters(self) -> List[FirmwareAdapter]:
        """Get all loaded adapters.

        Returns:
            List of adapter instances.
        """
        return self._adapters

    def get_adapter_for_device(self, device) -> Optional[FirmwareAdapter]:
        """Get the appropriate adapter for a device.

        Args:
            device: Device to find adapter for.

        Returns:
            Compatible adapter or None.
        """
        for adapter in self._adapters:
            if adapter.is_compatible(device):
                return adapter
        return None
