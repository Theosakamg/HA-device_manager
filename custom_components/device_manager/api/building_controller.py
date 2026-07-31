"""API controller for DmBuilding CRUD operations."""

from .crud import CrudListView, CrudDetailView


class BuildingsAPIView(CrudListView):
    """API endpoint for building list and creation."""

    url = "/api/device_manager/buildings"
    name = "api:device_manager:buildings"
    repo_key = "building"
    entity_name = "Building"


class BuildingAPIView(CrudDetailView):
    """API endpoint for individual building operations."""

    url = "/api/device_manager/buildings/{entity_id}"
    name = "api:device_manager:building"
    repo_key = "building"
    entity_name = "Building"
