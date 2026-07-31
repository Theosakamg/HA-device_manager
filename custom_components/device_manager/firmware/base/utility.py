import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Initializer:

    def __init__(self) -> None:
        load_dotenv()


def load_configs() -> dict:
    configs: dict[str, str] = {}
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(dotenv_path):
        logger.debug("No .env file found, skipping config file loading")
        return configs
    with open(dotenv_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                configs[key.strip()] = value.strip()
    logger.debug(f"Loaded {len(configs)} config(s) from .env file")
    return configs


CONFIGS = load_configs()

# Mapping: DB settings key → env variable name used by provisioning modules
_DB_TO_ENV_KEY: dict[str, str] = {
    "scan_ssh_key_file": "SCAN_SCRIPT_PRIVATE_KEY_FILE",
    "scan_ssh_user": "SCAN_SCRIPT_SSH_USER",
    "scan_ssh_host": "SCAN_SCRIPT_SSH_HOST",
    "scan_script_content": "SCAN_SCRIPT_CONTENT",
    "device_pass": "DEVICE_PASS",
    "ntp_server1": "NTP_SRV1",
    "wifi1_ssid": "WF1_SSID",
    "wifi1_password": "WF1_PASSWORD",
    "wifi2_ssid": "WF2_SSID",
    "wifi2_password": "WF2_PASSWORD",
    "bus_host": "BUS_HOST",
    "bus_port": "BUS_PORT",
    "bus_username": "BUS_USERNAME",
    "bus_password": "BUS_PASSWORD",
    "bridge_host": "BRIDGE_HOST",
    "bridge_devices_config_path": "BRIDGE_DEVICES_CONFIG_PATH",
}


def update_runtime_configs(settings: dict) -> None:
    """Merge DB settings into CONFIGS (call before each deploy/scan).

    Only non-empty values override existing entries so that .env fallbacks
    are preserved when a DB setting has not been configured yet.
    """
    for db_key, env_key in _DB_TO_ENV_KEY.items():
        value = settings.get(db_key)
        if value is not None and value != "":
            CONFIGS[env_key] = value
    logger.debug("Runtime configs updated from DB settings.")


def get_config(key: str, default=None):
    # Mask sensitive values in logs
    if any(sensitive in key.upper() for sensitive in ['PASS', 'PASSWORD', 'KEY']):
        logger.debug(f"Get config for key: {key} with default: ***")
    else:
        logger.debug(f"Get config for key: {key} with default: {default}")
    return CONFIGS.get(key, os.getenv(key, default))
