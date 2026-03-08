import logging

from .contract import (_FLD_FRMW, _FLD_STATE, _STA_ENABLE)
from .utility import get_config


logger = logging.getLogger(__name__)


class FirmwareManagerBase:

    def __init__(self, gm) -> None:
        logger.debug("Init Firmware manager...")
        self.gm = gm

    def is_found(self, device: dict) -> bool:
        return self.is_same_type(device) and self.is_enabled(device)

    def is_enabled(self, device: dict) -> bool:
        enabled = device[_FLD_STATE] == _STA_ENABLE
        logger.debug(f"Device is enable: {enabled}...")

        if not enabled:
            logger.info("Device is Disable")

        return enabled

    def is_same_type(self, device: dict) -> bool:
        result = device[_FLD_FRMW] == self.get_type()
        logger.debug(f"Device firmware type '{self.get_type()}': {result}...")

        if result:
            logger.info(f"Device is '{self.get_type()}'")

        return result

    def process(self, device: dict):
        logger.error("Need to implement it !")

    def post_process(self, devices):
        pass


class FirmwareFactory:
    __fwms = []

    def __init__(self, gm, firmware_types=None) -> None:
        logger.debug("Init Firmware factory...")

        if firmware_types is None:
            __fwms_str = 'tasmota', 'zigbee', 'wled'
        else:
            __fwms_str = firmware_types

        if 'tasmota' in __fwms_str:
            logger.info("Load Tasmota Manager...")
            from .tasmota import TasmotaManager
            __fm = TasmotaManager(gm)
            self.__fwms.append(__fm)

        if 'zigbee' in __fwms_str:
            logger.info("Load Zigbee Manager...")
            from .zigbee import ZigbeeManager
            __fm = ZigbeeManager(gm)
            self.__fwms.append(__fm)

        if 'wled' in __fwms_str:
            logger.info("Load WLED Manager...")
            from .wled import WLEDManager
            __fm = WLEDManager(gm)
            self.__fwms.append(__fm)

    def get_firmware_managers(self) -> list[FirmwareManagerBase]:
        return self.__fwms
