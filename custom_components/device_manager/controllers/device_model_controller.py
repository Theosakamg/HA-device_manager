"""API controller for DmDeviceModel CRUD operations."""

from .crud import CrudListView, CrudDetailView


class DeviceModelsAPIView(CrudListView):
    """API endpoint for device model list and creation."""

    url = "/api/device_manager/device-models"
    name = "api:device_manager:device_models"
    repo_key = "device_model"
    entity_name = "Device model"


class DeviceModelAPIView(CrudDetailView):
    """API endpoint for individual device model operations."""

    url = "/api/device_manager/device-models/{entity_id}"
    name = "api:device_manager:device_model"
    repo_key = "device_model"
    entity_name = "Device model"
