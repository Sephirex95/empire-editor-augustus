# -*- coding: utf-8 -*-
"""
Graphics objects for Empire Editor — slimmed & DRY.
Keeps UI logic separate from data objects in empire_data.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any, Dict, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QCursor, QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
)

import empire_data as ed

# --------------------------- Types ---------------------------


class GraphicsObjectType(Enum):
    CITY = auto()
    POLYCHAIN = auto()  # Base for border and trade route
    BORDER = auto()
    BORDER_EDGE = auto()
    TRADE_ROUTE = auto()
    TRADE_POINT = auto()
    EMPIRE_EDGE = auto()
    ORNAMENT = auto()
    INVASION_PATH = auto()
    DISTANT_BATTLE_PATH = auto()


# --------------------------- Z-Values constants --------------
# Lowest layer - backgrounds
z_background = -1000

# Trade route elements
z_trade_point_hit = 7

# Dotted lines and basic elements
z_dotted_lines = 12

# Polychain visual elements
z_polychain_visual = 75
z_polychain_hit = 76
z_polychain_hidden_edges = 77
z_polychain_hidden_vertices = 78

# Drawing operations and temporary lines
z_drawing_lines = 80
z_drawing_points = 90
z_temp_lines = 100

# Selection overlays
z_selection_overlay_base = 120
z_selection_overlay_edge = 121
z_selection_handles = 130

# Editing handles
z_editable_handles = 140

# Cities (highest priority)
z_city_icon = 250
# Labels and UI overlays
z_label_0 = 260
z_label_1 = 261

# --------------------------- Base ----------------------------


class GraphicsObjectBase(ABC):
    """Base for all graphical wrappers."""

    def __init__(self, data_object: Any, graphics_type: GraphicsObjectType):
        self.data_object = data_object
        self.graphics_type = graphics_type
        self.scene_items: List[QGraphicsItem] = []
        self.is_selected = False
        self.is_visible = True
        self.main_window = None  # set by subclasses as needed

    # ----- abstract API -----
    @abstractmethod
    def get_hit_test_items(self) -> List[QGraphicsItem]: ...
    @abstractmethod
    def update_visual_state(self): ...
    @abstractmethod
    def get_cursor_for_operation(self, operation: str) -> QCursor: ...

    # ----- context menu (non-abstract with default implementation) -----
    def get_context_menu_actions(self) -> List[Tuple[str, callable]]:
        """Get context menu actions. Override in subclasses. Default returns empty list."""
        return []

    def combine_context_menus(
        self,
        child_actions: List[Tuple[str, callable]],
        parent_actions: List[Tuple[str, callable]] = None,
        add_separator: bool = True,
    ) -> List[Tuple[str, callable]]:
        """Helper to combine child and parent context menu actions."""
        if parent_actions is None:
            parent_actions = []

        if not child_actions:
            return parent_actions
        if not parent_actions:
            return child_actions

        # Combine with separator
        combined = list(child_actions)
        if add_separator and child_actions and parent_actions:
            combined.append(("---", None))  # Separator
        combined.extend(parent_actions)
        return combined

    # ----- selection / visibility -----
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_visual_state()

    def set_visible(self, visible: bool):
        self.is_visible = visible
        for it in self.scene_items:
            it.setVisible(visible)

    def remove_from_scene(self):
        for it in list(self.scene_items):
            if it and it.scene():
                it.scene().removeItem(it)
        self.scene_items.clear()

    def create_editable_handles(self, pts: List[Tuple[float, float]], z=z_editable_handles, size=8.0):
        """Create editable vertex handles."""

        def style(i):
            return (QPen(Qt.blue, 1), QBrush(Qt.blue))

        return self.handles(pts, z, size, style, editable=True)

    # ============ Small helpers (DRY) ============

    # groups / items
    def g(self, z: float) -> Optional[QGraphicsItemGroup]:
        if not self.main_window:
            return None
        grp = QGraphicsItemGroup()
        grp.setZValue(z)
        self.main_window.scene.addItem(grp)
        self.scene_items.append(grp)
        return grp

    def line(self, x0, y0, x1, y1, pen: QPen, z: float, group: QGraphicsItemGroup = None, sel=False):
        p0 = self.main_window._img_to_scene(x0, y0)
        p1 = self.main_window._img_to_scene(x1, y1)
        it = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
        it.setPen(pen)
        it.setZValue(z)
        it.setFlag(QGraphicsItem.ItemIsSelectable, sel)
        (group.addToGroup(it) if group else self.main_window.scene.addItem(it))
        self.scene_items.append(it)
        return it

    def hits(
        self, pts: List[Tuple[float, float]], group, z: float, w=12.0, sel=True, meta=None
    ) -> List[QGraphicsLineItem]:
        if len(pts) < 2:
            return []
        pen = QPen(Qt.transparent, w)
        out = []
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            it = self.line(x0, y0, x1, y1, pen, z, group, sel)
            if meta:
                meta(i, it)  # metadata of each line already has an index
            out.append(it)
        return out

    def dotted(
        self, pts: List[Tuple[float, float]], pen: QPen = None, z=z_dotted_lines, group=None
    ) -> List[QGraphicsLineItem]:
        if len(pts) < 2:
            return []
        pen = pen or QPen(Qt.black, 1)
        pen.setStyle(Qt.DotLine)
        return [
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], pen, z, group, False)
            for i in range(len(pts) - 1)
        ]

    def handles(
        self, pts: List[Tuple[float, float]], z=z_selection_handles, size=6.0, style=None, tag=None, editable=False
    ) -> List[QGraphicsItem]:
        if not pts:
            return []
        half = size / 2.0
        items = []
        for i, (x, y) in enumerate(pts):
            p = self.main_window._img_to_scene(x, y)
            pen, brush = style(i) if style else (QPen(Qt.black, 1), QBrush(Qt.white))
            rect = self.main_window.scene.addRect(p.x() - half, p.y() - half, size, size, pen, brush)
            rect.setZValue(z)

            if editable:
                rect.setFlag(QGraphicsItem.ItemIsSelectable, True)
                rect.setCursor(Qt.CursorShape.PointingHandCursor)
                # Store vertex editing data
                rect.setData(Qt.ItemDataRole.UserRole, "VERTEX_HANDLE")
                rect.setData(Qt.ItemDataRole.UserRole + 1, self.graphics_type.name)  # Object type
                rect.setData(Qt.ItemDataRole.UserRole + 2, i)  # Vertex index
                rect.setData(Qt.ItemDataRole.UserRole + 3, self)  # Reference to graphics object

            items.append(rect)
            self.scene_items.append(rect)
            if tag:
                tag(i, rect)
        return items

    def rm(self, items: List[QGraphicsItem]):  # remove & clear
        for it in list(items):
            if it and it.scene():
                it.scene().removeItem(it)
        items.clear()

    # pixmaps / stamps / dots
    def place_pixmap(
        self,
        x,
        y,
        pm: QPixmap,
        z: float,
        group: QGraphicsItemGroup = None,
        center=True,
        data: Dict = None,
        cursor=Qt.CursorShape.ArrowCursor,
    ) -> Optional[QGraphicsPixmapItem]:
        if not self.main_window or not self.main_window.bg_item or pm.isNull():
            return None
        p = self.main_window._img_to_scene(x, y)
        it = QGraphicsPixmapItem(pm)
        if center:
            it.setOffset(-pm.width() / 2.0, -pm.height() / 2.0)
        it.setPos(p)
        it.setZValue(z)
        it.setCursor(cursor)
        if data:
            for role, val in data.items():
                it.setData(role, val)
        (group.addToGroup(it) if group else self.main_window.scene.addItem(it))
        return it

    def stamp_polyline_uniform(self, pts, spacing, place, ends=True):
        if not pts:
            return
        if len(pts) == 1:
            if ends:
                place(int(pts[0][0]), int(pts[0][1]))
            return

        interval = max(1, int(spacing))  # engine uses integer interval
        remaining = interval if ends else 0  # ends=True -> stamp at very start

        def seg(ax, ay, bx, by, rem):
            dx, dy = bx - ax, by - ay
            dist0 = int((dx * dx + dy * dy) ** 0.5)  # (int)sqrt(...)
            if dist0 <= 0:
                return interval - rem  # match C: return offset
            off = interval - rem
            if off > dist0:
                return off
            d = dist0 - off
            n = d // interval
            new_rem = d % interval
            for j in range(n + 1):  # j=0..n inclusive
                s = j * interval + off
                # C truncation toward 0: int((s*dx)/dist0) etc.
                x = ax + int((s * dx) / dist0)
                y = ay + int((s * dy) / dist0)
                place(x, y)
            return new_rem

        ax, ay = int(pts[0][0]), int(pts[0][1])
        for i in range(1, len(pts)):
            bx, by = int(pts[i][0]), int(pts[i][1])
            remaining = seg(ax, ay, bx, by, remaining)
            ax, ay = bx, by

    # --- pixmap wrapper, unchanged API, compact
    def stamp_pixmaps_polyline(self, pts, pix, spacing, z=z_polychain_visual, group=None, dedup=None, merge=None):
        if not pts or pix.isNull():
            return []
        items, seen = [], (dedup if dedup is not None else [])
        if merge is None:
            merge = max(pix.width(), pix.height()) / 2 + 1
        r2 = merge * merge

        def place(x, y):
            ix, iy = int(x), int(y)
            for rx, ry in seen:
                dx, dy = ix - rx, iy - ry
                if dx * dx + dy * dy <= r2:
                    return
            seen.append((ix, iy))
            it = self.place_pixmap(ix, iy, pix, z, group, True)
            if it:
                it.setFlag(QGraphicsPixmapItem.ItemIsSelectable, False)
                items.append(it)

        self.stamp_polyline_uniform(pts, spacing, place, True)
        return items

    def place_dot(self, x, y, r, brush: QBrush, z: float, group=None) -> Optional[QGraphicsEllipseItem]:
        if not self.main_window or not self.main_window.bg_item:
            return None
        p = self.main_window._img_to_scene(x, y)
        it = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        it.setBrush(brush)
        it.setPen(QPen(Qt.NoPen))
        it.setPos(p)
        it.setZValue(z)
        (group.addToGroup(it) if group else self.main_window.scene.addItem(it))
        return it


# --------------------------- Base Polychain -------------------------


@dataclass
class PolychainConfig:
    """Configuration for polychain rendering and behavior."""

    pixmap_key: str  # Key for stamping pixmap
    density: int = 28  # Stamping density
    is_closed: bool = False  # Whether chain connects back to start
    edge_selection_color: QColor = field(default_factory=lambda: Qt.red)
    edge_selection_width: int = 0
    object_selection_color: QColor = field(default_factory=lambda: Qt.black)
    object_selection_width: int = 1
    vertex_handle_color: QColor = field(default_factory=lambda: Qt.blue)
    hidden_edge_color: QColor = field(default_factory=lambda: Qt.black)
    hidden_vertex_color: QColor = field(default_factory=lambda: Qt.darkBlue)


class PolychainGraphicsObject(GraphicsObjectBase):
    """Base class for polychain objects (borders, trade routes)."""

    def __init__(self, data_object: Any, graphics_type: GraphicsObjectType, config: PolychainConfig, main_window=None):
        super().__init__(data_object, graphics_type)
        self.main_window = main_window
        self.config = config

        # Visual groups and items
        self.visual_group: Optional[QGraphicsItemGroup] = None
        self.stamped_items: List[QGraphicsItem] = []
        self.hit_items: List[QGraphicsItem] = []
        self.selection_overlay_items: List[QGraphicsItem] = []

        # Selection state
        self.selected_edge_index: Optional[int] = None

        if main_window:
            self.render()

    # Abstract methods for subclasses to implement
    @abstractmethod
    def get_points(self) -> List[Tuple[int, int]]:
        """Get the list of points for this polychain."""
        pass

    @abstractmethod
    def get_hidden_states(self) -> List[bool]:
        """Get list of hidden states for each edge."""
        pass

    @abstractmethod
    def update_point(self, index: int, x: int, y: int):
        """Update a point in the underlying data."""
        pass

    # Rendering
    def render(self):
        """Render the complete polychain."""
        if not self.main_window:
            return

        self.remove_from_scene()
        pts = self.get_points()
        if len(pts) < 2:
            return

        hidden = self.get_hidden_states()
        pixmap = self._get_stamping_pixmap()
        if pixmap.isNull():
            return

        self.visual_group = self.g(75)

        # Create hit areas for edge selection
        self._create_hit_areas(pts, hidden)

        # Stamp pixmaps along visible edges
        self._stamp_visible_edges(pts, hidden, pixmap)

        # Draw hidden edges as dotted lines
        self._draw_hidden_edges(pts, hidden)

        # Mark hidden vertices
        self._mark_hidden_vertices(pts, hidden)

    def _get_stamping_pixmap(self) -> QPixmap:
        """Get the pixmap for stamping along edges."""
        if not self.main_window or not hasattr(self.main_window, "state"):
            return QPixmap()
        pil = self.main_window.state.images.get(self.config.pixmap_key)
        if pil:
            return self.main_window.pil_to_qpixmap(pil)
        return QPixmap()

    def _create_hit_areas(self, pts: List[Tuple[int, int]], hidden: List[bool]):
        """Create clickable hit areas for each edge."""
        edges = self._get_edge_list(pts)

        def _meta(i, it):
            from program_state import EmpObjTypes

            it.setData(Qt.ItemDataRole.UserRole, EmpObjTypes.EMPIRE_EDGE)
            it.setData(Qt.ItemDataRole.UserRole + 1, i)  # Edge index
            it.setData(Qt.ItemDataRole.UserRole + 2, self)  # Reference to this object

        self.hit_items = self.hits(edges, self.visual_group, z=z_polychain_hit, w=12, sel=True, meta=_meta)

    def _get_edge_list(self, pts: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Get list of points for edge hit areas."""
        if self.config.is_closed:
            return pts + [pts[0]]  # Close the loop
        return pts

    def _stamp_visible_edges(self, pts: List[Tuple[int, int]], hidden: List[bool], pixmap: QPixmap):
        """Stamp pixmaps along visible edges with deduplication."""
        # Global deduplication list for this polychain
        dedup_list = []
        merge_distance = 6.0  # Minimum distance between pixmaps

        # Collect all edges to stamp
        edges_to_stamp = []

        for i in range(len(pts) - 1):
            if i < len(hidden) and hidden[i]:
                continue  # Skip hidden edges
            edges_to_stamp.append((pts[i], pts[i + 1]))

        # Handle closing edge for closed polychains
        if self.config.is_closed and len(pts) >= 3:
            last_idx = len(pts) - 1
            if last_idx < len(hidden) and not hidden[last_idx]:
                edges_to_stamp.append((pts[-1], pts[0]))

        # Stamp all edges with shared deduplication
        for (x0, y0), (x1, y1) in edges_to_stamp:
            stamped = self.stamp_pixmaps_polyline(
                [(x0, y0), (x1, y1)],
                pixmap,
                self.config.density,
                z=z_polychain_visual,
                group=self.visual_group,
                dedup=dedup_list,
                merge=merge_distance,
            )
            self.stamped_items.extend(stamped)

    def _draw_hidden_edges(self, pts: List[Tuple[int, int]], hidden: List[bool]):
        """Draw dotted lines for hidden edges."""
        pen = QPen(self.config.hidden_edge_color, 1)
        pen.setStyle(Qt.DotLine)

        for i in range(len(pts) - 1):
            if i < len(hidden) and hidden[i]:
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                line = self.line(x0, y0, x1, y1, pen, z=z_polychain_hidden_edges, group=self.visual_group)
                self.stamped_items.append(line)

        # Handle closing edge for closed polychains
        if self.config.is_closed and len(pts) >= 3:
            last_idx = len(pts) - 1
            if last_idx < len(hidden) and hidden[last_idx]:
                x0, y0 = pts[-1]
                x1, y1 = pts[0]
                line = self.line(x0, y0, x1, y1, pen, z=z_polychain_hidden_edges, group=self.visual_group)
                self.stamped_items.append(line)

    def _mark_hidden_vertices(self, pts: List[Tuple[int, int]], hidden: List[bool]):
        """Mark vertices of hidden edges with colored dots."""
        for i, (x, y) in enumerate(pts):
            # Check if this vertex is part of any hidden edge
            is_hidden_vertex = False
            if i < len(hidden) and hidden[i]:  # Edge starting from this vertex
                is_hidden_vertex = True
            if i > 0 and (i - 1) < len(hidden) and hidden[i - 1]:  # Edge ending at this vertex
                is_hidden_vertex = True
            # For closed chains, check the closing edge
            if self.config.is_closed and i == 0:
                last_idx = len(pts) - 1
                if last_idx < len(hidden) and hidden[last_idx]:
                    is_hidden_vertex = True

            if is_hidden_vertex:
                dot = self.place_dot(
                    x,
                    y,
                    r=3,
                    brush=QBrush(self.config.hidden_vertex_color),
                    z=z_polychain_hidden_vertices,
                    group=self.visual_group,
                )
                if dot:
                    self.stamped_items.append(dot)

    # Selection overlay management
    def _create_selection_overlay(self):
        """Create selection overlay with two levels: edge and object."""
        if not self.main_window:
            return
        self._clear_selection_overlay()

        pts = self.get_points()
        if len(pts) < 2:
            return

        # Object-level selection (thin dotted line around entire polychain)
        edges = self._get_edge_list(pts)
        pen = QPen(self.config.object_selection_color, self.config.object_selection_width)
        pen.setStyle(Qt.DotLine)
        self.selection_overlay_items += self.dotted(edges, pen, z=z_selection_overlay_base)

        # Edge-level selection (much thicker and more prominent line for selected edge)
        if self.selected_edge_index is not None and self.selected_edge_index < len(pts) - 1:
            i = self.selected_edge_index
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]

            # Create a very prominent highlight - thick solid line in bright color
            edge_pen = QPen(self.config.edge_selection_color, self.config.edge_selection_width)  # Much thicker
            edge_pen.setStyle(Qt.SolidLine)  # Solid line for maximum visibility
            edge_line = self.line(x0, y0, x1, y1, edge_pen, z=z_selection_overlay_edge)
            self.selection_overlay_items.append(edge_line)

            # # Add a second outline for even more visibility
            # outline_color = Qt.white if self.config.edge_selection_color == Qt.black else Qt.black
            # outline_pen = QPen(outline_color, self.config.edge_selection_width + 7)
            # outline_pen.setStyle(Qt.SolidLine)
            # outline_line = self.line(x0, y0, x1, y1, outline_pen, z=z_selection_overlay_base)  # Behind the main line
            # self.selection_overlay_items.append(outline_line)

        # Vertex handles (editable when object is selected)
        hidden = self.get_hidden_states()

        def style(i):
            is_hidden = i < len(hidden) and hidden[i]
            return (QPen(Qt.red, 1), QBrush(Qt.yellow)) if is_hidden else (QPen(Qt.blue, 1), QBrush(Qt.blue))

        self.selection_overlay_items += self.handles(pts, z=z_selection_handles, size=8, style=style, editable=True)

    def _clear_selection_overlay(self):
        """Clear selection overlay."""
        self.rm(self.selection_overlay_items)

    def update_visual_state(self):
        """Update visual state based on selection."""
        if self.is_selected:
            self._create_selection_overlay()
        else:
            self._clear_selection_overlay()

    # Edge selection
    def select_edge(self, edge_index: int):
        """Select a specific edge."""
        self.selected_edge_index = edge_index
        if self.is_selected:
            self._create_selection_overlay()

    def deselect_edge(self):
        """Deselect current edge."""
        self.selected_edge_index = None
        if self.is_selected:
            self._create_selection_overlay()

    # Vertex editing implementation
    def start_vertex_editing(self, vertex_index: int, handle_item):
        """Start editing a vertex."""
        if vertex_index >= len(self.get_points()):
            return
        handle_item.setBrush(QBrush(Qt.yellow))

    def update_vertex_position(self, vertex_index: int, scene_pos):
        """Update vertex position during editing."""
        pass  # Visual update handled by main window

    def finish_vertex_editing(self, vertex_index: int, scene_pos):
        """Finish editing a vertex and update data."""
        if not self.main_window or vertex_index >= len(self.get_points()):
            return False

        xy = self.main_window._scene_to_image_xy(scene_pos)
        if xy is None:
            return False

        x, y = xy
        self.update_point(vertex_index, int(x), int(y))

        self.main_window.mark_unsaved_changes()
        self.render()

        if self.is_selected:
            self._create_selection_overlay()

        return True

    def cancel_vertex_editing(self, vertex_index: int):
        """Cancel vertex editing."""
        pass  # Main window handles handle color restoration

    # Standard interface
    def get_hit_test_items(self):
        return self.hit_items

    def get_context_menu_actions(self):
        """Base context menu for polychains. Override in subclasses for specific actions."""
        actions = []
        if self.selected_edge_index is not None:
            actions.append(("Add Vertex", self._add_vertex_generic))
        return actions

    def _add_vertex_generic(self):
        """Generic vertex addition - override in subclasses for specific implementation."""
        pass

    def get_cursor_for_operation(self, op: str):
        return QCursor(Qt.CursorShape.ArrowCursor)

    def remove_from_scene(self):
        self._clear_selection_overlay()
        super().remove_from_scene()


