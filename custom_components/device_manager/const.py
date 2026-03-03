"""Constants for Device Manager integration."""

DOMAIN = "device_manager"
DB_NAME = "device_manager.db"

# Table names
TABLE_BUILDINGS = "dm_buildings"
TABLE_FLOORS = "dm_floors"
TABLE_ROOMS = "dm_rooms"
TABLE_DEVICES = "dm_devices"
TABLE_DEVICE_MODELS = "dm_device_models"
TABLE_DEVICE_FIRMWARES = "dm_device_firmwares"
TABLE_DEVICE_FUNCTIONS = "dm_device_functions"

# Allowed function values
ALLOWED_FUNCTIONS = {
    "button", "door", "doorbell", "heater", "light", "motion",
    "shutter", "tv", "window", "thermal", "ir", "presence",
    "energy", "infra", "water", "gaz", "sensor",
}

# Allowed firmware values
ALLOWED_FIRMWARES = {
    "embeded", "tasmota", "tuya", "zigbee", "na",
    "android", "android-cast", "wled",
}

# State mapping
STATE_MAP = {
    "enable": "Enable",
    "enable-hot": "Enable-Hot",
    "disable": "Disable",
    "na": "NA",
    "ko": "KO",
}

# Table for user settings
TABLE_SETTINGS = "dm_settings"

# Settings keys and their defaults
SETTING_DNS_SUFFIX = "dns_suffix"
SETTING_IP_PREFIX = "ip_prefix"
SETTING_MQTT_PREFIX = "mqtt_topic_prefix"
SETTING_DEFAULT_BUILDING = "default_building_name"

DEFAULT_SETTINGS: dict[str, str] = {
    SETTING_DNS_SUFFIX: "domo.local",
    SETTING_IP_PREFIX: "192.168.0",
    SETTING_MQTT_PREFIX: "home",
    SETTING_DEFAULT_BUILDING: "Building",
}

# Legacy aliases (for backward compat in code that imported these directly)
DNS_SUFFIX = DEFAULT_SETTINGS[SETTING_DNS_SUFFIX]
DEFAULT_IP_PREFIX = DEFAULT_SETTINGS[SETTING_IP_PREFIX]
