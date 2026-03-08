import logging
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
                      _FLD_INTERLOCK, _FLD_MODE, _FLD_TARGET, _FLD_EXTRA,
                      _MOD_3WAY,
                      _CMD_DUMP, _CMD_CMND, _CMD_REBOOT,
                      slug_device_id, slug_device_name, slug_device_topic_device, slug_device_topic_location)
from .discovery import GlobalManager
from .utility import (Sanitizer, DeviceError, get_config)


FOLDER_BACKUP = "backup/tasmota"
NUM_RETRY = 3

# Save state and aplly after reboot
SAVE_SATE = 1
POWERONSTATE = "TODO"

# Not add unit on result value
NO_UNIT = 0

# Display value on Fahrenheit (or Celsius)
UNIT_FAR = 0

DISPLAY_ENABLE = 1

# DEVICE ACCESS
DEVICE_USER = "admin"

# TIMEZONE & Location
TZ_TIMEZONE = "99"
TZ_STD = "0,0,10,1,3,60"
TZ_DST = "0,0,3,1,2,120"
GEO_LATITUDE = "48.16403653881043"
GEO_LONGITUDE = "-1.4358991384506228"

# DEFINE MANUALY ! (NOT USE FROM DHCP)
NTP_SRV2 = "pool.ntp.org"

# SERIAL CONFIG
# SER_BAUD = 9600

# MQTT
MQTT_ENABLE = "1"
MQTT_GRP = "all"
MQTT_FULLTOPIC = "{}/%topic%/%prefix%/"
MQTT_PREFIX_CMD = "cmnd"
MQTT_PREFIX_STA = "stat"
MQTT_MSG_OFF = "OFF"
MQTT_MSG_ON = "ON"
MQTT_MSG_TOGGLE = "TOGGLE"
MQTT_MSG_HOLD = "HOLD"


# Rule Stack
RULE_MANUAL = 'Rule1'
RULE_AUTO = 'Rule2'
RULE_SYSTEM = 'Rule3'

# CASE 3 - MODE MANUAL / AUTO
# CASE 4 - MODE MANUAL
RULE_DEF_3WAY = ('ON Power1#State=0 DO Power2 1 ENDON '
                 'ON Power1#State=1 DO Power2 0 ENDON '
                 ).strip()
# FIXME: go back from CASE 4 MODE AUTO !

RULE_DEF_MANUAL = RULE_DEF_3WAY

# CASE 4 - MODE AUTO
RULE_DEF_AUTO = ('ON Mqtt#Connected DO '
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
                 'ENDON '
                 ).strip()

RULE_DEF_3WAY_AUTO = ('ON Mqtt#Connected '
                      'backlog '
                      'Power1 1; '
                      'Power2 1 '
                      'ENDON '
                      'ON Mqtt#Disconnected DO '
                      'backlog '
                      'Power2 0 '
                      'ENDON '
                      ).strip()

# # TODO Tranform to Dict
# # (for manage dynamic list  eg. null is not send : SetOption0 null;)
# ACTIONS_NO_REBOOT = {
#     "SetOption0": SAVE_SATE,
#     "SetOption8": UNIT_FAR,
#     "SetOption53": DISPLAY_ENABLE,
#     "PowerOnState": POWERONSTATE,
#     "WifiConfig": 4,
# }
# # REMOVE COMMAND
# #  SetOption2 $NO_UNIT;\
# ACTIONS_WITH_REBOOT = {
#     "BlinkCount": 2,
#     "Power1": "Blink",
#     "restart": 1
# }

URL_BASE_TPL = (
    "http://{IP_DEV}/{CMND}?"
)

FIRMWARE_TYPE = "Tasmota"

logger = logging.getLogger(__name__)


