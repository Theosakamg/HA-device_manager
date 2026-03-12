"""API controller for hierarchy tree operations."""

import logging

from aiohttp import web

from .base import BaseView, get_repos

_LOGGER = logging.getLogger(__name__)


class HierarchyAPIView(BaseView):
    """API endpoint for the full hierarchy tree."""

    url = "/api/device_manager/hierarchy"
    name = "api:device_manager:hierarchy"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Build and return the full hierarchy tree.

        Returns:
            JSON with structure:
            {
                "buildings": [
                    {
                        "type": "building", "id": 1, "name": "...", "slug": "...",
                        "deviceCount": N,
                        "children": [
                            {
                                "type": "floor", "id": 1, "name": "...",
                                "slug": "...", "deviceCount": N,
                                "children": [
                                    {
                                        "type": "room", "id": 1, "name": "...",
                                        "slug": "...", "deviceCount": N,
                                        "children": []
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "totalDevices": N
            }
        """
        try:
            repos = get_repos(request)
            buildings = await repos["building"].find_all()

            # Single query for all device counts by room (avoids N+1)
            room_device_counts = await repos["device"].count_all_by_room()

            total_devices = 0
            building_nodes = []

            for building in buildings:
                building_device_count = 0
                floors = await repos["floor"].find_by_building(building.id)
                floor_nodes = []

                for floor in floors:
                    floor_device_count = 0
                    rooms = await repos["room"].find_by_floor(floor.id)
                    room_nodes = []

                    for room in rooms:
                        device_count = room_device_counts.get(
                            room.id, 0
                        )
                        floor_device_count += device_count
                        room_nodes.append({
                            "type": "room",
                            "id": room.id,
                            "name": room.name,
                            "slug": room.slug,
                            "description": room.description,
                            "image": room.image,
                            "createdAt": room.created_at,
                            "updatedAt": room.updated_at,
                            "deviceCount": device_count,
                            "children": [],
                        })

                    building_device_count += floor_device_count
                    floor_nodes.append({
                        "type": "floor",
                        "id": floor.id,
                        "name": floor.name,
                        "slug": floor.slug,
                        "description": floor.description,
                        "image": floor.image,
                        "createdAt": floor.created_at,
                        "updatedAt": floor.updated_at,
                        "deviceCount": floor_device_count,
                        "children": room_nodes,
                    })

                total_devices += building_device_count
                building_nodes.append({
                    "type": "building",
                    "id": building.id,
                    "name": building.name,
                    "slug": building.slug,
                    "description": building.description,
                    "image": building.image,
                    "createdAt": building.created_at,
                    "updatedAt": building.updated_at,
                    "deviceCount": building_device_count,
                    "children": floor_nodes,
                })

            return self.json({
                "buildings": building_nodes,
                "totalDevices": total_devices,
            })
        except Exception as err:
            _LOGGER.exception("Failed to build hierarchy", exc_info=err)
            return self.json(
                {"error": "Internal server error"},
                status_code=500,
            )
