import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QApplication, QListWidgetItem, QMessageBox,
    QLabel, QDialog, QWidget, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsItemGroup,  QGraphicsItem,  QMenu, QMenuBar

)
from PySide6.QtGui import QIcon, QPixmap, QImage, QCursor, QPainter, QPen, QBrush, QPainterPath, QAction
from PySide6.QtCore import QSize, QSettings, Qt, QEvent, QObject, QPoint, QRectF, QSizeF, QPointF
from sg_reader import SgFileReader
from ui_empire_editor import Ui_MainWindow
# top of main_window.py (with your other imports)
import empire_data as ed
import edit_city_dialog as emp_dlg
from math import hypot
from enum import Enum, auto

# ---------------------------------------------
# New, separated enums
# ---------------------------------------------
class EmpCityTypes(Enum):
    OUR = auto()
    DISTANT = auto()
    TRADE = auto()

class EmpObjTypes(Enum):
    EMPIRE_EDGE = auto()
    
    
CITYTYPE_TO_KIND = {
ed.CityType.OURS: EmpCityTypes.OUR,
getattr(ed.CityType, "TRADE", getattr(ed.CityType, "ROMAN", None)): EmpCityTypes.TRADE,
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
            bits = self.images["empire_bits"]
            # NOTE: "kind" now holds a value from EmpCityTypes OR EmpObjTypes.
            self.elements = [
                {"name": "Our City",      "pil": bits[0],  "kind": EmpCityTypes.OUR},
                {"name": "Roman City",    "pil": bits[7],  "kind": EmpCityTypes.TRADE},
                {"name": "Far away city", "pil": bits[21], "kind": EmpCityTypes.DISTANT},
                {"name": "Empire edge",   "pil": bits[71], "kind": EmpObjTypes.EMPIRE_EDGE},
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
        self.edge_hit_epsilon = 6                  # pixels in image coords to detect closing click
        self.edge_cursor_pixmap = None             # QPixmap used as cursor during edge drawing
        self.border_edge_hit_items = []   # selectable hit proxies for each segment
        self.selected_edge_index = None   # index i for edge i -> i+1

        # permanent empire border overlay (icon-based)
        self.empire_border = False
        self.border_visual_group = None          # QGraphicsItemGroup for the icon overlay
        self.border_icon_items = []              # QGraphicsPixmapItem[] belonging to the group

        # selection overlay (dotted stroke + square handles)
        self.border_sel_line_items = []      # QGraphicsLineItem[]
        self.border_sel_handle_items = []    # QGraphicsRectItem[]
        self.border_selected = False
        
        self.ui.mouse_position_label.setVisible(False)  # hidden until a map is set
        self.city_items = {}  # maps City -> QGraphicsPixmapItem

        # Data/state
        self.state = ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return

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
            ("Properties", lambda it: self._edit_city(it.data(1))),
            ("Delete City", self._placeholder_function),
            ("Move City", self._placeholder_function),
        ]

        self.context_menu_options = {
            EmpCityTypes.OUR: city_common_menu,
            EmpCityTypes.DISTANT: city_common_menu,
            EmpCityTypes.TRADE: city_common_menu,
            
            EmpObjTypes.EMPIRE_EDGE: [
                ("Toggle Edge Hidden", lambda it: self.toggle_edge_hidden_from_item(it)),
                ("Delete Border", self.delete_empire_border),
            ],
        }
# %% GLOBAL EVENT FILTER
    def eventFilter(self, obj, event):
        et = event.type()
    
        # 1) Always ignore modal dialogs

        if QApplication.activeModalWidget() or QApplication.activePopupWidget():
            return False
        #if self._widget_is_in_dialog(obj): #spare helper, might not be needed
           # return False
        #for tb in self.findChildren(QToolBar): #
           # if tb.isAncestorOf(obj):
               # return False

        # 2) Dispatch by event type
        if et == QEvent.MouseMove:
            return self._handle_mouse_move(event)
    
        elif et in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return self._handle_mouse_click(event)
    
        return QObject.eventFilter(self, obj, event)
    # =========================
    # HELPER HANDLERS
    # =========================

    def _handle_mouse_move(self, event):
        """Mouse move: update label, dragging icon, and edge preview."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        vp_pos = vp.mapFromGlobal(gp)
    
        # Update position label
        if vp.rect().contains(vp_pos):
            scene_pos = view.mapToScene(vp_pos)
            if self.edge_drawing_active:
                self._update_edge_temp_line(scene_pos)
            self._update_mouse_position_label(scene_pos)
    
        # Floating drag icon
        if self.is_dragging and self.current_icon:
            self.current_icon.move(self.mapFromGlobal(gp))
    
        return False  # don't consume
    
    def _handle_mouse_click(self, event):
        """Mouse clicks: route to drag, edge drawing, or selection logic."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        inside_view = vp.rect().contains(vp.mapFromGlobal(gp))
        btn = event.button()
        et = event.type()
    
        # Dragging mode
        if self.is_dragging:
            return self._handle_drag_click(event, gp, inside_view)
    
        # Edge drawing mode
        if self.edge_drawing_active and et == QEvent.MouseButtonPress:
            return self._handle_edge_click(event, gp, inside_view)
    
        # Normal mode selection
        if not self.is_dragging and not self.edge_drawing_active and et == QEvent.MouseButtonPress:
            return self._handle_normal_click(event, gp, inside_view)
    
        return False
    
    
    # =========================
    # SUB-MODE HANDLERS
    # =========================
    
    def _handle_drag_click(self, event, gp, inside_view):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() in (Qt.LeftButton, Qt.RightButton) and not inside_view:
                self.deselect_item()
                return True
        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() in (Qt.LeftButton, Qt.RightButton):
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
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None
    
        # Edge segment (hit proxy)
        if item in self.border_edge_hit_items:
            self.selected_edge_index = item.data(Qt.UserRole + 1)  # i for edge i -> i+1
            self.select_empire_border_overlay()  # keep your selection visuals
            self.selected_item = item
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
        self.set_cursor_to_icon(pixmap)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        
        self._apply_interactivity_to_all(False)

    def deselect_item(self):
        if self.current_icon:
            self.current_icon.deleteLater()
            self.current_icon = None
        # keep self.selected_kind intact so drop handler knows what was chosen
        self.selected_item = None
        self.is_dragging = False
        self.reset_cursor()
        self.ui.graphicsView.setInteractive(True)

        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)  # not ScrollHandDrag
    
        # FIX: also clear the QListWidget’s selection so it’s not visually highlighted
        self.ui.listWidget.clearSelection()
        self._apply_interactivity_to_all(True)
            
    def deselect_all(self):
        self.clear_border_selection_overlay()
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None
        self.selected_edge_index = None

    def clear_border_selection_overlay(self):
        """Remove dotted stroke + handles if present."""
        for it in self.border_sel_line_items:
            self.scene.removeItem(it)
        for it in self.border_sel_handle_items:
            self.scene.removeItem(it)
        self.border_sel_line_items.clear()
        self.border_sel_handle_items.clear()
        self.border_selected = False
        
        
    def remove_city(self, city):
        empire = self.state.current_empire_object
        if empire and city in empire.cities:
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
            # Pass both the scene item and its type to the callback if needed
            act.triggered.connect(lambda checked=False, cb=callback, it=item: cb(it))
            menu.addAction(act)
    
        menu.exec(global_pos)
        
    def _placeholder_function(self):
        print("joke's on you, this does nothing")