class TasmotaManager(FirmwareManagerBase):

    def __init__(self, gm: GlobalManager) -> None:
        logger.debug("Init Type manager...")
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
                                   ' - But Device not reponce. Shutdown ?')
                    raise DeviceError('Destination Host Unreachable')

        return is_found

    def process(self, device: dict) -> None:
        self.validate(device)
        self.dump_config(device)
        self.tasmota_set_base(device)

    def validate(self, device) -> None:
        is_valide = True

        if len(device[_FLD_HOST]) >= 32:
            logger.error('32 char limit => '
                         'https://tasmota.github.io/docs/Commands/#wi-fi')
            is_valide = False

        if not is_valide:
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
        url_base = URL_BASE_TPL.format(
            IP_DEV=ip,
            CMND=_CMD_DUMP
        )
        url = Sanitizer.url_sanity(url_base, None)

        for i in range(NUM_RETRY):
            try:
                r = requests.get(
                    url,
                    allow_redirects=True, timeout=5.0,
                    auth=HTTPBasicAuth(DEVICE_USER, get_config('DEVICE_PASS', 'p4ssW0rD')))

                filename = f"mac-{device[_FLD_MAC]}-{device[_FLD_HOST]}.bmp"
                open(self.path + '/' + filename, 'wb').write(r.content)
                break
            except requests.exceptions.ConnectionError:
                sleep(1.5)
                logger.warning("Oups, retry...")
                if i == NUM_RETRY:
                    raise DeviceError('Dead device ?!')

    def send_cmnds(self, ip, cmd=_CMD_CMND, one=False, configs=None) -> None:
        logger.debug("send commands...")

        if configs and cmd == _CMD_CMND:
            if len(configs) > 30:
                raise DeviceError("Too many action. ")

            action = ';'.join(' '
                              .join((key, val))
                              for (key, val) in configs.items())
            if (one):
                data_safe = f"&cmnd={action}"
            else:
                data_safe = f"&cmnd=Backlog0 {action}"
        else:
            data_safe = None

        url_base = URL_BASE_TPL.format(
            IP_DEV=ip,
            CMND=cmd,
        )
        url_safe = Sanitizer.url_sanity(url_base, data_safe)
        for i in range(NUM_RETRY + 1):
            try:
                r = requests.get(
                    url_safe, allow_redirects=True, timeout=10.0,
                    auth=HTTPBasicAuth(DEVICE_USER, get_config('DEVICE_PASS', 'p4ssW0rD')))
                logger.debug(f"status: {r.status_code} - {r.text}")
                break
            except requests.exceptions.ConnectionError:
                sleep(1.5)
                logger.warning("Oups, retry...")
                if i == NUM_RETRY:
                    raise DeviceError('Dead device ?!')

    def tasmota_restart(self, device) -> None:
        ip = self.get_ip(device, 'Restart...')
        self.send_cmnds(ip, cmd=_CMD_REBOOT)

    def tasmota_set_base(self, device) -> None:
        ip = self.get_ip(device, 'Tasmota set base...')
        mac = device[_FLD_MAC]
        hostname = device[_FLD_HOST]

        ACTIONS_DEVICE1 = {
            # Device name displayed in the webUI and used for HA autodiscovery.
            "DeviceName": slug_device_name(device),
            "FriendlyName0": "1",
            "FriendlyName1": "1",
            "FriendlyName2": "1",
            # For HA (can be multi)
            # "StateText1": MQTT_MSG_OFF,
            # "StateText2": MQTT_MSG_ON,
            # "StateText3": MQTT_MSG_TOGGLE,
            # "StateText4": MQTT_MSG_HOLD,
            "SetOption3": MQTT_ENABLE,
            "GroupTopic": MQTT_GRP,
            # "InfoRetain": "1",
            # "SensorRetain": "1",
            # "StateRetain": "1",
            # "StatusRetain": "1",
            "TelePeriod": "120",
            # "Delay": "102",
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
            # Disable Device recovery using fast power cycle detection [0=Enable, 1=Disable]
            # TODO remove when stable !!
            "SetOption65": "0",
            # Display hostname and IP
            "SetOption53": "1",
            "SetOption114": "0",
            "SwitchTopic": "0",
        }
        self.send_cmnds(ip, configs=ACTIONS_DEVICE1)

        self.tasmota_set_interlock(device)
        self.tasmota_set_bytype(device)

        logger.info(f"{ip} - Tasmota set base (post-hook)...")
        ACTIONS_FORCE_REBOOT = {
            "Hostname": hostname,
            "MqttClient": f"tasmota-{mac}",
            "MqttHost": get_config('BUS_HOST', 'bus'),
            "FullTopic": MQTT_FULLTOPIC.format(
                slug_device_topic_location(device)
            ),
            "Topic": (
                slug_device_topic_device(device).replace('/', '', 1)
                # Remove first slash
            ),
            "MqttPort": get_config('BUS_PORT', '1883'),
            "MqttUser": get_config('BUS_USERNAME', 'admin'),
            "MqttPassword": get_config('BUS_PASSWORD', 'mqtt_password'),
            # "Prefix1": MQTT_PREFIX_CMD,
            # "Prefix2": MQTT_PREFIX_STA,
            "SSID1": get_config('WF1_SSID', ''),
            "Password1": get_config('WF1_PASSWORD', ''),
            "SSID2": get_config('WF2_SSID', ''),
            "Password2": get_config('WF2_PASSWORD', ''),
            "Restart": "1",
        }
        self.send_cmnds(ip, configs=ACTIONS_FORCE_REBOOT)
        # self.tasmota_restart(device)

    def has_interlock(self, device):
        interlock = device[_FLD_INTERLOCK]
        return interlock and interlock != "" and interlock != "0"

    def has_mode_3way(self, device):
        mode = device[_FLD_MODE]
        return mode and mode == _MOD_3WAY

    def get_mode(self, device):
        return device[_FLD_MODE]

    def get_extra(self, device):
        return device[_FLD_EXTRA]

    def get_target(sefl, device):
        return device[_FLD_TARGET]

    def tasmota_set_interlock(self, device) -> None:
        ip = self.get_ip(device, 'Tasmota set Interlock...')
        if self.has_interlock(device):
            logger.debug(f'{ip} - Tasmota enable Interlock.')
            ACTIONS_DEVICE = {
                "Interlock": device[_FLD_INTERLOCK],
            }
            self.send_cmnds(ip, one=True, configs=ACTIONS_DEVICE)

            ACTIONS_DEVICE = {
                "Interlock": "On",
            }
            self.send_cmnds(ip, one=True, configs=ACTIONS_DEVICE)
        else:
            logger.debug(f'{ip} - Tasmota disbale Interlock.')
            ACTIONS_DEVICE = {
                "Interlock": "Off",
            }
            self.send_cmnds(ip, one=True, configs=ACTIONS_DEVICE)

    def tasmota_set_bytype(self, device) -> None:
        type = device[_FLD_FUNCTION]
        custom = None
        match type:
            case 'Button':
                custom = TasmotaButtonAdapter(self)
            case 'Light':
                custom = TasmotaLightAdapter(self)
            case 'Shutters':
                custom = TasmotaShuttersAdapter(self)

        if custom:
            self.get_ip(device,
                        f'\033[0;94mCustom device (based on type/function): {type}...\x1b[0m')
            custom.tasmota_set_custom(device)


