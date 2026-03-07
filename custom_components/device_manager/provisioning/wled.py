import logging
import json
import requests
from requests.auth import HTTPBasicAuth
import errno
import os
import subprocess
from datetime import datetime
from time import sleep

from .common import FirmwareManagerBase
from .contract import (_FLD_MAC, _FLD_HOST, _FLD_IP, _FLD_MQTT,
                      _FLD_LEVEL, _FLD_ROOM, _FLD_FUNCTION, _FLD_POSITION,
                      _FLD_TARGET, _FLD_EXTRA,
                      slug_device_name, slug_device_topic_device, slug_device_topic_location)
from .discovery import GlobalManager
from .utility import (Sanitizer, DeviceError, get_config)


FOLDER_BACKUP = "backup/wled"
NUM_RETRY = 3

# TIMEZONE & Location
TZ_OFFSET = 1  # UTC+1 (Europe/Paris)

# MQTT
MQTT_ENABLE = True

# Presets file to deploy on each device
# Path is relative to this file's location (provisioning/ -> project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PRESETS = os.path.join(_PROJECT_ROOT, "data", "wled", "presets.json")

# WLED JSON API endpoints
URL_CFG = "http://{IP_DEV}/json/cfg"
URL_INFO = "http://{IP_DEV}/json/info"
URL_UPLOAD = "http://{IP_DEV}/upload"

FIRMWARE_TYPE = "WLED"

logger = logging.getLogger(__name__)


