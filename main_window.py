import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QApplication, QListWidgetItem, QMessageBox,
    QLabel, QDialog, QWidget, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsItemGroup,  QGraphicsItem,  QMenu, QMenuBar

)
from PySide6.QtGui import QIcon, QPixmap, QImage, QCursor, QPainter, QPen, QBrush, QPainterPath, QAction, QColor
from PySide6.QtCore import QSize, QSettings, Qt, QEvent, QObject, QPoint, QRectF, QSizeF, QPointF, QTimer
from sg_reader import SgFileReader
from ui_empire_editor import Ui_MainWindow
# top of main_window.py (with your other imports)
import empire_data as ed
import edit_city_logic as emp_dlg
from math import hypot
from enum import Enum, auto
import copy

# ---------------------------------------------
# New, separated enums
# ---------------------------------------------
class EmpCityTypes(Enum):
    OUR = auto()
    DISTANT = auto()
    TRADE = auto()

class EmpObjTypes(Enum):
    EMPIRE_EDGE = auto()
    LAND_DOT = auto()
    SEA_DOT = auto()
    
    
CITYTYPE_TO_KIND = {
    ed.CityType.OURS: EmpCityTypes.OUR,
    getattr(ed.CityType, "TRADE", None): EmpCityTypes.TRADE,
    getattr(ed.CityType, "ROMAN", None): EmpCityTypes.TRADE,
    getattr(ed.CityType, "VULNERABLE", None): EmpCityTypes.TRADE,
    getattr(ed.CityType, "DISTANT", None): EmpCityTypes.DISTANT,
}
# ---------------------------------------------






