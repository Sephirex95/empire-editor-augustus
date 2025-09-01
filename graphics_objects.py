# -*- coding: utf-8 -*-
"""
Graphics objects for Empire Editor.

This module provides graphical wrapper classes that handle UI operations,
keeping them separate from the data objects in empire_data.py.

@author: sephirex95
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, Any, Dict, List, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QMenu
from PySide6.QtGui import QPixmap, QCursor, QPen, QBrush

import empire_data as ed


class GraphicsObjectType(Enum):
    """Types of graphical objects in the empire editor."""
    CITY = auto()
    BORDER_EDGE = auto()
    TRADE_ROUTE = auto()
    TRADE_POINT = auto()  # Individual points in trade routes
    EMPIRE_EDGE = auto()  # Individual edge segments in empire border
    ORNAMENT = auto()
    INVASION_PATH = auto()
    DISTANT_BATTLE_PATH = auto()


class GraphicsObjectBase(ABC):
    """Base class for all graphical objects in the empire editor."""
    
    def __init__(self, data_object: Any, graphics_type: GraphicsObjectType):
        self.data_object = data_object  # Reference to the data object from empire_data
        self.graphics_type = graphics_type
        self.scene_items: List[QGraphicsItem] = []  # Graphics items in the scene
        self.is_selected = False
        self.is_visible = True
        
    @abstractmethod
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return list of (label, callback) tuples for context menu."""
        pass
    
    @abstractmethod
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return graphics items that can be clicked/selected."""
        pass
    
    @abstractmethod
    def update_visual_state(self):
        """Update visual appearance based on current state."""
        pass
    
    @abstractmethod
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for different operations (move, edit, etc.)."""
        pass
    
    def set_selected(self, selected: bool):
        """Set selection state and update visuals."""
        self.is_selected = selected
        self.update_visual_state()
        
    def set_visible(self, visible: bool):
        """Set visibility and update all scene items."""
        self.is_visible = visible
        for item in self.scene_items:
            item.setVisible(visible)
    
    def remove_from_scene(self):
        """Remove all graphics items from scene."""
        for item in self.scene_items:
            if item.scene():
                item.scene().removeItem(item)
        self.scene_items.clear()


