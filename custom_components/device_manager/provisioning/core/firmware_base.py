"""Base class for firmware-specific adapters.

All firmware adapters (Tasmota, WLED, Zigbee) inherit from this base class.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

from ...models.device import DmDevice

logger = logging.getLogger(__name__)


class FirmwareAdapter(ABC):
    """Base class for firmware-specific provisioning adapters.

    Each adapter handles the provisioning logic for a specific firmware type.
    Adapters work directly with DmDevice model instances.
    """

    def __init__(self, manager) -> None:
        """Initialize the adapter.

        Args:
            manager: ProvisioningManager instance providing access to DB and settings.
        """
        self.manager = manager
        logger.debug(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def get_firmware_type(self) -> str:
        """Return the firmware type this adapter handles.

        Returns:
            Firmware type string (e.g., 'Tasmota', 'WLED', 'Zigbee').
        """
        pass

    def is_compatible(self, device: DmDevice) -> bool:
        """Check if this adapter is compatible with the device.

        Args:
            device: Device to check.

        Returns:
            True if this adapter can handle the device.
        """
        return (
            device._refs.firmware_name == self.get_firmware_type()
            and device.enabled
        )

    def can_deploy(self, device: DmDevice) -> bool:
        """Check if the device can be deployed (has IP, is enabled, etc.).

        Args:
            device: Device to check.

        Returns:
            True if the device is ready for deployment.
        """
        if not self.is_compatible(device):
            return False

        if not device.ip:
            logger.warning(f"Device {device.mac} has no IP address")
            return False

        return True

    @abstractmethod
    def process(self, device: DmDevice) -> None:
        """Process/deploy a single device.

        Args:
            device: Device to process.

        Raises:
            Exception: If processing fails.
        """
        pass

    def post_process(self, devices: List[DmDevice]) -> None:
        """Optional post-processing after all devices are processed.

        This is useful for firmware types that require batch operations
        (e.g., Zigbee bridge restart).

        Args:
            devices: All processed devices.
        """
        pass

    def validate(self, device: DmDevice) -> None:
        """Validate device configuration.

        Args:
            device: Device to validate.

        Raises:
            ValueError: If validation fails.
        """
        # Basic validation
        if not device.mac:
            raise ValueError("Device MAC address is required")

        hostname = device.hostname()
        if hostname and len(hostname) >= 32:
            raise ValueError(f"Hostname '{hostname}' exceeds 32 characters")