# --------------------------- City ----------------------------


class CityGraphicsObject(GraphicsObjectBase):
    def __init__(self, city: ed.City, pixmap: QPixmap, main_window=None):
        super().__init__(city, GraphicsObjectType.CITY)
        self.pixmap = pixmap
        self.main_window = main_window
        self.city_item: Optional[QGraphicsPixmapItem] = None
        self.label_item: Optional[QGraphicsItem] = None

        # Create and place the city item immediately
        if main_window and main_window.bg_item and not pixmap.isNull():
            self.create_city_item()

    def create_city_item(self):
        """Create the QGraphicsPixmapItem for this city."""
        if not self.main_window or not self.main_window.bg_item or self.pixmap.isNull():
            return

        # Calculate scene position (city data stores center coordinates)
        x, y = self.data_object.x, self.data_object.y
        offset_x = x - self.pixmap.width() // 2
        offset_y = y - self.pixmap.height() // 2
        scene_pt = self.main_window.bg_item.mapToScene(offset_x, offset_y)

        # Create the pixmap item
        self.city_item = QGraphicsPixmapItem(self.pixmap)
        self.city_item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        self.pixmap.setDevicePixelRatio(1.0)

        self.city_item.setZValue(z_city_icon)
        self.city_item.setOffset(0, 0)
        self.city_item.setPos(scene_pt)
        self.city_item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.city_item.setFlag(QGraphicsPixmapItem.ItemIsMovable, False)

        # Set data on the item for lookups
        city_key = id(self.data_object)
        self.city_item.setData(0, city_key)
        self.city_item.setData(1, self.data_object)
        if self.data_object.city_type is not None:
            self.city_item.setData(Qt.ItemDataRole.UserRole, self.data_object.city_type)

        # Add to scene and track
        self.main_window.scene.addItem(self.city_item)
        self.scene_items = [self.city_item]

        # Store in main window's tracking dict (for compatibility)
        if hasattr(self.main_window, "city_items"):
            self.main_window.city_items[city_key] = self.city_item

        # Apply interactivity
        self.city_item.setAcceptHoverEvents(not self.main_window.is_dragging)
        cursor = Qt.CursorShape.PointingHandCursor if not self.main_window.is_dragging else Qt.CursorShape.ArrowCursor
        self.city_item.setCursor(cursor)

        # Apply visibility from view options
        if hasattr(self.main_window.ui, "actionViewOption1"):
            self.city_item.setVisible(self.main_window.ui.actionViewOption1.isChecked())

    def update_interactivity(self, enable: bool):
        """Update the interactivity state of this city item."""
        if self.city_item:
            self.city_item.setAcceptHoverEvents(enable)
            cursor = Qt.CursorShape.PointingHandCursor if enable else Qt.CursorShape.ArrowCursor
            self.city_item.setCursor(cursor)

    def get_context_menu_actions(self):
        actions = []

        # Only show "Plot Trade Route" for trade cities
        if self.data_object.city_type in (ed.CityType.TRADE, ed.CityType.FUTURE_TRADE):
            actions.append(("Plot Trade Route", self._plot_trade_route))

        # Always show these options
        actions.extend(
            [
                ("Move City", self._move_city),
                ("Delete City", self._delete_city),
                ("Properties", self._edit),
            ]
        )

        return actions

    def get_hit_test_items(self):
        return [self.city_item] if self.city_item else []

    def update_visual_state(self):
        if self.city_item:
            self.city_item.setSelected(self.is_selected)

    def get_cursor_for_operation(self, op: str):
        return QCursor(self.pixmap) if op == "move" else QCursor(Qt.CursorShape.ArrowCursor)

    def _move_city(self):
        if self.main_window:
            self.main_window.move_city(self.data_object)

    def _delete_city(self):
        if self.main_window:
            self.main_window.remove_city(self.data_object)

    def _plot_trade_route(self):
        if self.main_window:
            self.main_window._draw_trade_route_from_context(self.data_object)

    def _edit(self):
        if self.main_window:
            self.main_window.edit_city(self.data_object)

    @property
    def city_type(self) -> ed.CityType:
        return self.data_object.city_type

    @property
    def position(self) -> Tuple[int, int]:
        return (self.data_object.x, self.data_object.y)

    def set_position(self, x: int, y: int):
        """Update city position in both data and visual representation."""
        self.data_object.x, self.data_object.y = x, y
        if self.city_item and self.main_window and self.main_window.bg_item:
            offset_x = x - self.pixmap.width() // 2
            offset_y = y - self.pixmap.height() // 2
            scene_pt = self.main_window.bg_item.mapToScene(offset_x, offset_y)
            self.city_item.setPos(scene_pt)

    def remove_from_scene(self):
        """Remove city item from scene and clean up tracking."""
        if self.city_item and self.main_window:
            # Remove from main window tracking
            city_key = id(self.data_object)
            if hasattr(self.main_window, "city_items") and city_key in self.main_window.city_items:
                del self.main_window.city_items[city_key]
        super().remove_from_scene()


