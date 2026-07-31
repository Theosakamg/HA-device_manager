"""API controller for hierarchy tree operations."""

import logging

from aiohttp import web

from .base import BaseView, get_repos
from ..dto import HierarchyDto, HierarchyNodeDto

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
                        room_nodes.append(
                            HierarchyNodeDto.from_entity(
                                "room", room, device_count, []
                            )
                        )

                    building_device_count += floor_device_count
                    floor_nodes.append(
                        HierarchyNodeDto.from_entity(
                            "floor", floor, floor_device_count, room_nodes
                        )
                    )

                total_devices += building_device_count
                building_nodes.append(
                    HierarchyNodeDto.from_entity(
                        "building", building, building_device_count, floor_nodes
                    )
                )

            return self.json(
                HierarchyDto(
                    buildings=building_nodes,
                    total_devices=total_devices,
                ).to_api_dict()
            )
        except Exception as err:
            _LOGGER.exception("Failed to build hierarchy", exc_info=err)
            return self.json(
                {"error": "Internal server error"},
                status_code=500,
            )
