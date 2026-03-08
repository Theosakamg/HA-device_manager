import logging
import errno
import os
import subprocess
from datetime import datetime

from .contract import (_FLD_MAC, _FLD_HOST, _FLD_MQTT, _FLD_HA_DEVICE_CLASS, _FLD_ROOM_NAME, _TOPIC_BASE, slug_device_name, slug_device_topic)
from .discovery import GlobalManager
from .utility import (DeviceError, get_config)
from .common import FirmwareManagerBase

from paho.mqtt.subscribe import simple as mqtt_simple
from paho.mqtt.publish import single as mqtt_single
import json
import yaml
import re


FOLDER_BACKUP = "backup/zigbee"
ZIGBEE_CONFIG_FILE = "/tmp/devices.yml"

FIRMWARE_TYPE = "Zigbee"

logger = logging.getLogger(__name__)


class ZigbeeManager(FirmwareManagerBase):

    def __init__(self, gm: GlobalManager) -> None:
        logger.debug("Init Zigbee2Mqtt manager...")
        self.gm = gm
        self.zigbee_devices = []
        self.devices_to_save = []
        self.topics_clean = []

        self._create_file()

        # if self._check_bridge():
        #     self.zigbee_devices = self._get_zigbee_addresses()
        # else:
        #     logger.error("Zigbee2Mqtt bridge not available...")

    def _check_bridge(self):
        result = False
        message = self._mqtt_get(f"{_TOPIC_BASE}/bridge/state")

        if message == "online":
            result = True

        return result

    def _get_zigbee_addresses(self):
        message = self._mqtt_get(f"{_TOPIC_BASE}/bridge/devices")
        result = {}

        for device in message:
            if device["type"] == "EndDevice":
                result[device["ieee_address"]] = {
                    'friendly_name': device["friendly_name"]}

        return result

    def process(self, device):
        self.validate(device)
        self.dump_config(device)
        self.set_base(device)

    def post_process(self, devices):
        base_devices = self._build_config_from_devices(devices)

        with open(ZIGBEE_CONFIG_FILE) as file:
            new_devices = yaml.load(file, Loader=yaml.FullLoader) or {}

        merged = {**base_devices, **new_devices}

        with open(ZIGBEE_CONFIG_FILE, 'w') as file:
            yaml.dump(merged, file)

        self._push_devices_config_file()
        self._mqtt_publish(f'{_TOPIC_BASE}/bridge/request/restart')

        # for topic in self.topics_clean:
        #     self._mqtt_publish(topic)
        #     self._mqtt_publish(f'{topic}/availability')

    def validate(self, device):
        is_valide = 1

        if len(device[_FLD_HOST]) >= 32:
            logger.error('32 char limit => '
                         'https://tasmota.github.io/docs/Commands/#wi-fi')
            is_valide = 0

        if not is_valide:
            raise DeviceError('Not valide device !')

    def get_type(self) -> str:
        return FIRMWARE_TYPE

    def is_found(self, device) -> bool:
        # Check Type and state.
        is_found = super().is_found(device)
        if is_found:
            # Check...
            ieee = device[_FLD_MAC]
            device_name = device[_FLD_MQTT]
            device_name = re.sub(f'^{_TOPIC_BASE}/', '', device_name)

            is_found = re.compile("^0x[0-9a-zA-Z]{16}$").match(ieee)

            if is_found:
                logger.info("{ieee} - Zigbee device found ! for {topic}"
                            .format(
                                ieee=ieee,
                                topic=device_name
                            ))

        return is_found

    def folder_dump(self):
        logger.debug("Create Dump structure...")
        mydir = os.path.join(
            os.getcwd(),
            FOLDER_BACKUP,
            datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        )

        try:
            logger.debug("Create folder...")
            os.makedirs(mydir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error(e)
                raise  # This was not a "directory exist" error...

        self.path = mydir

    def dump_config(self, device):
        pass

    def set_base(self, device):
        ieee = device[_FLD_MAC]
        logger.info("{} - Zigbee set base...".format(ieee))

        device_full_topic = slug_device_topic(device)
        device_name = slug_device_name(device)

        # Hack for remove Topic_Base from zigbee.
        # TODO remove Zigbee prefix topic.
        device_topic = device_full_topic.removeprefix(
            f"{_TOPIC_BASE}/".lower())

        conf_device = {
            'friendly_name': device_topic,
            'homeassistant': {
                'name': device_name,
                'device': {
                    'suggested_area': device[_FLD_ROOM_NAME],
                }
            }
        }

        if _FLD_HA_DEVICE_CLASS in device:
            device_class = device[_FLD_HA_DEVICE_CLASS].strip()

            if device_class != '':
                conf_device['homeassistant']['device_class'] = device_class

        self._add_device_to_file(ieee, conf_device)
        self.topics_clean.append(device_full_topic)

        # TODO: Why ???
        if (
            ieee in self.zigbee_devices
            and
            'friendly_name' in self.zigbee_devices[ieee]
           ):
            self.topics_clean.append(f'{_TOPIC_BASE}/{self.zigbee_devices[ieee]["friendly_name"]}')

    def _create_file(self):
        with open(f'{ZIGBEE_CONFIG_FILE}', 'w') as file:
            file.write('')

    def _add_device_to_file(self, ieee, data):
        devices = None

        with open(f'{ZIGBEE_CONFIG_FILE}') as file:
            devices = yaml.load(file, Loader=yaml.FullLoader)

        if not devices:
            devices = {}

        devices[ieee] = data

        with open(f'{ZIGBEE_CONFIG_FILE}', 'w') as file:
            yaml.dump(devices, file)

    def _build_config_from_devices(self, devices) -> dict:
        """Build a zigbee2mqtt devices config dict from all enabled Zigbee devices."""
        result = {}
        for device in devices:
            if not self.is_found(device):
                continue
            ieee = device[_FLD_MAC]
            device_full_topic = slug_device_topic(device)
            device_name = slug_device_name(device)
            device_topic = device_full_topic.removeprefix(f"{_TOPIC_BASE}/".lower())

            conf_device = {
                'friendly_name': device_topic,
                'homeassistant': {
                    'name': device_name,
                    'device': {
                        'suggested_area': device[_FLD_ROOM_NAME],
                    }
                }
            }

            device_class = device.get(_FLD_HA_DEVICE_CLASS, '').strip()
            if device_class:
                conf_device['homeassistant']['device_class'] = device_class

            result[ieee] = conf_device

        return result

    def _push_devices_config_file(self):
        bridge_host = get_config('BRIDGE_HOST', None)
        if bridge_host:
            logger.info("Push devices config file to Zigbee2Mqtt")
            bridge_config_path = get_config(
                'BRIDGE_DEVICES_CONFIG_PATH',
                '/home/pi/zigbee2mqtt/data/devices.yaml')

            _ssh_key = get_config('SCAN_SCRIPT_PRIVATE_KEY_FILE', '')

            cmd = ['scp']
            if _ssh_key:
                cmd += ['-i', _ssh_key]
            cmd += ['-o', 'LogLevel=ERROR', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null']
            cmd += [ZIGBEE_CONFIG_FILE, f'{bridge_host}:{bridge_config_path}']

            result = subprocess.run(
                ['bash', '-c', ' '.join(cmd)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Log output for debugging
            stdout_output = result.stdout.decode('utf-8').strip()
            stderr_output = result.stderr.decode('utf-8').strip()
            if result.returncode != 0:
                logger.error(f"Failed to push config file (exit {result.returncode}): {stderr_output}")
            else:
                logger.info("Config file pushed successfully.")
                if stdout_output:
                    logger.debug(f"Push command output: {stdout_output}")

    def _mqtt_get(self, topic: str):

        message = mqtt_simple(
            topic,
            hostname=get_config('BUS_HOST', 'bus'),
            auth={'username': get_config('BUS_USERNAME', 'admin'),
                  'password': get_config('BUS_PASSWORD', 'mqtt_password')},
            keepalive=2)

        message = str(message.payload.decode("utf-8"))

        if message.startswith('{') or message.startswith('['):
            message = json.loads(message)

        return message

    def _mqtt_publish(self, topic: str, message=None):
        mqtt_single(
            topic,
            json.dumps(message) if message else None,
            hostname=get_config('BUS_HOST', 'bus'),
            auth={'username': get_config('BUS_USERNAME', 'admin'),
                  'password': get_config('BUS_PASSWORD', 'mqtt_password')})
