"""API controller for Tasmota runtime operations.

Exposes the synchronous logic in the maintenance/update managers over REST so the
frontend can trigger restart / upgrade / status / batch operations. Unlike the
HA services (targeted by ``device_id``), these endpoints accept a ``mac``
directly, matching how the frontend already identifies devices.
"""

import logging

from .base import (
    BaseView,
    get_repos,
    get_db_path,
    rate_limit,
    csrf_protect,
    emit_activity_log,
)
from ..managers.maintenance_manager import MaintenanceManager, BatchInProgressError, TasmotaRuntimeError
from ..managers.update_manager import UpdateManager

_LOGGER = logging.getLogger(__name__)

_maintenance = MaintenanceManager()
_update = UpdateManager()


async def _load_settings(request):
    """Load current settings dict from the DB."""
    return await get_repos(request)["settings"].get_all()


async def _read_body(request):
    """Parse the JSON body, returning an empty dict on failure."""
    try:
        return await request.json()
    except Exception:  # noqa: BLE001
        return {}


class TasmotaRestartAPIView(BaseView):
    """Restart a single Tasmota device."""

    url = "/api/device_manager/tasmota/restart"
    name = "api:device_manager:tasmota:restart"

    @rate_limit(requests=10, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        mac = body.get("mac")
        if not mac:
            return self.json({"error": "mac is required"}, status_code=400)
        settings = await _load_settings(request)
        use_mqtt = bool(body.get("use_mqtt", False))
        try:
            result = await hass.async_add_executor_job(
                _maintenance.restart_device, get_db_path(request), mac, settings, use_mqtt
            )
        except TasmotaRuntimeError as exc:
            return self.json({"error": str(exc)}, status_code=502)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Restart `{mac}`",
        )
        return self.json(result, status_code=200)


class TasmotaUpgradeAPIView(BaseView):
    """Trigger OTA upgrade on a single Tasmota device."""

    url = "/api/device_manager/tasmota/upgrade"
    name = "api:device_manager:tasmota:upgrade"

    @rate_limit(requests=10, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        mac = body.get("mac")
        if not mac:
            return self.json({"error": "mac is required"}, status_code=400)
        settings = await _load_settings(request)
        use_mqtt = bool(body.get("use_mqtt", False))
        try:
            result = await hass.async_add_executor_job(
                _update.upgrade_device, get_db_path(request), mac, settings, use_mqtt
            )
        except TasmotaRuntimeError as exc:
            return self.json({"error": str(exc)}, status_code=502)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Upgrade `{mac}`",
        )
        return self.json(result, status_code=200)


class TasmotaStatusAPIView(BaseView):
    """Query the full status of a single Tasmota device."""

    url = "/api/device_manager/tasmota/status"
    name = "api:device_manager:tasmota:status"

    @rate_limit(requests=30, window=60)
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        mac = body.get("mac")
        if not mac:
            return self.json({"error": "mac is required"}, status_code=400)
        settings = await _load_settings(request)
        try:
            result = await hass.async_add_executor_job(
                _maintenance.get_status, get_db_path(request), mac, settings
            )
        except TasmotaRuntimeError as exc:
            return self.json({"error": str(exc)}, status_code=502)
        return self.json(result, status_code=200)


class TasmotaSwitchApAPIView(BaseView):
    """Switch the active AP of a single Tasmota device."""

    url = "/api/device_manager/tasmota/switch-ap"
    name = "api:device_manager:tasmota:switch-ap"

    @rate_limit(requests=10, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        mac = body.get("mac")
        if not mac:
            return self.json({"error": "mac is required"}, status_code=400)
        settings = await _load_settings(request)
        ap_id = int(body.get("ap_id", 1))
        try:
            result = await hass.async_add_executor_job(
                _maintenance.switch_ap, get_db_path(request), mac, settings, ap_id
            )
        except TasmotaRuntimeError as exc:
            return self.json({"error": str(exc)}, status_code=502)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Switch AP{ap_id} `{mac}`",
        )
        return self.json(result, status_code=200)