class CityGraphicsObject(GraphicsObjectBase):
    """Graphical representation of a city with UI operations."""
    
    def __init__(self, city_data: ed.City, pixmap: QPixmap, main_window=None):
        super().__init__(city_data, GraphicsObjectType.CITY)
        self.pixmap = pixmap
        self.main_window = main_window
        self.city_item: Optional[QGraphicsPixmapItem] = None
        self.label_item: Optional[QGraphicsItem] = None
        
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return context menu actions for cities."""
        return [
            ("Move City", self._move_city),
            ("Delete City", self._delete_city),
            ("Properties", self._edit_properties),
        ]
    
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return items that can be clicked."""
        items = []
        if self.city_item:
            items.append(self.city_item)
        return items
    
    def update_visual_state(self):
        """Update city visual state based on selection."""
        if self.city_item:
            self.city_item.setSelected(self.is_selected)
            # Could add glow, outline, etc. here
    
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for city operations."""
        if operation == "move":
            return QCursor(self.pixmap)
        return QCursor(Qt.CursorShape.ArrowCursor)
    
    def _move_city(self):
        """Trigger move city operation."""
        if self.main_window:
            self.main_window.move_city(self.data_object)
    
    def _delete_city(self):
        """Trigger delete city operation."""
        if self.main_window:
            self.main_window.remove_city(self.data_object)
    
    def _edit_properties(self):
        """Trigger edit properties operation."""
        if self.main_window:
            self.main_window.edit_city(self.data_object)
    
    @property
    def city_type(self) -> ed.CityType:
        """Get city type from data object."""
        return self.data_object.city_type
    
    @property
    def position(self) -> Tuple[int, int]:
        """Get city position from data object."""
        return (self.data_object.x, self.data_object.y)
    
    def set_position(self, x: int, y: int):
        """Update both data and visual position."""
        self.data_object.x = x
        self.data_object.y = y
        if self.city_item:
            # Update scene position (convert from center coords to top-left)
            scene_x = x - self.pixmap.width() // 2
            scene_y = y - self.pixmap.height() // 2
            self.city_item.setPos(scene_x, scene_y)


class BorderGraphicsObject(GraphicsObjectBase):
    """Graphical representation of empire border with UI operations."""
    
    def __init__(self, border_data: ed.Border, main_window=None):
        super().__init__(border_data, GraphicsObjectType.BORDER_EDGE)
        self.main_window = main_window
        self.border_visual_group: Optional[QGraphicsItem] = None
        self.border_icon_items: List[QGraphicsItem] = []
        self.hit_items: List[QGraphicsItem] = []  # Invisible hit areas for segments
        self.selection_overlay_items: List[QGraphicsItem] = []
        self.edge_objects: List['EmpireEdgeGraphicsObject'] = []  # Individual edge objects
        
        # Create individual graphics objects for each edge
        for edge in border_data.edges:
            edge_obj = EmpireEdgeGraphicsObject(edge, main_window)
            self.edge_objects.append(edge_obj)
        
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return context menu actions for border."""
        return [
            ("Toggle Border Visibility", self._toggle_border_visibility),
            ("Delete Border", self._delete_border),
            ("Edit Border Properties", self._edit_border_properties),
        ]
    
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return hit test items for border segments."""
        return self.hit_items
    
    def update_visual_state(self):
        """Update border visual state."""
        # Update selection overlay visibility
        for item in self.selection_overlay_items:
            item.setVisible(self.is_selected)
            
        # Update individual edge states
        for edge_obj in self.edge_objects:
            edge_obj.update_visual_state()
    
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for border operations."""
        # Could return empire edge cursor for drawing
        return QCursor(Qt.CursorShape.ArrowCursor)
    
    def _toggle_border_visibility(self):
        """Toggle border visibility."""
        if self.main_window:
            # Toggle the view option
            action = self.main_window.ui.actionViewOption3
            action.setChecked(not action.isChecked())
            self.main_window.toggle_border_visibility()
    
    def _delete_border(self):
        """Trigger delete border operation."""
        if self.main_window:
            self.main_window.delete_empire_border()
    
    def _edit_border_properties(self):
        """Edit border properties like density."""
        if self.main_window:
            # Could open border properties dialog
            pass
    
    def add_edge_object(self, edge_data: ed.Edge) -> 'EmpireEdgeGraphicsObject':
        """Add an individual edge object to this border."""
        edge_obj = EmpireEdgeGraphicsObject(edge_data, self, self.main_window)
        self.edge_objects.append(edge_obj)
        return edge_obj
    
    def remove_edge_object(self, edge_data: ed.Edge):
        """Remove an edge object from this border."""
        self.edge_objects = [obj for obj in self.edge_objects if obj.data_object != edge_data]
    
    @property
    def edges(self) -> List[ed.Edge]:
        """Get border edges from data object."""
        return self.data_object.edges if self.data_object else []


