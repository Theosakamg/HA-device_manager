"""API controller for deployment operations."""

import logging

from .base import BaseView, get_repos, get_db_path, rate_limit, csrf_protect, emit_activity_log, fmt_entity_label
from ..managers.deploy_manager import DeployManager, DeployInProgressError
from ..managers.network_scanner import NetworkScanError
from ..firmware.base.config import update_runtime_configs
from ..dto import ScanReportDto

_LOGGER = logging.getLogger(__name__)


class DeployAPIView(BaseView):
    """API endpoint for triggering device deployment."""

    url = "/api/device_manager/deploy"
    name = "api:device_manager:deploy"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        """Trigger device deployment."""
        hass = request.app["hass"]
        settings = await get_repos(request)["settings"].get_all()
        update_runtime_configs(settings)

        # Parse JSON body if present
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        # firmware_types: body takes precedence over query string
        firmware_types = body.get("firmware_types") or request.query.get("firmware_types")
        if isinstance(firmware_types, str):
            firmware_types = firmware_types.split(",")

        # mac_filter: body takes precedence over query string
        mac_filter = body.get("macs") or request.query.get("macs")
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")

        db_path = get_db_path(request)
        manager = DeployManager(db_path)
        try:
            await hass.async_add_executor_job(manager.deploy, firmware_types, mac_filter)
        except DeployInProgressError as exc:
            _LOGGER.warning("Deploy rejected: %s", exc)
            return self.json({"error": str(exc)}, status_code=409)

        # Build human-readable entity list when a MAC filter is provided.
        repos = get_repos(request)
        if mac_filter:
            labels = []
            for mac in mac_filter:
                device = await repos["device"].find_by_mac(mac)
                if device:
                    labels.append(
                        fmt_entity_label("Device", device.display_name(), device.id, device.position_slug)
                    )
                else:
                    labels.append(f"Device - ??? [mac={mac}]")
            entity_list = ", ".join(labels)
            msg = f"Triggered deployment for: {entity_list}"
        else:
            fw_part = f" for firmware types: `{', '.join(firmware_types)}`" if firmware_types else ""
            msg = f"Triggered deployment{fw_part} (all devices)"

        await emit_activity_log(
            request,
            event_type="action",
            entity_type="deploy",
            message=msg,
        )
        return self.json({"result": "Deployment triggered"}, status_code=200)


class DevicesScanAPIView(BaseView):
    """API endpoint for triggering device scan."""

    url = "/api/device_manager/scan"
    name = "api:device_manager:scan"
    # requires_auth = False  # Set to True in production

    async def post(self, request):
        """Trigger device scan."""
        hass = request.app["hass"]
        settings = await get_repos(request)["settings"].get_all()
        update_runtime_configs(settings)
        db_path = get_db_path(request)
        manager = DeployManager(db_path)
        try:
            stats = await hass.async_add_executor_job(manager.scan)
        except DeployInProgressError as exc:
            _LOGGER.warning("Scan rejected: %s", exc)
            return self.json({"error": str(exc)}, status_code=409)
        except NetworkScanError as exc:
            _LOGGER.error("Network scan failed: %s", exc)
            await emit_activity_log(
                request,
                event_type="action",
                entity_type="scan",
                message="Network scan failed",
                result=str(exc),
                severity="error",
            )
            return self.json({"error": str(exc)}, status_code=500)
        except Exception as exc:
            _LOGGER.exception("Unexpected error during network scan")
            await emit_activity_log(
                request,
                event_type="action",
                entity_type="scan",
                message="Network scan failed unexpectedly",
                result=str(exc),
                severity="error",
            )
            return self.json({"error": "Internal server error"}, status_code=500)
        await emit_activity_log(
            request,
            event_type="action",
            entity_type="scan",
            message="Network scan completed",
            result=str(stats) if isinstance(stats, dict) else None,
        )
        return self.json({
            "result": "Scan completed",
            "stats": ScanReportDto.from_stats(stats if isinstance(stats, dict) else {}).to_api_dict(),
        }, status_code=200)