class ProgramState:
    def __init__(self):
        self.images = {}
        self.selected_empire_image = None
        self.city_icons_map = {}
        self.init_failed = False
        self.c3_main_path = ""
        self.current_empire_object  = None
    def init(self):
        if not self.load_c3_folder():
            self.init_failed = True
            return False
        self.load_images()
        return not self.init_failed

    def load_c3_folder(self):
        config_path = os.path.join(os.path.dirname(__file__), "empire_editor.cfg")
        settings = QSettings(config_path, QSettings.IniFormat)
        self.c3_main_path = settings.value("c3_main_folder", type=str)

        if not self.c3_main_path:
            folder = QFileDialog.getExistingDirectory(
                None,
                "Select Caesar 3 Main Directory",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            if folder and self.validate_c3_directory(folder):
                settings.setValue("c3_main_folder", folder)
                self.c3_main_path = folder
                return True
            else:
                QMessageBox.critical(
                    None, "Invalid Folder", "Please select a valid Caesar 3 directory.", QMessageBox.Ok
                )
                return False
        return True

    def validate_c3_directory(self, path: str) -> bool:
        required_files = ["C3.sg2", "augustus.exe"]
        missing = [file for file in required_files if not os.path.isfile(os.path.join(path, file))]
        if missing:
            QMessageBox.critical(
                None,
                "Missing Files",
                "The following required files are missing:\n" + "\n".join(missing),
                QMessageBox.Ok
            )
            return False
        return True

    def load_images(self):
        if self.c3_main_path:
            c3_sg_path = os.path.join(self.c3_main_path, "C3.sg2")
            reader = SgFileReader(c3_sg_path)
            self.images = reader.load_filtered("The_empire", "empire_bits", "empire_panels")
            self.create_selectable_elements()
    
    def create_selectable_elements(self):
        try:
            def crop5x5(img):
                return img.crop((0, 0, 5, 5))  # (left, top, right, bottom), bottom is exclusive

            bits = self.images["empire_bits"]
            self.images["sea_dot"]  = crop5x5(bits[102])
            self.images["land_dot"] = crop5x5(bits[94])
            

            # NOTE: "kind" now holds a value from EmpCityTypes OR EmpObjTypes.
            self.elements = [
                {"name": "Our City",      "pil": bits[0],  "kind": EmpCityTypes.OUR},
                {"name": "Roman City",    "pil": bits[7],  "kind": EmpCityTypes.TRADE},
                {"name": "Far away city", "pil": bits[21], "kind": EmpCityTypes.DISTANT},
                {"name": "Empire edge",   "pil": bits[71], "kind": EmpObjTypes.EMPIRE_EDGE},
                #{"name": "Sea Dot",       "pil": crop5x5(bits[102]), "kind": EmpObjTypes.SEA_DOT},
                #{"name": "Land Dot",      "pil": crop5x5(bits[94]), "kind": EmpObjTypes.LAND_DOT}
            ]
        except (KeyError, IndexError):
            self.init_failed = True
            QMessageBox.critical(None, "Error", "Error loading selectable elements.", QMessageBox.Ok)


    def reset_state(self):
        self.images.clear()
        self.selected_empire_image = None
        self.city_icons_map.clear()
        self.init_failed = False

    def has_our_city(self):
        """Return (True, city) if an 'ours' city exists, else (False, None)."""
        e = self.current_empire_object
        if not e:
            return False, None
        for c in getattr(e, "cities", []):
            if getattr(c, "type", None) == ed.CityType.OURS:
                return True, c
        return False, None

    def has_any_data(self):
        """Rough check if current empire has any content worth warning about."""
        e = self.current_empire_object
        if not e:
            return False
        if getattr(e, "cities", []):
            return True
        if getattr(e, "ornaments", []):
            return True
        if getattr(e, "invasion_paths", []):
            return True
        if getattr(e, "distant_battle_paths", []):
            return True
        b = getattr(e, "border", None)
        if b and getattr(b, "edges", []):
            return True
        return False

    def check_if_empire(self):
        return self.current_empire_object is not None

    def new_empire(self):
        self.current_empire_object = ed.Empire()
    
    
    
class PaddedHitPixmapItem(QGraphicsPixmapItem):
    """
    QGraphicsPixmapItem with an enlarged hit area (for hover/selection).
    'hitpad' is padding in pixels added on all sides around the icon.
    """
    def __init__(self, pixmap, hitpad=6, parent=None):
        super().__init__(pixmap, parent)
        self._hitpad = float(hitpad)

    def shape(self) -> QPainterPath:
        # Local rect in item coords must include the current offset
        # because we call setOffset(-w/2, -h/2) when centering.
        pm = self.pixmap()
        r = QRectF(self.offset(), QSizeF(pm.width(), pm.height()))
        r.adjust(-self._hitpad, -self._hitpad, self._hitpad, self._hitpad)

        path = QPainterPath()
        path.addRect(r)
        return path

        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.no_bg_item = None
        self.bg_item = None  # the background QGraphicsPixmapItem
        # Edge drawing state
        self.edge_drawing_active = False           # are we in the border drawing mode?
        self.edge_points_img = []                  # [(x_img, y_img), ...]
        self.edge_point_items = []                 # [QGraphicsEllipseItem,...] small red dots
        self.edge_line_items = []                  # [QGraphicsLineItem,...] finalized segments
        self.edge_temp_line_item = None            # QGraphicsLineItem rubber-band
        self.edge_hit_epsilon = 10                # pixels in image coords to detect closing click
        self.border_edge_hit_items = []   # selectable hit proxies for each segment
        self.selected_edge_index = None   # index i for edge i -> i+1
        self.return_to_dialog = False
        # permanent empire border overlay (icon-based)
        self.empire_border = False
        self.border_visual_group = None          # QGraphicsItemGroup for the icon overlay
        self.border_icon_items = []              # QGraphicsPixmapItem[] belonging to the group

        # selection overlay (dotted stroke + square handles)
        self.border_sel_line_items = []      # QGraphicsLineItem[]
        self.border_sel_handle_items = []    # QGraphicsRectItem[]
        self.border_selected = False
        self.moving_city = None  # when set, a drop moves this city

        self.ui.mouse_position_label.setVisible(False)  # hidden until a map is set
        self.city_items = {}  # maps City -> QGraphicsPixmapItem
        # trade-route drawing state
        self.trade_drawing_active = False
        self.trade_is_land = True
        self.trade_drawing_points = []          # temp points during drawing
        self.trade_drawing_point_items = []     # temp visual dots during drawing
        self.trade_drawing_line_items = []      # temp visual lines during drawing
        self.trade_temp_line_item = None        # rubber band line
        self.trade_route_city = None            # city being edited

        # Trade route selection state (similar to border selection)
        self.trade_route_selected = False
        self.selected_trade_route_city = None
        self.trade_route_sel_line_items = []      # QGraphicsLineItem[] for dotted lines
        self.trade_route_sel_handle_items = []    # QGraphicsRectItem[] for white squares
        self.trade_route_hit_items = []           # Invisible hit areas for trade route segments
        # Permanent rendered trade routes (keyed by city index)
        self._trade_route_groups = {}  # {city_index: QGraphicsItemGroup}
        
        # Vertex editing state - unified for both trade routes and empire borders
        self.vertex_editing_active = False      # True when dragging a vertex
        self.editing_vertex_type = None         # "TRADE_ROUTE" or "EMPIRE_BORDER"
        self.editing_vertex_index = None        # Index of the vertex being edited
        self.editing_vertex_city = None         # City object (for trade routes only)
        self.editing_vertex_handle = None       # The handle item being dragged
        self.vertex_handle_items = []           # List of active vertex handles
        
        # Data/state
        self.state = ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return

        # Initialize cursor pixmaps once at startup
        self._init_cursor_pixmaps()

        # Scene / view
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)

        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)

        self.ui.graphicsView.viewport().setMouseTracking(True)
        
        self.ui.graphicsView.setRenderHint(QPainter.SmoothPixmapTransform, False)

        self.show_no_background_message()               # show placeholder on startup

        # UI wiring
        self.add_city_icons_to_list()
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)
        self.ui.listWidget.itemClicked.connect(self.on_item_clicked)

        # Drag handling
        self.selected_item = None
        self.selected_kind = None        # can be EmpCityTypes or EmpObjTypes
        self.current_icon = None
        self.is_dragging = False
        self._init_context_menus()

    def _init_context_menus(self):
        city_common_menu = [
            ("Move City", lambda it: self.move_city(it.data(1))),
            ("Delete City", lambda it: self.remove_city(it.data(1))),
            ("Properties", lambda it: self._edit_city(it.data(1))),
        ]

        self.context_menu_options = {
            EmpCityTypes.OUR: city_common_menu,
            EmpCityTypes.DISTANT: city_common_menu,
            EmpCityTypes.TRADE: city_common_menu,
            
            EmpObjTypes.EMPIRE_EDGE: [
                ("Toggle Edge Hidden", lambda it: self.toggle_edge_hidden_from_item(it)),
                ("Delete Border", self.delete_empire_border),
            ],
            
            # Add trade route context menu
            "TRADE_ROUTE": [
                ("Delete Trade Route Path", lambda it: self.delete_trade_route_from_item(it)),
                ("Edit City", lambda it: self.edit_city_from_trade_route_item(it)),
            ],
        }
    def _init_cursor_pixmaps(self):
        """Initialize cursor pixmaps once at startup for drawing modes."""
        # Edge drawing cursor - use empire edge icon
        edge_pm = self._get_empire_edge_pixmap()
        if edge_pm.isNull():
            # Fallback: create a simple red square
            edge_pm = QPixmap(8, 8)
            edge_pm.fill(Qt.red)
        self.edge_cursor_pixmap = edge_pm
        
        # Trade drawing cursors - use trade dot icons
        land_pm = self._get_trade_dot_pixmap(True)
        if land_pm.isNull():
            # Fallback: create a simple orange dot
            land_pm = QPixmap(8, 8)
            land_pm.fill(QColor(255, 140, 0))
        self.land_cursor_pixmap = land_pm
        
        sea_pm = self._get_trade_dot_pixmap(False)
        if sea_pm.isNull():
            # Fallback: create a simple cyan dot
            sea_pm = QPixmap(8, 8)
            sea_pm.fill(Qt.cyan)
        self.sea_cursor_pixmap = sea_pm
    def _get_city_index(self, city) -> int | None:
        """Get the index of a city in the current empire's cities list."""
        empire = self.state.current_empire_object
        if not empire or not hasattr(empire, 'cities'):
            return None
        try:
            return empire.cities.index(city)
        except ValueError:
            return None
    def delete_trade_route_from_item(self, item):
        """Delete trade route path from context menu selection."""
        city_index = item.data(Qt.UserRole + 1)
        city = self._get_city_by_index(city_index)
        if city and city.trade_route and city.trade_route.trade_points:
            resp = QMessageBox.question(
                self, "Delete Trade Route",
                f"Delete trade route path for {city.name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                # Clear selection if this was the selected route
                if self.selected_trade_route_city == city:
                    self.clear_trade_route_selection_overlay()
                # Clear only the plotted path, keep the trade route object
                city.trade_route.trade_points.clear()
                self.clear_trade_route_visuals(city_index)

    def edit_city_from_trade_route_item(self, item):
        """Edit city from trade route context menu selection."""
        city_index = item.data(Qt.UserRole + 1)
        city = self._get_city_by_index(city_index)
        if city:
            self._edit_city(city)
    def _get_city_center(self, city):
        """Get the center coordinates of a city icon."""
        city_pixmap = self._pixmap_for_city(city)
        center_x = city.x + city_pixmap.width() // 2
        center_y = city.y + city_pixmap.height() // 2
        return center_x, center_y

    def _trade_route_ends_at_city(self, trade_route, city):
        """Check if a trade route ends at the specified city (last point within city bounds)."""
        if not trade_route or not trade_route.trade_points or len(trade_route.trade_points) < 1:
            return False
        
        # Get the last trade point
        last_point = trade_route.trade_points[-1]
        
        # Get city bounds
        city_pixmap = self._pixmap_for_city(city)
        city_width = city_pixmap.width()
        city_height = city_pixmap.height()
        
        # Check if last point is within city icon bounds
        return (city.x <= last_point.x <= city.x + city_width and 
                city.y <= last_point.y <= city.y + city_height)

    def _get_city_by_index(self, index: int):
        """Get city by index from current empire's cities list."""
        empire = self.state.current_empire_object
        if not empire or not hasattr(empire, 'cities') or index < 0 or index >= len(empire.cities):
            return None
        return empire.cities[index]
    
    def set_drawing_cursor(self, enable: bool, pixmap=None):
        """Unified cursor management for all modes."""
        widgets = (self, self.ui.graphicsView, self.ui.graphicsView.viewport())
        if not enable:
            for w in widgets: 
                try: w.unsetCursor()
                except: pass
            return
        
        # Use provided pixmap or determine from drawing mode
        if not pixmap:
            if self.edge_drawing_active: pixmap = self.edge_cursor_pixmap
            elif self.trade_drawing_active: pixmap = self.land_cursor_pixmap if self.trade_is_land else self.sea_cursor_pixmap
        
        if pixmap:
            try:
                cursor = QCursor(pixmap, 0, 0)
                for w in widgets: w.setCursor(cursor)
            except:
                for w in widgets: 
                    try: w.unsetCursor()
                    except: pass
# %% GLOBAL EVENT FILTER
    def eventFilter(self, obj, event):
        et = event.type()
    
        # 1) Always ignore modal dialogs

        if QApplication.activeModalWidget() or QApplication.activePopupWidget():
            return False

        # 2) Dispatch by event type
        if et == QEvent.MouseMove:
            return self._handle_mouse_move(event)
    
        elif et in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return self._handle_mouse_click(event)
            
        elif et == QEvent.KeyPress:
            return self._handle_key_press(event)
    
        return QObject.eventFilter(self, obj, event)
    
    def _handle_key_press(self, event):
        """Handle keyboard events for vertex editing and other shortcuts."""
        key = event.key()
        
        # Escape key cancels various operations
        if key == Qt.Key_Escape:
            if self.vertex_editing_active:
                self.cancel_vertex_editing()
                return True
            elif self.edge_drawing_active:
                self._edge_prompt_incomplete()
                return True
            elif self.trade_drawing_active:
                self._abort_trade_drawing()
                return True
        
        # Backspace/Delete for undo in drawing modes
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.trade_drawing_active:
                self._trade_undo_last_point()
                return True
        
        return False  # Don't consume other keys

    # =========================
    # HELPER HANDLERS
    # =========================

    def _handle_mouse_move(self, event):
        """Mouse move: update label, dragging icon, vertex editing, and edge preview."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        vp_pos = vp.mapFromGlobal(gp)
    
        # Update position label
        if vp.rect().contains(vp_pos):
            scene_pos = view.mapToScene(vp_pos)
            
            # Handle vertex editing
            if self.vertex_editing_active:
                self.update_vertex_position(scene_pos)
            elif self.edge_drawing_active:
                self._edge_update_temp_line(scene_pos)
            elif self.trade_drawing_active:
                self._trade_update_temp_line(scene_pos)

            self._update_mouse_position_label(scene_pos)
            

        # Floating drag icon
        if self.is_dragging and self.current_icon:
            self.current_icon.move(self.mapFromGlobal(gp))
    
        return False  # don't consume
    
    def _handle_mouse_click(self, event):
        """Mouse clicks: route to drag, edge drawing, vertex editing, or selection logic."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        inside_view = vp.rect().contains(vp.mapFromGlobal(gp))
        btn = event.button()
        et = event.type()
    
        # Vertex editing mode
        if self.vertex_editing_active and et == QEvent.MouseButtonPress:
            if btn == Qt.RightButton:
                # Right-click cancels vertex editing
                self.cancel_vertex_editing()
                return True
            elif btn == Qt.LeftButton:
                # Left-click finishes vertex editing
                scene_pos = view.mapToScene(vp.mapFromGlobal(gp))
                self.finish_vertex_editing(scene_pos)
                return True  # Consume the event
    
        # Dragging mode
        if self.is_dragging:
            return self._handle_drag_click(event, gp, inside_view)
    
        # Edge drawing mode
        if self.edge_drawing_active and et == QEvent.MouseButtonPress:
            return self._handle_edge_click(event, gp, inside_view)

        # Trade drawing mode
        if self.trade_drawing_active and et == QEvent.MouseButtonPress:
            return self._handle_trade_click(event, gp, inside_view)
        
        # Normal mode selection
        if not self.is_dragging and not self.edge_drawing_active and et == QEvent.MouseButtonPress:
            return self._handle_normal_click(event, gp, inside_view)
    
        return False
    
    
    # =========================
    # SUB-MODE HANDLERS
    # =========================
        
    def _handle_drag_click(self, event, gp, inside_view):
        # cancel move/drag on right click (press or release), anywhere
        if event.button() == Qt.RightButton:
            self.moving_city = None
            self.deselect_item()
            return True
    
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and not inside_view:
                self.deselect_item()
                return True
    
        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.pending_drop_pixmap = getattr(self, "drag_pixmap", None)
                self.deselect_item()
                if inside_view:
                    view_pos = self.ui.graphicsView.mapFromGlobal(gp)
                    scene_pos = self.ui.graphicsView.mapToScene(view_pos)
                    self.handle_icon_drop(scene_pos)
                self.pending_drop_pixmap = None
                return True
    
        return False

    
    def _handle_edge_click(self, event, gp, inside_view):
        if event.button() == Qt.RightButton or not inside_view:
            self._edge_prompt_incomplete()
            return True
        if event.button() == Qt.LeftButton:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            xy = self._scene_to_image_xy(scene_pos)
            if xy is None:
                self._edge_prompt_incomplete()
                return True
            x, y = xy
            close_idx = self._edge_hit_existing_point(x, y)
            if close_idx is not None:
                self._finalize_edge(success=True, close_to_index=close_idx)
            else:
                self._edge_append_point(x, y)
            return True
        return False
            
    def _handle_normal_click(self, event, gp, inside_view):
        # --- RIGHT CLICK ---
        if event.button() == Qt.RightButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(
                self.ui.graphicsView.viewport().mapFromGlobal(gp)
            )
            items = self.scene.items(scene_pos)
    
            for it in items:
                if it.flags() & QGraphicsItem.ItemIsSelectable:
                    # Optional: auto-select before showing menu
                    self._select_scene_item(it)
                    self._show_context_menu_for_item(it, gp)
                    return True
    
            # No selectable item → clear selection
            self.deselect_all()
            return True
    
        # --- LEFT CLICK ---
        if event.button() == Qt.LeftButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(
                self.ui.graphicsView.viewport().mapFromGlobal(gp)
            )
            items = self.scene.items(scene_pos)
    
            for it in items:
                if it.flags() & QGraphicsItem.ItemIsSelectable:
                    self._select_scene_item(it)
                    return True
    
            # Clicked empty spot → clear selection
            self.deselect_all()
            return True
    
        return False


# %% Input adjacent Functions
# %%% Selection handling:
    def _select_scene_item(self, item):
        """
        Handle selecting any selectable object on the scene.
        Only one selection can be active at a time.
        """
        # Clear ALL previous selection states
        self.clear_border_selection_overlay()
        self.clear_trade_route_selection_overlay()
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None

        # Trade route segment hit
        if hasattr(item, "data") and callable(item.data):
            route_type = item.data(Qt.UserRole)
            if route_type == "TRADE_ROUTE":
                city_index = item.data(Qt.UserRole + 1)
                city = self._get_city_by_index(city_index)
                if city:
                    self.select_trade_route_overlay(city)
                    self.selected_item = item
                    # Create vertex handles for editing
                    if city.trade_route and city.trade_route.trade_points:
                        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
                        self.create_vertex_handles("TRADE_ROUTE", pts, city)
                    return
            
            # Vertex handle selection
            if route_type == "VERTEX_HANDLE":
                self.start_vertex_editing(item)
                return

        # Edge segment (hit proxy)
        if item in self.border_edge_hit_items:
            self.selected_edge_index = item.data(Qt.UserRole + 1)
            self.select_empire_border_overlay()
            self.selected_item = item
            # Create vertex handles for border editing
            empire = self.state.current_empire_object
            if empire and empire.border and empire.border.edges:
                pts = [(edge.x, edge.y) for edge in empire.border.edges]
                self.create_vertex_handles("EMPIRE_BORDER", pts)
            return
        
        # (optional: keep vertex/icon handling if you still want it)
        if item in self.border_icon_items:
            self.select_empire_border_overlay()
            self.selected_item = item
            return

        # City markers
        if hasattr(item, "data") and callable(item.data):
            city_obj = item.data(1)
            if city_obj and getattr(city_obj, "__class__", None).__name__ == "City":
                self.select_city_marker(item, city_obj)
                return
    
        # If nothing matched, ensure nothing is selected
        self.deselect_all()

        
    def select_city_marker(self, item, city_obj):
        """Visual + state change when a city marker is selected."""
        self.selected_item = item
        # You could change appearance here (glow, outline, etc.)
        # Or just rely on QGraphicsItem's built-in selection visuals
        item.setSelected(True)
        # Maybe update side panel UI here
    
    def deselect_city_marker(self):
        """Clear city selection visuals."""
        if self.selected_item and self.selected_item in self.city_items.values():
            self.selected_item.setSelected(False)
        self.selected_item = None

    # ---------- LIST / DRAGGING ----------
    def _update_mouse_position_label(self, scene_pos):
        pm_item = self.bg_item
        if pm_item is not None:
            img_pos = pm_item.mapFromScene(scene_pos)
            x, y = int(img_pos.x()), int(img_pos.y())
            pm = pm_item.pixmap()
            if 0 <= x < pm.width() and 0 <= y < pm.height():
                self.ui.mouse_position_label.setText(f"Mouse Position: ({x}, {y})")
            else:
                self.ui.mouse_position_label.setText("")
        return 
    def on_item_clicked(self, item):
        if self.selected_item == item:
            # already selected -> deselect
            self.deselect_item()
        else:
            self.select_item(item)
            # visually mark it selected in the list
            self.ui.listWidget.setCurrentItem(item)

    def select_item(self, item):
        self.deselect_all() # clear current selections first
        self.selected_item = item
        self.selected_kind = item.data(Qt.UserRole)  # EmpCityTypes or EmpObjTypes
        pixmap = item.icon().pixmap(self.ui.listWidget.iconSize())
        self.ui.graphicsView.setInteractive(False)

        # cache the exact pixmap used for drag
        self.drag_pixmap = pixmap
    
        if self.current_icon:
            self.current_icon.deleteLater()
        self.current_icon = QLabel(self)
        self.current_icon.setPixmap(pixmap)
        self.current_icon.setFixedSize(pixmap.size())
        self.current_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.is_dragging = True
        self.set_drawing_cursor(True, pixmap)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        
        self._apply_interactivity_to_all(False)

    def deselect_item(self):
        if self.current_icon:
            self.current_icon.deleteLater()
            self.current_icon = None
        # keep self.selected_kind intact so drop handler knows what was chosen
        self.selected_item = None
        self.is_dragging = False
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)

        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)  # not ScrollHandDrag
    
        # FIX: also clear the QListWidget’s selection so it’s not visually highlighted
        self.ui.listWidget.clearSelection()
        self._apply_interactivity_to_all(True)
            
    def deselect_all(self):
        self.clear_border_selection_overlay()
        self.clear_trade_route_selection_overlay()
        self.clear_vertex_handles()  # Clear vertex editing handles
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None
        self.selected_edge_index = None

    def clear_border_selection_overlay(self):
        """Remove dotted stroke + handles if present."""
        self._clear_selection_overlay("border")
        
    def clear_trade_route_selection_overlay(self):
        """Remove trade route selection visuals (dotted lines and white squares)."""
        self._clear_selection_overlay("trade_route")
        
    def _clear_selection_overlay(self, overlay_type):
        """Generic function to clear selection overlays."""
        if overlay_type == "border":
            items = [self.border_sel_line_items, self.border_sel_handle_items]
            for item_list in items:
                for it in item_list:
                    if hasattr(it, 'scene') and it.scene() is not None:
                        self.scene.removeItem(it)
                item_list.clear()
            self.border_selected = False
        elif overlay_type == "trade_route":
            items = [self.trade_route_sel_line_items, self.trade_route_sel_handle_items]
            for item_list in items:
                for it in item_list:
                    if hasattr(it, 'scene') and it.scene() is not None:
                        self.scene.removeItem(it)
                item_list.clear()
            self.trade_route_selected = False
            self.selected_trade_route_city = None
        
        
    def remove_city(self, city):
        empire = self.state.current_empire_object
        if empire and city in empire.cities:
            # Clear trade route visuals before removing city
            city_index = self._get_city_index(city)
            if city_index is not None:
                self.clear_trade_route_visuals(city_index)
            
            empire.cities.remove(city)
        self._remove_city_marker(city)
        # updated enum check
        if self.selected_item and self.selected_item.data(Qt.UserRole) == EmpCityTypes.OUR:
            self.deselect_item()
            
    def clear_empire_border_visual(self):
        self.clear_border_selection_overlay()
        if self.border_visual_group is not None:
            try:
                self.scene.removeItem(self.border_visual_group)
            except Exception:
                pass
            self.border_visual_group = None
        self.border_icon_items.clear()
    
    def _handle_trade_click(self, event, gp, inside_view):
        # Finish by right click anywhere or click same point twice
        if event.button() == Qt.RightButton or not inside_view:
            self._abort_trade_drawing()
            return True

        if event.button() == Qt.LeftButton:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            
            xy = self._scene_to_image_xy(scene_pos)
            if xy is None:
                self._finalize_trade_route(success=False)
                return True
            x, y = xy
            
            # Always add the point first
            self._trade_append_point(x, y)
            
            # Then check if we clicked on "Our City" - if so, finish the route
            for city in self.state.current_empire_object.cities:
                if city.type == ed.CityType.OURS:
                    # Get the actual city pixmap dimensions
                    city_pixmap = self._pixmap_for_city(city)
                    city_width = city_pixmap.width()
                    city_height = city_pixmap.height()
                    
                    # Check if click coordinates are within the city icon rectangle
                    if (city.x <= x <= city.x + city_width and 
                        city.y <= y <= city.y + city_height):
                        # Clicked on Our City - finish the trade route
                        self._finalize_trade_route(success=True, reopen_dialog=True)
                        return True
                    break  # Only one "Our City" exists
            
            # Check for clicking on existing points to finish
            hit_idx = self._trade_hit_existing_point(x, y)
            if hit_idx == len(self.trade_drawing_points) - 2 and len(self.trade_drawing_points) >= 2:
                resp = QMessageBox.information(
                    self,
                    "Incomplete Trade Route",
                    "This trade route doesn't end on our city. Would you like to save it anyway?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                if resp == QMessageBox.Yes:
                    self._finalize_trade_route(success=True)
                if resp == QMessageBox.No:
                    self._abort_trade_drawing()
                if resp == QMessageBox.Cancel:
                    self._trade_undo_last_point()
            
            return True
        return False
    
    def select_empire_border_overlay(self):
        """Mark the existing border overlay as selected, highlight selected edge thicker."""
        e = self.state.current_empire_object
        if not (self.empire_border and e and getattr(e, "border", None) and self.bg_item):
            return
        pts = [(edge.x, edge.y) for edge in getattr(e.border, "edges", [])]
        if len(pts) < 2:
            return
    
        self.clear_border_selection_overlay()
    
        selected_edge_idx = getattr(self, "selected_edge_index", None)
    
        # Draw dotted outline, making the selected edge thicker
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            p0 = self.bg_item.mapToScene(x0, y0)
            p1 = self.bg_item.mapToScene(x1, y1)
    
            # Thicker pen for the selected edge
            if selected_edge_idx == i:
                pen = QPen(Qt.black, 3)
            else:
                pen = QPen(Qt.black, 1)
            pen.setStyle(Qt.DotLine)
    
            seg = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
            seg.setZValue(120)  # above icons
            self.border_sel_line_items.append(seg)
    
        # Square handles at vertices
        handle_size = 6
        half = handle_size / 2.0
        hpen = QPen(Qt.black, 1)
        hbrush = QBrush(Qt.white)
        for x, y in pts:
            p = self.bg_item.mapToScene(x, y)
            rect = self.scene.addRect(p.x() - half, p.y() - half, handle_size, handle_size, hpen, hbrush)
            rect.setZValue(130)
            self.border_sel_handle_items.append(rect)
    
        self.border_selected = True
    

    # %%% other input-adjacent 
    def _show_context_menu_for_item(self, item, global_pos):
        """Show context menu based on enum stored in item."""
        if not (hasattr(item, "data") and callable(item.data)):
            return

        obj_type = item.data(Qt.UserRole)
        if obj_type not in self.context_menu_options:
            return

        menu = QMenu(self)
        for label, callback in self.context_menu_options[obj_type]:
            act = QAction(label, self)
            # Fix lambda capture issue by using default parameter
            act.triggered.connect(lambda checked=False, cb=callback, it=item: cb(it))
            menu.addAction(act)

        menu.exec(global_pos)
        
    def move_city(self, city_obj):
        """Enter drag mode to move an existing city."""
        self.moving_city = city_obj
        pm = self._pixmap_for_city(city_obj)
    
        # reuse existing drag UI bits
        if self.current_icon:
            self.current_icon.deleteLater()
        self.drag_pixmap = pm
        self.current_icon = QLabel(self)
        self.current_icon.setPixmap(pm)
        self.current_icon.setFixedSize(pm.size())
        self.current_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    
        self.is_dragging = True
        self.ui.graphicsView.setInteractive(False)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        self._apply_interactivity_to_all(False)
    
        # ensure cursor persists after the context menu closes
        QTimer.singleShot(0, lambda: self.set_drawing_cursor(True, pm))
    
    def _show_warning(self, title, message):
        """Show a standardized warning message box."""
        return QMessageBox.warning(self, title, message, QMessageBox.Ok)
    
    def _show_question(self, title, message, default_button=QMessageBox.No):
        """Show a standardized question message box."""
        return QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            default_button
        )
    
    def _show_no_background_warning(self):
        """Show the standard 'no background' warning."""
        self._show_warning("No background", "Drop onto the background image area.")

    def _placeholder_function(self):
        print("joke's on you, this does nothing")
    # %% General drawing
    def _is_near(self, x1: float, y1: float, x2: float, y2: float, epsilon: float) -> bool:
        """Check if two points are within epsilon distance of each other."""
        return abs(x1 - x2) <= epsilon and abs(y1 - y2) <= epsilon

    def _snap_to_item_center(self, x_img: int, y_img: int,
                         item: QGraphicsItem,
                         radius: float = 10.0) -> tuple[int, int, bool]:
        """
        If (x_img, y_img) is within `radius` px (image coords) of the given item's center,
        snap to it. Returns (sx, sy, snapped_flag).
    
        Works with any QGraphicsItem placed on the scene that maps to image coords.
        """
        if not item or self.bg_item is None:
            return x_img, y_img, False
    
        # Get bounding box in image coords
        # We assume x_img, y_img passed in are in *image coords* already.
        scene_pos = item.scenePos()
        img_pos = self.bg_item.mapFromScene(scene_pos)
        brect = item.boundingRect()
        cx_img = img_pos.x() + brect.width() / 2.0
        cy_img = img_pos.y() + brect.height() / 2.0
    
        if self._is_near(x_img, y_img, cx_img, cy_img, radius):
            return int(round(cx_img)), int(round(cy_img)), True
    
        return x_img, y_img, False

    # %% Edge drawing  
    # ==== small shared helpers ================================================
    def clear_vertex_handles(self):
        """Remove all vertex editing handles from the scene."""
        for item in self.vertex_handle_items:
            if hasattr(item, 'scene') and item.scene() is not None:
                self.scene.removeItem(item)
        self.vertex_handle_items.clear()
        
    def create_vertex_handles(self, vertex_type, points, city=None):
        """Create vertex handles for editing trade routes or empire borders."""
        self.clear_vertex_handles()
        
        if not points or not self.bg_item:
            return
        
        handle_size = 8
        half = handle_size / 2.0
        
        for i, (x, y) in enumerate(points):
            scene_pos = self.bg_item.mapToScene(x, y)
            
            # Create blue square handle
            handle = self.scene.addRect(
                scene_pos.x() - half, scene_pos.y() - half, 
                handle_size, handle_size,
                QPen(Qt.blue, 1), QBrush(Qt.blue)
            )
            handle.setZValue(140)  # Above everything else
            handle.setFlag(QGraphicsItem.ItemIsSelectable, True)
            handle.setCursor(Qt.PointingHandCursor)
            
            # Store data for vertex editing
            handle.setData(Qt.UserRole, "VERTEX_HANDLE")
            handle.setData(Qt.UserRole + 1, vertex_type)  # "TRADE_ROUTE" or "EMPIRE_BORDER"
            handle.setData(Qt.UserRole + 2, i)  # Vertex index
            if city:
                handle.setData(Qt.UserRole + 3, city)  # City object for trade routes
                
            self.vertex_handle_items.append(handle)

    def start_vertex_editing(self, handle_item):
        """Start editing a vertex by making it stick to the mouse."""
        if self.vertex_editing_active:
            return  # Already editing
            
        vertex_type = handle_item.data(Qt.UserRole + 1)
        vertex_index = handle_item.data(Qt.UserRole + 2)
        city = handle_item.data(Qt.UserRole + 3)  # May be None for borders
        
        self.vertex_editing_active = True
        self.editing_vertex_type = vertex_type
        self.editing_vertex_index = vertex_index
        self.editing_vertex_city = city
        self.editing_vertex_handle = handle_item
        
        # Visual feedback - make handle yellow while editing
        handle_item.setBrush(QBrush(Qt.yellow))
        
        # Disable view interaction during editing
        self.ui.graphicsView.setInteractive(False)

    def update_vertex_position(self, scene_pos):
        """Update vertex position during dragging."""
        if not self.vertex_editing_active or not self.editing_vertex_handle:
            return
            
        # Move the handle to follow the mouse
        handle_size = 8
        half = handle_size / 2.0
        rect = self.editing_vertex_handle.rect()
        rect.moveCenter(scene_pos)
        self.editing_vertex_handle.setRect(rect)

    def finish_vertex_editing(self, scene_pos):
        """Finish vertex editing and save changes."""
        if not self.vertex_editing_active:
            return
            
        # Convert scene position to image coordinates
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self.cancel_vertex_editing()
            return
            
        x, y = xy
        
        # Update the underlying data
        if self.editing_vertex_type == "TRADE_ROUTE" and self.editing_vertex_city:
            city = self.editing_vertex_city
            if (city.trade_route and city.trade_route.trade_points and 
                0 <= self.editing_vertex_index < len(city.trade_route.trade_points)):
                # Update the trade point
                city.trade_route.trade_points[self.editing_vertex_index].x = int(x)
                city.trade_route.trade_points[self.editing_vertex_index].y = int(y)
                # Re-render the trade route
                self.render_trade_route(city)
                # Recreate vertex handles with new positions
                pts = [(p.x, p.y) for p in city.trade_route.trade_points]
                self.create_vertex_handles("TRADE_ROUTE", pts, city)
                
        elif self.editing_vertex_type == "EMPIRE_BORDER":
            empire = self.state.current_empire_object
            if (empire and empire.border and empire.border.edges and 
                0 <= self.editing_vertex_index < len(empire.border.edges)):
                # Update the border edge
                empire.border.edges[self.editing_vertex_index].x = int(x)
                empire.border.edges[self.editing_vertex_index].y = int(y)
                # Re-render the empire border
                self.render_empire_border()
                # Recreate vertex handles with new positions
                pts = [(edge.x, edge.y) for edge in empire.border.edges]
                self.create_vertex_handles("EMPIRE_BORDER", pts)
        
        # Reset editing state
        self.vertex_editing_active = False
        self.editing_vertex_type = None
        self.editing_vertex_index = None
        self.editing_vertex_city = None
        self.editing_vertex_handle = None
        self.ui.graphicsView.setInteractive(True)

    def cancel_vertex_editing(self):
        """Cancel vertex editing without saving changes."""
        if not self.vertex_editing_active:
            return
            
        # Restore original handle color
        if self.editing_vertex_handle:
            self.editing_vertex_handle.setBrush(QBrush(Qt.blue))
        
        # Reset editing state
        self.vertex_editing_active = False
        self.editing_vertex_type = None
        self.editing_vertex_index = None
        self.editing_vertex_city = None
        self.editing_vertex_handle = None
        self.ui.graphicsView.setInteractive(True)
        
    def _trade_update_temp_line(self, cursor_scene_pos):
        if not self.trade_drawing_active or self.trade_temp_line_item is None or not self.trade_drawing_points or self.bg_item is None:
            return
        last_x, last_y = self.trade_drawing_points[-1]
        p0 = self.bg_item.mapToScene(last_x, last_y)
        line = self.trade_temp_line_item.line()
        line.setP1(p0)
        line.setP2(cursor_scene_pos)
        self.trade_temp_line_item.setLine(line)
        
        # Ensure cursor stays active during drawing - more aggressive approach
        if self.trade_drawing_active:
            self.set_drawing_cursor(True)
    
    def _trade_create_temp_line(self):
        if not self.trade_drawing_points or self.bg_item is None:
            return
        last_x, last_y = self.trade_drawing_points[-1]
        p0 = self.bg_item.mapToScene(last_x, last_y)
        pen = QPen(QColor(255, 140, 0) if self.trade_is_land else Qt.cyan, 2)  # Dark orange for land routes
        if self.trade_temp_line_item is None:
            self.trade_temp_line_item = self.scene.addLine(p0.x(), p0.y(), p0.x(), p0.y(), pen)
            self.trade_temp_line_item.setZValue(100)
        else:
            self.trade_temp_line_item.setLine(p0.x(), p0.y(), p0.x(), p0.y())
    
    def _trade_append_point(self, x_img: int, y_img: int, make_segment: bool = True):
        if self.bg_item is None:
            return
        self.trade_drawing_points.append((x_img, y_img))
    
        # small visual marker while drawing (reuse a tiny ellipse; final render uses dot sprites)
        p = self.bg_item.mapToScene(x_img, y_img)
        dot_rect = (p.x() - 2, p.y() - 2, 4, 4)
        dot_item = self.scene.addEllipse(*dot_rect, QPen(Qt.NoPen),
                                         QBrush(QColor(255, 140, 0) if self.trade_is_land else Qt.cyan))  # Dark orange for land routes
        dot_item.setZValue(90)
        self.trade_drawing_point_items.append(dot_item)
    
        if make_segment and len(self.trade_drawing_points) >= 2:
            x0, y0 = self.trade_drawing_points[-2]
            p0 = self.bg_item.mapToScene(x0, y0)
            pen = QPen(QColor(255, 140, 0) if self.trade_is_land else Qt.cyan, 2)  # Dark orange for land routes
            line_item = self.scene.addLine(p0.x(), p0.y(), p.x(), p.y(), pen)
            line_item.setZValue(80)
            self.trade_drawing_line_items.append(line_item)
    
        self._trade_create_temp_line()
    def _trade_undo_last_point(self):
        """Remove the last trade point and its visual elements."""
        if not self.trade_drawing_points:
            return
        
        # Remove last point from data
        self.trade_drawing_points.pop()
        
        # Remove visual dot
        if self.trade_drawing_point_items:
            dot_item = self.trade_drawing_point_items.pop()
            self.scene.removeItem(dot_item)
        
        # Remove visual line
        if self.trade_drawing_line_items:
            line_item = self.trade_drawing_line_items.pop()
            self.scene.removeItem(line_item)
        
        # Update temp line origin
        self._trade_create_temp_line()
    def _trade_hit_existing_point(self, x_img: int, y_img: int):
        eps = self.edge_hit_epsilon  # reuse your epsilon
        for idx, (px, py) in enumerate(self.trade_drawing_points):
            if abs(px - x_img) <= eps and abs(py - y_img) <= eps:
                return idx
        return -1
    def _finalize_trade_route(self, success: bool, reopen_dialog: bool = False):
        """Finalize the current trade route drawing."""
        city = self.trade_route_city
        
        if success and len(self.trade_drawing_points) >= 2 and city:
            # Save to model
            pts = [ed.TradePoint(x=int(x), y=int(y)) for (x, y) in self.trade_drawing_points]
            ttype = ed.TradeRouteType.LAND if self.trade_is_land else ed.TradeRouteType.SEA
            
            if city.trade_route is None:
                city.trade_route = ed.TradeRoute(cost=500, type=ttype, trade_points=pts)
            else:
                city.trade_route.type = ttype
                city.trade_route.trade_points = pts
            
            # Clear temporary drawing visuals
            self._abort_trade_drawing()
            
            # Render permanent visuals
            self.render_trade_route(city)
        else:
            # Just abort the drawing session
            self._abort_trade_drawing()
    
        self.ui.graphicsView.setInteractive(True)
        
        if reopen_dialog and city:
            QTimer.singleShot(100, lambda: self._edit_city(city))
    
    def _abort_trade_drawing(self):
        """Abort current trade route drawing session (temporary visuals only)."""
        # Remove temporary drawing visuals
        if self.trade_temp_line_item:
            self.scene.removeItem(self.trade_temp_line_item)
            self.trade_temp_line_item = None
            
        for item in self.trade_drawing_line_items:
            self.scene.removeItem(item)
        for item in self.trade_drawing_point_items:
            self.scene.removeItem(item)
        
        # Clear temporary drawing state
        self.trade_drawing_line_items.clear()
        self.trade_drawing_point_items.clear()
        self.trade_drawing_points = []
        self.trade_drawing_active = False
        self.trade_route_city = None
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)

    def _img_to_scene(self, x: float, y: float):
        return self.bg_item.mapToScene(x, y) if self.bg_item else None
    
    def _reset_group(self, bucket: dict, key, z: float):
        """Remove existing group for key and create a fresh one."""
        old = bucket.pop(key, None)
        if old is not None:
            self.scene.removeItem(old)
        group = QGraphicsItemGroup()
        group.setZValue(z)
        self.scene.addItem(group)
        bucket[key] = group
        return group
    
    def _place_pixmap(self, x: float, y: float, pm: QPixmap, z: float, group: QGraphicsItemGroup | None = None,
                      center: bool = True, data: dict | None = None, cursor=Qt.ArrowCursor,
                      item_cls=QGraphicsPixmapItem):
        """Place a pixmap at image coords (x,y) mapped to scene, return the item."""
        if self.bg_item is None or pm is None or pm.isNull():
            return None
        p = self._img_to_scene(x, y)
        it = item_cls(pm)
        if center:
            it.setOffset(-pm.width() / 2.0, -pm.height() / 2.0)
        it.setPos(p)
        it.setZValue(z)
        it.setCursor(cursor)
        if data:
            for role, val in data.items():
                it.setData(role, val)
        if group is not None:
            group.addToGroup(it)
        else:
            self.scene.addItem(it)
        return it
    
    def _place_dot(self, x: float, y: float, r: float, brush: QBrush, z: float,
                   group: QGraphicsItemGroup | None = None):
        """Place a filled circle at image coords; return the item."""
        if self.bg_item is None:
            return None
        p = self._img_to_scene(x, y)
        it = self.scene.addEllipse(p.x()-r, p.y()-r, 2*r, 2*r, QPen(Qt.NoPen), brush)
        it.setZValue(z)
        if group is not None:
            group.addToGroup(it)
        return it
    
    def _place_line(self, x0: float, y0: float, x1: float, y1: float, pen: QPen, z: float,
                    group: QGraphicsItemGroup | None = None):
        """Place a line between image coords; return the item."""
        if self.bg_item is None:
            return None
        p0 = self._img_to_scene(x0, y0)
        p1 = self._img_to_scene(x1, y1)
        it = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
        it.setZValue(z)
        if group is not None:
            group.addToGroup(it)
        return it
    
    def _stamp_along_segment(self, x0: float, y0: float, x1: float, y1: float, spacing: float,
                             place_cb, include_start=True, include_end=True):
        """Call place_cb(x, y) along one segment with uniform spacing."""
        dx, dy = (x1 - x0), (y1 - y0)
        seg_len = (dx*dx + dy*dy) ** 0.5
        if seg_len <= 1e-6:
            if include_start and include_end:
                place_cb(x0, y0)  # degenerate
            return
        ux, uy = dx / seg_len, dy / seg_len
        if include_start:
            place_cb(x0, y0)
        dist = spacing
        # center-to-center spacing; stop just before end, end handled by include_end
        while dist < seg_len - 1e-6:
            place_cb(x0 + ux*dist, y0 + uy*dist)
            dist += spacing
        if include_end:
            place_cb(x1, y1)
    
    def _stamp_along_polyline(self, pts: list[tuple[float, float]], spacing: float, place_cb,
                              include_ends=True):
        """Stamp along a whole polyline."""
        if not pts:
            return
        if len(pts) == 1:
            if include_ends:
                place_cb(pts[0][0], pts[0][1])
            return
        # first point stamped by the first segment when include_ends=True
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i+1]
            self._stamp_along_segment(x0, y0, x1, y1, spacing, place_cb,
                                      include_start=(include_ends and i == 0),
                                      include_end=(include_ends or i < len(pts)-2))
    
    def _get_trade_dot_pixmap(self, is_land: bool) -> QPixmap:
        """Get the appropriate dot pixmap for trade routes."""
        key = "land_dot" if is_land else "sea_dot"
        pil = self.state.images.get(key)       
        pm = self.pil_to_qpixmap(pil)
        pm.setDevicePixelRatio(1.0)
        return pm
        
    def _get_empire_edge_pixmap(self) -> QPixmap:
        """Get the empire edge pixmap for border rendering."""
        for el in getattr(self.state, "elements", []):
            if el["kind"] == EmpObjTypes.EMPIRE_EDGE:
                return self.pil_to_qpixmap(el["pil"])
        return QPixmap()
    
    # ==== trade route rendering (uses shared stamping) =========================
    
    def clear_trade_route_visuals(self, city_index: int):
        """Remove visual elements for a specific city's trade route."""
        # Clear selection if this route is selected
        if (self.trade_route_selected and 
            self.selected_trade_route_city and 
            self._get_city_index(self.selected_trade_route_city) == city_index):
            self.clear_trade_route_selection_overlay()
        
        # Remove the group and all its items
        if city_index in self._trade_route_groups:
            group = self._trade_route_groups[city_index]
            if group.scene() is not None:  # Defensive check
                self.scene.removeItem(group)
            del self._trade_route_groups[city_index]
            
        # Remove hit items for this city's trade route - more robust cleanup
        items_to_remove = []
        for item in self.trade_route_hit_items:
            if hasattr(item, 'data') and callable(item.data) and item.data(Qt.UserRole + 1) == city_index:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.trade_route_hit_items.remove(item)
            # Items are already removed with the group, no need to remove from scene again

    def clear_all_trade_route_visuals(self):
        """Remove all permanent trade route visuals."""
        for group in self._trade_route_groups.values():
            self.scene.removeItem(group)
        self._trade_route_groups.clear()
        
        # Clear all hit items
        self.trade_route_hit_items.clear()
        
        # Clear selection if any trade route is selected
        if self.trade_route_selected:
            self.clear_trade_route_selection_overlay()

    def clear_trade_route_selection_overlay(self):
        """Remove trade route selection visuals (dotted lines and white squares)."""
        self._clear_selection_overlay("trade_route")

    def select_trade_route_overlay(self, city):
        """Show selection overlay for a trade route (dotted lines + white squares)."""
        if not city or not city.trade_route or not city.trade_route.trade_points or len(city.trade_route.trade_points) < 2:
            return
        
        # Ensure background item exists before proceeding
        if self.bg_item is None:
            return
            
        self.clear_trade_route_selection_overlay()
        
        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
        
        # Draw dotted outline for each segment
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            p0 = self.bg_item.mapToScene(x0, y0)
            p1 = self.bg_item.mapToScene(x1, y1)
            
            pen = QPen(QColor(255, 140, 0) if city.trade_route.type == ed.TradeRouteType.LAND else Qt.cyan, 2)
            pen.setStyle(Qt.DotLine)
            
            seg = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
            seg.setZValue(120)  # Above everything else
            self.trade_route_sel_line_items.append(seg)
        
        # Add white square handles at vertices
        handle_size = 6
        half = handle_size / 2.0
        hpen = QPen(Qt.black, 1)
        hbrush = QBrush(Qt.white)
        for x, y in pts:
            p = self.bg_item.mapToScene(x, y)
            rect = self.scene.addRect(p.x() - half, p.y() - half, handle_size, handle_size, hpen, hbrush)
            rect.setZValue(130)  # Above dotted lines
            self.trade_route_sel_handle_items.append(rect)
        
        self.trade_route_selected = True
        self.selected_trade_route_city = city
        
    def render_trade_route(self, city):
        """Render permanent trade route visuals for a specific city."""
        city_index = self._get_city_index(city)
        if city_index is None:
            return
            
        # Clear existing visuals for this city
        self.clear_trade_route_visuals(city_index)
        
        if not city.trade_route or not city.trade_route.trade_points or len(city.trade_route.trade_points) < 2:
            return
            
        # Create new group for this city's trade route
        group = QGraphicsItemGroup()
        group.setZValue(5)  # Below city pixmaps (which use Z=10)
        self.scene.addItem(group)
        self._trade_route_groups[city_index] = group
        
        # Render the route
        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
        is_land = (city.trade_route.type == ed.TradeRouteType.LAND)
        dot_pm = self._get_trade_dot_pixmap(is_land)
        
        if not dot_pm.isNull():
            def place_trade_dot(x, y):
                self._place_pixmap(x, y, dot_pm, z=5, group=group, center=True)
            self._stamp_along_polyline(pts, spacing=7.0, place_cb=place_trade_dot, include_ends=True)
        
        # Add invisible hit areas for each segment (similar to border)
        for i in range(len(pts) - 1):
            p0 = self._img_to_scene(pts[i][0], pts[i][1])
            p1 = self._img_to_scene(pts[i+1][0], pts[i+1][1])
            hit = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
            hit.setPen(QPen(Qt.transparent, 12))  # Wide invisible hit area
            hit.setZValue(6)  # Above trade dots but below selection
            hit.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hit.setData(Qt.UserRole, "TRADE_ROUTE")  # Mark as trade route
            hit.setData(Qt.UserRole + 1, city_index)  # Store city index
            hit.setData(Qt.UserRole + 2, i)  # Store segment index
            group.addToGroup(hit)
            self.trade_route_hit_items.append(hit)
    # ==== edge/border drawing (temp) ===========================================
    
    def _begin_edge_drawing(self, x_img: int, y_img: int):
        """Start edge drawing mode by clearing any existing state and adding the first point."""
        # Clear any leftovers and (re)start state
        self._edge_abort(erase=True)
        self.edge_points_img = []
        self.edge_point_items = []
        self.edge_line_items = []
        self.edge_temp_line_item = None
        self.edge_drawing_active = True
        
        # Set the drawing cursor immediately when edge drawing begins
        self.set_drawing_cursor(True)
        
        # first point (no segment yet)
        self._edge_append_point(x_img, y_img, make_segment=False)
    
    def _edge_update_temp_line(self, cursor_scene_pos=None):
        """Create/update the rubber-band line from the last point to the cursor."""
        if not (self.edge_drawing_active and self.edge_points_img and self.bg_item):
            return
        
        last_x, last_y = self.edge_points_img[-1]
        p_last = self._img_to_scene(last_x, last_y)
        
        if p_last is None:
            return  # Invalid coordinate conversion
            
        if self.edge_temp_line_item is None:
            self.edge_temp_line_item = self.scene.addLine(
                p_last.x(), p_last.y(), p_last.x(), p_last.y(), QPen(Qt.red, 2)
            )
            self.edge_temp_line_item.setZValue(100)
            
        if cursor_scene_pos is None:
            self.edge_temp_line_item.setLine(p_last.x(), p_last.y(), p_last.x(), p_last.y())
        else:
            self.edge_temp_line_item.setLine(
                p_last.x(), p_last.y(), cursor_scene_pos.x(), cursor_scene_pos.y()
            )
            
        # Ensure cursor stays active during drawing
        if self.edge_drawing_active:
            self.set_drawing_cursor(True)

    def _edge_append_point(self, x_img: int, y_img: int, make_segment: bool = True):
        """Append a point, draw its red dot, and optionally the connecting segment."""
        if self.bg_item is None:
            return
            
        # Prevent duplicate consecutive points
        if self.edge_points_img and self.edge_points_img[-1] == (x_img, y_img):
            return

        self.edge_points_img.append((x_img, y_img))

        # red vertex dot
        dot_item = self._place_dot(x_img, y_img, r=5.0, brush=QBrush(Qt.red), z=90)
        if dot_item:
            self.edge_point_items.append(dot_item)

        # segment to previous point
        if make_segment and len(self.edge_points_img) >= 2:
            x0, y0 = self.edge_points_img[-2]
            line_item = self._place_line(x0, y0, x_img, y_img, pen=QPen(Qt.red, 2), z=80)
            if line_item:
                self.edge_line_items.append(line_item)

        # rubber-band should originate from the newest point
        self._edge_update_temp_line()
        
    def _edge_hit_existing_point(self, x_img: int, y_img: int) -> int | None:
        """Check if (x_img, y_img) is close to any existing point. Return the index or None."""
        eps = self.edge_hit_epsilon
        for idx, (px, py) in enumerate(self.edge_points_img):
            if abs(px - x_img) <= eps and abs(py - y_img) <= eps:
                return idx
        return None
        
    def _edge_prompt_incomplete(self):
        """Handle incomplete border: offer to save, discard, or continue drawing."""
        if not self.edge_points_img:
            # Nothing to do - just abort
            self._edge_abort(erase=True)
            return

        resp = QMessageBox.warning(
            self,
            "Incomplete Border",
            "You have not closed the border shape. Would you like to save this border shape?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        
        if resp == QMessageBox.Yes:
            # Save as is, closing back to the first point
            self._finalize_edge(success=True, close_to_index=0)
        elif resp == QMessageBox.No:
            # Erase and cancel
            self._edge_abort(erase=True)
        # Cancel -> continue drawing (do nothing)
        
    def _finalize_edge(self, success: bool, close_to_index: int | None = None):
        """Finalize the edge drawing by saving to model and rendering permanent border."""
        if not success or len(self.edge_points_img) < 2:
            self._edge_abort(erase=True)
            self.empire_border = False
            return

        pts = list(self.edge_points_img)

        # If we know which vertex we clicked to close, draw the closing segment visually
        if close_to_index is not None and self.bg_item is not None:
            x_last, y_last = pts[-1]
            x_close, y_close = pts[close_to_index]
            close_item = self._place_line(x_last, y_last, x_close, y_close, QPen(Qt.red, 2), 80)
            if close_item:
                self.edge_line_items.append(close_item)
                
            # Rotate so the first vertex becomes the clicked/closed one (canonical order)
            if close_to_index != 0:
                pts = pts[close_to_index:] + pts[:close_to_index]

        # Clean consecutive duplicates (defensive)
        cleaned = []
        for x, y in pts:
            if not cleaned or cleaned[-1] != (x, y):
                cleaned.append((x, y))

        # Save to model with default density=28
        self._save_border_shape(cleaned, density=28)

        # Erase temporary red dots/lines and stop drawing mode
        self._edge_abort(erase=True)

        # Mark border present and render the permanent overlay
        self.empire_border = True
        self.render_empire_border()
        
    def _save_border_shape(self, points_img_xy: list[tuple[int, int]], density: int = 28):
        """Persist the border polyline to the model as ed.Border with ed.Edge entries."""
        empire = self.state.current_empire_object
        if empire is None:
            return

        try:
            edges = [ed.Edge(x=int(x), y=int(y), hidden=False) for (x, y) in points_img_xy]
            border_obj = ed.Border(density=int(density), edges=edges)
            empire.border = border_obj  # single border only
        except Exception:
            # Fallback if dataclasses not available for some reason
            border_obj = type("Border", (), {})()
            border_obj.density = int(density)
            border_obj.edges = [type("Edge", (), {"x": int(x), "y": int(y), "hidden": False})() for (x, y) in points_img_xy]
            empire.border = border_obj
    
    def _edge_abort(self, erase: bool):
        """Stop drawing; optionally erase temp items; always reset cursor consistently."""
        if self.edge_temp_line_item is not None:
            self.scene.removeItem(self.edge_temp_line_item)
            self.edge_temp_line_item = None
    
        if erase:
            for it in self.edge_line_items:
                self.scene.removeItem(it)
            for it in self.edge_point_items:
                self.scene.removeItem(it)
    
        self.edge_line_items.clear()
        self.edge_point_items.clear()
        self.edge_points_img = []
        self.edge_drawing_active = False
        self.set_drawing_cursor(False)
    
    # ==== trade route start (cursor now uses shared setter) ====================
    
    def start_trade_route(self, city):
        """Start drawing a trade route for a specific city."""
        if self.bg_item is None:
            self._show_no_background_warning()
            return

        # Clear any existing drawing session
        self._abort_trade_drawing()
        
        # Set up new drawing session
        self.trade_drawing_active = True
        self.trade_is_land = bool(city.trade_route and city.trade_route.type == ed.TradeRouteType.LAND)
        self.trade_route_city = city
        self.trade_drawing_points = []
        self.trade_drawing_point_items = []
        self.trade_drawing_line_items = []
        self.trade_temp_line_item = None
        
        self.ui.graphicsView.setInteractive(False)
        self.set_drawing_cursor(True)

    
    # ==== border rendering (uses the same stamping helpers) ====================
    
    def render_empire_border(self):
        if not self.empire_border:
            return
        e = self.state.current_empire_object
        if e is None or getattr(e, "border", None) is None or self.bg_item is None:
            return
    
        pts = [(edge.x, edge.y) for edge in getattr(e.border, "edges", [])]
        if len(pts) < 2:
            return
    
        hidden = [bool(getattr(edg, "hidden", False)) for edg in e.border.edges]
        density = getattr(e.border, "density", 28) or 28
        icon_pm = self._get_empire_edge_pixmap()
        if icon_pm.isNull():
            return
    
        # clear previous visuals
        self.clear_border_selection_overlay()
        self.clear_empire_border_visual()
        self.border_edge_hit_items.clear()
    
        # group for everything
        self.border_visual_group = QGraphicsItemGroup()
        self.border_visual_group.setZValue(75)
        self.scene.addItem(self.border_visual_group)

        def place_flag_icon(x_img: int, y_img: int):
            it = self._place_pixmap(
                x_img, y_img, icon_pm, z=75, group=self.border_visual_group, center=True
            )
            if it:
                it.setFlag(QGraphicsPixmapItem.ItemIsSelectable, False)
                it.setAcceptHoverEvents(False)
                it.setCursor(Qt.ArrowCursor)
                it.setData(Qt.UserRole, EmpObjTypes.EMPIRE_EDGE)
                self.border_icon_items.append(it)
    
        def place_blue_vertex(i: int):
            self._place_dot(pts[i][0], pts[i][1], r=5.0, brush=QBrush(Qt.blue), z=85,
                            group=self.border_visual_group)
    
        n = len(pts)
        # selectable hit-lines and stamping/blue-dots per segment
        for i in range(n):
            j = (i + 1) % n
            # fat invisible selectable hit
            p0 = self._img_to_scene(pts[i][0], pts[i][1])
            p1 = self._img_to_scene(pts[j][0], pts[j][1])
            hit = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
            hit.setPen(QPen(Qt.transparent, 12))
            hit.setZValue(76)
            hit.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hit.setData(Qt.UserRole, EmpObjTypes.EMPIRE_EDGE)
            hit.setData(Qt.UserRole + 1, i)  # edge index
            self.border_visual_group.addToGroup(hit)
            self.border_edge_hit_items.append(hit)
    
            if hidden[i]:
                place_blue_vertex(i)
                continue
    
            # stamp flags along this visible segment using the shared segment stamper
            self._stamp_along_segment(
                pts[i][0], pts[i][1], pts[j][0], pts[j][1],
                spacing=density, place_cb=lambda x, y: place_flag_icon(int(round(x)), int(round(y))),
                include_start=True, include_end=True
            )
        return
    
    def delete_empire_border(self, force = False):
        """Delete the empire border with optional confirmation."""
        if not force:
            resp = QMessageBox.question(
                self,
                "Delete Border",
                "Are you sure you want to delete the empire border?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return
        
        # Clear from model
        empire = self.state.current_empire_object
        if empire:
            empire.border = None
        
        # Clear visuals
        self.clear_empire_border_visual()
        self.empire_border = False
        
    def toggle_edge_hidden_from_item(self, item):
        """Toggle the hidden state of an edge segment."""
        empire = self.state.current_empire_object
        if not (empire and getattr(empire, "border", None)):
            return
        
        edge_index = item.data(Qt.UserRole + 1)  # stored during render
        if edge_index is None:
            return
            

        edges = empire.border.edges
        if 0 <= edge_index < len(edges):
            edges[edge_index].hidden = not bool(getattr(edges[edge_index], "hidden", False))
            self.render_empire_border()
        
        
    def handle_drop_empire_edge(self, scene_pos):
        # If we already have a border, ask first
        if self.empire_border and getattr(self.state.current_empire_object, "border", None):
            resp = QMessageBox.question(
                self,
                "Start New Border?",
                "An empire border already exists. Start a new one and discard the current border?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return
            # erase model + visuals
            self.delete_empire_border(force = True)
    
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self._show_no_background_warning()
            return
        x, y = xy
        
        if not self.state.check_if_empire():
            self.state.new_empire()

        # Start edge drawing immediately
        self._begin_edge_drawing(x, y)

# %% Everything else
    def _edit_city(self, city_obj):

        snapshot = copy.deepcopy(city_obj)

        dlg = emp_dlg.CityPropertiesDialog(city_obj, self)
        result = None
        try:
            result = dlg.exec()
        finally:
            dlg.deleteLater()  # deleted when control returns to the main event loop
        if result != QDialog.Accepted:
            return  # cancel -> no changes
        if dlg.requested_route_draw:
            #self._apply_drawing_cursor(True)
            #self.is_dragging = False #cancel dragging
            if city_obj.trade_route and len(city_obj.trade_route.trade_points) > 0:
                result = QMessageBox.warning(
                    self, "Trade Route already exists",
                    "There is already a trade route plotted for this city. Would you like to remove it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if result == QMessageBox.No:
                    QTimer.singleShot(100, lambda: self._edit_city(city_obj))
                    return
                else:
                    # Clear both model and visuals for this specific city
                    city_index = self._get_city_index(city_obj)
                    if city_index is not None:
                        self.clear_trade_route_visuals(city_index)
                    city_obj.trade_route.trade_points = []
            self.start_trade_route(city_obj)
            self.return_to_dialog = True
            return
            
        # Check if city type changed from trade to non-trade
        old_type = getattr(snapshot, "type", None)
        new_type = getattr(city_obj, "type", None)
        
        # If city type changed from trade to non-trade, remove trade route
        if (old_type in (getattr(ed.CityType, "TRADE", None), getattr(ed.CityType, "ROMAN", None), getattr(ed.CityType, "VULNERABLE", None)) and
            new_type not in (getattr(ed.CityType, "TRADE", None), getattr(ed.CityType, "ROMAN", None), getattr(ed.CityType, "VULNERABLE", None), ed.CityType.OURS)):
            # Clear trade route for non-trade cities
            city_index = self._get_city_index(city_obj)
            if city_index is not None:
                self.clear_trade_route_visuals(city_index)
            if city_obj.trade_route:
                city_obj.trade_route.trade_points = []
        
        # validations
        if city_obj.type == ed.CityType.OURS: #TODO: replace this by normal property check, not getattr
            has_ours, ours = self.state.has_our_city()
            if has_ours and ours is not city_obj:
                QMessageBox.warning(
                    self, "Duplicate 'Our City'",
                    "There is already an 'Our City'. Remove it first.", QMessageBox.Ok
                )
                # revert and reopen
                city_obj.__dict__.clear()
                city_obj.__dict__.update(copy.deepcopy(snapshot.__dict__))
                return  # Exit early after revert

        # Check if trade route type changed and re-render if needed
        old_route_type = getattr(snapshot.trade_route, "type", None) if snapshot.trade_route else None
        new_route_type = getattr(city_obj.trade_route, "type", None) if city_obj.trade_route else None
        
        if old_route_type != new_route_type and city_obj.trade_route and city_obj.trade_route.trade_points:
            # Re-render trade route with new type colors
            self.render_trade_route(city_obj)

        # valid -> update visuals
        if not self.trade_drawing_active:
            key = id(city_obj)
            if key in self.city_items:
                it = self.city_items[key]
                it.setPixmap(self._pixmap_for_city(city_obj))
                kind = CITYTYPE_TO_KIND.get(getattr(city_obj, "type", None))
                if kind is not None:
                    it.setData(Qt.UserRole, kind)
                else:
                    print("save error: kind is none")
   
    # ---------- ROUTER ----------
    def drop_object(self, scene_pos):
        """
        Decide which handler to call based on selected_kind.
        City kinds -> handle_city_drop
        Object kinds -> dedicated handler (e.g., handle_drop_empire_edge)
        """
        kind = getattr(self, "selected_kind", None)
        if kind is None:
            return

        # City types
        if isinstance(kind, EmpCityTypes):
            self.handle_city_drop(scene_pos)
            return

        # Object types
        if isinstance(kind, EmpObjTypes):
            if kind == EmpObjTypes.EMPIRE_EDGE:
                self.handle_drop_empire_edge(scene_pos)
            else:
                print(f"No handler for object kind: {kind}")
            return

        print(f"Unknown kind: {kind}")

    # ---------- DROP HANDLER ----------
    def handle_icon_drop(self, scene_pos):
        # moving existing city?
        if getattr(self, "moving_city", None) is not None:
            xy = self._scene_to_image_xy(scene_pos)
            city = self.moving_city
            self.moving_city = None
            if xy is not None:
                x, y = xy
                self._remove_city_marker(city)
                
                # Store old position for comparison
                old_x, old_y = city.x, city.y
                
                # If this is "Our City", find all trade routes that end at it BEFORE moving
                affected_cities = []
                if city.type == ed.CityType.OURS:
                    empire = self.state.current_empire_object
                    if empire and hasattr(empire, 'cities'):
                        for other_city in empire.cities:
                            if (other_city != city and 
                                other_city.trade_route and 
                                self._trade_route_ends_at_city(other_city.trade_route, city)):
                                affected_cities.append(other_city)
                
                # Now update the city position
                city.x, city.y = x, y
                
                # Update trade route if city has one
                if city.trade_route and city.trade_route.trade_points:
                    # Get new center coordinates
                    center_x, center_y = self._get_city_center(city)
                    
                    # Insert new center point at the beginning of trade route
                    new_point = ed.TradePoint(x=center_x, y=center_y)
                    city.trade_route.trade_points.insert(0, new_point)
                    
                    # Re-render the trade route
                    self.render_trade_route(city)
                
                # Update all affected trade routes that ended at the old Our City position
                if affected_cities:
                    new_center_x, new_center_y = self._get_city_center(city)
                    
                    for other_city in affected_cities:
                        # Add new endpoint to match new Our City position
                        new_endpoint = ed.TradePoint(x=new_center_x, y=new_center_y)
                        other_city.trade_route.trade_points.append(new_endpoint)
                        
                        # Re-render the updated trade route
                        self.render_trade_route(other_city)
                
                self._place_city_marker(city, x, y)
            return
        else:
            # Unified entry point now
            self.drop_object(scene_pos)

    def add_city_icons_to_list(self):
        self.ui.listWidget.clear()
        for el in self.state.elements:
            item = QListWidgetItem(el["name"])
            item.setIcon(QIcon(self.pil_to_qpixmap(el["pil"])))
            item.setSizeHint(QSize(100, 80))
            item.setData(Qt.UserRole, el["kind"])   # store the enum directly (EmpCityTypes or EmpObjTypes)
            self.ui.listWidget.addItem(item)
        self.ui.listWidget.setIconSize(QSize(64, 64))

    def on_map_setting_changed(self, index):
        if self.ui.mapSettingsMenu.currentText() == "Default Empire Map":
            if "The_empire" in self.state.images:
                self.set_background_image(self.state.images["The_empire"])
            else:
                QMessageBox.warning(
                    self, "Missing Map",
                    "The 'Default Empire Map' is not available in the loaded images.",
                    QMessageBox.Ok
                    )
    def _no_bg_item_alive(self):
        # alive iff we have an object AND it still belongs to a scene
        return self.no_bg_item is not None and self.no_bg_item.scene() is not None
    
    def _widget_is_in_dialog(self, obj) -> bool:
        """Return True if the event target is inside a dialog/menu/menubar."""
        w = obj
        while w is not None:
            if isinstance(w, (QDialog, QMenu, QMenuBar)):
                return True
            w = w.parent()
        return False



    def _scene_to_image_xy(self, scene_pos):
        if self.bg_item is None:
            return None
        img_pos = self.bg_item.mapFromScene(scene_pos)
        x, y = int(img_pos.x()), int(img_pos.y())
        pm = self.bg_item.pixmap()
        if 0 <= x < pm.width() and 0 <= y < pm.height():
            return x, y
        return None
    
    def _citytype_and_name_for_kind(self, kind):
        # kind is EmpCityTypes
        if kind == EmpCityTypes.OUR:
            return ed.CityType.OURS, "Our City"
        elif kind == EmpCityTypes.TRADE:
            # handle possible naming differences in your model
            trade_type = getattr(ed.CityType, "TRADE", None) or getattr(ed.CityType, "ROMAN", None)
            return trade_type, "Roman City"
        elif kind == EmpCityTypes.DISTANT:
            return getattr(ed.CityType, "DISTANT", None), "Far away city"
        else:
            return None, "City"
    
    def _pixmap_for_city(self, city) -> QPixmap:
        # 0) If we have a pending drop pixmap, use it EXACTLY
        pm = getattr(self, "pending_drop_pixmap", None)
        if isinstance(pm, QPixmap) and not pm.isNull():
            return pm
    
        # 1) Otherwise, try the currently selected item (if any) — use native pixmap size
        if self.selected_item is not None:
            try:
                icon = self.selected_item.icon()
                sizes = icon.availableSizes()
                if sizes:
                    # pick the largest native size available (still unscaled)
                    nat = max(sizes, key=lambda s: s.width() * s.height())
                    return icon.pixmap(nat)
            except Exception:
                pass
    
        # 2) Fallback by city.type -> EmpCityTypes kind (no scaling)
        kind = None
        ct = getattr(city, "type", None)
        try:
            if ct == ed.CityType.OURS:
                kind = EmpCityTypes.OUR
            elif ct in (
                getattr(ed.CityType, "TRADE", None),
                getattr(ed.CityType, "ROMAN", None),
                getattr(ed.CityType, "VULNERABLE", None),
            ):
                kind = EmpCityTypes.TRADE
            elif ct == getattr(ed.CityType, "DISTANT", None):
                kind = EmpCityTypes.DISTANT
        except Exception:
            kind = None
    
        if kind is None and self.state.elements:
            kind = EmpCityTypes.OUR
    
        for el in getattr(self.state, "elements", []):
            if el["kind"] == kind:
                # keep original image size from your PIL source
                return self.pil_to_qpixmap(el["pil"])
    
        # Ultimate fallback: return a null pixmap (no assumed size)
        return QPixmap()


    def _place_city_marker(self, city, x, y):
        pm = self._pixmap_for_city(city)
        if self.bg_item is None:
            return
        scene_pt = self.bg_item.mapToScene(x, y)
    
        key = id(city)
        if key in self.city_items:
            item = self.city_items[key]
            item.setPixmap(pm)
            item.setOffset(0, 0)      # top-left anchor
            item.setPos(scene_pt)
        else:
            item = QGraphicsPixmapItem(pm)
            item.setZValue(10)
            item.setOffset(0, 0)
            item.setPos(scene_pt)
            item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
            item.setFlag(QGraphicsPixmapItem.ItemIsMovable, False)
            item.setData(0, key)
            item.setData(1, city)
            kind = CITYTYPE_TO_KIND.get(getattr(city, "type", None))
            if kind is not None:
                item.setData(Qt.UserRole, kind)
            self.scene.addItem(item)
            self.city_items[key] = item
    
        # Apply current interactivity state (pointer on hover only when not dragging)
        self._apply_item_interactivity(item, enable=not self.is_dragging)

    def _apply_item_interactivity(self, item, enable: bool):
        item.setAcceptHoverEvents(enable)
        item.setCursor(Qt.PointingHandCursor if enable else Qt.ArrowCursor)
    
    def _apply_interactivity_to_all(self, enable: bool):
        for it in self.city_items.values():
            self._apply_item_interactivity(it, enable)

    def _remove_city_marker(self, city):
        """Remove the scene item for this city, if it exists."""
        key = id(city)
        item = self.city_items.pop(key, None)
        if item is not None:
            self.scene.removeItem(item)
            # let Qt delete C++ object; don't keep stale refs

    def show_no_background_message(self):
        """Show the placeholder text when no background is set."""
        if not self._no_bg_item_alive():
            # if we had a stale pointer (e.g., scene.clear() deleted it), drop it
            self.no_bg_item = None
            self.no_bg_item = self.scene.addText("No Empire background image selected.")
        self.center_no_background_message()
        self.ui.mouse_position_label.setVisible(False)
    
    def remove_no_background_message(self):
        """Remove the placeholder text when a background is set."""
        if self._no_bg_item_alive():
            self.scene.removeItem(self.no_bg_item)
        self.no_bg_item = None  # clear stale reference
        self.ui.mouse_position_label.setVisible(True)
    
    def center_no_background_message(self):
        if not self._no_bg_item_alive():
            return
        view = self.ui.graphicsView
        vp = view.viewport()
        br = self.no_bg_item.boundingRect()
        x = (vp.width() - br.width()) / 2
        y = (vp.height() - br.height()) / 2
        self.no_bg_item.setPos(view.mapToScene(int(x), int(y)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.center_no_background_message()  # now harmless if item was deleted
    
    def set_background_image(self, pil_img):
        # Ask/prepare a new empire first
        if not self._ensure_new_empire_for_new_background():
            return
    
        pixmap = self.pil_to_qpixmap(pil_img)
        self.state.selected_empire_image = pixmap
    
        self.scene.clear()
        self.bg_item = None
        
        # Clear all trade route state when scene is cleared
        self._clear_scene_state()

        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()
        if self.empire_border and getattr(self.state.current_empire_object, "border", None):
            self.render_empire_border()
    
    def on_default_empire_map_selected(self):
        if "The_empire" in self.state.images:
            empire_image = self.state.images["The_empire"]
            if isinstance(empire_image, list):
                empire_image = empire_image[0]

            self.set_background_image(empire_image)
        else:
            QMessageBox.warning(self, "Missing Map",
                                "The 'Default Empire Map' is not available in the loaded images.",
                                QMessageBox.Ok)

    def _clear_scene_state(self):
        """Clear all scene-related state when scene is cleared or reset."""
        # Clear selection state
        self.selected_item = None
        self.selected_kind = None
        self.selected_edge_index = None
        self.selected_trade_route_city = None
        
        # Clear edge drawing state
        self.edge_drawing_active = False
        self.edge_points_img = []
        self.edge_point_items = []
        self.edge_line_items = []
        self.edge_temp_line_item = None
        
        # Clear trade route drawing state
        self.trade_drawing_active = False
        self.trade_drawing_points = []
        self.trade_drawing_point_items = []
        self.trade_drawing_line_items = []
        self.trade_temp_line_item = None
        self.trade_route_city = None
        self.trade_route_selected = False
        self.trade_route_sel_line_items = []
        self.trade_route_sel_handle_items = []
        self.trade_route_hit_items = []
        
        # Clear vertex editing state
        self.vertex_editing_active = False
        self.vertex_handle_items = []
        
        # Clear visual overlays (call the actual clear functions)
        self.clear_border_selection_overlay()
        self.clear_trade_route_selection_overlay()
        # Note: clear_vertex_handles() is called by deselect_all() if needed

    def pil_to_qpixmap(self, pil_img):
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        w, h = pil_img.size
        data = pil_img.tobytes("raw", "RGBA")
        qimg = QImage(data, w, h, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)
    
    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
        )
        if not file_path:
            return
    
        # Ask/prepare a new empire first
        if not self._ensure_new_empire_for_new_background():
            return
    
        pixmap = QPixmap(file_path)
        self.state.selected_empire_image = pixmap
        self.scene.clear()
        
        # Clear all trade route state when scene is cleared
        self._clear_scene_state()
        
        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()
        if self.empire_border and getattr(self.state.current_empire_object, "border", None):
            self.render_empire_border()

    def _ensure_new_empire_for_new_background(self) -> bool:
        """
        Returns True if it's OK to proceed (new empire created or none existed).
        Returns False if the user cancels.
        """
        # If there is data, warn
        if self.state.check_if_empire() and self.state.has_any_data():
            resp = QMessageBox.question(
                self,
                "Create New Empire?",
                "You have unsaved work in the current empire.\n"
                "Create a new one and discard current progress?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return False
    
        # Create a fresh empire (always on new background as requested)
        self.state.new_empire()
        # Clear any old markers
        self.city_items.clear()
        return True
        

    # -------------------------------------------------------
    # New "city" drop handler (generalized), keeps old name too
    # -------------------------------------------------------
    def handle_city_drop(self, scene_pos):
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self._show_no_background_warning()
            return
        x, y = xy

        kind = getattr(self, "selected_kind", None)  # EmpCityTypes.*
        if kind is None or not isinstance(kind, EmpCityTypes):
            return

        # Ensure there's an empire
       
        if not self.state.check_if_empire():
            self.state.new_empire()
        empire = self.state.current_empire_object

        # OUR city: single instance with move-confirmation
        if kind == EmpCityTypes.OUR:
            has_ours, ours = self.state.has_our_city()
            if has_ours:
                resp = QMessageBox.question(
                    self,
                    "Move Our City?",
                    f"Move 'Our City' from ({ours.x}, {ours.y}) to ({x}, {y})?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if resp == QMessageBox.No:
                    return
                self._remove_city_marker(ours)
                ours.x, ours.y = x, y
                self._place_city_marker(ours, x, y)
                return

            ours = ed.City(name="Our City", x=x, y=y, type=ed.CityType.OURS, sells=[])
            empire.cities.append(ours)
            self._place_city_marker(ours, x, y)
            return

        # Other city types: create freely
        ctype, default_name = self._citytype_and_name_for_kind(kind)
        if ctype is None:
            return
        city = ed.City(name=default_name, x=x, y=y, type=ctype, sells=[])
        empire.cities.append(city)
        self._place_city_marker(city, x, y)

    # Back-compat: keep the original name, delegate to new method
    def handle_drop_city(self, scene_pos):
        self.handle_city_drop(scene_pos)

    # -------------------------------------------------------
    # Non-city handler(s)
    # -------------------------------------------------------


    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    # One global filter to observe ALL widgets
    app.installEventFilter(window)
    if not window.init_failed:
        window.show()
        sys.exit(app.exec())
    sys.exit(0)
