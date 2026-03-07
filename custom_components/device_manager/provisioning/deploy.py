import logging

from .common import FirmwareFactory
from .contract import _FLD_MAC
from .discovery import GlobalManager
from .utility import (Sanitizer, Initializer)


def base_config(device, logger, ff):
    global success
    Sanitizer.entity_sanity(device)

    logger.info(f"\033[0;34mCheck Device: {device[_FLD_MAC]}\x1b[0m")
    # Find if device.
    fwm_count = 0
    for fwm in ff.get_firmware_managers():
        # logger.debug(f"switch to {fwm.__class__} Manager.")
        if device[_FLD_MAC] and fwm.is_found(device):
            # fwm.process(device)
            success += 1
            fwm_count += 1

    # if fwm_count == 0:
    #    logger.warning('No Firmware found ! Firmware is supported or load ? ')


def deploy(db_path):
    Initializer()
    logger = logging.getLogger(__name__)
    logger.info('Initialize App...')

    gm = GlobalManager(db_path)
    ff = FirmwareFactory(gm)

    count = 0
    success = 0
    error = 0

    logger.info('Run App...')

    for __dev in gm.get_devices():
        count += 1
        logger.debug(f'Process new device: {__dev[_FLD_MAC]}')

        try:
            base_config(__dev, logger, ff)
        except Exception as e:
            logger.error(e)
            error += 1

    for fwm in ff.get_firmware_managers():
        logger.debug(f"Post process for {fwm.__class__} Manager.")
        # fwm.post_process()

    logger.info(f"Goodbye ! {count} Total Device"
                f" process, but sucess: {success} - error: {error}."
                )


def scan(db_path):
    Initializer()
    logger = logging.getLogger(__name__)
    logger.info('Initialize Scan...')

    gm = GlobalManager(db_path)
    gm.update_devices_ip()

