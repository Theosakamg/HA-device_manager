"""Zigbee firmware adapter.

Handles provisioning of Zigbee devices via Zigbee2MQTT bridge.
"""

import errno
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import yaml
from paho.mqtt.publish import single as mqtt_single
from paho.mqtt.subscribe import simple as mqtt_simple

from ..core.firmware_base import FirmwareAdapter
from ..utility import get_config
from ...models.device import DmDevice

logger = logging.getLogger(__name__)


# Constants
FIRMWARE_TYPE = "Zigbee"
FOLDER_BACKUP = "dm/backup/zigbee"
ZIGBEE_CONFIG_FILE = "/tmp/devices.yml"


class ZigbeeAdapter(FirmwareAdapter):
    """Adapter for provisioning Zigbee devices via Zigbee2MQTT."""

    def __init__(self, manager) -> None:
        """Initialize the Zigbee adapter.

        Args:
            manager: ProvisioningManager instance.
        """
        super().__init__(manager)
        self.backup_path: Optional[str] = None
        self.zigbee_devices: Dict[str, Dict] = {}
        self.devices_to_configure: List[DmDevice] = []
        self._create_backup_folder()
        self._create_temp_config_file()

    def get_firmware_type(self) -> str:
        """Return firmware type."""
        return FIRMWARE_TYPE

    def _create_backup_folder(self) -> None:
        """Create backup folder for config dumps."""
        backup_dir = os.path.join(
            os.getcwd(),
            FOLDER_BACKUP,
            datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

        try:
            os.makedirs(backup_dir, exist_ok=True)
            self.backup_path = backup_dir
            logger.debug(f"Created backup folder: {backup_dir}")
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error(f"Failed to create backup folder: {e}")
                raise

    def _create_temp_config_file(self) -> None:
        """Create temporary config file for devices."""
        if not os.path.exists(ZIGBEE_CONFIG_FILE):
            Path(ZIGBEE_CONFIG_FILE).touch()

    def _get_mqtt_params(self) -> Dict[str, Any]:
        """Get MQTT connection parameters."""
        return {
            'hostname': get_config('BUS_HOST', 'localhost'),
            'port': int(get_config('BUS_PORT', '1883')),
            'auth': {
                'username': get_config('BUS_USERNAME', 'admin'),
                'password': get_config('BUS_PASSWORD', 'mqtt_password'),
            }
        }

    def _mqtt_publish(self, topic: str, payload: Optional[str] = None) -> None:
        """Publish MQTT message.

        Args:
            topic: MQTT topic.
            payload: Optional message payload.
        """
        try:
            mqtt_params = self._get_mqtt_params()
            mqtt_single(
                topic,
                payload=payload,
                hostname=mqtt_params['hostname'],
                port=mqtt_params['port'],
                auth=mqtt_params['auth']
            )
            logger.debug(f"Published to {topic}: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}")
            raise

    def _mqtt_get(self, topic: str, timeout: int = 5):
        """Subscribe to MQTT topic and get message.

        Args:
            topic: MQTT topic.
            timeout: Timeout in seconds.

        Returns:
            Parsed JSON message or original message.
        """
        try:
            mqtt_params = self._get_mqtt_params()
            message = mqtt_simple(
                topic,
                hostname=mqtt_params['hostname'],
                port=mqtt_params['port'],
                auth=mqtt_params['auth'],
                msg_count=1,
                keepalive=timeout
            )

            payload = message.payload.decode('utf-8')

            # Try to parse as JSON
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return payload

        except Exception as e:
            logger.error(f"Failed to receive MQTT message from {topic}: {e}")
            return None

    def _check_bridge(self) -> bool:
        """Check if Zigbee2MQTT bridge is online.

        Returns:
            True if bridge is online.
        """
        mqtt_prefix = self.manager.get_setting('mqtt_topic_prefix', 'home')
        state = self._mqtt_get(f"{mqtt_prefix}/bridge/state")
        return state == "online"

    def _get_zigbee_devices(self) -> Dict[str, Dict]:
        """Get devices from Zigbee2MQTT bridge.

        Returns:
            Dictionary mapping IEEE addresses to device info.
        """
        mqtt_prefix = self.manager.get_setting('mqtt_topic_prefix', 'home')
        devices_list = self._mqtt_get(f"{mqtt_prefix}/bridge/devices")

        if not isinstance(devices_list, list):
            logger.warning("Failed to get Zigbee devices from bridge")
            return {}

        result = {}
        for device in devices_list:
            if device.get("type") == "EndDevice":
                ieee = device.get("ieee_address")
                if ieee:
                    result[ieee] = {
                        'friendly_name': device.get("friendly_name", ""),
                        'model': device.get("model", ""),
                    }

        logger.info(f"Found {len(result)} Zigbee devices on bridge")
        return result

    def can_deploy(self, device: DmDevice) -> bool:
        """Check if device can be deployed.

        For Zigbee devices, we check if they're registered on the bridge.

        Args:
            device: Device to check.

        Returns:
            True if device can be deployed.
        """
        if not self.is_compatible(device):
            return False

        # Zigbee devices don't need IP, they use MAC (IEEE address)
        if not device.mac:
            logger.warning("Device has no MAC address")
            return False

        # Check if device exists on bridge
        if not self.zigbee_devices:
            self.zigbee_devices = self._get_zigbee_devices()

        if device.mac.lower() not in self.zigbee_devices:
            logger.warning(f"Zigbee device {device.mac} not found on bridge")
            return False

        return True

    def process(self, device: DmDevice) -> None:
        """Process/deploy a Zigbee device.

        For Zigbee, we collect devices and configure them in post_process.

        Args:
            device: Device to process.
        """
        logger.info(f"Preparing Zigbee device: {device.mac}")

        self.validate(device)
        self._dump_config(device)
        self.devices_to_configure.append(device)

        logger.debug(f"Zigbee device {device.mac} queued for configuration")

    def post_process(self, devices: List[DmDevice]) -> None:
        """Post-process all Zigbee devices.

        This updates the Zigbee2MQTT configuration and restarts the bridge.

        Args:
            devices: All processed devices.
        """
        if not self.devices_to_configure:
            logger.info("No Zigbee devices to configure")
            return

        logger.info(f"Configuring {len(self.devices_to_configure)} Zigbee devices")

        # Build device configuration
        zigbee_config = self._build_devices_config()

        # Merge with existing configuration
        existing_config = {}
        if os.path.exists(ZIGBEE_CONFIG_FILE):
            with open(ZIGBEE_CONFIG_FILE, 'r') as f:
                existing_config = yaml.safe_load(f) or {}

        merged_config = {**existing_config, **zigbee_config}

        # Write merged configuration
        with open(ZIGBEE_CONFIG_FILE, 'w') as f:
            yaml.dump(merged_config, f, default_flow_style=False)

        logger.info(f"Wrote Zigbee configuration to {ZIGBEE_CONFIG_FILE}")

        # Upload configuration to bridge
        self._upload_config_to_bridge()

        # Restart bridge to apply changes
        self._restart_bridge()

    def _dump_config(self, device: DmDevice) -> None:
        """Dump device configuration to backup file.

        Args:
            device: Device to dump.
        """
        if not self.backup_path:
            return

        hostname = device.hostname() or device.mac
        filename = f"mac-{device.mac}-{hostname}.json"
        filepath = os.path.join(self.backup_path, filename)

        config = {
            "mac": device.mac,
            "hostname": hostname,
            "friendly_name": device.display_name(),
            "mqtt_topic": device.mqtt_topic(),
        }

        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)

        logger.debug(f"Config dumped to: {filepath}")

    def _build_devices_config(self) -> Dict:
        """Build Zigbee2MQTT device configuration.

        Returns:
            Dictionary of device configurations.
        """
        config = {}

        for device in self.devices_to_configure:
            ieee = device.mac.lower()
            friendly_name = device.hostname() or f"zigbee_{device.mac.replace(':', '_')}"

            config[ieee] = {
                'friendly_name': friendly_name,
                'retain': True,
            }

            # Add MQTT topic if available
            mqtt_topic = device.mqtt_topic()
            if mqtt_topic:
                config[ieee]['mqtt_topic'] = mqtt_topic

        return config

    def _upload_config_to_bridge(self) -> None:
        """Upload device configuration to Zigbee2MQTT bridge."""
        bridge_config_path = get_config('BRIDGE_DEVICES_CONFIG_PATH', None)

        if not bridge_config_path:
            logger.warning("BRIDGE_DEVICES_CONFIG_PATH not configured, skipping upload")
            return

        try:
            import shutil
            shutil.copy(ZIGBEE_CONFIG_FILE, bridge_config_path)
            logger.info(f"Uploaded configuration to bridge: {bridge_config_path}")
        except Exception as e:
            logger.error(f"Failed to upload configuration to bridge: {e}")
            raise

    def _restart_bridge(self) -> None:
        """Restart Zigbee2MQTT bridge to apply configuration."""
        mqtt_prefix = self.manager.get_setting('mqtt_topic_prefix', 'home')

        try:
            self._mqtt_publish(f"{mqtt_prefix}/bridge/request/restart", "")
            logger.info("Sent restart request to Zigbee2MQTT bridge")
        except Exception as e:
            logger.error(f"Failed to restart bridge: {e}")
            raise