# --------------------------- Border --------------------------


class BorderGraphicsObject(PolychainGraphicsObject):
    def __init__(self, border: ed.Border, main_window=None):
        config = PolychainConfig(
            pixmap_key="empire_edge",
            density=border.density or 28,
            is_closed=True,
            edge_selection_color=QColor(255, 50, 50),  # Bright red-orange
            edge_selection_width=3,  # Very thick for maximum visibility
            object_selection_color=Qt.black,
            object_selection_width=1,
            vertex_handle_color=Qt.blue,
            hidden_edge_color=Qt.black,
            hidden_vertex_color=Qt.darkBlue,
        )
        super().__init__(border, GraphicsObjectType.BORDER, config, main_window)

    # Polychain interface implementation
    def get_points(self) -> List[Tuple[int, int]]:
        return [(e.x, e.y) for e in self.data_object.edges]

    def get_hidden_states(self) -> List[bool]:
        return [bool(e.hidden) for e in self.data_object.edges]

    def update_point(self, index: int, x: int, y: int):
        if 0 <= index < len(self.data_object.edges):
            self.data_object.edges[index].x = x
            self.data_object.edges[index].y = y

    def _get_stamping_pixmap(self) -> QPixmap:
        return self.main_window._get_empire_edge_pixmap() if self.main_window else QPixmap()

    # Context menu
    def get_context_menu_actions(self):
        actions = [("Delete Border", lambda: self.main_window.delete_empire_border() if self.main_window else None)]
        if self.selected_edge_index is not None:
            actions.insert(0, ("Add Vertex", self._add_vertex_after_selected))
            actions.insert(1, ("Toggle Edge Hidden", self._toggle_selected_edge_hidden))
        return actions

    def _add_vertex_after_selected(self):
        if self.selected_edge_index is not None and self.main_window:
            edge = self.data_object.edges[self.selected_edge_index]
            self.data_object.add_vertex_after(edge)
            self.main_window.mark_unsaved_changes()
            self.render()
            if self.is_selected:
                self._create_selection_overlay()

    def _toggle_selected_edge_hidden(self):
        if self.selected_edge_index is not None and self.main_window:
            edge = self.data_object.edges[self.selected_edge_index]
            edge.hidden = not edge.hidden
            self.main_window.mark_unsaved_changes()
            self.render()
            if self.is_selected:
                self._create_selection_overlay()

    # Legacy method aliases
    def render_border(self):
        self.render()

    @property
    def edges(self) -> List[ed.Edge]:
        return self.data_object.edges if self.data_object else []