class TradeRouteGraphicsObject(GraphicsObjectBase):
    """Graphical representation of trade route with UI operations."""
    
    def __init__(self, city_data: ed.City, main_window=None):
        super().__init__(city_data, GraphicsObjectType.TRADE_ROUTE)
        self.main_window = main_window
        self.route_visual_group: Optional[QGraphicsItem] = None
        self.route_hit_items: List[QGraphicsItem] = []
        self.selection_overlay_items: List[QGraphicsItem] = []
        self.trade_point_objects: List['TradePointGraphicsObject'] = []  # Individual point objects
        
        # Create individual graphics objects for each trade point if trade route exists
        if city_data.trade_route and city_data.trade_route.trade_points:
            for trade_point in city_data.trade_route.trade_points:
                point_obj = TradePointGraphicsObject(trade_point, main_window)
                self.trade_point_objects.append(point_obj)
        
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return context menu actions for trade route."""
        return [
            ("Delete Trade Route Path", self._delete_trade_route),
            ("Edit City", self._edit_city),
        ]
    
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return hit test items for trade route segments."""
        return self.route_hit_items
    
    def update_visual_state(self):
        """Update trade route visual state."""
        for item in self.selection_overlay_items:
            item.setVisible(self.is_selected)
    
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for trade route operations."""
        return QCursor(Qt.CursorShape.ArrowCursor)
    
    def _delete_trade_route(self):
        """Trigger delete trade route operation."""
        if self.main_window:
            self.main_window.delete_trade_route_from_item(None, self.data_object)
    
    def _edit_city(self):
        """Trigger edit city operation."""
        if self.main_window:
            self.main_window.edit_city(self.data_object)
    
    @property
    def trade_route(self) -> Optional[ed.TradeRoute]:
        """Get trade route from city data object."""
        return self.data_object.trade_route if self.data_object else None


class TradePointGraphicsObject(GraphicsObjectBase):
    """Graphical representation of individual trade route points."""
    
    def __init__(self, trade_point_data: ed.TradePoint, parent_route: TradeRouteGraphicsObject, main_window=None):
        super().__init__(trade_point_data, GraphicsObjectType.TRADE_POINT)
        self.main_window = main_window
        self.parent_route = parent_route
        self.point_item: Optional[QGraphicsItem] = None
        
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return context menu actions for trade point."""
        return [
            ("Delete Point", self._delete_point),
            ("Edit Route", self._edit_route),
        ]
    
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return hit test items for trade point."""
        return [self.point_item] if self.point_item else []
    
    def update_visual_state(self):
        """Update trade point visual state."""
        if self.point_item:
            # Could add highlighting here
            pass
    
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for trade point operations."""
        return QCursor(Qt.CursorShape.PointingHandCursor)
    
    def _delete_point(self):
        """Delete this trade point."""
        if self.main_window and self.parent_route:
            # Remove point from route data
            route = self.parent_route.trade_route
            if route and self.data_object in route.trade_points:
                route.trade_points.remove(self.data_object)
                self.main_window.render_trade_route(self.parent_route.data_object)
    
    def _edit_route(self):
        """Edit the parent route's city."""
        if self.parent_route:
            self.parent_route._edit_city()


