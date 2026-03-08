import asyncio
import os
import subprocess
import yaml
import logging

from .contract import (
    _FLD_ID, _FLD_MAC, _FLD_STATE, _FLD_LEVEL, _FLD_LEVEL_NAME, _FLD_FUNCTION, _FLD_ROOM, _FLD_ROOM_NAME,
    _FLD_POSITION, _FLD_POSITION_NAME, _FLD_FRMW, _FLD_MODEL, _FLD_INTERLOCK, _FLD_MODE,
    _FLD_TARGET, _FLD_EXTRA, _FLD_MQTT, _FLD_HOST, _FLD_HA_DEVICE_CLASS,
    _FLD_IP, _STA_ENABLE, _STA_DISABLE,
    slug_device_topic, slug_device_id, slug_device_topic_device,
)
from .utility import get_config

from pathlib import Path

from custom_components.device_manager.services.database_manager import DatabaseManager
from custom_components.device_manager.repositories import DeviceRepository

FILE_CACHE = get_config('FILE_CACHE', 'cache_ip.yaml')
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
            logger.warning(f"Cache file {FILE_CACHE} not found on {Path(FILE_CACHE).resolve()}.Starting with empty cache.")

    def make_dict(self) -> None:
        self.load_dict()

        if not SCAN_SCRIPT:
            logger.error("SCAN_SCRIPT is not configured. Cannot perform network scan.")
            return

        logger.info(f"Running scan script: {SCAN_SCRIPT}")
        # Pass SSH config from settings as environment variables to the script.
        # SCAN_SCRIPT_PRIVATE_KEY_FILE is now the *absolute path* to the key
        # (uploaded via the UI and stored in the settings DB).
        env = os.environ.copy()
        _ssh_key = get_config('SCAN_SCRIPT_PRIVATE_KEY_FILE', '')
        _ssh_user = get_config('SCAN_SCRIPT_SSH_USER', 'root')
        _ssh_host = get_config('SCAN_SCRIPT_SSH_HOST', '')
        if _ssh_key:
            env['SCAN_SCRIPT_PRIVATE_KEY_FILE'] = _ssh_key
        if _ssh_user:
            env['SCAN_SCRIPT_SSH_USER'] = _ssh_user
        if _ssh_host:
            env['SCAN_SCRIPT_SSH_HOST'] = _ssh_host
        result = subprocess.run(
            ['bash', SCAN_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
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

    def _to_contract(self, device) -> dict:
        """Convert a DmDevice instance to a contract-field dict."""
        draft = {
            _FLD_LEVEL:      device._floor.slug,
            _FLD_LEVEL_NAME: device._floor.name,
            _FLD_ROOM:       device._room.slug,
            _FLD_FUNCTION:   device._refs.function_name,
            _FLD_POSITION:   device.position_slug,
        }
        return {
            _FLD_ID:            device.id,
            _FLD_MAC:           device.mac,
            _FLD_STATE:         _STA_ENABLE if device.enabled else _STA_DISABLE,
            _FLD_LEVEL:         draft[_FLD_LEVEL],
            _FLD_LEVEL_NAME:    draft[_FLD_LEVEL_NAME],
            _FLD_FUNCTION:      draft[_FLD_FUNCTION],
            _FLD_ROOM:          draft[_FLD_ROOM],
            _FLD_ROOM_NAME:     device._room.name,
            _FLD_POSITION:      draft[_FLD_POSITION],
            _FLD_POSITION_NAME: device.position_name,
            _FLD_FRMW:          device._refs.firmware_name,
            _FLD_MODEL:         device._refs.model_name,
            _FLD_INTERLOCK:     device.interlock,
            _FLD_MODE:          device.mode,
            _FLD_TARGET:        device.target_id or '',
            _FLD_EXTRA:         device.extra,
            _FLD_HA_DEVICE_CLASS: device.ha_device_class,
            _FLD_IP:            device.ip or '',
            _FLD_MQTT:          slug_device_topic(draft),
            _FLD_HOST:          slug_device_id(draft),
        }

    def read(self, db_path: Path):
        logger.info("Load devices from database...")
        try:
            db = DatabaseManager(db_path)
            repo = DeviceRepository(db)

            async def _fetch():
                try:
                    rows = await repo.find_all()
                    self.__devices = [self._to_contract(row) for row in rows]

                    # Replace _FLD_TARGET (MAC) with the MQTT topic of the target device
                    for device in self.__devices:
                        target_id = device.get(_FLD_TARGET, '')
                        logger.debug(f"Processing device {device[_FLD_MAC]} with target ID: {target_id}")
                        if target_id:
                            target_ = await repo.find_by_id(target_id)
                            if target_:
                                logger.debug(f"Found target device for ID {target_id}: {target_.mac}")
                                target_draft = {
                                    _FLD_LEVEL:      target_._floor.slug,
                                    _FLD_LEVEL_NAME: target_._floor.name,
                                    _FLD_ROOM:       target_._room.slug,
                                    _FLD_FUNCTION:   target_._refs.function_name,
                                    _FLD_POSITION:   target_.position_slug,
                                }
                                device[_FLD_TARGET] = slug_device_topic_device(target_draft)
                            else:
                                logger.warning(
                                    "Target device with ID %s not found",
                                    target_id,
                                )
                finally:
                    await db.close()

            asyncio.run(_fetch())

            logger.info(f"Reading {len(self.__devices)} devices.")
        except Exception as e:
            logger.error(f"Database error: {e}")

    def get(self):
        return self.__devices


class GlobalManager:
    __cache = None
    __dev_mng = None

    def __init__(self, db_path: Path) -> None:
        logger.debug("Init Global manager...")
        self.__db_path = db_path
        self.__cache = CacheManager()
        self.__dev_mng = DevicesManager()
        self.__cache.make_dict()
        self.__dev_mng.read(db_path)

    def get_devices(self):
        return self.__dev_mng.get()

    def get_macs(self):
        return self.__cache.get_macs()

    def update_devices_ip(self) -> dict:
        """Update device IPs from the cache and return scan statistics."""
        macs = self.get_macs()
        stats = {"total": 0, "mapped": 0, "not_found": 0, "errors": 0, "error_details": []}

        async def update_all():
            db = DatabaseManager(self.__db_path)
            repo = DeviceRepository(db)
            try:
                devices = await repo.find_all()
                stats["total"] = len(devices)
                for device in devices:
                    mac = device.mac.lower()
                    if mac in macs:
                        ip = macs[mac]
                        try:
                            await repo.update(device.id, {'ip': ip})
                            logger.info(f"Updated IP for {mac}: {ip}")
                            stats["mapped"] += 1
                        except Exception as e:
                            logger.error(f"Failed to update IP {ip} for {mac}: {e}")
                            stats["errors"] += 1
                            stats["error_details"].append(f"{mac}: {e}")
                    else:
                        logger.debug(f"No IP found in cache for {mac}")
                        stats["not_found"] += 1
            finally:
                await db.close()

        try:
            asyncio.run(update_all())
        except Exception as e:
            logger.error(f"Failed to update device IPs: {e}")
            stats["errors"] += 1
            stats["error_details"].append(str(e))

        logger.info(
            f"Scan report — Total: {stats['total']} | "
            f"Mapped: {stats['mapped']} | "
            f"Not found: {stats['not_found']} | "
            f"Errors: {stats['errors']}"
        )
        if stats["error_details"]:
            for detail in stats["error_details"]:
                logger.error(f"  Error detail: {detail}")

        return stats
