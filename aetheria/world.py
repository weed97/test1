"""The world graph: regions, locations and the connections between them.

A :class:`Location` is a single place the player can stand in (a tavern, a market
square, a forest clearing).  Locations are grouped into :class:`Region` s and are
linked by named *exits* to form a navigable graph.  The :class:`World` ties it all
together and also owns the registries, clock, RNG and the living population.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Terrain(str, Enum):
    TOWN = "town"
    ROAD = "road"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    PLAINS = "plains"
    SWAMP = "swamp"
    CAVE = "cave"
    RUINS = "ruins"
    COAST = "coast"
    DUNGEON = "dungeon"
    CASTLE = "castle"

    @property
    def danger(self) -> int:
        return {
            Terrain.TOWN: 0, Terrain.CASTLE: 0, Terrain.ROAD: 1,
            Terrain.PLAINS: 1, Terrain.COAST: 1, Terrain.FOREST: 2,
            Terrain.MOUNTAIN: 3, Terrain.SWAMP: 3, Terrain.RUINS: 3,
            Terrain.CAVE: 4, Terrain.DUNGEON: 5,
        }[self]


@dataclass
class Location:
    id: str
    name: str
    region_id: str
    terrain: Terrain
    description: str
    exits: dict[str, str] = field(default_factory=dict)   # direction/name -> location_id
    is_safe: bool = False              # no random encounters here
    spawn_table: list[tuple[str, float]] = field(default_factory=list)  # (npc_template, weight)
    travel_hours: int = 1              # time cost to enter this location
    discovered_desc: str = ""          # extra description once visited
    points_of_interest: list[str] = field(default_factory=list)
    ambient: list[str] = field(default_factory=list)   # flavour lines

    def exit_list(self) -> list[str]:
        return sorted(self.exits.keys())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "region_id": self.region_id,
            "terrain": self.terrain.value, "description": self.description,
            "exits": dict(self.exits), "is_safe": self.is_safe,
            "spawn_table": [list(x) for x in self.spawn_table],
            "travel_hours": self.travel_hours, "discovered_desc": self.discovered_desc,
            "points_of_interest": list(self.points_of_interest),
            "ambient": list(self.ambient),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(
            id=data["id"], name=data["name"], region_id=data["region_id"],
            terrain=Terrain(data["terrain"]), description=data["description"],
            exits=dict(data.get("exits", {})), is_safe=bool(data.get("is_safe", False)),
            spawn_table=[tuple(x) for x in data.get("spawn_table", [])],
            travel_hours=int(data.get("travel_hours", 1)),
            discovered_desc=data.get("discovered_desc", ""),
            points_of_interest=list(data.get("points_of_interest", [])),
            ambient=list(data.get("ambient", [])),
        )


@dataclass
class Region:
    id: str
    name: str
    description: str
    controlling_faction: str = ""
    danger_level: int = 1
    lore: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "controlling_faction": self.controlling_faction,
            "danger_level": self.danger_level, "lore": self.lore,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Region":
        return cls(
            id=data["id"], name=data["name"], description=data["description"],
            controlling_faction=data.get("controlling_faction", ""),
            danger_level=int(data.get("danger_level", 1)),
            lore=data.get("lore", ""),
        )


class WorldMap:
    """Holds every region and location and answers navigation queries."""

    def __init__(self) -> None:
        self.regions: dict[str, Region] = {}
        self.locations: dict[str, Location] = {}

    def add_region(self, region: Region) -> Region:
        self.regions[region.id] = region
        return region

    def add_location(self, location: Location) -> Location:
        self.locations[location.id] = location
        return location

    def get_location(self, location_id: str) -> Location:
        return self.locations[location_id]

    def get_region(self, region_id: str) -> Region:
        return self.regions[region_id]

    def neighbours(self, location_id: str) -> dict[str, str]:
        loc = self.locations.get(location_id)
        return dict(loc.exits) if loc else {}

    def resolve_exit(self, location_id: str, direction: str) -> str | None:
        loc = self.locations.get(location_id)
        if not loc:
            return None
        direction = direction.lower().strip()
        # exact direction match
        for name, dest in loc.exits.items():
            if name.lower() == direction:
                return dest
        # match by destination location name
        for dest in loc.exits.values():
            target = self.locations.get(dest)
            if target and target.name.lower() == direction:
                return dest
        # partial match by exit name or destination name
        for name, dest in loc.exits.items():
            if direction in name.lower():
                return dest
            target = self.locations.get(dest)
            if target and direction in target.name.lower():
                return dest
        return None

    def path(self, start: str, goal: str) -> list[str]:
        """Breadth-first shortest path between two locations (inclusive)."""
        if start == goal:
            return [start]
        from collections import deque
        queue = deque([[start]])
        seen = {start}
        while queue:
            route = queue.popleft()
            for dest in self.locations[route[-1]].exits.values():
                if dest in seen:
                    continue
                new_route = route + [dest]
                if dest == goal:
                    return new_route
                seen.add(dest)
                queue.append(new_route)
        return []

    def locations_in_region(self, region_id: str) -> list[Location]:
        return [l for l in self.locations.values() if l.region_id == region_id]

    def to_dict(self) -> dict:
        return {
            "regions": {r.id: r.to_dict() for r in self.regions.values()},
            "locations": {l.id: l.to_dict() for l in self.locations.values()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldMap":
        wm = cls()
        for rdata in data.get("regions", {}).values():
            wm.add_region(Region.from_dict(rdata))
        for ldata in data.get("locations", {}).values():
            wm.add_location(Location.from_dict(ldata))
        return wm
