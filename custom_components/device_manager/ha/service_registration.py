"""Registration of Home Assistant services for Tasmota runtime operations.

Bridges HA service calls to the synchronous logic in the maintenance/update
managers by:
  * resolving the ``device_id`` target to a MAC (single-device services);
  * loading current settings from the DB;
  * running the blocking network/DB work in an executor thread;
  * emitting an activity-log entry attributed to the calling HA user;
  * returning a response dict (services declare ``SupportsResponse.OPTIONAL``).
"""

import logging
from pathlib import Path
from typing import Any, Dict

from homeassistant.core import (  # type: ignore[import]
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError  # type: ignore[import]

from .. import const
from ..const import (
    DATA_KEY_DB,
    DB_NAME,
    DOMAIN,
    SERVICE_TASMOTA_CHECK_UNAVAILABLE,
    SERVICE_TASMOTA_FORCE_AP,
    SERVICE_TASMOTA_RESTART,
    SERVICE_TASMOTA_STATUS,
    SERVICE_TASMOTA_SWITCH_AP,
    SERVICE_TASMOTA_UPDATE_FIRMWARE,
    SERVICE_TASMOTA_UPGRADE,
)
from ..persistence.repositories import SettingsRepository
from ..firmware.tasmota.target import TasmotaTargetError, resolve_device_id_to_mac
from ..managers.maintenance_manager import MaintenanceManager
from ..managers.update_manager import UpdateManager

_LOGGER = logging.getLogger(__name__)


def _db_path(hass: HomeAssistant) -> Path:
    """Return the SQLite DB path used by the integration."""
    return Path(hass.config.config_dir) / DB_NAME


async def _load_settings(hass: HomeAssistant) -> Dict[str, Any]:
    """Load the current settings dict from the DB."""
    db = hass.data[DOMAIN][DATA_KEY_DB]
    repo = SettingsRepository(db)
    return await repo.get_all()


async def _resolve_mac(hass: HomeAssistant, call: ServiceCall) -> str:
    """Resolve the call's ``device_id`` to a MAC, raising for invalid input."""
    device_id = call.data.get("device_id")
    if not device_id:
        raise ServiceValidationError("device_id is required")
    try:
        return resolve_device_id_to_mac(hass, device_id)
    except TasmotaTargetError as err:
        raise ServiceValidationError(str(err)) from err


def _get_username(hass: HomeAssistant, call: ServiceCall) -> str:
    """Best-effort resolution of the calling HA user (for activity logging)."""
    user_id = getattr(call.context, "user_id", None)
    if not user_id:
        return "system"
    user = hass.auth.async_get_user(user_id) if hasattr(hass.auth, "async_get_user") else None
    return getattr(user, "name", None) or "system"


async def _log(hass: HomeAssistant, call: ServiceCall, message: str, result: str) -> None:
    """Emit an activity-log entry for a service invocation."""
    try:
        from ..persistence.repositories import ActivityLogRepository

        db = hass.data[DOMAIN][DATA_KEY_DB]
        repo = ActivityLogRepository(db)
        await repo.log_entry(
            user=_get_username(hass, call),
            event_type="action",
            entity_type="device",
            message=f"[{call.service}] {message}",
            result=result,
        )
    except Exception as err:  # noqa: BLE001 - logging must never break a service
        _LOGGER.debug("Failed to write activity log: %s", err)


def async_register_services(hass: HomeAssistant) -> None:
    """Register all Tasmota runtime services on *hass*."""

    maintenance = MaintenanceManager()
    update = UpdateManager()

    async def _restart(call: ServiceCall) -> ServiceResponse:
        mac = await _resolve_mac(hass, call)
        settings = await _load_settings(hass)
        use_mqtt = bool(call.data.get("use_mqtt", False))
        result = await hass.async_add_executor_job(
            maintenance.restart_device, _db_path(hass), mac, settings, use_mqtt
        )
        await _log(hass, call, f"Restart {mac}", "success")
        return dict(result)

    async def _upgrade(call: ServiceCall) -> ServiceResponse:
        mac = await _resolve_mac(hass, call)
        settings = await _load_settings(hass)
        use_mqtt = bool(call.data.get("use_mqtt", False))
        result = await hass.async_add_executor_job(
            update.upgrade_device, _db_path(hass), mac, settings, use_mqtt
        )
        await _log(hass, call, f"Upgrade {mac}", "success")
        return dict(result)

    async def _status(call: ServiceCall) -> ServiceResponse:
        mac = await _resolve_mac(hass, call)
        settings = await _load_settings(hass)
        result = await hass.async_add_executor_job(
            maintenance.get_status, _db_path(hass), mac, settings
        )
        return dict(result)

    async def _switch_ap(call: ServiceCall) -> ServiceResponse:
        mac = await _resolve_mac(hass, call)
        settings = await _load_settings(hass)
        ap_id = int(call.data.get("ap_id", 1))
        result = await hass.async_add_executor_job(
            maintenance.switch_ap, _db_path(hass), mac, settings, ap_id
        )
        await _log(hass, call, f"Switch AP{ap_id} {mac}", "success")
        return dict(result)

    async def _check_unavailable(call: ServiceCall) -> ServiceResponse:
        settings = await _load_settings(hass)
        mac_filter = call.data.get("mac_filter") or None
        result = await hass.async_add_executor_job(
            maintenance.check_unavailable, _db_path(hass), settings, mac_filter
        )
        return dict(result)

    async def _force_ap(call: ServiceCall) -> ServiceResponse:
        settings = await _load_settings(hass)
        ap_id = int(call.data.get("ap_id", 1))
        mac_filter = call.data.get("mac_filter") or None
        result = await hass.async_add_executor_job(
            maintenance.force_ap_batch, _db_path(hass), settings, ap_id, mac_filter
        )
        await _log(hass, call, f"Force AP{ap_id} (batch)", "success")
        return dict(result)

    async def _update_firmware(call: ServiceCall) -> ServiceResponse:
        settings = await _load_settings(hass)
        target_version = str(call.data.get("version", ""))
        if not target_version:
            raise ServiceValidationError("version is required")
        mac_filter = call.data.get("mac_filter") or None
        result = await hass.async_add_executor_job(
            update.update_firmware_batch,
            _db_path(hass),
            settings,
            target_version,
            mac_filter,
        )
        await _log(hass, call, f"Update firmware -> {target_version} (batch)", "success")
        return dict(result)

    handlers = {
        SERVICE_TASMOTA_RESTART: _restart,
        SERVICE_TASMOTA_UPGRADE: _upgrade,
        SERVICE_TASMOTA_STATUS: _status,
        SERVICE_TASMOTA_SWITCH_AP: _switch_ap,
        SERVICE_TASMOTA_CHECK_UNAVAILABLE: _check_unavailable,
        SERVICE_TASMOTA_FORCE_AP: _force_ap,
        SERVICE_TASMOTA_UPDATE_FIRMWARE: _update_firmware,
    }

    for name, handler in handlers.items():
        hass.services.async_register(
            DOMAIN, name, handler, supports_response=SupportsResponse.OPTIONAL
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all Tasmota runtime services from *hass*."""
    for name in (
        SERVICE_TASMOTA_RESTART,
        SERVICE_TASMOTA_UPGRADE,
        SERVICE_TASMOTA_STATUS,
        SERVICE_TASMOTA_SWITCH_AP,
        SERVICE_TASMOTA_CHECK_UNAVAILABLE,
        SERVICE_TASMOTA_FORCE_AP,
        SERVICE_TASMOTA_UPDATE_FIRMWARE,
    ):
        hass.services.async_remove(DOMAIN, name)


# Reference const so linters don't flag the import as unused when service
# names are re-exported elsewhere.
_ = const