# --------------------------- Trade Route ---------------------


class TradeRouteGraphicsObject(PolychainGraphicsObject):
    def __init__(self, city: ed.City, main_window=None):
        # Initialize trade point objects first (before super().__init__ which calls render)
        self.trade_point_objects: List["TradePointGraphicsObject"] = []

        # Configure for trade routes (open polychain, different colors)
        is_land = city.trade_route and city.trade_route.r_type == ed.TradeRouteType.LAND
        config = PolychainConfig(
            pixmap_key="trade_dot",
            density=12,  # tighter spacing for trade dots
            is_closed=False,
            edge_selection_color=QColor(255, 140, 0) if is_land else Qt.cyan,  # Bright red-orange/cyan
            edge_selection_width=3,  # Very thick for maximum visibility
            object_selection_color=Qt.black,
            object_selection_width=1,
            vertex_handle_color=Qt.blue,
            hidden_edge_color=Qt.black,
            hidden_vertex_color=Qt.darkBlue,
        )
        super().__init__(city, GraphicsObjectType.TRADE_ROUTE, config, main_window)

        # Create trade point objects for interaction (after super init)
        if city.trade_route and city.trade_route.trade_points:
            for tp in city.trade_route.trade_points:
                self.trade_point_objects.append(TradePointGraphicsObject(tp, self, main_window))

    # Polychain interface implementation
    def get_points(self) -> List[Tuple[int, int]]:
        if not self.data_object.trade_route:
            return []

        # Build full route: city -> trade points -> our city (if exists)
        pts = [(self.data_object.x, self.data_object.y)]  # Start from city

        for tp in self.data_object.trade_route.trade_points:
            pts.append((tp.x, tp.y))

        # Add our city if it exists
        has_ours, our_city = self.main_window.state.has_our_city()
        if has_ours:
            pts.append((our_city.x, our_city.y))

        return pts

    def get_hidden_states(self) -> List[bool]:
        # Trade routes don't have hidden segments currently
        pts = self.get_points()
        return [False] * max(0, len(pts) - 1)

    def update_point(self, index: int, x: int, y: int):
        # Index 0 is the city itself - can't move that here
        # Indices 1+ are trade points
        if index > 0 and self.data_object.trade_route:
            tp_index = index - 1
            if tp_index < len(self.data_object.trade_route.trade_points):
                self.data_object.trade_route.trade_points[tp_index].x = x
                self.data_object.trade_route.trade_points[tp_index].y = y

    def _get_stamping_pixmap(self) -> QPixmap:
        if not self.main_window or not self.data_object.trade_route:
            return QPixmap()
        is_land = self.data_object.trade_route.r_type == ed.TradeRouteType.LAND
        return self.main_window._get_trade_dot_pixmap(is_land)

    # Override render to handle trade-specific logic
    def render(self):
        if not self.main_window or not self.data_object.trade_route:
            return

        # Update trade point objects to match current trade points
        self.trade_point_objects.clear()
        if self.data_object.trade_route and self.data_object.trade_route.trade_points:
            for tp in self.data_object.trade_route.trade_points:
                self.trade_point_objects.append(TradePointGraphicsObject(tp, self, self.main_window))

        # Use parent polychain render
        super().render()

        # Create additional hit areas for trade points
        self._create_trade_point_hit_areas()

    def _create_trade_point_hit_areas(self):
        """Create clickable hit areas for individual trade points."""
        if not self.data_object.trade_route or not self.data_object.trade_route.trade_points:
            return

        for i, tp in enumerate(self.data_object.trade_route.trade_points):
            # Create a small clickable circle for each trade point
            hit_item = self.place_dot(
                tp.x, tp.y, r=8, brush=QBrush(Qt.transparent), z=z_trade_point_hit, group=self.visual_group
            )
            if hit_item:
                hit_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                hit_item.setData(Qt.ItemDataRole.UserRole, "TRADE_POINT")
                hit_item.setData(Qt.ItemDataRole.UserRole + 1, i)  # index of trade point
                self.scene_items.append(hit_item)

                # Find the corresponding trade point graphics object and attach the item
                if i < len(self.trade_point_objects):
                    self.trade_point_objects[i].attach_point_item(hit_item)

    # Context menu
    def get_context_menu_actions(self):
        actions = [
            (
                "Delete Trade Route Path",
                lambda: self.main_window.delete_trade_route_from_item(None, self.data_object)
                if self.main_window
                else None,
            ),
            ("Edit City", lambda: self.main_window.edit_city(self.data_object) if self.main_window else None),
        ]
        if self.selected_edge_index is not None:
            actions.insert(0, ("Add new vertex", self._add_trade_point_after_selected))
        return actions

    def _add_trade_point_after_selected(self):
        if self.selected_edge_index is not None and self.main_window and self.data_object.trade_route:
            # Convert edge index to trade point position
            if self.selected_edge_index == 0:
                # Add after city, before first trade point
                if self.data_object.trade_route.trade_points:
                    # Create point after city position
                    new_tp = ed.TradePoint(self.data_object.x + 50, self.data_object.y + 50)
                    self.data_object.trade_route.trade_points.insert(0, new_tp)
                else:
                    # No trade points yet, just add one
                    new_tp = ed.TradePoint(self.data_object.x + 50, self.data_object.y + 50)
                    self.data_object.trade_route.trade_points.append(new_tp)
            else:
                # Add after an existing trade point using the proper method
                tp_index = self.selected_edge_index - 1
                if tp_index < len(self.data_object.trade_route.trade_points):
                    tp = self.data_object.trade_route.trade_points[tp_index]
                    self.data_object.trade_route.create_tradepoint_after(tp)

            self.main_window.mark_unsaved_changes()
            self.render()
            if self.is_selected:
                self._create_selection_overlay()

    # Override finish_vertex_editing to handle trade route specific updates
    def finish_vertex_editing(self, vertex_index: int, scene_pos):
        result = super().finish_vertex_editing(vertex_index, scene_pos)
        if result and self.main_window:
            # Trade routes need special handling - refresh through main window to handle deduplication
            self.main_window.refresh_map(snap=False)
        return result

    def remove_from_scene(self):
        for p in self.trade_point_objects:
            p.remove_from_scene()
        super().remove_from_scene()

    # Legacy method aliases
    def render_trade_route(self):
        self.render()

    @property
    def trade_route(self) -> Optional[ed.TradeRoute]:
        return self.data_object.trade_route if self.data_object else None


