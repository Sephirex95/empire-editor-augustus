from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


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
    MEAT = "meat"
    FISH = "fish"
    CLAY = "clay"
    TIMBER = "timber"
    OLIVES = "olives"
    VINES = "vines"
    IRON = "iron"
    MARBLE = "marble"
    GOLD = "gold"
    SAND = "sand"
    STONE = "stone"
    POTTERY = "pottery"
    FURNITURE = "furniture"
    OIL = "oil"
    WINE = "wine"
    WEAPONS = "weapons"
    # CONCRETE = "concrete"   # not storable
    BRICKS = "bricks"
    # DENARII = "denarii"     # not storable unless in ya pocket mate
    # TROOPS = "troops"       # not storable unless in barracks lmao 


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
class TradeRoute:
    cost: int
    type: TradeRouteType
    trade_points: List[TradePoint] = field(default_factory=list)


@dataclass
class City:
    """<city ...> with optional <buys>, <sells>, <trade_points>"""
    name: str = "City Name"
    x: int = 0
    y: int = 0
    type: CityType = CityType.TRADE
    trade_route: Optional[TradeRoute] = None  # <- replaces cost/type/points on City
    buys: List[Resource] = field(default_factory=list)
    sells: List[Resource] = field(default_factory=list)

    def __post_init__(self):
        if self.type == CityType.OURS and not self.sells:
            pass


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
    def __init__(self, version=1, ornaments=None, border=None, cities=None, invasion_paths=None, distant_battle_paths=None):
        self.version = int(version)
        self.ornaments = list(ornaments) if ornaments else []
        self.border = border
        self.cities = list(cities) if cities else []
        self.invasion_paths = list(invasion_paths) if invasion_paths else []
        self.distant_battle_paths = list(distant_battle_paths) if distant_battle_paths else []

    # ------------------------ XML writing (serialization) ------------------------

    def _to_element(self):
        root = Element("empire")
        root.set("version", str(self.version))

        for o in self.ornaments:
            o_el = SubElement(root, "ornament")
            o_el.set("type", o.type)

        if self.border is not None:
            b_el = SubElement(root, "border")
            if self.border.density is not None:
                b_el.set("density", str(self.border.density))
            for e in self.border.edges:
                e_el = SubElement(b_el, "edge")
                e_el.set("x", str(e.x))
                e_el.set("y", str(e.y))
                if e.hidden:
                    e_el.set("hidden", "true")

        cities_el = SubElement(root, "cities")
        for c in self.cities:
            c_el = SubElement(cities_el, "city")
            c_el.set("name", c.name)
            c_el.set("x", str(c.x))
            c_el.set("y", str(c.y))
            if c.type and c.type != CityType.TRADE:
                c_el.set("type", c.type)

            if c.trade_route is not None:
                tr = c.trade_route
                if tr.cost is not None:
                    c_el.set("trade_route_cost", str(tr.cost))
                if tr.type is not None:
                    c_el.set("trade_route_type", tr.type)
                if tr.trade_points:
                    tp_el = SubElement(c_el, "trade_points")
                    for p in tr.trade_points:
                        pt = SubElement(tp_el, "point")
                        pt.set("x", str(p.x))
                        pt.set("y", str(p.y))

            if c.buys:
                buys_el = SubElement(c_el, "buys")
                for r in c.buys:
                    r_el = SubElement(buys_el, "resource")
                    r_el.set("type", r.type)
                    if r.amount not in (None, 1):
                        r_el.set("amount", str(r.amount))

            if c.sells:
                sells_el = SubElement(c_el, "sells")
                omit_amount = (c.type == CityType.OURS)
                for r in c.sells:
                    r_el = SubElement(sells_el, "resource")
                    r_el.set("type", r.type)
                    if not omit_amount and r.amount not in (None, 1):
                        r_el.set("amount", str(r.amount))

            if c.type == CityType.OURS and not c.sells:
                raise ValueError("City '%s' is type='ours' but has no <sells> resources." % c.name)

        if self.invasion_paths:
            inv_el = SubElement(root, "invasion_paths")
            for p in self.invasion_paths:
                p_el = SubElement(inv_el, "path")
                for b in p.battles:
                    b_el = SubElement(p_el, "battle")
                    b_el.set("x", str(b.x))
                    b_el.set("y", str(b.y))

        if self.distant_battle_paths:
            dist_el = SubElement(root, "distant_battle_paths")
            for p in self.distant_battle_paths:
                p_el = SubElement(dist_el, "path")
                p_el.set("type", p.type)
                p_el.set("start_x", str(p.start_x))
                p_el.set("start_y", str(p.start_y))
                for w in p.waypoints:
                    w_el = SubElement(p_el, "waypoint")
                    w_el.set("num_months", str(w.num_months))
                    w_el.set("x", str(w.x))
                    w_el.set("y", str(w.y))

        return root

    def to_xml_string(self, include_declaration=True, include_doctype=True, pretty=True, encoding="utf-8"):
        root = self._to_element()
        if pretty:
            rough = tostring(root, encoding=encoding)
            reparsed = minidom.parseString(rough)
            body = reparsed.toprettyxml(indent="    ", encoding=encoding).decode(encoding)
            lines = body.splitlines()
            if lines and lines[0].startswith("<?xml"):
                body = "\n".join(lines[1:]).lstrip()
        else:
            body = tostring(root, encoding=encoding).decode(encoding)
        parts = []
        if include_declaration:
            parts.append("<?xml version=\"1.0\"?>")
        if include_doctype:
            parts.append("<!DOCTYPE empire>")
        parts.append(body)
        return "\n".join(parts)

    def write_xml(self, path, include_declaration=True, include_doctype=True, pretty=True, encoding="utf-8"):
        xml_text = self.to_xml_string(include_declaration, include_doctype, pretty, encoding)
        with open(path, "w", encoding=encoding) as f:
            f.write(xml_text)

    # ------------------------ XML reading (deserialization) ------------------------

    @classmethod
    def _parse_bool(cls, text):
        return str(text).lower() == "true"

    @classmethod
    def _child(cls, el, tag):
        return el.find(tag)
    
    @staticmethod
    def _get_attr_str(el, name, default=None):
        v = el.get(name) if el is not None else None
        return v if v is not None and v != "" else default
    
    @staticmethod
    def _get_attr_int(el, name, default=None):
        try:
            v = el.get(name) if el is not None else None
            if v is None or v == "":
                return default
            return int(v)
        except Exception:
            return default
    
    @staticmethod
    def _get_attr_bool(el, name, default=False):
        v = el.get(name) if el is not None else None
        if v is None:
            return default
        return str(v).strip().lower() == "true"
    
    
    @classmethod
    def from_xml_string(cls, xml_text):
        tree = ET.ElementTree(ET.fromstring(xml_text))
        root = tree.getroot()
        if root.tag != "empire":
            raise ValueError("Root tag must be <empire>")
    
        version = cls._get_attr_int(root, "version", 1)
    
        # ornaments
        ornaments = []
        for o_el in root.findall("ornament"):
            otype = cls._get_attr_str(o_el, "type")
            if otype:
                ornaments.append(Ornament(otype))
    
        # border
        border = None
        b_el = cls._child(root, "border")
        if b_el is not None:
            density = cls._get_attr_int(b_el, "density", None)
            edges = []
            for e_el in b_el.findall("edge"):
                x = cls._get_attr_int(e_el, "x", None)
                y = cls._get_attr_int(e_el, "y", None)
                if x is None or y is None:
                    # skip incomplete edge
                    continue
                hidden = cls._get_attr_bool(e_el, "hidden", False)
                edges.append(Edge(x, y, hidden))
            # only build Border if there is something meaningful
            if density is not None or edges:
                border = Border(density, edges)
    
        # cities
        cities = []
        cities_el = cls._child(root, "cities")
        if cities_el is not None:
            for c_el in cities_el.findall("city"):
                name = cls._get_attr_str(c_el, "name", None)
                x = cls._get_attr_int(c_el, "x", None)
                y = cls._get_attr_int(c_el, "y", None)
                ctype = cls._get_attr_str(c_el, "type", None) or CityType.TRADE
    
                # Trade route bits (all optional)
                tr_cost = cls._get_attr_int(c_el, "trade_route_cost", None)
                tr_type = cls._get_attr_str(c_el, "trade_route_type", None)
    
                # trade_points (optional)
                trade_points = []
                tp_el = cls._child(c_el, "trade_points")
                if tp_el is not None:
                    for pt in tp_el.findall("point"):
                        px = cls._get_attr_int(pt, "x", None)
                        py = cls._get_attr_int(pt, "y", None)
                        if px is None or py is None:
                            continue
                        trade_points.append(TradePoint(px, py))
    
                trade_route = None
                if tr_cost is not None or tr_type is not None or trade_points:
                    trade_route = TradeRoute(
                        cost=tr_cost,
                        type=tr_type,
                        trade_points=trade_points
                    )
    
                # buys / sells (optional)
                buys = []
                sells = []
    
                buys_el = cls._child(c_el, "buys")
                if buys_el is not None:
                    for r in buys_el.findall("resource"):
                        rtype = cls._get_attr_str(r, "type", None)
                        if not rtype:
                            continue
                        amount = cls._get_attr_int(r, "amount", None)
                        buys.append(Resource(rtype, amount))
    
                sells_el = cls._child(c_el, "sells")
                if sells_el is not None:
                    for r in sells_el.findall("resource"):
                        rtype = cls._get_attr_str(r, "type", None)
                        if not rtype:
                            continue
                        amount = cls._get_attr_int(r, "amount", None)
                        sells.append(Resource(rtype, amount))
    
                # Build city even if some attributes are missing
                # (name/x/y can be None if upstream data is partial)
                cities.append(City(name, x, y, ctype, buys, sells, trade_route))
    
        # invasion paths (optional)
        invasion_paths = []
        inv_el = cls._child(root, "invasion_paths")
        if inv_el is not None:
            for p_el in inv_el.findall("path"):
                battles = []
                for b in p_el.findall("battle"):
                    bx = cls._get_attr_int(b, "x", None)
                    by = cls._get_attr_int(b, "y", None)
                    if bx is None or by is None:
                        continue
                    battles.append(Battle(bx, by))
                if battles:
                    invasion_paths.append(InvasionPath(battles))
    
        # distant battle paths (optional)
        distant_battle_paths = []
        dist_el = cls._child(root, "distant_battle_paths")
        if dist_el is not None:
            for p_el in dist_el.findall("path"):
                ptype = cls._get_attr_str(p_el, "type", None)
                start_x = cls._get_attr_int(p_el, "start_x", None)
                start_y = cls._get_attr_int(p_el, "start_y", None)
    
                waypoints = []
                for w in p_el.findall("waypoint"):
                    months = cls._get_attr_int(w, "num_months", None)
                    wx = cls._get_attr_int(w, "x", None)
                    wy = cls._get_attr_int(w, "y", None)
                    if months is None or wx is None or wy is None:
                        continue
                    waypoints.append(Waypoint(months, wx, wy))
    
                # Create the path even if some attrs are missing; skip if nothing useful
                if ptype is not None or start_x is not None or start_y is not None or waypoints:
                    distant_battle_paths.append(DistantBattlePath(ptype, start_x, start_y, waypoints))
    
        return Empire(version, ornaments, border, cities, invasion_paths, distant_battle_paths)

    @classmethod
    def read_xml(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        return cls.from_xml_string(data)


__all__ = [
    "OrnamentType", "CityType", "ResourceType", "TradeRouteType", "DistantPathType",
    "Ornament", "Edge", "Border", "Resource", "TradePoint", "TradeRoute",
    "City", "Battle", "InvasionPath", "Waypoint", "DistantBattlePath",
    "Empire"]