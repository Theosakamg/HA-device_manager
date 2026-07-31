"""API controller for DmRoom CRUD operations."""

from .crud import CrudListView, CrudDetailView


class RoomsAPIView(CrudListView):
    """API endpoint for room list and creation."""

    url = "/api/device_manager/rooms"
    name = "api:device_manager:rooms"
    repo_key = "room"
    entity_name = "Room"
    filter_param = "floor_id"
    filter_method = "find_by_floor"


class RoomAPIView(CrudDetailView):
    """API endpoint for individual room operations."""

    url = "/api/device_manager/rooms/{entity_id}"
    name = "api:device_manager:room"
    repo_key = "room"
    entity_name = "Room"
