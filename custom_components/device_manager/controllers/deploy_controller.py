"""API controller for deployment operations."""

import logging

from .base import BaseView, get_repos, get_db_path, rate_limit, csrf_protect, emit_activity_log, fmt_entity_label
from ..provisioning.deploy import deploy, scan
from ..provisioning.utility import update_runtime_configs

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
        await hass.async_add_executor_job(deploy, db_path, firmware_types, mac_filter)

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
        stats = await hass.async_add_executor_job(scan, db_path)
        await emit_activity_log(
            request,
            event_type="action",
            entity_type="scan",
            message="Network scan completed",
            result=str(stats) if isinstance(stats, dict) else None,
        )
        return self.json({
            "result": "Scan completed",
            "stats": stats if isinstance(stats, dict) else {},
        }, status_code=200)