# --------------------------- Trade Point ---------------------


class TradePointGraphicsObject(GraphicsObjectBase):
    def __init__(self, tp: ed.TradePoint, parent_route: TradeRouteGraphicsObject, main_window=None):
        super().__init__(tp, GraphicsObjectType.TRADE_POINT)
        self.main_window = main_window
        self.parent_route = parent_route
        self.point_item: Optional[QGraphicsItem] = None

    def attach_point_item(self, point_item: QGraphicsItem):
        """Attach a clickable scene item to this trade point."""
        self.point_item = point_item
        self.scene_items.clear()
        if point_item:
            self.scene_items.append(point_item)

    def get_context_menu_actions(self):
        # Trade point specific actions
        point_actions = [("Add Point", self._add_point), ("Delete Point", self._delete_point)]

        # Get parent route actions
        route_actions = []
        if self.parent_route:
            route_actions = [
                ("Edit City", self._edit_route),
                (
                    "Delete Route",
                    lambda: self.parent_route._delete_trade_route()
                    if hasattr(self.parent_route, "_delete_trade_route")
                    else None,
                ),
            ]

        # Combine with separator
        return self.combine_context_menus(point_actions, route_actions)

    def get_hit_test_items(self):
        return [self.point_item] if self.point_item else []

    def update_visual_state(self):
        pass

    def get_cursor_for_operation(self, op: str):
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def _add_point(self):
        """Add a new trade point after this one."""
        if not (self.main_window and self.parent_route):
            return
        route = self.parent_route.trade_route
        if route and self.data_object in route.trade_points:
            # Use the data model method to add the point
            route.create_tradepoint_after(self.data_object)
            # Re-render the trade route to show the new point
            self.parent_route.render_trade_route()
            # Mark as changed
            if self.main_window:
                self.main_window.mark_unsaved_changes()

    def _delete_point(self):
        """Delete this trade point from the route."""
        if not (self.main_window and self.parent_route):
            return
        route = self.parent_route.trade_route
        if route and self.data_object in route.trade_points:
            route.trade_points.remove(self.data_object)
            # Re-render the trade route to update the display
            self.parent_route.render_trade_route()
            # Mark as changed
            if self.main_window:
                self.main_window.mark_unsaved_changes()

    def _edit_route(self):
        if self.parent_route:
            self.parent_route._edit_city()


