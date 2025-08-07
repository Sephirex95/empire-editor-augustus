from dataclasses import dataclass, field
from typing import List

# Empire class holds the overall empire data
@dataclass
class Empire:
    version: str = "1"  # Version of the empire
    show_ireland: str = "true"  # Whether to show Ireland
    ornament: 'Ornament' = field(default_factory=lambda: Ornament())  # Ornament data (type)
    border: 'Border' = field(default_factory=lambda: Border())  # Border data (density and edges)
    cities: List['City'] = field(default_factory=list)  # List of cities in the empire
    invasion_paths: List['InvasionPath'] = field(default_factory=list)  # Paths for invasion
    distant_battle_paths: List['DistantBattlePath'] = field(default_factory=list)  # Distant battle paths


# Ornament data (just the type for now)
@dataclass
class Ornament:
    type: str = "all"  # Type of ornament (e.g., "all", "none")


# Border data (holds density and edges)
@dataclass
class Border:
    density: str = "28"  # Border density (strength or thickness)
    edges: List['Edge'] = field(default_factory=list)  # List of edge points on the border


# Edge data (represents a point on the border with x, y coordinates)
@dataclass
class Edge:
    x: int  # x-coordinate of the edge
    y: int  # y-coordinate of the edge
    hidden: bool = False  # Whether the edge is hidden


# City data (represents a city with name, coordinates, and resources)
@dataclass
class City:
    name: str  # Name of the city (e.g., "Lugdunum")
    x: int  # x-coordinate of the city
    y: int  # y-coordinate of the city
    city_type: str = ""  # Type of city (e.g., "ours", "roman")
    sells: List['Resource'] = field(default_factory=list)  # Resources the city sells
    buys: List['Resource'] = field(default_factory=list)  # Resources the city buys
    trade_points: List['TradePoint'] = field(default_factory=list)  # List of trade points for the city


# Resource data (represents a resource with a type and amount)
@dataclass
class Resource:
    type: str  # Type of resource (e.g., "wheat", "iron")
    amount: int = 0  # Amount of the resource


# TradePoint data (represents a trade route point with coordinates)
@dataclass
class TradePoint:
    x: int  # x-coordinate of the trade point
    y: int  # y-coordinate of the trade point


# InvasionPath data (represents a series of battles for an invasion)
@dataclass
class InvasionPath:
    battles: List['Battle'] = field(default_factory=list)  # List of battles in the path


# Battle data (represents a battle with x, y coordinates)
@dataclass
class Battle:
    x: int  # x-coordinate of the battle
    y: int  # y-coordinate of the battle


# DistantBattlePath data (represents a distant battle with waypoints)
@dataclass
class DistantBattlePath:
    path_type: str  # Type of the path (e.g., "roman", "enemy")
    start_x: int  # Starting x-coordinate
    start_y: int  # Starting y-coordinate
    waypoints: List['Waypoint'] = field(default_factory=list)  # List of waypoints along the path


# Waypoint data (represents a waypoint in a distant battle path)
@dataclass
class Waypoint:
    num_months: int  # Number of months to reach the waypoint
    x: int  # x-coordinate of the waypoint
    y: int  # y-coordinate of the waypoint
