# Field of device
_FLD_ID = 'id'
_FLD_MAC = 'mac'
_FLD_STATE = 'state'
_FLD_LEVEL = 'level'
_FLD_LEVEL_NAME = 'level_name'
_FLD_FUNCTION = 'function'
_FLD_ROOM = 'room_slug'
_FLD_ROOM_NAME = 'room_name'
_FLD_POSITION = 'position_slug'
_FLD_POSITION_NAME = 'position_name'
_FLD_FRMW = 'firmware'
_FLD_MODEL = 'model'
_FLD_INTERLOCK = 'interlock'  # DEPRECATED : remove in futur version
_FLD_MODE = 'mode'
_FLD_TARGET = 'target'
_FLD_EXTRA = 'extra'
_FLD_MQTT = 'mqtt'
_FLD_HOST = 'hostname'
_FLD_HA_DEVICE_CLASS = 'ha_device_class'

_FLD_IP = 'IPresolv'


# Mode
_MOD_STD = 'standard'
_MOD_3WAY = "3way"

# State value
_STA_ENABLE = 'Enable'
_STA_DISABLE = 'Disable'
_STA_NA = 'NA'

# Command
_CMD_DUMP = 'dl'
_CMD_CMND = 'cm'
_CMD_REBOOT = '.'

# Name constant
_TOPIC_BASE = 'Home'
_TOPIC_LVL = 'Lvl'


def slug_device_name(device) -> str:
    device_name = (
      f"{_TOPIC_BASE.capitalize()}"
      f" > {device[_FLD_LEVEL_NAME].capitalize()}"
      f" > {device[_FLD_ROOM].capitalize()}"
      f" > {device[_FLD_FUNCTION].capitalize()}"
      f" > {device[_FLD_POSITION].capitalize()}"
      )
    return device_name


def slug_device_topic_location(device) -> str:
    device_topic = (
      f"{_TOPIC_BASE}"
      f"/{device[_FLD_LEVEL]}"
      f"/{device[_FLD_ROOM]}"
      ).lower()
    return device_topic


def slug_device_topic_device(device) -> str:
    device_topic = (
      f"/{device[_FLD_FUNCTION]}"
      f"/{device[_FLD_POSITION]}"
      ).lower()
    return device_topic


def slug_device_topic(device) -> str:
    device_topic = (
      f"{slug_device_topic_location(device)}"
      f"{slug_device_topic_device(device)}"
      ).lower()
    return device_topic


def slug_device_id(device) -> str:
    device_topic = (
      f"{_TOPIC_BASE}"
      f"_{device[_FLD_LEVEL]}"
      f"_{device[_FLD_ROOM]}"
      f"_{device[_FLD_FUNCTION]}"
      f"_{device[_FLD_POSITION]}"
      ).lower()
    return device_topic