# --------------------------- Empire Edge ---------------------


class EmpireEdgeGraphicsObject(GraphicsObjectBase):
    def __init__(self, edge: ed.Edge, parent_border: "BorderGraphicsObject", main_window=None):
        super().__init__(edge, GraphicsObjectType.EMPIRE_EDGE)
        self.main_window = main_window
        self.parent_border = parent_border
        self.edge_item: Optional[QGraphicsItem] = None
        self.hit_item: Optional[QGraphicsItem] = None
        self._hilites: List[QGraphicsItem] = []

    def attach_items(self, edge_item: QGraphicsItem, hit_item: QGraphicsItem):
        self.edge_item, self.hit_item = edge_item, hit_item
        self.scene_items.clear()
        if edge_item:
            self.scene_items.append(edge_item)
        if hit_item:
            self.scene_items.append(hit_item)

    def get_context_menu_actions(self):
        return [
            ("Add Vertex", self._add_vertex),
            ("Toggle Edge Hidden", self._toggle_edge_hidden),
            ("Delete Edge", self._delete_edge),
        ]

    def get_hit_test_items(self):
        return [self.hit_item] if self.hit_item else []

    def update_visual_state(self):
        vis = self.parent_border and self.parent_border.is_visible and self.is_visible
        if self.edge_item:
            self.edge_item.setVisible(vis)
        if self.hit_item:
            self.hit_item.setVisible(vis)
        (self._create_selection_highlight() if self.is_selected else self._clear_selection_highlight())

    def _create_selection_highlight(self):
        if not self.main_window or not self.parent_border:
            return
        self._clear_selection_highlight()
        edges = self.parent_border.data_object.edges
        try:
            i = next(k for k, e in enumerate(edges) if e is self.data_object)
        except StopIteration:
            return
        nxt = edges[(i + 1) % len(edges)]
        pen = QPen(Qt.red, 3)
        self._hilites.append(
            self.parent_border.line(self.data_object.x, self.data_object.y, nxt.x, nxt.y, pen, 125, None, False)
        )

    def _clear_selection_highlight(self):
        self.parent_border.rm(self._hilites)

    def get_cursor_for_operation(self, op: str):
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def _add_vertex(self):
        if self.parent_border:
            self.parent_border.data_object.add_vertex_after(self.data_object)
            self.parent_border.render_border()
            self.main_window.refresh_map()
        if self.main_window:
            self.main_window.mark_unsaved_changes()

    def _toggle_edge_hidden(self):
        self.data_object.hidden = not self.data_object.hidden
        if self.parent_border:
            self.parent_border.render_border()
        if self.main_window:
            self.main_window.mark_unsaved_changes()

    def _delete_edge(self):
        if not (self.main_window and self.parent_border):
            return
        border = self.parent_border.data_object
        if border and self.data_object in border.edges:
            border.edges.remove(self.data_object)
            self.parent_border.render_border()
            self.main_window.mark_unsaved_changes()


