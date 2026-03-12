"""WLED firmware adapter.

Handles provisioning of WLED devices.
"""

import errno
import json
import logging
import os
import subprocess
from datetime import datetime
from time import sleep
from typing import Optional

import requests  # type: ignore[import-untyped]

from ..core.firmware_base import FirmwareAdapter
from ..utility import get_config
from ...models.device import DmDevice

logger = logging.getLogger(__name__)


# Constants
FIRMWARE_TYPE = "WLED"
FOLDER_BACKUP = "dm/backup/wled"
NUM_RETRY = 3

# Timezone
TZ_OFFSET = 1  # UTC+1

# MQTT
MQTT_ENABLE = True

# WLED JSON API endpoints
URL_CFG = "http://{IP_DEV}/json/cfg"
URL_INFO = "http://{IP_DEV}/json/info"
URL_STATE = "http://{IP_DEV}/json/state"
URL_UPLOAD = "http://{IP_DEV}/upload"

# Presets file
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILE_PRESETS = os.path.join(_PROJECT_ROOT, "data", "wled", "presets.json")


class WLEDAdapter(FirmwareAdapter):
    """Adapter for provisioning WLED devices."""

    def __init__(self, manager) -> None:
        """Initialize the WLED adapter.

        Args:
            manager: ProvisioningManager instance.
        """
        super().__init__(manager)
        self.backup_path: Optional[str] = None
        self._create_backup_folder()

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

    def can_deploy(self, device: DmDevice) -> bool:
        """Check if device can be deployed (has IP and is reachable).

        Args:
            device: Device to check.

        Returns:
            True if device is ready for deployment.
        """
        if not super().can_deploy(device):
            return False

        # Check if device responds to ping
        try:
            cmd: list[str] = ['ping', '-c1', '-W1', str(device.ip)]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.warning(f"Device {device.mac} @ {device.ip} not responding to ping")
                return False
        except Exception as e:
            logger.error(f"Ping failed for {device.mac}: {e}")
            return False

        return True

    def process(self, device: DmDevice) -> None:
        """Process/deploy a WLED device.

        Args:
            device: Device to process.
        """
        logger.info(f"Processing WLED device: {device.mac}")

        self.validate(device)
        self._dump_config(device)
        self._upload_presets(device)
        self._configure_device(device)

        logger.info(f"Successfully deployed WLED device: {device.mac}")

    def _dump_config(self, device: DmDevice) -> None:
        """Dump device configuration to backup file.

        Args:
            device: Device to dump.
        """
        if not device.ip or not self.backup_path:
            logger.warning(f"Cannot dump config for {device.mac}: missing IP or backup path")
            return

        logger.info(f"Dumping config for {device.mac} @ {device.ip}")

        url_cfg = URL_CFG.format(IP_DEV=device.ip)

        for attempt in range(NUM_RETRY):
            try:
                response = requests.get(url_cfg, timeout=5.0)
                response.raise_for_status()

                hostname = device.hostname() or device.mac
                filename = f"mac-{device.mac}-{hostname}-cfg.json"
                filepath = os.path.join(self.backup_path, filename)

                with open(filepath, 'w') as f:
                    json.dump(response.json(), f, indent=2)

                logger.debug(f"Config dumped to: {filepath}")
                break

            except requests.exceptions.RequestException as e:
                if attempt == NUM_RETRY - 1:
                    logger.error(f"Failed to dump config after {NUM_RETRY} attempts: {e}")
                    return
                logger.warning(f"Dump attempt {attempt + 1} failed, retrying...")
                sleep(1.5)

    def _upload_presets(self, device: DmDevice) -> None:
        """Upload presets file to WLED device.

        Args:
            device: Device to upload presets to.
        """
        if not device.ip:
            raise ValueError(f"Device {device.mac} has no IP address")

        if not os.path.isfile(FILE_PRESETS):
            logger.warning(f"Presets file not found: {FILE_PRESETS}")
            return

        logger.info(f"Uploading presets to {device.mac} @ {device.ip}")

        url_upload = URL_UPLOAD.format(IP_DEV=device.ip)

        for attempt in range(NUM_RETRY):
            try:
                with open(FILE_PRESETS, 'rb') as f:
                    files = {'data': ('presets.json', f, 'application/json')}
                    response = requests.post(url_upload, files=files, timeout=10.0)
                    response.raise_for_status()

                logger.debug("Presets uploaded successfully")
                break

            except requests.exceptions.RequestException as e:
                if attempt == NUM_RETRY - 1:
                    raise RuntimeError(f"Failed to upload presets after {NUM_RETRY} attempts: {e}")
                logger.warning(f"Upload attempt {attempt + 1} failed, retrying...")
                sleep(1.5)

    def _configure_device(self, device: DmDevice) -> None:
        """Configure WLED device with base settings.

        Args:
            device: Device to configure.
        """
        if not device.ip:
            raise ValueError(f"Device {device.mac} has no IP address")

        logger.info(f"Configuring WLED device: {device.mac} @ {device.ip}")

        hostname = device.hostname() or f"wled-{device.mac}"
        mqtt_topic = device.mqtt_topic()

        # Build configuration payload
        config = {
            "id": {
                "mdns": hostname,
                "name": device.display_name(),
            },
            "nw": {
                "ins": [
                    {
                        "ssid": get_config('WF1_SSID', ''),
                        "pskl": len(get_config('WF1_PASSWORD', '')),
                    }
                ]
            },
            "ap": {
                "ssid": f"WLED-{device.mac[-6:]}",
                "pskl": 8,
            },
            "wifi": {
                "sleep": False
            },
            "eth": {
                "type": 0
            },
            "hw": {
                "led": {
                    "total": 1,
                    "maxpwr": 0,
                    "ledma": 0,
                },
            },
            "light": {
                "scale-bri": 100,
                "pal-mode": 0,
            },
            "def": {
                "on": True,
                "bri": 128,
            },
            "mqtt": {
                "en": MQTT_ENABLE,
                "broker": get_config('BUS_HOST', 'bus'),
                "port": int(get_config('BUS_PORT', '1883')),
                "user": get_config('BUS_USERNAME', 'admin'),
                "psk": get_config('BUS_PASSWORD', 'mqtt_password'),
                "cid": f"wled-{device.mac}",
                "topics": {
                    "device": mqtt_topic or hostname,
                    "group": "wled/all",
                },
            },
            "time": {
                "enabled": True,
                "tz": TZ_OFFSET,
            },
            "ol": {
                "clock": 0,
            },
        }

        # Send configuration
        url_cfg = URL_CFG.format(IP_DEV=device.ip)

        for attempt in range(NUM_RETRY):
            try:
                response = requests.post(
                    url_cfg,
                    json=config,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.debug("Configuration applied successfully")
                break

            except requests.exceptions.RequestException as e:
                if attempt == NUM_RETRY - 1:
                    raise RuntimeError(f"Failed to configure device after {NUM_RETRY} attempts: {e}")
                logger.warning(f"Config attempt {attempt + 1} failed, retrying...")
                sleep(1.5)

        # Reboot device to apply changes
        logger.info(f"Rebooting WLED device {device.mac}")
        self._reboot_device(device)

    def _reboot_device(self, device: DmDevice) -> None:
        """Reboot WLED device.

        Args:
            device: Device to reboot.
        """
        if not device.ip:
            return

        url_state = URL_STATE.format(IP_DEV=device.ip)

        try:
            # WLED reboot via state API
            payload = {"rb": True}
            requests.post(url_state, json=payload, timeout=5.0)
            logger.debug(f"Reboot command sent to {device.mac}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to reboot {device.mac}: {e}")