class TasmotaDeviceAdapter:
    pass


class TasmotaButtonAdapter(TasmotaDeviceAdapter):
    def __init__(self, owner) -> None:
        logger.debug("Init Tasmota button customizer...")
        self.owner = owner

    def tasmota_set_custom(self, device: dict):
        ip = self.owner.get_ip(device, 'Tasmota set Button...')

        rule_manual = RULE_DEF_MANUAL
        rule_interlock = ' '
        rule_auto = ' '
        rule_3way_auto = ' '

        target = f"{device[_FLD_TARGET]}"

        # Disable 3way for now
        # if self.owner.has_mode_3way(device):
        #     logger.debug(f"{ip} - Tasmota set 3 way mode...")

        #     if target and target != "None":
        #         rule_3way_auto = RULE_DEF_3WAY_AUTO

        if target and target != "None":
            logger.debug(f"{ip} - Tasmota set Target pub...")
            rule_auto = RULE_DEF_AUTO

            if target != "light/ceiling":
                rule_auto = rule_auto.replace("light/ceiling", target)

        ACTIONS = {
            RULE_MANUAL: ' '.join([
                rule_manual,
                rule_interlock,
            ]),
        }
        self.owner.send_cmnds(ip, one=True, configs=ACTIONS)
        ACTIONS = {
            RULE_AUTO: ' '.join([
                rule_interlock,
                rule_auto,
                rule_3way_auto
            ]),
        }
        self.owner.send_cmnds(ip, one=True, configs=ACTIONS)
        ACTIONS = {
            RULE_SYSTEM: ' '.join([
                rule_interlock,
                rule_manual
            ]),
        }
        self.owner.send_cmnds(ip, one=True, configs=ACTIONS)

        ACTIONS = {
            RULE_MANUAL: '0',
            RULE_AUTO: '1',
            RULE_SYSTEM: '0',
        }
        self.owner.send_cmnds(ip, configs=ACTIONS)


class TasmotaLightAdapter(TasmotaDeviceAdapter):
    def __init__(self, owner) -> None:
        logger.debug("Init Tasmota Light customizer...")
        self.owner = owner

    def tasmota_set_custom(self, device: dict):
        pass
        # Only for light without buld light after.
        # ACTIONS = {
        #     # Force light mode
        #     # (https://tasmota.github.io/docs/Commands/#SetOption30)
        #     "SetOption30": '1'
        # }
        # self.owner.send_cmnds(ip, configs=ACTIONS)


class TasmotaShuttersAdapter(TasmotaDeviceAdapter):
    def __init__(self, owner) -> None:
        logger.debug("Init Tasmota shutters customizer...")
        self.owner = owner

    def tasmota_set_custom(self, device: dict):
        # ip = self.owner.get_ip(device, 'Tasmota set Shutters...')
        pass