# --------------------------- Palette entries -----------------


class SelectableElement:
    """Represents an element selectable from a list widget."""

    def __init__(
        self, name: str, pixmap: QPixmap, data_type: Any, graphics_type: GraphicsObjectType, enabled: bool = True
    ):
        self.name = name
        self.pixmap = pixmap
        self.data_type = data_type
        self.graphics_type = graphics_type
        self.enabled = enabled

    def create_data_object(self, **kw) -> Any:
        if self.graphics_type == GraphicsObjectType.CITY:
            return ed.City(city_type=self.data_type, **kw)
        if self.graphics_type == GraphicsObjectType.BORDER_EDGE:
            return None
        if self.graphics_type == GraphicsObjectType.EMPIRE_EDGE:
            return ed.Edge(**kw)
        if self.graphics_type == GraphicsObjectType.TRADE_POINT:
            return ed.TradePoint(**kw)
        return None

    def create_graphics_object(self, data_object: Any, main_window=None) -> GraphicsObjectBase:
        if self.graphics_type == GraphicsObjectType.CITY:
            return CityGraphicsObject(data_object, self.pixmap, main_window)
        if self.graphics_type == GraphicsObjectType.BORDER_EDGE:
            return BorderGraphicsObject(data_object, main_window)
        if self.graphics_type == GraphicsObjectType.TRADE_ROUTE:
            return TradeRouteGraphicsObject(data_object, main_window)
        raise ValueError(f"Unknown graphics type: {self.graphics_type}")


