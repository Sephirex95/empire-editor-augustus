from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------- Enums map 1:1 to XML attribute values ----------

class OrnamentType(str, Enum):
    STONEHENGE = "The Stonehenge"
    GALLIC_WHEAT = "Gallic Wheat"
    THE_PYRENEES = "The Pyrenees"
    IBERIAN_AQUEDUCT = "Iberian Aqueduct"
    TRIUMPHAL_ARCH = "Triumphal Arch"
    WEST_DESERT_WHEAT = "West Desert Wheat"
    LIGHTHOUSE_OF_ALEXANDRIA = "Lighthouse of Alexandria"
    WEST_DESERT_PALMS = "West Desert Palm Trees"
    TRADE_SHIP = "Trade Ship"
    WATERSIDE_PALMS = "Waterside Palm Trees"
    COLOSSEUM = "Colosseum"
    THE_ALPS = "The Alps"
    ROMAN_TREE = "Roman Tree"
    GREEK_MOUNTAIN_RANGE = "Greek Mountain Range"
    THE_PARTHENON = "The Parthenon"
    THE_PYRAMIDS = "The Pyramids"
    THE_HAGIA_SOPHIA = "The Hagia Sophia"
    EAST_DESERT_PALMS = "East Desert Palm Trees"
    EAST_DESERT_WHEAT = "East Desert Wheat"
    TRADE_CAMEL = "Trade Camel"


class CityType(str, Enum):
    OURS = "ours"
    ROMAN = "roman"
    DISTANT = "distant"
    TRADE = "trade"
    VULNERABLE = "vulnerable"   # distant roman city that can be attacked


class TradeRouteType(str, Enum):
    LAND = "land"
    SEA = "sea"


class ResourceType(str, Enum):
    WHEAT = "wheat"
    VEGETABLES = "vegetables"
    FRUIT = "fruit"
    OLIVES = "olives"
    VINES = "vines"
    MEAT = "meat"
    FISH = "fish"
    WINE = "wine"
    OIL = "oil"
    IRON = "iron"
    GOLD = "gold"
    TIMBER = "timber"   # alias "wood" handled in validation/serializer if you want
    CLAY = "clay"
    MARBLE = "marble"
    WEAPONS = "weapons"
    FURNITURE = "furniture"
    POTTERY = "pottery"


# ---------- Value objects ----------

@dataclass
class Ornament:
    """<ornament type="...">"""
    type: OrnamentType


@dataclass
class Edge:
    """<edge x="" y="" hidden="true|false">"""
    x: int
    y: int
    hidden: bool = False


@dataclass
class Border:
    """<border density=""> <edge/>* </border>"""
    density: Optional[int] = 50  # defaults to 50 per docs
    edges: List[Edge] = field(default_factory=list)


@dataclass
class Resource:
    """<resource type="" amount=""> (amount optional, defaults to 1; ours can omit)"""
    type: ResourceType
    amount: Optional[int] = 1  # per docs; for 'ours' can be omitted

    def __post_init__(self):
        if self.amount is not None and self.amount < 0:
            raise ValueError("resource.amount cannot be negative")


@dataclass
class TradePoint:
    """<point x="" y=""> inside <trade_points>"""
    x: int
    y: int


@dataclass
class City:
    """<city ...> with optional <buys>, <sells>, <trade_points>"""
    name: str
    x: int
    y: int
    type: CityType = CityType.TRADE
    trade_route_cost: Optional[int] = 500         # only for trade cities; defaults to 500
    trade_route_type: TradeRouteType = TradeRouteType.LAND
    buys: List[Resource] = field(default_factory=list)
    sells: List[Resource] = field(default_factory=list)
    trade_points: List[TradePoint] = field(default_factory=list)

    def __post_init__(self):
        # If it's our city, <sells> list is required to define what we can produce.
        if self.type == CityType.OURS and not self.sells:
            # Keep it soft: you may prefer to just allow empty and validate later during export.
            pass
        # For non-trade cities, trade route attributes are irrelevant; leave as-is or clear on export.


@dataclass
class Battle:
    """<battle x="" y="">"""
    x: int
    y: int


@dataclass
class InvasionPath:
    """<path> <battle/>* </path> inside <invasion_paths>"""
    battles: List[Battle] = field(default_factory=list)


@dataclass
class Waypoint:
    """<waypoint num_months="" x="" y="">"""
    num_months: int
    x: int
    y: int

    def __post_init__(self):
        if self.num_months <= 0:
            raise ValueError("waypoint.num_months must be > 0")


class DistantPathType(str, Enum):
    ROMAN = "roman"
    ENEMY = "enemy"


@dataclass
class DistantBattlePath:
    """
    <path type="roman|enemy" start_x="" start_y="">
        <waypoint num_months="" x="" y=""/>
        ...
    </path>
    """
    type: DistantPathType
    start_x: int
    start_y: int
    waypoints: List[Waypoint] = field(default_factory=list)


# ---------- Root ----------

@dataclass
class Empire:
    """
    <empire version="1">
        <ornament .../>*
        <border density=""><edge .../>*</border> (optional)
        <cities><city .../>*</cities>
        <invasion_paths><path>...</path>*</invasion_paths> (optional)
        <distant_battle_paths><path ...>...</path>*</distant_battle_paths> (optional)
    </empire>
    """
    version: str = "1"
    ornaments: List[Ornament] = field(default_factory=list)
    border: Optional[Border] = None
    cities: List[City] = field(default_factory=list)
    invasion_paths: List[InvasionPath] = field(default_factory=list)
    distant_battle_paths: List[DistantBattlePath] = field(default_factory=list)

    # --- convenience helpers (optional) ---

    def add_city(self,
                 name: str,
                 x: int,
                 y: int,
                 type: CityType = CityType.TRADE,
                 trade_route_cost: Optional[int] = 500,
                 trade_route_type: TradeRouteType = TradeRouteType.LAND) -> City:
        c = City(
            name=name, x=x, y=y,
            type=type,
            trade_route_cost=trade_route_cost,
            trade_route_type=trade_route_type
        )
        self.cities.append(c)
        return c

    def ensure_border(self) -> Border:
        if self.border is None:
            self.border = Border()
        return self.border
