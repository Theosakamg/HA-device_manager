"""Tasmota firmware adapter.

Handles provisioning of Tasmota devices.
"""

import errno
import logging
import os
from datetime import datetime
from time import sleep
from typing import Optional, Dict

import requests
from requests.auth import HTTPBasicAuth
from requests.utils import requote_uri

from ..core.firmware_base import FirmwareAdapter
from ..utility import get_config
from ...models.device import DmDevice

logger = logging.getLogger(__name__)


# Constants
FIRMWARE_TYPE = "Tasmota"
FOLDER_BACKUP = "dm/backup/tasmota"
NUM_RETRY = 3

# Device access
DEVICE_USER = "admin"

# Commands
_CMD_DUMP = "dl"
_CMD_CMND = "cm"
_CMD_REBOOT = "."

# MQTT
MQTT_ENABLE = "1"
MQTT_GRP = "all"
MQTT_FULLTOPIC = "{}/%topic%/%prefix%/"

# Timezone & Location
TZ_TIMEZONE = "99"
TZ_STD = "0,0,10,1,3,60"
TZ_DST = "0,0,3,1,2,120"
GEO_LATITUDE = "48.16403653881043"
GEO_LONGITUDE = "-1.4358991384506228"

# NTP
NTP_SRV2 = "pool.ntp.org"

# Rule stacks
RULE_MANUAL = 'Rule1'
RULE_AUTO = 'Rule2'
RULE_SYSTEM = 'Rule3'

# Rule definitions
RULE_DEF_3WAY = (
    'ON Power1#State=0 DO Power2 1 ENDON '
    'ON Power1#State=1 DO Power2 0 ENDON'
).strip()

RULE_DEF_MANUAL = RULE_DEF_3WAY

RULE_DEF_AUTO = (
    'ON Mqtt#Connected DO '
    'backlog '
    f"{RULE_MANUAL} 0; "
    'SetOption114 1; '
    'SwitchTopic light/ceiling; '
    'Power 1 '
    'ENDON '
    'ON Mqtt#Disconnected DO '
    'backlog '
    'SetOption114 0; '
    'SwitchTopic 0; '
    f"{RULE_MANUAL} 1 "
    'ENDON'
).strip()

RULE_DEF_3WAY_AUTO = (
    'ON Mqtt#Connected '
    'backlog '
    'Power1 1; '
    'Power2 1 '
    'ENDON '
    'ON Mqtt#Disconnected DO '
    'backlog '
    'Power2 0 '
    'ENDON'
).strip()

# URL template
URL_BASE_TPL = "http://{IP_DEV}/{CMND}?"


