import asyncio
import logging

from .common import FirmwareFactory
from .contract import _FLD_ID, _FLD_MAC
from .discovery import GlobalManager
from .utility import (Sanitizer, Initializer)

from custom_components.device_manager.services.database_manager import DatabaseManager
from custom_components.device_manager.repositories import DeviceRepository

_DEPLOY_DONE = "done"
_DEPLOY_FAIL = "fail"


def base_config(device, logger, ff):
    Sanitizer.entity_sanity(device)

    logger.info(f"\033[0;34mCheck Device: {device[_FLD_MAC]}\x1b[0m")

    # Find if device.
    success = False
    fwm_count = 0
    for fwm in ff.get_firmware_managers():
        if device[_FLD_MAC] and fwm.is_found(device):
            logger.info(f"Process Device with {fwm.__class__} Manager.")
            fwm.process(device)
            success = True
            fwm_count += 1

    if fwm_count == 0:
        logger.warning('No Firmware found ! Firmware is supported or loaded ?')

    return success


def _persist_deploy_results(
    db_path, results: dict[int, str], logger
) -> None:
    """Persist per-device deploy status to the database (sync wrapper)."""

    async def _update_all():
        db = DatabaseManager(db_path)
        repo = DeviceRepository(db)
        try:
            for device_id, status in results.items():
                try:
                    await repo.update_deploy_status(device_id, status)
                except Exception as e:
                    logger.error(
                        f"Failed to persist deploy status for device {device_id}: {e}"
                    )
        finally:
            await db.close()

    try:
        asyncio.run(_update_all())
    except Exception as e:
        logger.error(f"Failed to persist deploy results: {e}")


def deploy(db_path, firmware_types, mac_filter=None):
    """Deploy devices with config file.
    firmware_types is a list of firmware to deploy. Can be "tasmota", "zigbee", "wled".
    mac_filter is an optional list of MAC addresses to restrict which devices are updated.
    If mac_filter is empty or None, all devices are updated.
    """

    Initializer()
    logger = logging.getLogger(__name__)
    logger.info('Initialize Deploy...')

    gm = GlobalManager(db_path)
    ff = FirmwareFactory(gm, firmware_types)

    count = 0
    success = 0
    error = 0
    deploy_results: dict[int, str] = {}

    mac_filter = [m.upper() for m in mac_filter] if mac_filter else []
    if mac_filter:
        logger.info(f'Filtering devices to MACs: {mac_filter}')
    logger.info(f'Start deploy process for all devices for firmwares: {firmware_types}...')

    devices = gm.get_devices()

    for __dev in devices:
        if mac_filter and __dev[_FLD_MAC].upper() not in mac_filter:
            logger.debug(f'Skipping device (not in mac_filter): {__dev[_FLD_MAC]}')
            continue

        count += 1
        device_id = __dev.get(_FLD_ID)
        logger.debug(f'Process new device: {__dev[_FLD_MAC]}')

        try:
            matched = base_config(__dev, logger, ff)
            if matched:
                success += 1
            if device_id is not None:
                deploy_results[device_id] = _DEPLOY_DONE
        except Exception as e:
            logger.error(e)
            error += 1
            if device_id is not None:
                deploy_results[device_id] = _DEPLOY_FAIL

    for fwm in ff.get_firmware_managers():
        logger.debug(f"Post process for {fwm.__class__} Manager. For {len(devices)} devices...")
        fwm.post_process(devices)

    if deploy_results:
        logger.info(f"Persisting deploy status for {len(deploy_results)} devices...")
        _persist_deploy_results(db_path, deploy_results, logger)

    logger.info(
        f"Goodbye ! {count} Total Device"
        f" process, but success: {success} - error: {error}."
    )


def scan(db_path) -> dict:
    Initializer()
    logger = logging.getLogger(__name__)
    logger.info('Initialize Scan...')

    gm = GlobalManager(db_path)
    stats = gm.update_devices_ip()

    logger.info("=" * 50)
    logger.info("SCAN REPORT")
    logger.info("=" * 50)
    logger.info(f"  Total devices  : {stats['total']}")
    logger.info(f"  Mapped (IP OK) : {stats['mapped']}")
    logger.info(f"  Not found      : {stats['not_found']}")
    logger.info(f"  Errors         : {stats['errors']}")
    if stats.get("error_details"):
        logger.info("  Error details:")
        for detail in stats["error_details"]:
            logger.error(f"    - {detail}")
    logger.info("=" * 50)

    return stats