class WLEDManager(FirmwareManagerBase):

    def __init__(self, gm: GlobalManager) -> None:
        logger.debug("Init WLED manager...")
        self.gm = gm
        self.folder_dump()

    def get_type(self) -> str:
        return FIRMWARE_TYPE

    def get_ip(self, device, msg='Not define :s') -> str:
        ip = device[_FLD_IP]
        logger.info(f'{ip} - {msg}')
        return ip

    def is_found(self, device: dict) -> bool:
        # Check Type and state.
        is_found = super().is_found(device)
        if is_found:

            # Check if MAC/IP is define.
            mac = device[_FLD_MAC]
            macs = self.gm.get_macs()

            is_found = mac and mac in macs
            if is_found:

                # Add extra field of resolved IP.
                device[_FLD_IP] = macs[mac]

                # Check if alive.
                cmd = ['ping', '-c1', device[_FLD_IP]]
                result_raw = subprocess.run(cmd, stdout=subprocess.PIPE)
                is_found = result_raw.returncode == 0

                logger.info(f'{device[_FLD_IP]} '
                            f'- Finded ! {mac} for {device[_FLD_MQTT]}')

                if not is_found:
                    logger.warning(f'{device[_FLD_IP]} '
                                   ' - But Device not respond. Shutdown ?')
                    raise DeviceError('Destination Host Unreachable')

        return is_found

    def process(self, device: dict) -> None:
        self.validate(device)
        self.dump_config(device)
        self.upload_presets(device)
        self.wled_set_base(device)

    def validate(self, device) -> None:
        is_valid = True

        if len(device[_FLD_HOST]) >= 32:
            logger.error('32 char limit for hostname')
            is_valid = False

        if not is_valid:
            raise DeviceError('No valid device !')

    def folder_dump(self) -> None:
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

    def dump_config(self, device) -> None:
        ip = self.get_ip(device, 'Create dump...')
        url = URL_CFG.format(IP_DEV=ip)

        for i in range(NUM_RETRY):
            try:
                r = requests.get(
                    url,
                    allow_redirects=True, timeout=5.0,
                    auth=HTTPBasicAuth('', get_config('DEVICE_PASS', 'p4ssW0rD')))

                filename = f"mac-{device[_FLD_MAC]}-{device[_FLD_HOST]}.json"
                with open(self.path + '/' + filename, 'w') as f:
                    json.dump(r.json(), f, indent=2)
                break
            except requests.exceptions.ConnectionError:
                sleep(1.5)
                logger.warning("Oups, retry...")
                if i == NUM_RETRY - 1:
                    raise DeviceError('Dead device ?!')

    def send_cfg(self, ip, payload: dict) -> None:
        """Send a partial config payload via WLED JSON API (POST /json/cfg)."""
        logger.debug(f"send cfg to {ip}: {payload}")
        url = URL_CFG.format(IP_DEV=ip)

        for i in range(NUM_RETRY):
            try:
                r = requests.post(
                    url,
                    json=payload,
                    allow_redirects=True, timeout=10.0,
                    auth=HTTPBasicAuth('', get_config('DEVICE_PASS', 'p4ssW0rD')))
                logger.debug(f"status: {r.status_code} - {r.text}")
                break
            except requests.exceptions.ConnectionError:
                sleep(1.5)
                logger.warning("Oups, retry...")
                if i == NUM_RETRY - 1:
                    raise DeviceError('Dead device ?!')

    def upload_presets(self, device) -> None:
        ip = self.get_ip(device, 'Upload presets...')
        url = URL_UPLOAD.format(IP_DEV=ip)

        if not os.path.isfile(FILE_PRESETS):
            logger.warning(f'{ip} - Presets file not found: {FILE_PRESETS}, skipping.')
            return

        for i in range(NUM_RETRY):
            try:
                with open(FILE_PRESETS, 'rb') as f:
                    r = requests.post(
                        url,
                        files={'data': ('/presets.json', f)},
                        allow_redirects=True, timeout=10.0,
                        auth=HTTPBasicAuth('', get_config('DEVICE_PASS', 'p4ssW0rD')))
                logger.debug(f"status: {r.status_code} - {r.text}")
                logger.info(f'{ip} - Presets uploaded successfully.')
                break
            except requests.exceptions.ConnectionError:
                sleep(1.5)
                logger.warning("Oups, retry...")
                if i == NUM_RETRY - 1:
                    raise DeviceError('Dead device ?!')

    def wled_restart(self, device) -> None:
        ip = self.get_ip(device, 'Restart...')
        url = f"http://{ip}/reset"
        try:
            requests.get(url, timeout=5.0, auth=HTTPBasicAuth('', get_config('DEVICE_PASS', 'p4ssW0rD')))
        except requests.exceptions.ConnectionError:
            pass  # Expected after reboot

    def wled_set_base(self, device) -> None:
        ip = self.get_ip(device, 'WLED set base...')
        mac = device[_FLD_MAC]
        hostname = device[_FLD_HOST]
        topic = slug_device_topic_location(device) + slug_device_topic_device(device)

        cfg = {
            "id": {
                "name": slug_device_name(device).replace(' > ', '_').lower(),
                "mdns": hostname,
            },
            "nw": {
                "ins": [
                    {
                        "ssid": get_config('WF1_SSID', ''),
                        "psk": get_config('WF1_PASSWORD', ''),
                    },
                    # {
                    #     "ssid": get_config('WF2_SSID', ''),
                    #     "psk": get_config('WF2_PASSWORD', ''),
                    # },
                ]
            },
            # "ap": {
            #     "psk": get_config('DEVICE_PASS', 'p4ssW0rD'),
            # },
            'if': {
                "ntp": {
                "host": get_config('NTP_SRV1', 'pool.ntp.org'),
                "utcOffst": TZ_OFFSET * 3600,
                },
                "mqtt": {
                    "en": MQTT_ENABLE,
                    "broker": get_config('BUS_HOST', 'bus'),
                    "port": int(get_config('BUS_PORT', '1883')),
                    "user": get_config('BUS_USERNAME', 'admin'),
                    "psk": get_config('BUS_PASSWORD', 'mqtt_password'),
                    "cid": f"wled-{mac}",
                    "topics": {
                        "device": topic.lstrip('/')
                    }
                }
            }
        }
        self.send_cfg(ip, cfg)

        logger.info(f"{ip} - WLED set base done. Restarting...")
        self.wled_restart(device)
