"""Network scanner for discovering device IP addresses.

"""

import logging
import os
import subprocess
from typing import Dict, Any

import yaml

from ...services.database_manager import DatabaseManager
from ...repositories import DeviceRepository
from ..utility import get_config

logger = logging.getLogger(__name__)


class NetworkScanner:
    """Scans network and updates device IPs in the database.

    Uses an external script to discover MAC-to-IP mappings on the network,
    then updates the database directly without using intermediate cache files.
    The database connection is provided at initialization to avoid constant
    open/close cycles.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the scanner.

        Args:
            db: DatabaseManager instance (must be already initialized).
        """
        self.db = db
        self._scan_results: Dict[str, str] = {}

    def run_network_scan(self) -> Dict[str, str]:
        """Execute network scan script to discover MAC-to-IP mappings.

        Returns:
            Dictionary mapping MAC addresses (lowercase) to IP addresses.
        """
        scan_script_content = get_config('SCAN_SCRIPT_CONTENT', '')

        if not scan_script_content:
            logger.error("SCAN_SCRIPT_CONTENT is not configured. Cannot perform network scan.")
            return {}

        logger.info("Executing scan script from database")

        # Prepare environment variables for the script
        env = os.environ.copy()
        ssh_key = get_config('SCAN_SCRIPT_PRIVATE_KEY_FILE', '')
        ssh_user = get_config('SCAN_SCRIPT_SSH_USER', 'root')
        ssh_host = get_config('SCAN_SCRIPT_SSH_HOST', '')

        if ssh_key:
            env['SCAN_SCRIPT_PRIVATE_KEY_FILE'] = ssh_key
        if ssh_user:
            env['SCAN_SCRIPT_SSH_USER'] = ssh_user
        if ssh_host:
            env['SCAN_SCRIPT_SSH_HOST'] = ssh_host

        # Execute the script content directly via bash -c
        try:
            result = subprocess.run(
                ['bash', '-c', scan_script_content],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=300,  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            logger.error("Scan script timed out after 5 minutes")
            return {}
        except Exception as e:
            logger.error(f"Failed to execute scan script: {e}")
            return {}

        # Check for errors
        stderr_output = result.stderr.decode('utf-8').strip()
        if result.returncode != 0:
            logger.error(f"Scan script error (exit {result.returncode}): {stderr_output}")
            return {}
        if stderr_output:
            logger.warning(f"Scan script stderr: {stderr_output}")

        # Parse output (expected format: YAML with "ip: mac")
        try:
            raw_output = result.stdout.decode('utf-8')
            scan_result = yaml.safe_load(raw_output)

            if not isinstance(scan_result, dict):
                logger.error(
                    f"Unexpected scan output format (expected dict, got {type(scan_result).__name__}): "
                    f"{raw_output!r}"
                )
                return {}

            # Normalize: lowercase MACs
            self._scan_results = {
                str(mac).lower(): str(ip)
                for ip, mac in scan_result.items()
            }

            logger.info(f"Scan completed: found {len(self._scan_results)} devices")
            return self._scan_results

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse scan script output: {e}")
            return {}

    async def update_device_ips(self) -> Dict[str, Any]:
        """Update device IP addresses in the database from scan results.

        Returns:
            Statistics dictionary with keys: total, mapped, not_found, errors, error_details.
        """
        if not self._scan_results:
            logger.warning("No scan results available. Run run_network_scan() first.")
            return {
                "total": 0,
                "mapped": 0,
                "not_found": 0,
                "errors": 1,
                "error_details": ["No scan results available"]
            }

        stats = {
            "total": 0,
            "mapped": 0,
            "not_found": 0,
            "errors": 0,
            "error_details": []
        }

        repo = DeviceRepository(self.db)

        try:
            devices = await repo.find_all()
            stats["total"] = len(devices)

            for device in devices:
                mac = device.mac.lower().strip()

                if mac in self._scan_results:
                    ip = self._scan_results[mac]
                    try:
                        if device.id is not None:
                            await repo.update(device.id, {'ip': ip})
                        logger.info(f"Updated IP for {mac}: {ip}")
                        stats["mapped"] += 1
                    except Exception as e:
                        logger.error(f"Failed to update IP {ip} for {mac}: {e}")
                        stats["errors"] += 1
                        stats["error_details"].append(f"{mac}: {e}")
                else:
                    logger.debug(f"No IP found in scan results for {mac}")
                    stats["not_found"] += 1

        except Exception as e:
            logger.error(f"Failed to update device IPs: {e}")
            stats["errors"] += 1
            stats["error_details"].append(str(e))

        return stats

    def scan_and_update(self) -> Dict[str, Any]:
        """Run network scan and update device IPs in database (synchronous wrapper).

        Note: Prefer using async version when possible.

        Returns:
            Statistics dictionary.
        """
        import asyncio

        # Run the scan
        self.run_network_scan()

        # Update IPs in database
        return asyncio.run(self.update_device_ips())