# --------------------------- Manager -------------------------


class GraphicsObjectManager:
    """Tracks all on-scene wrappers and selection."""

    def __init__(self):
        self.city_objects: Dict[int, CityGraphicsObject] = {}
        self.border_object: Optional[BorderGraphicsObject] = None
        self.trade_route_objects: Dict[int, TradeRouteGraphicsObject] = {}
        self.selected_object: Optional[GraphicsObjectBase] = None

    @staticmethod
    def get_city_pixmap(city: ed.City, main_window) -> QPixmap:
        """Get pixmap for a city type from main window state."""
        if not main_window or not hasattr(main_window, "state"):
            return QPixmap()
        if isinstance(city.icon, ed.CityIconType):
            icon_key = city.icon.value
        else:
            icon_key = city.icon
        pil_image = main_window.state.city_icons_map[icon_key]
        return main_window.pil_to_qpixmap(pil_image)

    # cities
    def add_city(self, city: ed.City, pixmap: QPixmap = None, main_window=None) -> CityGraphicsObject:
        # Get pixmap if not provided
        if pixmap is None or pixmap.isNull():
            pixmap = self.get_city_pixmap(city, main_window)

        obj = CityGraphicsObject(city, pixmap, main_window)
        self.city_objects[id(city)] = obj
        return obj

    def remove_city(self, city: ed.City):
        cid = id(city)
        if cid in self.city_objects:
            obj = self.city_objects[cid]
            obj.remove_from_scene()
            del self.city_objects[cid]
            if cid in self.trade_route_objects:
                self.remove_trade_route(city)

    # border
    def add_border(self, border: ed.Border, main_window=None) -> BorderGraphicsObject:
        if self.border_object:
            self.border_object.remove_from_scene()
        self.border_object = BorderGraphicsObject(border, main_window)
        return self.border_object

    def remove_border(self):
        if self.border_object:
            self.border_object.remove_from_scene()
            self.border_object = None

    # routes
    def add_trade_route(self, city: ed.City, main_window=None) -> TradeRouteGraphicsObject:
        obj = TradeRouteGraphicsObject(city, main_window)
        self.trade_route_objects[id(city)] = obj
        if city.trade_route:
            obj.render_trade_route()
        return obj

    def remove_trade_route(self, city: ed.City):
        cid = id(city)
        if cid in self.trade_route_objects:
            obj = self.trade_route_objects[cid]
            obj.remove_from_scene()
            del self.trade_route_objects[cid]

    # global ops
    def clear_all(self):
        for obj in list(self.city_objects.values()):
            obj.remove_from_scene()
        self.city_objects.clear()
        if self.border_object:
            self.border_object.remove_from_scene()
            self.border_object = None
        for obj in list(self.trade_route_objects.values()):
            obj.remove_from_scene()
        self.trade_route_objects.clear()
        self.selected_object = None

    def select_object(self, obj: Optional[GraphicsObjectBase]):
        if self.selected_object:
            self.selected_object.set_selected(False)
        self.selected_object = obj
        if obj:
            obj.set_selected(True)

    def deselect_all(self):
        self.select_object(None)

    # lookup
    def get_graphics_object_for_scene_item(self, scene_item: QGraphicsItem) -> Optional[GraphicsObjectBase]:
        # Check border object directly (no more individual edge objects)
        if self.border_object and scene_item in self.border_object.get_hit_test_items():
            return self.border_object

        for pt in self.get_trade_point_objects():
            if scene_item in pt.get_hit_test_items():
                return pt
        for obj in self.city_objects.values():
            if scene_item in obj.get_hit_test_items():
                return obj
        for obj in self.trade_route_objects.values():
            if scene_item in obj.get_hit_test_items():
                return obj
        return None

    def set_cities_visibility(self, visible: bool):
        for obj in self.city_objects.values():
            obj.set_visible(visible)

    def set_border_visibility(self, visible: bool):
        if self.border_object:
            self.border_object.set_visible(visible)

    def set_trade_routes_visibility(self, visible: bool):
        for obj in self.trade_route_objects.values():
            obj.set_visible(visible)

    def get_empire_edge_objects(self) -> List["EmpireEdgeGraphicsObject"]:
        # Legacy method - no longer used with unified polychain system
        return []

    def get_trade_point_objects(self) -> List["TradePointGraphicsObject"]:
        pts = []
        for obj in self.trade_route_objects.values():
            pts.extend(obj.trade_point_objects)
        return pts

    def get_graphics_object_for_scene_item_including_nested(
        self, scene_item: QGraphicsItem
    ) -> Optional[GraphicsObjectBase]:
        obj = self.get_graphics_object_for_scene_item(scene_item)
        if obj:
            return obj

        # Check border object directly (no more individual edge objects)
        if self.border_object and scene_item in self.border_object.get_hit_test_items():
            return self.border_object

        for pt in self.get_trade_point_objects():
            if scene_item in pt.get_hit_test_items():
                return pt
        return None