# %% Everything else    
    def _edit_city(self, city_obj):
        dlg = emp_dlg.EmpireCityDialog(city_obj, self)
        if dlg.exec() == QDialog.Accepted:
            # re-render marker if visuals depend on type/resources
            key = id(city_obj)
            if key in self.city_items:
                it = self.city_items[key]
                # update icon if type changed
                pm = self._pixmap_for_city(city_obj)
                it.setPixmap(pm)


    def _begin_edge_drawing(self, x_img: int, y_img: int):
        self._edge_clear_scene_items()
        self.edge_points_img = []
        self.edge_drawing_active = True
        self._edge_append_point(x_img, y_img, make_segment=False)  # first point
        self._edge_create_temp_line()                               # rubber-band
    
    
    def _edge_create_temp_line(self):
        if not self.edge_points_img or self.bg_item is None:
            return
        last_x, last_y = self.edge_points_img[-1]
        p0 = self.bg_item.mapToScene(last_x, last_y)
        pen = QPen(Qt.red, 2)
        if self.edge_temp_line_item is None:
            self.edge_temp_line_item = self.scene.addLine(p0.x(), p0.y(), p0.x(), p0.y(), pen)
            self.edge_temp_line_item.setZValue(100)
        else:
            self.edge_temp_line_item.setLine(p0.x(), p0.y(), p0.x(), p0.y())
    
    def _update_edge_temp_line(self, cursor_scene_pos):
        if not self.edge_drawing_active or self.edge_temp_line_item is None or not self.edge_points_img or self.bg_item is None:
            return
        last_x, last_y = self.edge_points_img[-1]
        p0 = self.bg_item.mapToScene(last_x, last_y)
        line = self.edge_temp_line_item.line()
        line.setP1(p0)
        line.setP2(cursor_scene_pos)
        self.edge_temp_line_item.setLine(line)

    
    def _edge_append_point(self, x_img: int, y_img: int, make_segment: bool = True):
        """Append a point to the polyline, place a red dot, and optionally finalize a segment from previous point."""

    
        if self.bg_item is None:
            return
    
        # Add point to model list
        self.edge_points_img.append((x_img, y_img))
    
        # Draw red dot centered at (x_img, y_img), radius 3 px
        p = self.bg_item.mapToScene(x_img, y_img)
        dot_rect = (p.x() - 3, p.y() - 3, 6, 6)
        dot_item = self.scene.addEllipse(*dot_rect, QPen(Qt.NoPen), QBrush(Qt.red))
        dot_item.setZValue(90)
        self.edge_point_items.append(dot_item)
    
        # If we have at least two points and make_segment is True, finalize a line between them
        if make_segment and len(self.edge_points_img) >= 2:
            x0, y0 = self.edge_points_img[-2]
            p0 = self.bg_item.mapToScene(x0, y0)
            pen = QPen(Qt.red, 2)
            line_item = self.scene.addLine(p0.x(), p0.y(), p.x(), p.y(), pen)
            line_item.setZValue(80)
            self.edge_line_items.append(line_item)
    
        # Rubber-band should start from the newest point
        self._edge_create_temp_line()
    
    def _edge_hit_existing_point(self, x_img: int, y_img: int):
        """Return index of an existing point the click hits (within epsilon), else None."""
        eps = self.edge_hit_epsilon
        for idx, (px, py) in enumerate(self.edge_points_img):
            if abs(px - x_img) <= eps and abs(py - y_img) <= eps:
                return idx
        return None
    
    def _edge_prompt_incomplete(self):
        """Handle not-success termination: offer Yes/No/Cancel."""
        if not self.edge_points_img:
            # nothing to do
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
            # Save as is, closing last link to the first point
            self._finalize_edge(success=True, close_to_index=0)
        elif resp == QMessageBox.No:
            # Erase and cancel
            self._edge_abort(erase=True)
        else:
            # Cancel -> continue drawing
            # nothing changes
            return
        
    def _finalize_edge(self, success: bool, close_to_index: int | None):
        """
        Success finalize: close the shape to the given point index (usually 0 or a hit index),
        save to the model, and end the session by replacing temp visuals with a permanent icon overlay.
        """
        if not success:
            self._edge_abort(erase=True)
            self.empire_border = False
            return
    
        if not self.edge_points_img or len(self.edge_points_img) < 2:
            self._edge_abort(erase=True)
            self.empire_border = False
            return
    
        # Work on a copy so we can rotate safely
        pts = list(self.edge_points_img)
    
        # If we know which vertex we clicked to close, draw the closing segment visually
        if close_to_index is not None and self.bg_item is not None:
            x_last, y_last = pts[-1]
            x_close, y_close = pts[close_to_index]
            p_last = self.bg_item.mapToScene(x_last, y_last)
            p_close = self.bg_item.mapToScene(x_close, y_close)
            close_item = self.scene.addLine(p_last.x(), p_last.y(), p_close.x(), p_close.y(), QPen(Qt.red, 2))
            close_item.setZValue(80)
            self.edge_line_items.append(close_item)
    
            # Rotate so the first vertex becomes the clicked/closed one (canonical order)
            if close_to_index != 0:
                pts = pts[close_to_index:] + pts[:close_to_index]
    
        # Clean consecutive duplicates (defensive)
        cleaned = []
        for x, y in pts:
            if not cleaned or cleaned[-1] != (x, y):
                cleaned.append((x, y))
    
        # 1) Save to model with default density=28
        self._save_border_shape(cleaned, density=28)
    
        # 2) Erase temporary red dots/lines and stop drawing mode
        self._edge_abort(erase=True)
    
        # 3) Mark border present and render the permanent overlay
        self.empire_border = True
        self.render_empire_border()
    


    def _edge_abort(self, erase: bool):
        """Stop the drawing session. If erase is True, remove items from the scene."""
        # Remove rubber-band
        if self.edge_temp_line_item is not None:
            self.scene.removeItem(self.edge_temp_line_item)
            self.edge_temp_line_item = None
    
        if erase:
            # Remove all visual items
            for it in self.edge_line_items:
                self.scene.removeItem(it)
            for it in self.edge_point_items:
                self.scene.removeItem(it)
    
        # Reset state
        self.edge_line_items.clear()
        self.edge_point_items.clear()
        self.edge_points_img = []
        self.edge_drawing_active = False
        # clear the drawing cursor
        self._apply_drawing_cursor(False)
        self.edge_cursor_pixmap = None
    
    def _edge_clear_scene_items(self):
        """Utility to clear any leftover edge items (without touching state flags)."""
        if self.edge_temp_line_item is not None:
            self.scene.removeItem(self.edge_temp_line_item)
            self.edge_temp_line_item = None
        for it in self.edge_line_items:
            self.scene.removeItem(it)
        for it in self.edge_point_items:
            self.scene.removeItem(it)
        self.edge_line_items.clear()
        self.edge_point_items.clear()
        
    def _save_border_shape(self, points_img_xy, density: int = 28):
        """
        Persist the border polyline to the model as ed.Border with ed.Edge entries.
        The polyline is understood as closed (last segment to first).
        """
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
    
    def _get_empire_edge_pixmap(self) -> QPixmap:
        """
        Return the Empire Edge icon pixmap at its ORIGINAL size (no scaling).
        """
        for el in getattr(self.state, "elements", []):
            # find the empire-edge entry
            try:
                if el["kind"].name == "EMPIRE_EDGE":
                    # convert PIL -> QPixmap WITHOUT scaling
                    pm = self.pil_to_qpixmap(el["pil"])
                    # (optional) make sure DPR doesn’t inflate it on HiDPI
                    pm.setDevicePixelRatio(1.0)
                    return pm
            except Exception:
                pass
        # fallback transparent 1×1 to avoid crashes
        fallback = QPixmap(1, 1)
        fallback.fill(Qt.transparent)
        return fallback

    def toggle_selected_edge_hidden(self): #toggles selected edge
        e = self.state.current_empire_object
        i = self.selected_edge_index
        if not (e and getattr(e, "border", None)) or i is None:
            return
        edges = e.border.edges
        if 0 <= i < len(edges):
            edges[i].hidden = not bool(getattr(edges[i], "hidden", False))
            self.render_empire_border()
            
    def toggle_edge_hidden_from_item(self, item): #from item reference
        e = self.state.current_empire_object
        if not (e and getattr(e, "border", None)):
            return
        i = item.data(Qt.UserRole + 1)
        if i is None:
            return
        edges = e.border.edges
        if 0 <= i < len(edges):
            edges[i].hidden = not bool(getattr(edges[i], "hidden", False))
            self.render_empire_border()

             
            
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
    
        # helpers
        def place_flag_icon(x_img: int, y_img: int):
            pos_scene = self.bg_item.mapToScene(x_img, y_img)
            it = PaddedHitPixmapItem(icon_pm, hitpad=6)
            it.setOffset(-icon_pm.width() / 2, -icon_pm.height() / 2)
            it.setPos(pos_scene)
            it.setZValue(75)
            it.setFlag(QGraphicsPixmapItem.ItemIsSelectable, False)
            it.setAcceptHoverEvents(False)
            it.setCursor(Qt.ArrowCursor)
            # tags (optional): treat as border visuals
            it.setData(Qt.UserRole, EmpObjTypes.EMPIRE_EDGE)
            self.border_visual_group.addToGroup(it)
            self.border_icon_items.append(it)
    
        def place_blue_vertex(i: int):
            p = self.bg_item.mapToScene(pts[i][0], pts[i][1])
            r = 5.0
            dot = self.scene.addEllipse(p.x()-r, p.y()-r, 2*r, 2*r,
                                        QPen(Qt.NoPen), QBrush(Qt.blue))
            dot.setZValue(85)
            self.border_visual_group.addToGroup(dot)
    
        n = len(pts)
    
        # build a selectable, thick, invisible line for EACH segment i -> j
        for i in range(n):
            j = (i + 1) % n
    
            p0 = self.bg_item.mapToScene(pts[i][0], pts[i][1])
            p1 = self.bg_item.mapToScene(pts[j][0], pts[j][1])
    
            hit = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
            hit.setPen(QPen(Qt.transparent, 12))  # fat invisible hit area
            hit.setZValue(76)
            hit.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hit.setData(Qt.UserRole, EmpObjTypes.EMPIRE_EDGE)   # same menu bucket
            hit.setData(Qt.UserRole + 1, i)                     # edge index i
            self.border_visual_group.addToGroup(hit)
            self.border_edge_hit_items.append(hit)
    
            # show blue dot at START vertex of any hidden edge
            if hidden[i]:
                place_blue_vertex(i)
                continue  # skip flag stamping on this segment
    
            # stamp flags along visible segment i -> j
            dx = pts[j][0] - pts[i][0]
            dy = pts[j][1] - pts[i][1]
            seg_len = (dx*dx + dy*dy) ** 0.5
            if seg_len <= 1e-6:
                continue
            ux, uy = dx/seg_len, dy/seg_len
    
            # optionally place one at the start
            place_flag_icon(pts[i][0], pts[i][1])
    
            dist = density
            while dist <= seg_len + 1e-6:
                sx = pts[i][0] + ux * dist
                sy = pts[i][1] + uy * dist
                place_flag_icon(int(round(sx)), int(round(sy)))
                dist += density

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
        size = self.ui.listWidget.iconSize()
    
        # 0) If we have a pending drop pixmap, use it EXACTLY
        pm = getattr(self, "pending_drop_pixmap", None)
        if pm is not None and not pm.isNull():
            return pm
    
        # 1) Otherwise, try the currently selected item (if any)
        if self.selected_item is not None:
            try:
                return self.selected_item.icon().pixmap(size)
            except Exception:
                pass

        # 2) Fallback by city.type -> EmpCityTypes kind
        kind = None
        ct = getattr(city, "type", None)
        try:
            if ct == ed.CityType.OURS:
                kind = EmpCityTypes.OUR
            elif hasattr(ed.CityType, "TRADE") and ct == ed.CityType.TRADE:
                kind = EmpCityTypes.TRADE
            elif hasattr(ed.CityType, "DISTANT") and ct == ed.CityType.DISTANT:
                kind = EmpCityTypes.DISTANT
        except Exception:
            kind = None

        # Find matching element
        if kind is None and self.state.elements:
            # last resort: default to first element ("Our City")
            kind = EmpCityTypes.OUR

        for el in getattr(self.state, "elements", []):
            if el["kind"] == kind:
                pm = self.pil_to_qpixmap(el["pil"])
                # scale to icon size similar to QListWidget’s icon rendering
                return pm.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Ultimate fallback: empty pixmap of icon size (avoids crashes)
        fallback = QPixmap(size)
        fallback.fill(Qt.transparent)
        return fallback

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

        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()
        if self.empire_border and getattr(self.state.current_empire_object, "border", None):
            self.render_empire_border()
    def set_cursor_to_icon(self, pixmap):
        """
        Set the cursor to the custom icon on *all* relevant widgets so the
        viewport can't revert it to Arrow while dragging.
        """
        cursor = QCursor(pixmap, 0, 0)  # hotspot at (0,0)
    
        # Apply to the main window, view, and the viewport
        self.setCursor(cursor)
        self.ui.graphicsView.setCursor(cursor)
        self.ui.graphicsView.viewport().setCursor(cursor)
        
    def _apply_drawing_cursor(self, enable: bool):
        """Show/hide the 'drawing mode' cursor across main, view, and viewport."""
        if enable and self.edge_cursor_pixmap is not None:
            cursor = QCursor(self.edge_cursor_pixmap, 0, 0)
            self.setCursor(cursor)
            self.ui.graphicsView.setCursor(cursor)
            self.ui.graphicsView.viewport().setCursor(cursor)
        else:
            for w in (self, self.ui.graphicsView, self.ui.graphicsView.viewport()):
                try:
                    w.unsetCursor()
                except Exception:
                    pass

    def reset_cursor(self):
        """
        Reset cursors back to default on all widgets touched above.
        Use unsetCursor() so they inherit normally again.
        """
        for w in (self, self.ui.graphicsView, self.ui.graphicsView.viewport()):
            try:
                w.unsetCursor()
            except Exception:
                pass

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
            QMessageBox.warning(self, "No background", "Drop onto the background image area.", QMessageBox.Ok)
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
    def delete_empire_border(self, force = False):
        resp = QMessageBox.question(
            self,
            "Remove border?",
            "Would you like to remove current empire border?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        self.clear_empire_border_visual()
        self.state.current_empire_object.border = None
        self.empire_border = False
        self.clear_border_selection_overlay() 
        
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
            QMessageBox.warning(self, "No background", "Drop onto the background image area.", QMessageBox.Ok)
            return
        x, y = xy
    
        if not self.state.check_if_empire():
            self.state.new_empire()
    
        # Keep the same drawing cursor as during drag
        self.edge_cursor_pixmap = getattr(self, "pending_drop_pixmap", None) or getattr(self, "drag_pixmap", None)
        # if you use global overrides here, call your helper; otherwise skip
        self._apply_drawing_cursor(True)
        self._begin_edge_drawing(x, y)




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
