"""Firmware runtime configuration.

Loads runtime values from the module-level ``.env`` file and lets DB-stored
settings override them before each deploy/scan. Firmware provisioning modules
(``firmware/tasmota|wled|zigbee``) and the network scanner read values through
:func:`get_config`.
"""

import logging
import os

from dotenv import load_dotenv

from ...const import (
    SETTING_BRIDGE_DEVICES_CONFIG_PATH,
    SETTING_BRIDGE_HOST,
    SETTING_BUS_HOST,
    SETTING_BUS_PASSWORD,
    SETTING_BUS_PORT,
    SETTING_BUS_USERNAME,
    SETTING_DEVICE_PASS,
    SETTING_NTP_SERVER1,
    SETTING_SCAN_SCRIPT_CONTENT,
    SETTING_SCAN_SSH_HOST,
    SETTING_SCAN_SSH_KEY_FILE,
    SETTING_SCAN_SSH_USER,
    SETTING_WIFI1_PASSWORD,
    SETTING_WIFI1_SSID,
    SETTING_WIFI2_PASSWORD,
    SETTING_WIFI2_SSID,
)

logger = logging.getLogger(__name__)

# .env / .env.sample live at the root of the deployed module
# (custom_components/device_manager/), not inside firmware/base/, so the fallback
# file is found identically in every deployment case:
# - dev: docker-compose bind-mounts ./custom_components/device_manager as-is
# - prod: install.sh does `cp -r custom_components/device_manager <config>/custom_components/device_manager`
_MODULE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DOTENV_PATH = os.path.join(_MODULE_ROOT, '.env')


class Initializer:

    def __init__(self) -> None:
        load_dotenv(dotenv_path=_DOTENV_PATH)


def load_configs() -> dict:
    configs: dict[str, str] = {}
    dotenv_path = _DOTENV_PATH
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

# Mapping: DB settings key → env variable name used by provisioning modules.
# Keys reference the SETTING_* constants (single source of truth in const.py) so
# a settings-key rename cannot silently drift from this mapping.
_DB_TO_ENV_KEY: dict[str, str] = {
    SETTING_SCAN_SSH_KEY_FILE: "SCAN_SCRIPT_PRIVATE_KEY_FILE",
    SETTING_SCAN_SSH_USER: "SCAN_SCRIPT_SSH_USER",
    SETTING_SCAN_SSH_HOST: "SCAN_SCRIPT_SSH_HOST",
    SETTING_SCAN_SCRIPT_CONTENT: "SCAN_SCRIPT_CONTENT",
    SETTING_DEVICE_PASS: "DEVICE_PASS",
    SETTING_NTP_SERVER1: "NTP_SRV1",
    SETTING_WIFI1_SSID: "WF1_SSID",
    SETTING_WIFI1_PASSWORD: "WF1_PASSWORD",
    SETTING_WIFI2_SSID: "WF2_SSID",
    SETTING_WIFI2_PASSWORD: "WF2_PASSWORD",
    SETTING_BUS_HOST: "BUS_HOST",
    SETTING_BUS_PORT: "BUS_PORT",
    SETTING_BUS_USERNAME: "BUS_USERNAME",
    SETTING_BUS_PASSWORD: "BUS_PASSWORD",
    SETTING_BRIDGE_HOST: "BRIDGE_HOST",
    SETTING_BRIDGE_DEVICES_CONFIG_PATH: "BRIDGE_DEVICES_CONFIG_PATH",
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