class EmpireEdgeGraphicsObject(GraphicsObjectBase):
    """Graphical representation of individual empire border edge segments."""
    
    def __init__(self, edge_data: ed.Edge, parent_border: BorderGraphicsObject, main_window=None):
        super().__init__(edge_data, GraphicsObjectType.EMPIRE_EDGE)
        self.main_window = main_window
        self.parent_border = parent_border
        self.edge_item: Optional[QGraphicsItem] = None
        self.hit_item: Optional[QGraphicsItem] = None  # Invisible hit area
        
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Return context menu actions for empire edge."""
        return [
            ("Toggle Edge Hidden", self._toggle_edge_hidden),
            ("Delete Edge", self._delete_edge),
            ("Edit Border", self._edit_border),
        ]
    
    def get_hit_test_items(self) -> List[QGraphicsItem]:
        """Return hit test items for empire edge."""
        return [self.hit_item] if self.hit_item else []
    
    def update_visual_state(self):
        """Update empire edge visual state."""
        if self.edge_item:
            # Update visibility based on hidden state
            self.edge_item.setVisible(not self.data_object.hidden and self.is_visible)
    
    def get_cursor_for_operation(self, operation: str) -> QCursor:
        """Get cursor for empire edge operations."""
        return QCursor(Qt.CursorShape.PointingHandCursor)
    
    def _toggle_edge_hidden(self):
        """Toggle the hidden state of this edge."""
        self.data_object.hidden = not self.data_object.hidden
        self.update_visual_state()
        if self.main_window:
            self.main_window.mark_unsaved_changes()
    
    def _delete_edge(self):
        """Delete this edge from the border."""
        if self.main_window and self.parent_border:
            # Remove edge from border data
            border = self.parent_border.data_object
            if border and self.data_object in border.edges:
                border.edges.remove(self.data_object)
                self.main_window.render_empire_border()
    
    def _edit_border(self):
        """Edit the parent border."""
        if self.main_window:
            # Could open border properties dialog
            pass


class SelectableElement:
    """Represents an element that can be selected from the list widget."""
    
    def __init__(self, name: str, pixmap: QPixmap, data_type: Any, graphics_type: GraphicsObjectType, enabled: bool = True):
        self.name = name
        self.pixmap = pixmap
        self.data_type = data_type  # The data class type (ed.CityType, EmpObjTypes, etc.)
        self.graphics_type = graphics_type
        self.enabled = enabled
    
    def create_data_object(self, **kwargs) -> Any:
        """Create a new data object of this element's type."""
        if self.graphics_type == GraphicsObjectType.CITY:
            return ed.City(city_type=self.data_type, **kwargs)
        elif self.graphics_type == GraphicsObjectType.BORDER_EDGE:
            # For border edge, we don't create individual edges but signal border drawing
            # The empire edge drawing is handled specially by the main window
            return None
        elif self.graphics_type == GraphicsObjectType.EMPIRE_EDGE:
            # Individual edge creation
            return ed.Edge(**kwargs)
        elif self.graphics_type == GraphicsObjectType.TRADE_POINT:
            # Individual trade point creation
            return ed.TradePoint(**kwargs)
        # Add other types as needed
        return None
    
    def create_graphics_object(self, data_object: Any, main_window=None) -> GraphicsObjectBase:
        """Create a graphics object wrapper for the data object."""
        if self.graphics_type == GraphicsObjectType.CITY:
            return CityGraphicsObject(data_object, self.pixmap, main_window)
        elif self.graphics_type == GraphicsObjectType.BORDER_EDGE:
            return BorderGraphicsObject(data_object)
        elif self.graphics_type == GraphicsObjectType.TRADE_ROUTE:
            return TradeRouteGraphicsObject(data_object)
        # Add other types as needed
        raise ValueError(f"Unknown graphics type: {self.graphics_type}")


