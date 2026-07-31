"""API controller for DmDeviceFunction CRUD operations."""

from .crud import CrudListView, CrudDetailView


class DeviceFunctionsAPIView(CrudListView):
    """API endpoint for device function list and creation."""

    url = "/api/device_manager/device-functions"
    name = "api:device_manager:device_functions"
    repo_key = "device_function"
    entity_name = "Device function"


class DeviceFunctionAPIView(CrudDetailView):
    """API endpoint for individual device function operations."""

    url = "/api/device_manager/device-functions/{entity_id}"
    name = "api:device_manager:device_function"
    repo_key = "device_function"
    entity_name = "Device function"
