"""API controller for DmDeviceFirmware CRUD operations."""

from .crud import CrudListView, CrudDetailView


class DeviceFirmwaresAPIView(CrudListView):
    """API endpoint for device firmware list and creation."""

    url = "/api/device_manager/device-firmwares"
    name = "api:device_manager:device_firmwares"
    repo_key = "device_firmware"
    entity_name = "Device firmware"


class DeviceFirmwareAPIView(CrudDetailView):
    """API endpoint for individual device firmware operations."""

    url = "/api/device_manager/device-firmwares/{entity_id}"
    name = "api:device_manager:device_firmware"
    repo_key = "device_firmware"
    entity_name = "Device firmware"