class GraphicsObjectManager:
    """Manages all graphics objects in the empire editor."""
    
    def __init__(self):
        self.city_objects: Dict[int, CityGraphicsObject] = {}  # Use id(city) as key
        self.border_object: Optional[BorderGraphicsObject] = None
        self.trade_route_objects: Dict[int, TradeRouteGraphicsObject] = {}  # Use id(city) as key
        self.selected_object: Optional[GraphicsObjectBase] = None
        
    def add_city(self, city_data: ed.City, pixmap: QPixmap, main_window=None) -> CityGraphicsObject:
        """Add a city graphics object."""
        graphics_obj = CityGraphicsObject(city_data, pixmap, main_window)
        self.city_objects[id(city_data)] = graphics_obj
        return graphics_obj
    
    def remove_city(self, city_data: ed.City):
        """Remove a city graphics object."""
        city_id = id(city_data)
        if city_id in self.city_objects:
            graphics_obj = self.city_objects[city_id]
            graphics_obj.remove_from_scene()
            del self.city_objects[city_id]
            
            # Also remove any trade route for this city
            if city_id in self.trade_route_objects:
                self.remove_trade_route(city_data)
    
    def add_border(self, border_data: ed.Border) -> BorderGraphicsObject:
        """Add border graphics object."""
        if self.border_object:
            self.border_object.remove_from_scene()
        self.border_object = BorderGraphicsObject(border_data)
        return self.border_object
    
    def remove_border(self):
        """Remove border graphics object."""
        if self.border_object:
            self.border_object.remove_from_scene()
            self.border_object = None
    
    def add_trade_route(self, city_data: ed.City) -> TradeRouteGraphicsObject:
        """Add trade route graphics object."""
        graphics_obj = TradeRouteGraphicsObject(city_data)
        self.trade_route_objects[id(city_data)] = graphics_obj
        return graphics_obj
    
    def remove_trade_route(self, city_data: ed.City):
        """Remove trade route graphics object."""
        city_id = id(city_data)
        if city_id in self.trade_route_objects:
            graphics_obj = self.trade_route_objects[city_id]
            graphics_obj.remove_from_scene()
            del self.trade_route_objects[city_id]
    
    def clear_all(self):
        """Clear all graphics objects."""
        for graphics_obj in list(self.city_objects.values()):
            graphics_obj.remove_from_scene()
        self.city_objects.clear()
        
        if self.border_object:
            self.border_object.remove_from_scene()
            self.border_object = None
            
        for graphics_obj in list(self.trade_route_objects.values()):
            graphics_obj.remove_from_scene()
        self.trade_route_objects.clear()
        
        self.selected_object = None
    
    def select_object(self, graphics_obj: Optional[GraphicsObjectBase]):
        """Select a graphics object, deselecting others."""
        # Deselect current selection
        if self.selected_object:
            self.selected_object.set_selected(False)
        
        # Select new object
        self.selected_object = graphics_obj
        if graphics_obj:
            graphics_obj.set_selected(True)
    
    def deselect_all(self):
        """Deselect all objects."""
        self.select_object(None)
    
    def get_graphics_object_for_scene_item(self, scene_item: QGraphicsItem) -> Optional[GraphicsObjectBase]:
        """Find graphics object that owns a scene item."""
        # Check cities
        for graphics_obj in self.city_objects.values():
            if scene_item in graphics_obj.get_hit_test_items():
                return graphics_obj
        
        # Check border
        if self.border_object and scene_item in self.border_object.get_hit_test_items():
            return self.border_object
        
        # Check trade routes
        for graphics_obj in self.trade_route_objects.values():
            if scene_item in graphics_obj.get_hit_test_items():
                return graphics_obj
        
        return None
    
    def set_cities_visibility(self, visible: bool):
        """Set visibility for all cities."""
        for graphics_obj in self.city_objects.values():
            graphics_obj.set_visible(visible)
    
    def set_border_visibility(self, visible: bool):
        """Set visibility for border."""
        if self.border_object:
            self.border_object.set_visible(visible)
    
    def set_trade_routes_visibility(self, visible: bool):
        """Set visibility for all trade routes."""
        for graphics_obj in self.trade_route_objects.values():
            graphics_obj.set_visible(visible)

    def get_empire_edge_objects(self) -> List["EmpireEdgeGraphicsObject"]:
        """Get all empire edge graphics objects from border."""
        if self.border_object:
            return self.border_object.edge_objects
        return []

    def get_trade_point_objects(self) -> List["TradePointGraphicsObject"]:
        """Get all trade point graphics objects from all trade routes."""
        points = []
        for graphics_obj in self.trade_route_objects.values():
            points.extend(graphics_obj.trade_point_objects)
        return points

    def get_graphics_object_for_scene_item_including_nested(self, scene_item: QGraphicsItem) -> Optional[GraphicsObjectBase]:
        """Find graphics object that owns a scene item, including nested objects."""
        # First try the standard search
        graphics_obj = self.get_graphics_object_for_scene_item(scene_item)
        if graphics_obj:
            return graphics_obj
        
        # Check empire edges within border
        for edge_obj in self.get_empire_edge_objects():
            if scene_item in edge_obj.get_hit_test_items():
                return edge_obj
        
        # Check trade points within trade routes
        for point_obj in self.get_trade_point_objects():
            if scene_item in point_obj.get_hit_test_items():
                return point_obj
        
        return None
