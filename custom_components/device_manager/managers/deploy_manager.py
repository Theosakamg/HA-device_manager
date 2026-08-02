"""Device deployment operations.

Handles deploying firmware configurations to devices.
"""

import asyncio
import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..persistence.database_manager import DatabaseManager
from ..persistence.repositories import DeviceRepository

from .provision_manager import ProvisioningManager
from ..firmware.base.firmware_factory import FirmwareFactory
from .network_scanner import NetworkScanner
from ..firmware.base.config import Initializer

logger = logging.getLogger(__name__)

_DEPLOY_DONE = "done"
_DEPLOY_FAIL = "fail"


class DeployInProgressError(RuntimeError):
    """Raised when deploy() or scan() is invoked while one is already running."""


class DeployManager:
    """Coordinates device deployment and network-scan operations.

    An instance is bound to one SQLite database file. ``deploy()`` and
    ``scan()`` each run synchronously inside a Home Assistant executor thread
    and open their own DatabaseManager connection to that file.

    Both operations share a single class-level lock: without serialization, two
    concurrent calls (e.g. a user triggering a second deploy while one is
    running) can collide on writes to the same file. A second call is rejected
    immediately (see DeployInProgressError) rather than letting it race - the
    caller (deploy_controller.py) turns that into a 409.
    """

    # Class-level so the guard is shared across every DeployManager instance
    # (they all target the same on-disk SQLite file).
    _DEPLOY_LOCK = threading.Lock()

    def __init__(self, db_path: Path) -> None:
        """Initialize the manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path

    def deploy(
        self,
        firmware_types: Optional[List[str]] = None,
        mac_filter: Optional[List[str]] = None
    ) -> None:
        """Deploy configurations to devices.

        Rejects immediately (raises DeployInProgressError) if a deploy or scan is
        already running, instead of letting a second executor-thread call open a
        competing DB connection to the same file mid-run.

        Args:
            firmware_types: Optional list of firmware types to filter devices by.
                           If provided, only devices with these firmware types will be deployed.
                           If None, all enabled devices are deployed.
            mac_filter: Optional list of MAC addresses to filter devices.
                       If None or empty, all enabled devices are deployed.

        Raises:
            DeployInProgressError: If a deploy or scan is already running.
        """
        if not self._DEPLOY_LOCK.acquire(blocking=False):
            raise DeployInProgressError("A deployment or scan is already in progress")
        try:
            self._deploy_impl(firmware_types, mac_filter)
        finally:
            self._DEPLOY_LOCK.release()

    def scan(self) -> Dict[str, Any]:
        """Scan network and update device IP addresses.

        Rejects immediately (raises DeployInProgressError) if a deploy or scan is
        already running.

        Returns:
            Statistics dictionary with scan results.

        Raises:
            DeployInProgressError: If a deploy or scan is already running.
        """
        if not self._DEPLOY_LOCK.acquire(blocking=False):
            raise DeployInProgressError("A deployment or scan is already in progress")
        try:
            return self._scan_impl()
        finally:
            self._DEPLOY_LOCK.release()

    def _persist_device_status(
        self,
        db: DatabaseManager,
        device_id: int,
        status: str
    ) -> None:
        """Persist a single device's deploy status to the database (sync wrapper).

        Called right after each device is processed, rather than batching all
        statuses into one commit at the end of the loop, so already-processed
        devices keep their status even if a later device raises or the whole
        run is interrupted.

        Args:
            db: DatabaseManager instance.
            device_id: ID of the device to update.
            status: New deploy status (_DEPLOY_DONE or _DEPLOY_FAIL).
        """

        async def _update() -> None:
            repo = DeviceRepository(db)
            await repo.update_deploy_status(device_id, status)

        try:
            asyncio.run(_update())
        except Exception as e:
            logger.error(f"Failed to persist deploy status for device {device_id}: {e}")

    def _deploy_impl(
        self,
        firmware_types: Optional[List[str]] = None,
        mac_filter: Optional[List[str]] = None
    ) -> None:
        """Actual deploy implementation, guarded by deploy()'s lock."""
        Initializer()
        logger.info('Initializing deployment...')

        # Open database connection for the entire deployment
        db = DatabaseManager(self._db_path)

        async def _initialize_db():
            await db.initialize()

        asyncio.run(_initialize_db())

        try:
            # Create provisioning manager with shared DB connection
            manager = ProvisioningManager(db)

            # Load deployable firmwares from database
            deployable_firmwares = manager.load_deployable_firmwares_sync()

            if not deployable_firmwares:
                logger.error('No deployable firmwares found in database')
                return

            logger.info(f'Found {len(deployable_firmwares)} deployable firmwares: {deployable_firmwares}')

            # Load devices from database
            mac_filter_normalized = [m.upper() for m in mac_filter] if mac_filter else None
            if mac_filter_normalized:
                logger.info(f'Filtering devices to MACs: {mac_filter_normalized}')

            # Determine state filter based on deployment mode:
            # - Deploy all (no mac_filter): only 'deployed' devices
            # - Batch selection (with mac_filter): 'deployed' + 'deployed_hot'
            if mac_filter_normalized:
                # Batch mode: include deployed_hot devices
                states_filter = ['deployed', 'deployed_hot']
                logger.info('Batch deployment mode: including deployed and deployed_hot devices')
            else:
                # Deploy all mode: exclude deployed_hot devices
                states_filter = ['deployed']
                logger.info('Deploy all mode: only deployed devices (excluding deployed_hot)')

            devices = manager.load_devices_sync(
                mac_filter=mac_filter_normalized,
                enabled_only=True,
                states_filter=states_filter
            )

            if not devices:
                logger.warning('No devices found to deploy')
                return

            # Filter devices by firmware_types if provided
            if firmware_types:
                firmware_types_lower = [ft.lower() for ft in firmware_types]
                initial_count = len(devices)
                devices = [
                    d for d in devices
                    if d._refs.firmware_name.lower() in firmware_types_lower
                ]
                logger.info(
                    f'Filtered devices by firmware types {firmware_types}: '
                    f'{len(devices)}/{initial_count} devices match'
                )

            if not devices:
                logger.warning('No devices match the firmware filter')
                return

            logger.info(f'Loaded {len(devices)} devices for deployment')

            # Create firmware factory with deployable firmwares from DB
            factory = FirmwareFactory(manager, deployable_firmwares)
            adapters = factory.get_adapters()

            if not adapters:
                logger.error('No firmware adapters loaded')
                return

            logger.info(f'Loaded {len(adapters)} firmware adapters: {[a.get_firmware_type() for a in adapters]}')

            # Deploy devices
            count = 0
            success = 0
            error = 0
            skipped = 0

            for device in devices:
                count += 1
                logger.info(f"Processing device {count}/{len(devices)}: {device.mac}")

                try:
                    # Find compatible adapter
                    adapter = factory.get_adapter_for_device(device)

                    if not adapter:
                        logger.warning(
                            f"No adapter found for device {device.mac} "
                            f"(firmware: {device._refs.firmware_name})"
                        )
                        skipped += 1
                        if device.id is not None:
                            self._persist_device_status(db, device.id, _DEPLOY_FAIL)
                        continue

                    # Check if device can be deployed
                    if not adapter.can_deploy(device):
                        logger.warning(f"Device {device.mac} cannot be deployed (no IP or not reachable)")
                        skipped += 1
                        if device.id is not None:
                            self._persist_device_status(db, device.id, _DEPLOY_FAIL)
                        continue

                    # Deploy device
                    logger.info(f"Deploying with {adapter.get_firmware_type()} adapter...")
                    adapter.process(device)

                    success += 1
                    if device.id is not None:
                        self._persist_device_status(db, device.id, _DEPLOY_DONE)

                except Exception as e:
                    logger.error(f"Failed to deploy device {device.mac}: {e}", exc_info=True)
                    error += 1
                    if device.id is not None:
                        self._persist_device_status(db, device.id, _DEPLOY_FAIL)

            # Post-process (e.g., Zigbee bridge restart)
            logger.info("Running post-processing...")
            for adapter in adapters:
                try:
                    adapter.post_process(devices)
                except Exception as e:
                    logger.error(f"Post-processing failed for {adapter.get_firmware_type()}: {e}")

            logger.info(
                f"Deployment completed! Total: {count}, Success: {success}, "
                f"Skipped: {skipped}, Error: {error}"
            )

        finally:
            # Close database connection
            async def _close_db():
                await db.close()
            asyncio.run(_close_db())

    def _scan_impl(self) -> Dict[str, Any]:
        """Actual scan implementation, guarded by scan()'s lock."""
        Initializer()
        logger.info('Initializing network scan...')

        # Open database connection for the entire scan
        db = DatabaseManager(self._db_path)

        async def _initialize_db():
            await db.initialize()

        asyncio.run(_initialize_db())

        try:
            # Create network scanner with shared DB connection
            scanner = NetworkScanner(db)

            # Run scan and update IPs
            stats = scanner.scan_and_update()

            # Log results
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

        finally:
            # Close database connection
            async def _close_db():
                await db.close()
            asyncio.run(_close_db())