class TasmotaAdapter(FirmwareAdapter):
    """Adapter for provisioning Tasmota devices."""

    # Sensitive fields to mask in logs
    _SENSITIVE_FIELDS = {
        'WebPassword', 'Password', 'Password1', 'Password2',
        'MqttPassword', 'password', 'pass'
    }

    def __init__(self, manager) -> None:
        """Initialize the Tasmota adapter.

        Args:
            manager: ProvisioningManager instance.
        """
        super().__init__(manager)
        self.backup_path: Optional[str] = None
        self._create_backup_folder()

    def get_firmware_type(self) -> str:
        """Return firmware type."""
        return FIRMWARE_TYPE

    def _mask_sensitive_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive values in a dictionary for logging.

        Args:
            data: Dictionary that may contain sensitive data.

        Returns:
            Copy of dictionary with sensitive values masked.
        """
        masked = data.copy()
        for key in masked:
            if key in self._SENSITIVE_FIELDS:
                masked[key] = '***'
        return masked

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

    def validate(self, device: DmDevice) -> None:
        """Validate device configuration."""
        super().validate(device)

        hostname = device.hostname()
        if hostname and len(hostname) >= 32:
            raise ValueError(
                f"Hostname '{hostname}' exceeds 32 chars "
                "(https://tasmota.github.io/docs/Commands/#wi-fi)"
            )

    def process(self, device: DmDevice) -> None:
        """Process/deploy a Tasmota device.

        Args:
            device: Device to process.
        """
        logger.info(f"Processing Tasmota device: {device.mac}")

        self.validate(device)
        self._dump_config(device)
        self._configure_device(device)

        logger.info(f"Successfully deployed Tasmota device: {device.mac}")

    def _sanitize_data(self, data: str) -> str:
        """Sanitize data for URL encoding."""
        data_safe = data.replace("%", "%25")
        data_safe = data_safe.replace("/", "%2F")
        data_safe = data_safe.replace("#", "%23")
        data_safe = data_safe.replace(" ", "%20")
        data_safe = data_safe.replace(";", "%3B")
        return data_safe

    def _build_url(self, ip: str, cmd: str, data: Optional[str] = None) -> str:
        """Build and sanitize URL for Tasmota HTTP API.

        Args:
            ip: Device IP address.
            cmd: Command type.
            data: Optional command data.

        Returns:
            Sanitized URL string.
        """
        url_base = URL_BASE_TPL.format(IP_DEV=ip, CMND=cmd)

        if data:
            data_safe = self._sanitize_data(data)
            url_full = url_base + data_safe
        else:
            url_full = url_base

        return requote_uri(url_full)

    def _dump_config(self, device: DmDevice) -> None:
        """Dump device configuration to backup file.

        Args:
            device: Device to dump.
        """
        if not device.ip or not self.backup_path:
            logger.warning(f"Cannot dump config for {device.mac}: missing IP or backup path")
            return

        logger.info(f"Dumping config for {device.mac} @ {device.ip}")

        url = self._build_url(device.ip, _CMD_DUMP)
        password = get_config('DEVICE_PASS', 'p4ssW0rD')

        logger.debug(f"  Curl equivalent: curl -u '{DEVICE_USER}:***' '{url}' -o config.dmp")

        for attempt in range(NUM_RETRY):
            try:
                response = requests.get(
                    url,
                    allow_redirects=True,
                    timeout=5.0,
                    auth=HTTPBasicAuth(DEVICE_USER, password)
                )
                response.raise_for_status()

                hostname = device.hostname() or device.mac
                filename = f"mac-{device.mac}-{hostname}.dmp"
                filepath = os.path.join(self.backup_path, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                logger.debug(f"Config dumped to: {filepath}")
                break

            except requests.exceptions.RequestException as e:
                if attempt == NUM_RETRY - 1:
                    raise RuntimeError(f"Failed to dump config after {NUM_RETRY} attempts: {e}")
                logger.warning(f"Dump attempt {attempt + 1} failed, retrying...")
                sleep(1.5)

    def _send_commands(
        self,
        device: DmDevice,
        configs: Dict[str, str],
        use_backlog: bool = True
    ) -> None:
        """Send commands to Tasmota device.

        Args:
            device: Target device.
            configs: Dictionary of command: value pairs.
            use_backlog: If True, use Backlog0 to batch commands.
        """
        if not device.ip:
            raise ValueError(f"Device {device.mac} has no IP address")

        if len(configs) > 30:
            raise ValueError("Too many commands (max 30)")

        # Build command string
        action = ';'.join(f"{key} {val}" for key, val in configs.items())

        if use_backlog:
            data = f"&cmnd=Backlog0 {action}"
        else:
            data = f"&cmnd={action}"

        url = self._build_url(device.ip, _CMD_CMND, data)
        password = get_config('DEVICE_PASS', 'p4ssW0rD')

        # Mask sensitive data for logging
        configs_masked = self._mask_sensitive_data(configs)

        for attempt in range(NUM_RETRY + 1):
            logger.debug(f"Sending commands to {device.mac} @ {device.ip}")
            logger.debug(f"  Commands: {configs_masked}")
            logger.debug(f"  Curl equivalent: curl -u '{DEVICE_USER}:***' '{url}'")

            try:
                response = requests.get(
                    url,
                    allow_redirects=True,
                    timeout=10.0,
                    auth=HTTPBasicAuth(DEVICE_USER, password)
                )

                # Verify HTTP status code
                if response.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )

                # Parse and verify Tasmota response
                try:
                    result = response.json()
                    # Check for Tasmota error indicators
                    if isinstance(result, dict):
                        # Check for explicit error messages
                        if "ERROR" in str(result).upper():
                            raise RuntimeError(f"Tasmota error in response: {result}")
                        # Check for WARNING in response (still log but don't fail)
                        if "WARNING" in str(result).upper():
                            logger.warning(f"Tasmota warning: {result}")
                    logger.debug(f"  Response: {response.status_code} - {result}")
                except ValueError:
                    # Non-JSON response, just log it (some commands return plain text)
                    logger.debug(f"  Response: {response.status_code} - {response.text[:200]}")

                break

            except requests.exceptions.RequestException as e:
                if attempt == NUM_RETRY:
                    raise RuntimeError(f"Failed to send commands after {NUM_RETRY + 1} attempts: {e}")
                logger.warning(f"Command attempt {attempt + 1} failed, retrying...")
                sleep(1.5)

    def _configure_device(self, device: DmDevice) -> None:
        """Configure Tasmota device with base settings.

        Args:
            device: Device to configure.
        """
        if not device.ip:
            raise ValueError(f"Device {device.mac} has no IP address")

        logger.info(f"Configuring Tasmota device: {device.mac} @ {device.ip}")

        # Get device names and topics
        display_name = device.display_name()
        hostname = device.hostname()
        mqtt_topic_location = self._get_mqtt_topic_location(device)
        mqtt_topic_device = self._get_mqtt_topic_device(device)

        # Base configuration (Part 1)
        logger.info(f"[{device.mac}] Applying base configuration...")
        base_config = {
            "DeviceName": display_name,
            "FriendlyName0": "1",
            "FriendlyName1": "1",
            "FriendlyName2": "1",
            "SetOption3": MQTT_ENABLE,
            "GroupTopic": MQTT_GRP,
            "TelePeriod": "120",
            "NtpServer1": get_config('NTP_SRV1', 'pool.ntp.org'),
            "NtpServer2": NTP_SRV2,
            "NtpServer3": "0",
            "WebPassword": get_config('DEVICE_PASS', 'p4ssW0rD'),
            "Timezone": TZ_TIMEZONE,
            "TimeStd": TZ_STD,
            "TimeDst": TZ_DST,
            "Latitude": GEO_LATITUDE,
            "Longitude": GEO_LONGITUDE,
            "WebLog": "2",
            "SetOption65": "0",  # Device recovery via fast power cycle
            "SetOption53": "1",  # Display hostname and IP
            "SetOption114": "0",
            "SwitchTopic": "0",
        }
        self._send_commands(device, base_config)

        # Configure interlock if needed
        logger.info(f"[{device.mac}] Configuring interlock...")
        self._configure_interlock(device)

        # Configure by device function type
        logger.info(f"[{device.mac}] Configuring function-specific settings (type: {device._refs.function_name})...")
        self._configure_by_function(device)

        # Network and MQTT configuration (requires restart)
        logger.info(f"[{device.mac}] Applying network/MQTT config (will restart device)...")
        logger.debug(f"  MQTT FullTopic: {MQTT_FULLTOPIC.format(mqtt_topic_location)}")
        logger.debug(f"  MQTT Topic: {mqtt_topic_device.lstrip('/')}")
        logger.debug(f"  Hostname: {hostname}")
        network_config = {
            "Hostname": hostname,
            "MqttClient": f"tasmota-{device.mac}",
            "MqttHost": get_config('BUS_HOST', 'bus'),
            "FullTopic": MQTT_FULLTOPIC.format(mqtt_topic_location),
            "Topic": mqtt_topic_device.lstrip('/'),  # Remove leading slash
            "MqttPort": get_config('BUS_PORT', '1883'),
            "MqttUser": get_config('BUS_USERNAME', 'admin'),
            "MqttPassword": get_config('BUS_PASSWORD', 'mqtt_password'),
            "SSID1": get_config('WF1_SSID', ''),
            "Password1": get_config('WF1_PASSWORD', ''),
            "SSID2": get_config('WF2_SSID', ''),
            "Password2": get_config('WF2_PASSWORD', ''),
            "Restart": "1",  # Restart to apply network changes
        }
        self._send_commands(device, network_config)

    def _get_mqtt_topic_location(self, device: DmDevice) -> str:
        """Get MQTT topic location part.

        Args:
            device: Device instance.

        Returns:
            Topic location string (e.g., "home/l0/room").
        """
        mqtt_prefix = self.manager.get_setting('mqtt_topic_prefix', 'home')
        return f"{mqtt_prefix}/{device._floor.slug}/{device._room.slug}"

    def _get_mqtt_topic_device(self, device: DmDevice) -> str:
        """Get MQTT topic device part.

        Args:
            device: Device instance.

        Returns:
            Topic device string (e.g., "/function/position").
        """
        function_slug = device._refs.function_name.lower().replace(" ", "_")
        return f"/{function_slug}/{device.position_slug}"

    def _configure_interlock(self, device: DmDevice) -> None:
        """Configure interlock settings.

        Args:
            device: Device to configure.
        """
        if not device.interlock or device.interlock == "" or device.interlock == "0":
            logger.debug(f"  Disabling interlock for {device.mac}")
            self._send_commands(device, {"Interlock": "Off"}, use_backlog=False)
        else:
            logger.debug(f"  Enabling interlock for {device.mac}: {device.interlock}")
            self._send_commands(device, {"Interlock": device.interlock}, use_backlog=False)
            self._send_commands(device, {"Interlock": "On"}, use_backlog=False)

    def _configure_by_function(self, device: DmDevice) -> None:
        """Configure device based on its function type.

        Args:
            device: Device to configure.
        """
        function = device._refs.function_name.lower()

        if function == 'button':
            logger.debug("  Configuring as button device")
            self._configure_button(device)
        elif function == 'light':
            logger.debug("  Configuring as light device")
            self._configure_light(device)
        elif function == 'shutters':
            logger.debug("  Configuring as shutters device")
            self._configure_shutters(device)
        else:
            logger.debug(f"  No special configuration for function: {function}")

    def _configure_button(self, device: DmDevice) -> None:
        """Configure button-specific settings.

        Args:
            device: Button device to configure.
        """
        logger.debug(f"  Configuring button rules for {device.mac}")

        rule_manual = RULE_DEF_MANUAL
        rule_auto = ' '

        # Check if device has a target (for triggering other devices)
        if device.target_id:
            # Get target device (if available)
            target_topic = self._get_target_topic(device)
            if target_topic:
                logger.debug(f"  Button {device.mac} has target: {target_topic}")
                rule_auto = RULE_DEF_AUTO.replace("light/ceiling", target_topic)
            else:
                logger.debug(f"  Button {device.mac} has target_id but topic could not be resolved")
        else:
            logger.debug(f"  Button {device.mac} has no target configured")

        # Apply rules
        logger.debug(f"  Setting {RULE_MANUAL}: {rule_manual}")
        self._send_commands(device, {RULE_MANUAL: rule_manual}, use_backlog=False)

        logger.debug(f"  Setting {RULE_AUTO}: {rule_auto}")
        self._send_commands(device, {RULE_AUTO: rule_auto}, use_backlog=False)

        logger.debug(f"  Setting {RULE_SYSTEM}: {rule_manual}")
        self._send_commands(device, {RULE_SYSTEM: rule_manual}, use_backlog=False)

        # Enable rules
        logger.debug(f"  Enabling rules: {RULE_AUTO}=1, others=0")
        self._send_commands(device, {
            RULE_MANUAL: '0',
            RULE_AUTO: '1',
            RULE_SYSTEM: '0',
        })

    def _get_target_topic(self, device: DmDevice) -> Optional[str]:
        """Get MQTT topic for target device.

        Args:
            device: Device with target_id set.

        Returns:
            Target MQTT topic or None.
        """
        # In the refactored version, the repository should resolve target devices
        # For now, we'll just return a placeholder
        # TODO: Implement proper target resolution in ProvisioningManager
        return None

    def _configure_light(self, device: DmDevice) -> None:
        """Configure light-specific settings.

        Args:
            device: Light device to configure.
        """
        logger.debug(f"Configuring light for {device.mac}")
        # Currently no special configuration needed for lights
        pass

    def _configure_shutters(self, device: DmDevice) -> None:
        """Configure shutters-specific settings.

        Args:
            device: Shutters device to configure.
        """
        logger.debug(f"Configuring shutters for {device.mac}")
        # Currently no special configuration needed for shutters
        pass