class TasmotaCheckUnavailableAPIView(BaseView):
    """Ping devices and report which are offline."""

    url = "/api/device_manager/tasmota/check-unavailable"
    name = "api:device_manager:tasmota:check-unavailable"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        settings = await _load_settings(request)
        mac_filter = body.get("macs") or None
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")
        try:
            result = await hass.async_add_executor_job(
                _maintenance.check_unavailable, get_db_path(request), settings, mac_filter
            )
        except BatchInProgressError as exc:
            return self.json({"error": str(exc)}, status_code=409)
        return self.json(result, status_code=200)


class TasmotaForceApAPIView(BaseView):
    """Switch the active AP on every (or filtered) device."""

    url = "/api/device_manager/tasmota/force-ap"
    name = "api:device_manager:tasmota:force-ap"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        settings = await _load_settings(request)
        ap_id = int(body.get("ap_id", 1))
        mac_filter = body.get("macs") or None
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")
        try:
            result = await hass.async_add_executor_job(
                _maintenance.force_ap_batch, get_db_path(request), settings, ap_id, mac_filter
            )
        except BatchInProgressError as exc:
            return self.json({"error": str(exc)}, status_code=409)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Force AP{ap_id} (batch)",
        )
        return self.json(result, status_code=200)


class TasmotaRestartBatchAPIView(BaseView):
    """Restart every (or a filtered subset of) device."""

    url = "/api/device_manager/tasmota/restart-batch"
    name = "api:device_manager:tasmota:restart-batch"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        settings = await _load_settings(request)
        use_mqtt = bool(body.get("use_mqtt", False))
        mac_filter = body.get("macs") or None
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")
        try:
            result = await hass.async_add_executor_job(
                _maintenance.restart_batch, get_db_path(request), settings, mac_filter, use_mqtt
            )
        except BatchInProgressError as exc:
            return self.json({"error": str(exc)}, status_code=409)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Restart {result['total']} device(s) (batch)",
        )
        return self.json(result, status_code=200)


class TasmotaUpdateFirmwareAPIView(BaseView):
    """Trigger OTA upgrade only on devices older than a target version."""

    url = "/api/device_manager/tasmota/update-firmware"
    name = "api:device_manager:tasmota:update-firmware"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        target_version = body.get("version")
        if not target_version:
            return self.json({"error": "version is required"}, status_code=400)
        settings = await _load_settings(request)
        mac_filter = body.get("macs") or None
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")
        try:
            result = await hass.async_add_executor_job(
                _update.update_firmware_batch,
                get_db_path(request),
                settings,
                str(target_version),
                mac_filter,
            )
        except BatchInProgressError as exc:
            return self.json({"error": str(exc)}, status_code=409)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Update firmware -> `{target_version}` (batch)",
        )
        return self.json(result, status_code=200)


class TasmotaUpgradeBatchAPIView(BaseView):
    """Trigger an unconditional OTA upgrade on every (or a filtered subset of) device."""

    url = "/api/device_manager/tasmota/upgrade-batch"
    name = "api:device_manager:tasmota:upgrade-batch"

    @rate_limit(requests=5, window=60)
    @csrf_protect
    async def post(self, request):
        hass = request.app["hass"]
        body = await _read_body(request)
        settings = await _load_settings(request)
        use_mqtt = bool(body.get("use_mqtt", False))
        mac_filter = body.get("macs") or None
        if isinstance(mac_filter, str):
            mac_filter = mac_filter.split(",")
        try:
            result = await hass.async_add_executor_job(
                _update.upgrade_batch, get_db_path(request), settings, mac_filter, use_mqtt
            )
        except BatchInProgressError as exc:
            return self.json({"error": str(exc)}, status_code=409)
        await emit_activity_log(
            request, event_type="action", entity_type="device",
            message=f"Upgrade {result['total']} device(s) (batch)",
        )
        return self.json(result, status_code=200)
