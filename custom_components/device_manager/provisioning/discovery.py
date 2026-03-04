import asyncio
import os
import subprocess
import yaml
import logging
from pathlib import Path

from .contract import (
    _FLD_MAC, _FLD_STATE, _FLD_LEVEL, _FLD_FUNCTION, _FLD_ROOM,
    _FLD_POSITION, _FLD_FRMW, _FLD_MODEL, _FLD_INTERLOCK, _FLD_MODE,
    _FLD_TARGET, _FLD_EXTRA, _FLD_MQTT, _FLD_HOST, _FLD_HA_DEVICE_CLASS,
    _FLD_IP, _STA_ENABLE, _STA_DISABLE,
    slug_device_topic, slug_device_id,
)
from .utility import get_config

from custom_components.device_manager.services.database_manager import DatabaseManager
from custom_components.device_manager.repositories import DeviceRepository

FILE_CACHE = get_config('FILE_CACHE', 'cache_ip.yaml')
FILE_DB = get_config('FILE_DB', 'device_manager.db')
SCAN_SCRIPT = get_config('SCAN_SCRIPT', None)

logger = logging.getLogger(__name__)


class CacheManager:
    __macs_c = {}

    def __init__(self) -> None:
        logger.debug("Init Cache manager...")

    def load_dict(self) -> None:
        logger.info(f"Re/load cache... from cache file {FILE_CACHE}")
        if os.path.isfile(FILE_CACHE):
            with open(FILE_CACHE, 'r') as stream:
                try:
                    self.__macs_c = yaml.safe_load(stream)
                    logger.info(f"Reading {len(self.__macs_c)} mac address.")
                except yaml.YAMLError as e:
                    logger.error(e)
        else:
            logger.warning(f"Cache file {FILE_CACHE} not found on {Path(FILE_CACHE).resolve()}. Starting with empty cache.")

    def make_dict(self) -> None:
        self.load_dict()

        if not SCAN_SCRIPT:
            logger.error("SCAN_SCRIPT is not configured. Cannot perform network scan.")
            return

        logger.info(f"Running scan script: {SCAN_SCRIPT}")
        result = subprocess.run(
            ['bash', SCAN_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stderr_output = result.stderr.decode('utf-8').strip()
        if result.returncode != 0:
            logger.error(f"Scan script error (exit {result.returncode}): {stderr_output}")
            return
        if stderr_output:
            logger.warning(f"Scan script stderr: {stderr_output}")

        try:
            # Expected output format: "ip: mac" (YAML)
            raw_output = result.stdout.decode('utf-8')
            scan_result = yaml.safe_load(raw_output)
            if not isinstance(scan_result, dict):
                logger.error(f"Unexpected scan script output (expected dict, got {type(scan_result).__name__}): {raw_output!r}")
                return
            self.__macs_c.update({str(mac).lower(): str(ip) for ip, mac in scan_result.items()})
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse scan script output: {e}")
            return

        logger.info("Save on cache...")
        with open(FILE_CACHE, "w") as stream:
            try:
                yaml.dump(self.__macs_c, stream)
            except OSError as e:
                logger.error(e)

        logger.info(f"Reading {len(self.__macs_c)} mac address.")

    def get_macs(self):
        return self.__macs_c


class DevicesManager:
    __devices = []

    def __init__(self) -> None:
        logger.debug("Init Devices manager...")

    def _to_contract(self, row: dict) -> dict:
        """Convert a repository row to a contract-field dict."""
        draft = {
            _FLD_LEVEL:    row.get('floor_slug', ''),
            _FLD_ROOM:     row.get('room_slug', ''),
            _FLD_FUNCTION: row.get('function_name', ''),
            _FLD_POSITION: row.get('position_slug', ''),
        }
        return {
            _FLD_MAC:           row.get('mac', ''),
            _FLD_STATE:         _STA_ENABLE if row.get('enabled', 0) else _STA_DISABLE,
            _FLD_LEVEL:         draft[_FLD_LEVEL],
            _FLD_FUNCTION:      draft[_FLD_FUNCTION],
            _FLD_ROOM:          draft[_FLD_ROOM],
            _FLD_POSITION:      draft[_FLD_POSITION],
            _FLD_FRMW:          row.get('firmware_name', ''),
            _FLD_MODEL:         row.get('model_name', ''),
            _FLD_INTERLOCK:     row.get('interlock', ''),
            _FLD_MODE:          row.get('mode', ''),
            _FLD_TARGET:        row.get('target_mac', ''),
            _FLD_EXTRA:         row.get('extra', ''),
            _FLD_HA_DEVICE_CLASS: row.get('ha_device_class', ''),
            _FLD_IP:            row.get('ip', ''),
            _FLD_MQTT:          slug_device_topic(draft),
            _FLD_HOST:          slug_device_id(draft),
        }

    def read(self):
        logger.info(f"Load devices from database: {FILE_DB}...")
        try:
            db_manager = DatabaseManager(Path(FILE_DB))
            repo = DeviceRepository(db_manager)

            async def _fetch():
                try:
                    return await repo.find_all()
                finally:
                    await db_manager.close()

            rows = asyncio.run(_fetch())
            self.__devices = [self._to_contract(row) for row in rows]
            logger.info(f"Reading {len(self.__devices)} devices.")
        except Exception as e:
            logger.error(f"Database error: {e}")

    def get(self):
        return self.__devices


class GlobalManager:
    __cache = None
    __dev_mng = None

    def __init__(self) -> None:
        logger.debug("Init Global manager...")
        self.__cache = CacheManager()
        self.__dev_mng = DevicesManager()
        self.__cache.make_dict()
        self.__dev_mng.read()

    def get_devices(self):
        return self.__dev_mng.get()

    def get_macs(self):
        return self.__cache.get_macs()

    def update_devices_ip(self):
        db_manager = DatabaseManager(Path(FILE_DB))
        repo = DeviceRepository(db_manager)
        macs = self.get_macs()

        async def update_all():
            devices = await repo.find_all()

            for device in devices:
                mac = device.get('mac', '').lower()
                if mac in macs:
                    ip = macs[mac]
                    try:
                        await repo.update(device['id'], {'ip': ip})
                        logger.info(f"Updated IP for {mac}: {ip}")
                    except Exception as e:
                        logger.error(f"Failed to update IP {ip} for {mac}: {e}")

        try:
            asyncio.run(update_all())
        except Exception as e:
            logger.error(f"Failed to update device IPs: {e}")
        finally:
            asyncio.run(db_manager.close())
