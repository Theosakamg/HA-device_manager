"""API controller for DmFloor CRUD operations."""

from .crud import CrudListView, CrudDetailView


class FloorsAPIView(CrudListView):
    """API endpoint for floor list and creation."""

    url = "/api/device_manager/floors"
    name = "api:device_manager:floors"
    repo_key = "floor"
    entity_name = "Floor"
    filter_param = "building_id"
    filter_method = "find_by_building"


class FloorAPIView(CrudDetailView):
    """API endpoint for individual floor operations."""

    url = "/api/device_manager/floors/{entity_id}"
    name = "api:device_manager:floor"
    repo_key = "floor"
    entity_name = "Floor"
