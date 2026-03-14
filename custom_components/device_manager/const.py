"""Constants for Device Manager integration."""

DOMAIN = "device_manager"
DB_NAME = "dm/device_manager.db"

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

# Provisioning: network scan
SETTING_SCAN_SSH_KEY_FILE = "scan_ssh_key_file"
SETTING_SCAN_SSH_USER = "scan_ssh_user"
SETTING_SCAN_SSH_HOST = "scan_ssh_host"
SETTING_SCAN_SCRIPT_CONTENT = "scan_script_content"

# Provisioning: device access
SETTING_DEVICE_PASS = "device_pass"

# Provisioning: NTP
SETTING_NTP_SERVER1 = "ntp_server1"

# Provisioning: WiFi
SETTING_WIFI1_SSID = "wifi1_ssid"
SETTING_WIFI1_PASSWORD = "wifi1_password"
SETTING_WIFI2_SSID = "wifi2_ssid"
SETTING_WIFI2_PASSWORD = "wifi2_password"

# Provisioning: MQTT bus
SETTING_BUS_HOST = "bus_host"
SETTING_BUS_PORT = "bus_port"
SETTING_BUS_USERNAME = "bus_username"
SETTING_BUS_PASSWORD = "bus_password"

# Provisioning: Zigbee bridge
SETTING_BRIDGE_HOST = "bridge_host"
SETTING_BRIDGE_DEVICES_CONFIG_PATH = "bridge_devices_config_path"
# HA Groups generation
SETTING_HA_GROUPS_EMPTY_GROUPS = "ha_groups_empty_groups"

DEFAULT_SETTINGS: dict[str, str] = {
    SETTING_DNS_SUFFIX: "domo.local",
    SETTING_IP_PREFIX: "192.168.0",
    SETTING_MQTT_PREFIX: "home",
    SETTING_DEFAULT_BUILDING: "Building",
    # Network scan
    SETTING_SCAN_SSH_KEY_FILE: "",
    SETTING_SCAN_SSH_USER: "root",
    SETTING_SCAN_SSH_HOST: "",
    SETTING_SCAN_SCRIPT_CONTENT: (
        r"""SSH_USER=$SCAN_SCRIPT_SSH_USER
SSH_HOST=$SCAN_SCRIPT_SSH_HOST
PRIVATE_KEY_FILE=$SCAN_SCRIPT_PRIVATE_KEY_FILE

if [ -z "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SCAN_SCRIPT_PRIVATE_KEY_FILE is not set" >&2
    exit 1
fi

if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SSH key file not found: $PRIVATE_KEY_FILE" >&2
    exit 1
fi

ssh -T -i "$PRIVATE_KEY_FILE" """
        r"""-o BatchMode=yes -o LogLevel=ERROR -o StrictHostKeyChecking=no """
        r""""$SSH_USER@$SSH_HOST" | """
        r"""jq -r '.arguments.leases[] | "\(."ip-address"): \(."hw-address")"' """
        r"""2>/dev/null"""
    ),
    # Device access
    SETTING_DEVICE_PASS: "",
    # NTP
    SETTING_NTP_SERVER1: "pool.ntp.org",
    # WiFi
    SETTING_WIFI1_SSID: "",
    SETTING_WIFI1_PASSWORD: "",
    SETTING_WIFI2_SSID: "",
    SETTING_WIFI2_PASSWORD: "",
    # MQTT bus
    SETTING_BUS_HOST: "bus",
    SETTING_BUS_PORT: "1883",
    SETTING_BUS_USERNAME: "admin",
    SETTING_BUS_PASSWORD: "",
    # Zigbee bridge
    SETTING_BRIDGE_HOST: "",
    SETTING_BRIDGE_DEVICES_CONFIG_PATH: "/home/pi/zigbee2mqtt/data/devices.yaml",
    # HA Groups
    SETTING_HA_GROUPS_EMPTY_GROUPS: "false",
}

# Legacy aliases (for backward compat in code that imported these directly)
DNS_SUFFIX = DEFAULT_SETTINGS[SETTING_DNS_SUFFIX]
DEFAULT_IP_PREFIX = DEFAULT_SETTINGS[SETTING_IP_PREFIX]
